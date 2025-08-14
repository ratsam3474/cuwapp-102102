"""
User management API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta
from database.connection import get_db
from database.subscription_models import UserSubscription, PlanType, SubscriptionStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])

class UserSyncRequest(BaseModel):
    user_id: str
    email: EmailStr
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class UserSubscriptionResponse(BaseModel):
    user_id: str
    email: str
    plan_type: str
    status: str
    messages_used: int
    messages_limit: int
    contacts_exported: int
    contacts_limit: int
    campaigns_created: int
    campaigns_limit: int
    sessions_limit: int
    current_sessions: int = 0
    warmer_hours: Optional[float] = None
    warmer_hours_used: float = 0
    current_period_end: Optional[datetime] = None
    grace_period_end: Optional[datetime] = None

def verify_token(authorization: Optional[str] = Header(None)):
    """Verify the authorization token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    # In production, verify the Clerk token here
    return authorization.replace("Bearer ", "")

@router.post("/sync")
async def sync_user(request: UserSyncRequest, token: str = Depends(verify_token)):
    """Sync user data from Clerk and create/update subscription"""
    try:
        with get_db() as db:
            # Check if user subscription exists
            subscription = db.query(UserSubscription).filter(
                UserSubscription.user_id == request.user_id
            ).first()
            
            if not subscription:
                # Create new free subscription
                subscription = UserSubscription(
                    user_id=request.user_id,
                    email=request.email,
                    username=request.name or request.email.split('@')[0],
                    plan_type=PlanType.FREE,
                    status=SubscriptionStatus.ACTIVE,
                    current_period_start=datetime.utcnow(),
                    current_period_end=datetime.utcnow() + timedelta(days=30),
                    # Free plan limits
                    max_sessions=1,
                    max_messages_per_month=100,
                    max_contacts_export=100,
                    max_campaigns=1,
                    warmer_duration_hours=None
                )
                db.add(subscription)
                db.commit()
                db.refresh(subscription)
                logger.info(f"Created new free subscription for user {request.user_id}")
            else:
                # Update email if changed
                if subscription.email != request.email:
                    subscription.email = request.email
                    db.commit()
                    logger.info(f"Updated email for user {request.user_id}")
            
            # Get current active sessions count for the user from database (same as analytics)
            from database.user_sessions import UserWhatsAppSession
            user_sessions = db.query(UserWhatsAppSession).filter(
                UserWhatsAppSession.user_id == subscription.user_id
            ).all()
            current_sessions_count = len(user_sessions)
            
            # Get actual message count from UserMetrics (same as analytics dashboard)
            from database.user_metrics import UserMetrics
            user_metrics = UserMetrics.get_or_create(db, subscription.user_id)
            
            # Calculate warmer hours used this month
            warmer_hours_used = 0
            try:
                from warmer.warmer_engine import warmer_engine
                warmers = warmer_engine.get_all_warmers()
                # Count warmer hours for this user's warmers
                for warmer_id, warmer_info in warmers.items():
                    if warmer_info.get('user_id') == subscription.user_id:
                        # Each warmer session counts as hours used based on its duration
                        warmer_hours_used += warmer_info.get('hours_used_this_month', 0)
            except:
                warmer_hours_used = 0
            
            return UserSubscriptionResponse(
                user_id=subscription.user_id,
                email=subscription.email,
                plan_type=subscription.plan_type.value,
                status=subscription.status.value,
                messages_used=user_metrics.total_messages_sent,  # Use UserMetrics like analytics does
                messages_limit=subscription.max_messages_per_month,
                contacts_exported=subscription.contacts_exported_this_month,
                contacts_limit=subscription.max_contacts_export,
                campaigns_created=user_metrics.total_campaigns_created,  # Use UserMetrics like analytics does
                campaigns_limit=subscription.max_campaigns,
                sessions_limit=subscription.max_sessions,
                current_sessions=current_sessions_count,
                warmer_hours=subscription.warmer_duration_hours,
                warmer_hours_used=warmer_hours_used,
                current_period_end=subscription.current_period_end,
                grace_period_end=subscription.grace_period_end
            )
            
    except Exception as e:
        logger.error(f"Error syncing user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/subscription/{user_id}")
