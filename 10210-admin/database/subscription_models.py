"""
Subscription and Payment Models for Cuwhapp
Plans: Free ($0), Starter ($7), Hobby ($20), Pro ($45), Premium ($99)
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, JSON, Enum
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import enum
from .connection import Base

class SubscriptionStatus(enum.Enum):
    """Subscription status enum"""
    TRIAL = "trial"
    ACTIVE = "active"
    GRACE_PERIOD = "grace_period"  # 7 days after expiry
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"

class PlanType(enum.Enum):
    """Available subscription plans"""
    FREE = "free"          # $0
    STARTER = "starter"    # $7
    HOBBY = "hobby"        # $20
    PRO = "pro"           # $45
    PREMIUM = "premium"    # $99
    ADMIN = "admin"        # Internal use - unlimited everything

class PaymentStatus(enum.Enum):
    """Payment status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"

class UserSubscription(Base):
    """User subscription model"""
    __tablename__ = "user_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)  # From Clerk auth
    email = Column(String, index=True)
    username = Column(String, index=True)
    
    # Plan details
    plan_type = Column(Enum(PlanType), default=PlanType.FREE)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.TRIAL)
    
    # Subscription dates
    trial_ends_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=14))
    current_period_start = Column(DateTime, default=func.now())
    current_period_end = Column(DateTime)
    grace_period_end = Column(DateTime)  # 7 days after expiry
    
    # Payment integration
    hyperswitch_customer_id = Column(String)
    hyperswitch_subscription_id = Column(String)
    payment_method = Column(String)  # stripe, paypal, paystack, crypto
    last_payment_date = Column(DateTime)
    next_billing_date = Column(DateTime)
    
    # Resource limits based on plan
    max_sessions = Column(Integer, default=1)
    max_messages_per_month = Column(Integer, default=100)
    max_contacts_export = Column(Integer, default=100)  # Contact/group export limit
    max_campaigns = Column(Integer, default=1)
    warmer_duration_hours = Column(Integer, default=0)  # 0 means not available
    
    # Usage tracking
    current_sessions = Column(Integer, default=0)
    messages_sent_this_month = Column(Integer, default=0)
    contacts_exported_this_month = Column(Integer, default=0)
    total_campaigns = Column(Integer, default=0)
    messages_reset_date = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def is_within_limits(self, resource_type: str) -> bool:
        """Check if user is within plan limits"""
        if self.status == SubscriptionStatus.SUSPENDED:
            return False
        
        # Check if monthly counters need reset
        if self.messages_reset_date and datetime.utcnow() > self.messages_reset_date:
            self.messages_sent_this_month = 0
            self.contacts_exported_this_month = 0
            self.messages_reset_date = datetime.utcnow() + timedelta(days=30)
            
        if resource_type == "sessions":
            return self.current_sessions < self.max_sessions
        elif resource_type == "messages":
            return self.max_messages_per_month == -1 or self.messages_sent_this_month < self.max_messages_per_month
        elif resource_type == "contacts_export":
            return self.max_contacts_export == -1 or self.contacts_exported_this_month < self.max_contacts_export
        elif resource_type == "campaigns":
            return self.max_campaigns == -1 or self.total_campaigns < self.max_campaigns
        elif resource_type == "warmer":
            return self.warmer_duration_hours > 0
        return True
    
    def enter_grace_period(self):
        """Enter 7-day grace period after subscription expires"""
        self.status = SubscriptionStatus.GRACE_PERIOD
        self.grace_period_end = datetime.utcnow() + timedelta(days=7)
        # Restrict to free tier limits during grace period
        self.max_sessions = 1
        self.max_messages_per_month = 100
        self.max_contacts_export = 100
        self.max_campaigns = 1
        self.warmer_duration_hours = 0  # No warmer access during grace period
    
    def check_and_update_status(self):
        """Check subscription status and update if needed"""
        now = datetime.utcnow()
        
        # Check if trial ended
        if self.status == SubscriptionStatus.TRIAL and self.trial_ends_at < now:
            if self.plan_type == PlanType.FREE:
                self.status = SubscriptionStatus.ACTIVE
            else:
                self.enter_grace_period()
        
        # Check if subscription expired
        elif self.status == SubscriptionStatus.ACTIVE and self.current_period_end and self.current_period_end < now:
            self.enter_grace_period()
        
        # Check if grace period ended
        elif self.status == SubscriptionStatus.GRACE_PERIOD and self.grace_period_end < now:
            self.status = SubscriptionStatus.SUSPENDED
            # Suspend all features
            self.max_sessions = 0
            self.max_messages_per_day = 0
            self.max_contacts = 0
            self.max_campaigns = 0
        
        return self.status
    
    def update_plan(self, new_plan: PlanType):
        """Update user's subscription plan"""
        self.plan_type = new_plan
        
        # Update limits based on plan
        # Format: (sessions, messages/month, contacts_export, campaigns, warmer_hours)
        plan_limits = {
            PlanType.FREE: (1, 100, 100, -1, 0),         # No warmer - only 1 session
            PlanType.STARTER: (1, 1000, -1, -1, 0),      # No warmer - only 1 session
            PlanType.HOBBY: (3, 10000, -1, -1, 24),     # Warmer enabled - 3 sessions
            PlanType.PRO: (10, 30000, -1, -1, 96),      # Warmer enabled - 10 sessions
            PlanType.PREMIUM: (30, -1, -1, -1, 360),    # Warmer enabled - 30 sessions
            PlanType.ADMIN: (-1, -1, -1, -1, -1)        # Unlimited everything
        }
        
        limits = plan_limits.get(new_plan, (1, 100, 100, 1, 0))
        self.max_sessions = limits[0]
        self.max_messages_per_month = limits[1]
        self.max_contacts_export = limits[2]
        self.max_campaigns = limits[3]
        self.warmer_duration_hours = limits[4]

class Payment(Base):
    """Payment transaction model"""
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    subscription_id = Column(Integer, index=True)
    
    # Payment details
    amount = Column(Float)
    currency = Column(String, default="USD")
    payment_method = Column(String)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Hyperswitch integration
    hyperswitch_payment_id = Column(String, unique=True, index=True)
    hyperswitch_intent_id = Column(String)
    hyperswitch_redirect_url = Column(String)
    
    # Transaction details
    description = Column(String)
    payment_metadata = Column(JSON)
    failure_reason = Column(String)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime)

class WebhookEvent(Base):
    """Webhook events from payment providers"""
    __tablename__ = "webhook_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True)
    provider = Column(String)  # hyperswitch, stripe, paypal, etc.
    event_type = Column(String)  # payment.succeeded, subscription.updated, etc.
    
    # Event data
    payload = Column(JSON)
    processed = Column(Boolean, default=False)
    error_message = Column(String)
    
    # Timestamps
    received_at = Column(DateTime, default=func.now())
    processed_at = Column(DateTime)

class UsageLog(Base):
    """Track resource usage for billing"""
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    resource_type = Column(String)  # sessions, messages, contacts, campaigns
    action = Column(String)  # create, send, add, etc.
    quantity = Column(Integer, default=1)
    usage_metadata = Column(JSON)
    timestamp = Column(DateTime, default=func.now())