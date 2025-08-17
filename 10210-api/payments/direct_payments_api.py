"""
Direct Payment API - Stripe and Cryptomus
Bypasses Hyperswitch for direct integration
"""

from fastapi import APIRouter, HTTPException, Request, Form
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import logging
import uuid
import os
import json
from datetime import datetime, timedelta
from .stripe_direct import StripeDirectClient
from .cryptomus_client import CryptomusClient
from .config import PaymentConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/direct-payments", tags=["direct-payments"])

# Initialize payment clients
stripe_client = StripeDirectClient()
cryptomus_client = CryptomusClient()

class CreateCheckoutRequest(BaseModel):
    plan_id: str
    user_id: str
    email: EmailStr
    payment_method: str  # "stripe" or "crypto"

class CheckoutResponse(BaseModel):
    success: bool
    checkout_url: Optional[str] = None
    session_id: Optional[str] = None
    error: Optional[str] = None

class DirectPaymentSuccessRequest(BaseModel):
    payment_id: str  # session_id for Stripe, order_id for Cryptomus
    user_id: str
    plan_type: str
    payment_method: str  # "stripe" or "crypto"
    amount: Optional[int] = None

@router.post("/create-checkout", response_model=CheckoutResponse)
async def create_checkout(request: CreateCheckoutRequest):
    """
    Create a checkout session for either Stripe or Cryptomus
    """
    try:
        from auth.session_manager import session_manager
        
        # Get plan details
        plan = PaymentConfig.SUBSCRIPTION_PLANS.get(
            request.plan_id, 
            PaymentConfig.SUBSCRIPTION_PLANS["free"]
        )
        
        if plan["price"] == 0:
            return CheckoutResponse(
                success=False,
                error="Cannot checkout free plan"
            )
        
        # Check if user has an active session and store it for later upgrade
        user_session = session_manager.get_user_session(request.user_id)
        if user_session:
            logger.info(f"User {request.user_id} has active session with plan {user_session['plan_type'].value}")
        
        # Amount in cents for Stripe, string for Cryptomus
        amount_cents = plan["price"] * 100
        amount_usd = str(plan["price"])
        
        base_url = "https://app.cuwapp.com"  # Update this for production
        
        if request.payment_method == "stripe":
            # Create Stripe Checkout Session
            result = stripe_client.create_checkout_session(
                plan_id=request.plan_id,
                amount=amount_cents,
                user_id=request.user_id,
                email=request.email,
                success_url=f"{base_url}/static/payment-success-direct.html?plan={request.plan_id}&method=stripe&user_id={request.user_id}",
                cancel_url=f"{base_url}/static/checkout-direct.html?plan={request.plan_id}"
            )
            
            if result["success"]:
                # Store checkout session info for later verification
                await store_checkout_session(
                    session_id=result["session_id"],
                    user_id=request.user_id,
                    plan_id=request.plan_id,
                    payment_method="stripe"
                )
                
                return CheckoutResponse(
                    success=True,
                    checkout_url=result["checkout_url"],
                    session_id=result["session_id"]
                )
            else:
                return CheckoutResponse(
                    success=False,
                    error=result.get("error", "Failed to create Stripe session")
                )
                
        elif request.payment_method == "crypto":
            # Create Cryptomus Invoice
            order_id = f"cuwhapp_{request.user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            result = cryptomus_client.create_invoice(
                amount=amount_usd,
                order_id=order_id,
                user_id=request.user_id,
                email=request.email,
                plan_id=request.plan_id,
                success_url=f"{base_url}/static/payment-success-direct.html?plan={request.plan_id}&method=crypto&order_id={order_id}&user_id={request.user_id}",
                fail_url=f"{base_url}/static/checkout-direct.html?plan={request.plan_id}&error=payment_failed"
            )
            
            if result["success"]:
                # Store checkout session info for later verification
                await store_checkout_session(
                    session_id=result["invoice_id"],
                    user_id=request.user_id,
                    plan_id=request.plan_id,
                    payment_method="crypto"
                )
                
                return CheckoutResponse(
                    success=True,
                    checkout_url=result["payment_url"],
                    session_id=result["invoice_id"]
                )
            else:
                return CheckoutResponse(
                    success=False,
                    error=result.get("error", "Failed to create crypto invoice")
                )
        else:
            return CheckoutResponse(
                success=False,
                error="Invalid payment method. Choose 'stripe' or 'crypto'"
            )
            
    except Exception as e:
        logger.error(f"Checkout creation error: {str(e)}")
        return CheckoutResponse(
            success=False,
            error=str(e)
        )