async def get_user_subscription(user_id: str, token: str = Depends(verify_token)):
    """Get user subscription details"""
    try:
        with get_db() as db:
            subscription = db.query(UserSubscription).filter(
                UserSubscription.user_id == user_id
            ).first()
            
            if not subscription:
                raise HTTPException(status_code=404, detail="Subscription not found")
            
            # Check if subscription needs renewal
            if subscription.current_period_end and subscription.current_period_end < datetime.utcnow():
                # Reset monthly counters
                subscription.reset_monthly_usage()
                subscription.current_period_start = datetime.utcnow()
                subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
                db.commit()
            
            # Get current active sessions count for the user from database (same as analytics)
            from database.user_sessions import UserWhatsAppSession
            user_sessions = db.query(UserWhatsAppSession).filter(
                UserWhatsAppSession.user_id == subscription.user_id
            ).all()
            current_sessions_count = len(user_sessions)
            
            # Get actual message count from UserMetrics (same as analytics dashboard)
            from database.user_metrics import UserMetrics
            user_metrics = UserMetrics.get_or_create(db, subscription.user_id)
            
            # Calculate warmer hours used this month
            warmer_hours_used = 0
            try:
                from warmer.warmer_engine import warmer_engine
                warmers = warmer_engine.get_all_warmers()
                # Count warmer hours for this user's warmers
                for warmer_id, warmer_info in warmers.items():
                    if warmer_info.get('user_id') == subscription.user_id:
                        # Each warmer session counts as hours used based on its duration
                        warmer_hours_used += warmer_info.get('hours_used_this_month', 0)
            except:
                warmer_hours_used = 0
            
            return UserSubscriptionResponse(
                user_id=subscription.user_id,
                email=subscription.email,
                plan_type=subscription.plan_type.value,
                status=subscription.status.value,
                messages_used=user_metrics.total_messages_sent,  # Use UserMetrics like analytics does
                messages_limit=subscription.max_messages_per_month,
                contacts_exported=subscription.contacts_exported_this_month,
                contacts_limit=subscription.max_contacts_export,
                campaigns_created=user_metrics.total_campaigns_created,  # Use UserMetrics like analytics does
                campaigns_limit=subscription.max_campaigns,
                sessions_limit=subscription.max_sessions,
                current_sessions=current_sessions_count,
                warmer_hours=subscription.warmer_duration_hours,
                warmer_hours_used=warmer_hours_used,
                current_period_end=subscription.current_period_end,
                grace_period_end=subscription.grace_period_end
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/check-limit/{user_id}")
async def check_resource_limit(
    user_id: str, 
    resource: str,
    quantity: int = 1,
    token: str = Depends(verify_token)
):
    """Check if user can use a resource based on their subscription limits"""
    try:
        with get_db() as db:
            subscription = db.query(UserSubscription).filter(
                UserSubscription.user_id == user_id
            ).first()
            
            if not subscription:
                raise HTTPException(status_code=404, detail="Subscription not found")
            
            if subscription.status != SubscriptionStatus.ACTIVE:
                return {
                    "allowed": False,
                    "reason": f"Subscription is {subscription.status.value}"
                }
            
            # Check resource limits
            if resource == "messages":
                if subscription.max_messages_per_month == -1:  # Unlimited
                    return {"allowed": True}
                remaining = subscription.max_messages_per_month - subscription.messages_used
                allowed = remaining >= quantity
                return {
                    "allowed": allowed,
                    "remaining": max(0, remaining),
                    "limit": subscription.max_messages_per_month
                }
                
            elif resource == "contacts":
                if subscription.max_contacts_export == -1:  # Unlimited
                    return {"allowed": True}
                remaining = subscription.max_contacts_export - subscription.contacts_exported
                allowed = remaining >= quantity
                return {
                    "allowed": allowed,
                    "remaining": max(0, remaining),
                    "limit": subscription.max_contacts_export
                }
                
            elif resource == "campaigns":
                if subscription.max_campaigns == -1:  # Unlimited
                    return {"allowed": True}
                remaining = subscription.max_campaigns - subscription.campaigns_created
                allowed = remaining >= quantity
                return {
                    "allowed": allowed,
                    "remaining": max(0, remaining),
                    "limit": subscription.max_campaigns
                }
                
            elif resource == "sessions":
                # Sessions don't have usage tracking, just a limit
                return {
                    "allowed": True,
                    "limit": subscription.max_sessions
                }
                
            else:
                raise HTTPException(status_code=400, detail="Invalid resource type")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking resource limit: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/track-usage/{user_id}")
async def track_resource_usage(
    user_id: str,
    resource: str,
    quantity: int = 1,
    token: str = Depends(verify_token)
):
    """Track resource usage for a user"""
    try:
        with get_db() as db:
            subscription = db.query(UserSubscription).filter(
                UserSubscription.user_id == user_id
            ).first()
            
            if not subscription:
                raise HTTPException(status_code=404, detail="Subscription not found")
            
            # Update usage counters
            if resource == "messages":
                subscription.messages_sent_this_month += quantity
            elif resource == "contacts":
                subscription.contacts_exported_this_month += quantity
            elif resource == "campaigns":
                subscription.total_campaigns += quantity
            else:
                raise HTTPException(status_code=400, detail="Invalid resource type")
            
            db.commit()
            
            return {
                "success": True,
                "resource": resource,
                "quantity": quantity,
                "new_total": getattr(subscription, f"{resource}_used" if resource == "messages" else f"{resource}_exported" if resource == "contacts" else f"{resource}_created")
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking usage: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
class PaymentSuccessRequest(BaseModel):
    payment_id: str
    user_id: str
    plan_type: str
    amount: Optional[int] = None

@router.post("/payment-success")
async def handle_payment_success(request: PaymentSuccessRequest):
    """Handle successful payment and update subscription"""
    try:
        logger.info(f"Processing payment success for user {request.user_id}, plan {request.plan_type}")
        
        # In sandbox/test mode, skip Hyperswitch verification
        from payments.config import PaymentConfig
        import os
        
        # Check if in test mode
        test_mode = os.getenv("PAYMENT_TEST_MODE", "false").lower() == "true"
        
        if test_mode or request.payment_id.startswith("test_"):
            logger.info("Test mode: Skipping payment verification")
            payment_verified = True
        else:
            # Verify payment status with Hyperswitch
            import requests
            
            headers = {
                "Content-Type": "application/json",
                "api-key": PaymentConfig.HYPERSWITCH_API_KEY
            }
            
            # Get payment status from Hyperswitch
            try:
                response = requests.get(
                    f"{PaymentConfig.HYPERSWITCH_BASE_URL}/payments/{request.payment_id}",
                    headers=headers,
                    timeout=10
                )
                
                if response.ok:
                    payment_data = response.json()
                    payment_status = payment_data.get("status")
                    # In sandbox, also accept requires_payment_method as valid for testing
                    valid_statuses = ["succeeded", "processing", "requires_capture", "requires_payment_method"]
                    payment_verified = payment_status in valid_statuses
                    logger.info(f"Payment verification result: {payment_status} (verified: {payment_verified})")
                    
                    # For sandbox testing, be more lenient
                    if not payment_verified and "sandbox" in PaymentConfig.HYPERSWITCH_BASE_URL:
                        logger.info("Sandbox mode: Accepting payment for testing")
                        payment_verified = True
                else:
                    logger.warning(f"Payment verification failed: {response.status_code}")
                    # In sandbox, still proceed
                    if "sandbox" in PaymentConfig.HYPERSWITCH_BASE_URL:
                        logger.info("Sandbox mode: Proceeding despite verification failure")
                        payment_verified = True
                    else:
                        payment_verified = False
            except Exception as e:
                logger.error(f"Error verifying payment: {e}")
                # In case of API error, proceed with update but log warning
                payment_verified = True
                logger.warning("Proceeding with subscription update despite verification error")
        
        if payment_verified:
            # Update user subscription in database
            with get_db() as db:
                    subscription = db.query(UserSubscription).filter(
                        UserSubscription.user_id == request.user_id
                    ).first()
                    
                    if not subscription:
                        # Create new subscription if doesn't exist
                        logger.info(f"Creating new subscription for user {request.user_id}")
                        subscription = UserSubscription(
                            user_id=request.user_id,
                            email=request.user_id,  # Will be updated on next sync
                            plan_type=PlanType(request.plan_type),
                            status=SubscriptionStatus.ACTIVE
                        )
                        db.add(subscription)
                        db.flush()  # Get the ID without committing
                    
                    # Update subscription
                    old_plan = subscription.plan_type
                    subscription.plan_type = PlanType(request.plan_type)
                    subscription.status = SubscriptionStatus.ACTIVE
                    subscription.updated_at = datetime.utcnow()
                    
                    # Update limits based on plan
                    plan_config = PaymentConfig.SUBSCRIPTION_PLANS.get(request.plan_type, {})
                    features = plan_config.get("features", {})
                    
                    subscription.max_sessions = features.get("sessions", 1)
                    subscription.max_messages_per_month = features.get("messages_per_month", 100)
                    subscription.max_contacts_export = features.get("contacts_export", 100)
                    subscription.max_campaigns = features.get("campaigns", 1)
                    subscription.warmer_duration_hours = features.get("warmer_duration", 0)
                    
                    # Reset usage for new period
                    subscription.messages_sent_this_month = 0
                    subscription.contacts_exported_this_month = 0
                    
                    # Set billing period
                    subscription.current_period_start = datetime.utcnow()
                    subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
                    subscription.last_payment_date = datetime.utcnow()
                    subscription.next_billing_date = datetime.utcnow() + timedelta(days=30)
                    
                    db.commit()
                    
                    logger.info(f"Successfully updated user {request.user_id} from {old_plan.value if old_plan else 'new'} to {request.plan_type}")
                    
                    return {
                        "success": True,
                        "message": f"Successfully upgraded to {request.plan_type} plan",
                        "subscription": {
                            "plan_type": request.plan_type,
                            "status": "active",
                            "features": features
                        }
                    }
        else:
            return {
                "success": False,
                "message": "Payment verification failed"
            }
            
    except Exception as e:
        logger.error(f"Error handling payment success: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))