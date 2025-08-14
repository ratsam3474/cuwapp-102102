"""
Webhook handler for payment events from Hyperswitch
Handles subscription updates, grace periods, and account restrictions
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from database.subscription_models import UserSubscription, Payment, WebhookEvent, PaymentStatus, SubscriptionStatus, PlanType
from database.connection import get_db
from payments.config import PaymentConfig

logger = logging.getLogger(__name__)

class WebhookHandler:
    """Handle payment webhooks from Hyperswitch"""
    
    def process_webhook(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming webhook event"""
        try:
            # Log the webhook event
            with get_db() as db:
                webhook_event = WebhookEvent(
                    event_id=event_data.get("id"),
                    provider="hyperswitch",
                    event_type=event_data.get("type"),
                    payload=event_data,
                    received_at=datetime.utcnow()
                )
                db.add(webhook_event)
                db.commit()
                
                # Process based on event type
                event_type = event_data.get("type")
                
                if event_type == "payment.succeeded":
                    return self.handle_payment_success(db, event_data)
                elif event_type == "payment.failed":
                    return self.handle_payment_failed(db, event_data)
                elif event_type == "subscription.created":
                    return self.handle_subscription_created(db, event_data)
                elif event_type == "subscription.updated":
                    return self.handle_subscription_updated(db, event_data)
                elif event_type == "subscription.cancelled":
                    return self.handle_subscription_cancelled(db, event_data)
                elif event_type == "subscription.expired":
                    return self.handle_subscription_expired(db, event_data)
                else:
                    logger.info(f"Unhandled webhook event type: {event_type}")
                    
                # Mark webhook as processed
                webhook_event.processed = True
                webhook_event.processed_at = datetime.utcnow()
                db.commit()
                
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            raise
    
    def handle_payment_success(self, db, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful payment"""
        payment_data = event_data.get("data", {})
        customer_email = payment_data.get("email")
        metadata = payment_data.get("metadata", {})
        plan_id = metadata.get("plan_id")
        user_id = metadata.get("user_id")
        
        # Find or create user subscription
        subscription = db.query(UserSubscription).filter_by(user_id=user_id).first()
        if not subscription:
            subscription = UserSubscription(
                user_id=user_id,
                email=customer_email,
                plan_type=PlanType(plan_id) if plan_id else PlanType.FREE
            )
            db.add(subscription)
        
        # Update subscription based on plan
        if plan_id:
            subscription.update_plan(PlanType(plan_id))
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.current_period_start = datetime.utcnow()
            subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
            subscription.last_payment_date = datetime.utcnow()
            subscription.next_billing_date = datetime.utcnow() + timedelta(days=30)
            subscription.hyperswitch_customer_id = payment_data.get("customer_id")
            subscription.payment_method = payment_data.get("payment_method", {}).get("type")
        
        # Record payment
        payment = Payment(
            user_id=user_id,
            subscription_id=subscription.id,
            amount=payment_data.get("amount") / 100,  # Convert from cents
            currency=payment_data.get("currency"),
            payment_method=payment_data.get("payment_method", {}).get("type"),
            status=PaymentStatus.SUCCEEDED,
            hyperswitch_payment_id=payment_data.get("payment_id"),
            completed_at=datetime.utcnow()
        )
        db.add(payment)
        db.commit()
        
        logger.info(f"Payment successful for user {user_id}, upgraded to {plan_id}")
        return {"status": "success", "message": "Payment processed successfully"}
    
    def handle_payment_failed(self, db, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed payment"""
        payment_data = event_data.get("data", {})
        metadata = payment_data.get("metadata", {})
        user_id = metadata.get("user_id")
        
        # Record failed payment
        payment = Payment(
            user_id=user_id,
            amount=payment_data.get("amount") / 100,
            currency=payment_data.get("currency"),
            payment_method=payment_data.get("payment_method", {}).get("type"),
            status=PaymentStatus.FAILED,
            hyperswitch_payment_id=payment_data.get("payment_id"),
            failure_reason=payment_data.get("error_message"),
            completed_at=datetime.utcnow()
        )
        db.add(payment)
        
        # Check if subscription should enter grace period
        subscription = db.query(UserSubscription).filter_by(user_id=user_id).first()
        if subscription and subscription.status == SubscriptionStatus.ACTIVE:
            # Check if this is a renewal failure
            if subscription.next_billing_date and subscription.next_billing_date <= datetime.utcnow():
                subscription.enter_grace_period()
                logger.warning(f"User {user_id} entered grace period due to payment failure")
        
        db.commit()
        return {"status": "failed", "message": "Payment failed, grace period activated"}
    
    def handle_subscription_expired(self, db, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription expiration - activate 7-day grace period"""
        subscription_data = event_data.get("data", {})
        user_id = subscription_data.get("metadata", {}).get("user_id")
        
        subscription = db.query(UserSubscription).filter_by(user_id=user_id).first()
        if subscription:
            subscription.enter_grace_period()
            db.commit()
            logger.info(f"User {user_id} subscription expired, 7-day grace period activated")
            
            # TODO: Send email notification about grace period
            
        return {"status": "grace_period", "message": "7-day grace period activated"}
    
    def handle_subscription_cancelled(self, db, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription cancellation"""
        subscription_data = event_data.get("data", {})
        user_id = subscription_data.get("metadata", {}).get("user_id")
        
        subscription = db.query(UserSubscription).filter_by(user_id=user_id).first()
        if subscription:
            subscription.status = SubscriptionStatus.CANCELLED
            # Downgrade to free plan
            subscription.update_plan(PlanType.FREE)
            db.commit()
            logger.info(f"User {user_id} subscription cancelled, downgraded to free")
            
        return {"status": "cancelled", "message": "Subscription cancelled"}
    
    def handle_subscription_created(self, db, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle new subscription creation"""
        subscription_data = event_data.get("data", {})
        metadata = subscription_data.get("metadata", {})
        user_id = metadata.get("user_id")
        plan_id = metadata.get("plan_id")
        
        subscription = db.query(UserSubscription).filter_by(user_id=user_id).first()
        if subscription:
            subscription.hyperswitch_subscription_id = subscription_data.get("subscription_id")
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.update_plan(PlanType(plan_id))
            db.commit()
            
        return {"status": "created", "message": "Subscription created"}
    
    def handle_subscription_updated(self, db, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription update (upgrade/downgrade)"""
        subscription_data = event_data.get("data", {})
        metadata = subscription_data.get("metadata", {})
        user_id = metadata.get("user_id")
        new_plan_id = metadata.get("plan_id")
        
        subscription = db.query(UserSubscription).filter_by(user_id=user_id).first()
        if subscription:
            old_plan = subscription.plan_type
            subscription.update_plan(PlanType(new_plan_id))
            subscription.status = SubscriptionStatus.ACTIVE
            db.commit()
            logger.info(f"User {user_id} subscription updated from {old_plan} to {new_plan_id}")
            
        return {"status": "updated", "message": "Subscription updated"}

# Singleton instance
webhook_handler = WebhookHandler()