@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    try:
        import stripe
        
        # Get the webhook payload and signature
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        # Your webhook secret from Stripe Dashboard
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError:
            # Invalid payload
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            # Invalid signature
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            # Update user subscription in database
            user_id = session['metadata'].get('user_id')
            plan_id = session['metadata'].get('plan_id')
            
            if user_id and plan_id:
                # TODO: Update user subscription in database
                logger.info(f"Subscription activated for user {user_id} with plan {plan_id}")
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Stripe webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cryptomus/webhook")
async def cryptomus_webhook(request: Request):
    """Handle Cryptomus webhook events"""
    try:
        # Get webhook data
        body = await request.body()
        signature = request.headers.get('sign')
        
        # Verify signature
        if not cryptomus_client.verify_webhook(body.decode(), signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook data
        data = await request.json()
        
        # Check payment status
        if data.get("status") == "paid":
            # Extract metadata
            additional_data = json.loads(data.get("additional_data", "{}"))
            user_id = additional_data.get("user_id")
            plan_id = additional_data.get("plan_id")
            
            if user_id and plan_id:
                # TODO: Update user subscription in database
                logger.info(f"Crypto payment received for user {user_id} with plan {plan_id}")
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Cryptomus webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/payment-success")
async def handle_direct_payment_success(request: DirectPaymentSuccessRequest):
    """
    Handle payment success for direct payments (Stripe/Cryptomus)
    Checks actual payment status and triggers appropriate actions
    """
    try:
        logger.info(f"Processing direct payment success for user {request.user_id}, plan {request.plan_type}, method {request.payment_method}")
        
        payment_status = None
        payment_details = {}
        
        # Check payment status based on method
        if request.payment_method == "stripe":
            # Verify Stripe session
            result = stripe_client.verify_session(request.payment_id)
            
            if not result["success"]:
                return {
                    "success": False,
                    "error": result.get("error", "Failed to verify Stripe payment")
                }
            
            # Map Stripe statuses
            stripe_status = result.get("status", "unknown")
            if stripe_status == "paid" or stripe_status == "complete":
                payment_status = "succeeded"
            elif stripe_status == "unpaid" or stripe_status == "processing":
                payment_status = "processing"
            else:
                payment_status = "failed"
                
            payment_details = {
                "subscription_id": result.get("subscription_id"),
                "customer_email": result.get("customer_email"),
                "payment_intent": result.get("payment_intent")
            }
            
        elif request.payment_method == "crypto":
            # Verify Cryptomus payment
            result = cryptomus_client.check_payment_status(request.payment_id)
            
            if not result["success"]:
                return {
                    "success": False,
                    "error": result.get("error", "Failed to verify crypto payment")
                }
            
            # Map Cryptomus statuses
            crypto_status = result.get("status", "unknown")
            if crypto_status == "paid" or result.get("is_final"):
                payment_status = "succeeded"
            elif crypto_status == "pending" or crypto_status == "check":
                payment_status = "processing"
            else:
                payment_status = "failed"
                
            payment_details = {
                "amount_paid": result.get("amount_paid"),
                "currency": result.get("currency"),
                "txid": result.get("txid")
            }
        else:
            return {
                "success": False,
                "error": "Invalid payment method"
            }
        
        logger.info(f"Payment status for {request.payment_id}: {payment_status}")
        
        # Handle based on payment status
        if payment_status == "succeeded":
            # Payment successful - upgrade plan immediately
            upgrade_result = await upgrade_user_plan(
                user_id=request.user_id,
                plan_type=request.plan_type,
                payment_id=request.payment_id,
                payment_method=request.payment_method,
                amount=request.amount
            )
            
            # Trigger success hook (for future email/notification system)
            await trigger_payment_hook(
                event="payment.succeeded",
                user_id=request.user_id,
                plan_type=request.plan_type,
                payment_details=payment_details
            )
            
            return {
                "success": True,
                "status": "succeeded",
                "message": "Payment successful and plan upgraded",
                "plan_upgraded": upgrade_result
            }
            
        elif payment_status == "processing":
            # Payment still processing - don't upgrade yet
            # Trigger processing hook (for future email notification)
            await trigger_payment_hook(
                event="payment.processing",
                user_id=request.user_id,
                plan_type=request.plan_type,
                payment_details=payment_details
            )
            
            # Store pending payment for later processing
            await store_pending_payment(
                payment_id=request.payment_id,
                user_id=request.user_id,
                plan_type=request.plan_type,
                payment_method=request.payment_method,
                amount=request.amount
            )
            
            return {
                "success": True,
                "status": "processing",
                "message": "Payment is being processed. You will be notified once complete.",
                "plan_upgraded": False
            }
            
        else:
            # Payment failed
            await trigger_payment_hook(
                event="payment.failed",
                user_id=request.user_id,
                plan_type=request.plan_type,
                payment_details=payment_details
            )
            
            return {
                "success": False,
                "status": "failed",
                "message": "Payment failed. Please try again.",
                "plan_upgraded": False
            }
            
    except Exception as e:
        logger.error(f"Error handling direct payment success: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def upgrade_user_plan(user_id: str, plan_type: str, payment_id: str, payment_method: str, amount: Optional[int] = None):
    """
    Upgrade user's subscription plan and session
    """
    try:
        from database.subscription_models import UserSubscription, PlanType, SubscriptionStatus
        from database.connection import get_db
        from datetime import datetime, timedelta
        from auth.session_manager import session_manager
        
        # First upgrade the database subscription
        with get_db() as db:
            # Get or create subscription
            subscription = db.query(UserSubscription).filter(
                UserSubscription.user_id == user_id
            ).first()
            
            if not subscription:
                # Create new subscription
                subscription = UserSubscription(
                    user_id=user_id,
                    email=user_id,  # You might want to get actual email
                    plan_type=PlanType[plan_type.upper()],
                    status=SubscriptionStatus.ACTIVE,
                    current_period_start=datetime.utcnow(),
                    current_period_end=datetime.utcnow() + timedelta(days=30)
                )
                db.add(subscription)
            else:
                # Update existing subscription
                subscription.plan_type = PlanType[plan_type.upper()]
                subscription.status = SubscriptionStatus.ACTIVE
                subscription.current_period_start = datetime.utcnow()
                subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
            
            # Record payment
            from database.subscription_models import Payment, PaymentStatus
            payment = Payment(
                hyperswitch_payment_id=payment_id,
                user_id=user_id,
                amount=amount or 0,
                currency="USD",
                status=PaymentStatus.SUCCEEDED,
                payment_method=payment_method,
                payment_metadata={"plan": plan_type}
            )
            db.add(payment)
            
            db.commit()
            
            logger.info(f"Successfully upgraded user {user_id} to plan {plan_type}")
            
        # Now upgrade the active session if one exists
        session_upgrade_result = session_manager.upgrade_session_plan(
            user_id=user_id,
            new_plan_type=PlanType[plan_type.upper()]
        )
        
        if session_upgrade_result["success"]:
            logger.info(f"Session upgraded for user {user_id}: {session_upgrade_result['message']}")
        else:
            logger.warning(f"Could not upgrade session for user {user_id}: {session_upgrade_result.get('error', 'Unknown error')}")
        
        return True
            
    except Exception as e:
        logger.error(f"Error upgrading user plan: {str(e)}")
        return False

async def trigger_payment_hook(event: str, user_id: str, plan_type: str, payment_details: dict):
    """
    Trigger payment event hooks (placeholder for future email/notification system)
    This is where you'll connect email notifications or other triggers
    """
    try:
        logger.info(f"Payment hook triggered: {event} for user {user_id}")
        
        # PLACEHOLDER: Add your email/notification logic here
        # For now, just log the event
        hook_data = {
            "event": event,
            "user_id": user_id,
            "plan_type": plan_type,
            "payment_details": payment_details,
            "timestamp": datetime.now().isoformat()
        }
        
        # You can extend this to:
        # 1. Send to a message queue (RabbitMQ, Redis, etc.)
        # 2. Call an email service API
        # 3. Write to a webhook endpoint
        # 4. Store in database for batch processing
        
        if event == "payment.processing":
            # Future: Send "Payment Processing" email
            logger.info(f"TODO: Send processing email to user {user_id}")
            pass
        elif event == "payment.succeeded":
            # Future: Send "Payment Successful" email
            logger.info(f"TODO: Send success email to user {user_id}")
            pass
        elif event == "payment.failed":
            # Future: Send "Payment Failed" email
            logger.info(f"TODO: Send failure email to user {user_id}")
            pass
            
    except Exception as e:
        logger.error(f"Error triggering payment hook: {str(e)}")
        # Don't fail the main process if hook fails

async def store_pending_payment(payment_id: str, user_id: str, plan_type: str, payment_method: str, amount: Optional[int]):
    """
    Store pending payment for later processing when webhook confirms completion
    """
    try:
        from database.subscription_models import Payment, PaymentStatus
        from database.connection import get_db
        
        with get_db() as db:
            payment = Payment(
                hyperswitch_payment_id=payment_id,
                user_id=user_id,
                amount=amount or 0,
                currency="USD",
                status=PaymentStatus.PENDING,
                payment_method=payment_method,
                payment_metadata={
                    "plan": plan_type,
                    "pending_upgrade": True
                }
            )
            db.add(payment)
            db.commit()
            
        logger.info(f"Stored pending payment {payment_id} for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error storing pending payment: {str(e)}")

async def store_checkout_session(session_id: str, user_id: str, plan_id: str, payment_method: str):
    """
    Store checkout session info for later verification
    This helps us track which user initiated which payment session
    """
    try:
        # In production, you'd store this in database or Redis
        # For now, we'll use in-memory storage
        if not hasattr(store_checkout_session, "sessions"):
            store_checkout_session.sessions = {}
        
        store_checkout_session.sessions[session_id] = {
            "user_id": user_id,
            "plan_id": plan_id,
            "payment_method": payment_method,
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"Stored checkout session {session_id} for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error storing checkout session: {str(e)}")

@router.get("/session-status")
async def get_session_status(user_id: str):
    """
    Get current session status for a user
    Used to check if session was upgraded after payment
    """
    try:
        from auth.session_manager import session_manager
        
        user_session = session_manager.get_user_session(user_id)
        
        if not user_session:
            return {
                "success": False,
                "error": "No active session found"
            }
        
        return {
            "success": True,
            "session_id": user_session.get("session_id"),
            "plan_type": user_session["plan_type"].value,
            "persistent": user_session.get("persistent", False),
            "expires_at": user_session["expires_at"].isoformat() if user_session.get("expires_at") else None,
            "message": f"Active {user_session['plan_type'].value} session"
        }
        
    except Exception as e:
        logger.error(f"Error getting session status: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/verify-payment")
async def verify_payment(
    session_id: Optional[str] = None,
    order_id: Optional[str] = None,
    method: str = "stripe"
):
    """Verify payment status for either Stripe or Cryptomus"""
    try:
        if method == "stripe" and session_id:
            result = stripe_client.verify_session(session_id)
            return result
            
        elif method == "crypto" and order_id:
            result = cryptomus_client.check_payment_status(order_id)
            return result
            
        else:
            return {
                "success": False,
                "error": "Invalid parameters"
            }
            
    except Exception as e:
        logger.error(f"Payment verification error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
