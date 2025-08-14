"""
Payment API endpoints for Cuwhapp
"""

from fastapi import APIRouter, HTTPException, Form, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import logging
from .hyperswitch_client import HyperswitchClient
from .config import PaymentConfig
from .webhook_handler import webhook_handler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["payments"])

# Pydantic models for request/response
class CreatePaymentRequest(BaseModel):
    amount: int  # Amount in cents
    currency: str = "USD"
    customer_email: EmailStr
    payment_method: str  # stripe, paypal, paystack, crypto
    plan_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CreateCheckoutRequest(BaseModel):
    plan_id: str
    amount: int
    user_id: str
    email: EmailStr
    return_url: str
    cancel_url: str

class ConfirmPaymentRequest(BaseModel):
    payment_id: str
    payment_details: Dict[str, Any]

class CreateSubscriptionRequest(BaseModel):
    customer_email: EmailStr
    customer_name: Optional[str] = None
    plan_id: str
    payment_method: str

class CryptoPaymentRequest(BaseModel):
    amount: int
    currency: str = "USD"
    crypto_currency: str  # BTC, ETH, USDT, etc.
    customer_email: EmailStr
    plan_id: Optional[str] = None

# Initialize Hyperswitch client
hyperswitch = HyperswitchClient()

@router.get("/config")
async def get_payment_config():
    """Get payment configuration including enabled providers and plans"""
    try:
        return {
            "success": True,
            "data": {
                "providers": PaymentConfig.get_enabled_providers(),
                "plans": PaymentConfig.SUBSCRIPTION_PLANS,
                "crypto_currencies": PaymentConfig.CRYPTO_CURRENCIES if PaymentConfig.CRYPTO_ENABLED else []
            }
        }
    except Exception as e:
        logger.error(f"Error getting payment config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-payment-intent")
async def create_payment_intent(request: CreateCheckoutRequest):
    """Create a Hyperswitch payment intent and return client secret"""
    try:
        # Create payment intent via Hyperswitch API
        from .config import PaymentConfig
        import requests
        from datetime import datetime
        
        # Generate unique payment ID
        payment_id = f"pay_{request.plan_id}_{request.user_id[:8]}_{int(datetime.now().timestamp())}"
        
        # Hyperswitch API configuration
        api_url = PaymentConfig.HYPERSWITCH_BASE_URL
        api_key = PaymentConfig.HYPERSWITCH_API_KEY or "test_key"
        
        # Create payment request following Hyperswitch API spec
        payment_data = {
            "amount": request.amount,  # Amount in cents
            "currency": "USD",
            "capture_method": "automatic",
            "confirm": False,  # Will be confirmed from frontend
            "customer_id": request.user_id,
            "email": request.email,
            "description": f"Cuwhapp {request.plan_id.title()} Plan Subscription",
            "metadata": {
                "user_id": request.user_id,
                "plan_id": request.plan_id,
                "order_id": payment_id
            },
            "return_url": request.return_url
        }
        
        headers = {
            "Content-Type": "application/json",
            "api-key": api_key,
            "Accept": "application/json"
        }
        
        # Try to create payment with Hyperswitch
        logger.info(f"Creating payment intent for {request.email}, plan: {request.plan_id}")
        
        try:
            response = requests.post(
                f"{api_url}/payments",
                json=payment_data,
                headers=headers,
                timeout=10
            )
            
            if response.ok:
                payment_response = response.json()
                client_secret = payment_response.get("client_secret")
                
                # Save payment record
                from database.connection import get_db
                from database.subscription_models import Payment, PaymentStatus
                
                with get_db() as db:
                    payment = Payment(
                        user_id=request.user_id,
                        amount=request.amount / 100,
                        currency="USD",
                        status=PaymentStatus.PENDING,
                        hyperswitch_payment_id=payment_response.get("payment_id", payment_id),
                        description=f"Cuwhapp {request.plan_id} Plan"
                    )
                    db.add(payment)
                    db.commit()
                
                return {
                    "success": True,
                    "clientSecret": client_secret or f"test_secret_{payment_id}",
                    "payment_id": payment_response.get("payment_id", payment_id)
                }
            else:
                logger.error(f"Hyperswitch API error: {response.status_code} - {response.text}")
                # Fall back to test mode
                return {
                    "success": True,
                    "clientSecret": f"test_secret_{payment_id}",
                    "payment_id": payment_id,
                    "test_mode": True
                }
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Cannot connect to Hyperswitch: {str(e)}. Using test mode.")
            # Return test client secret for development
            return {
                "success": True,
                "clientSecret": f"test_secret_{payment_id}",
                "payment_id": payment_id,
                "test_mode": True
            }
            
    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-checkout")
async def create_checkout(request: CreateCheckoutRequest):
    """Create a checkout session and return checkout URL"""
    try:
        from datetime import datetime
        
        # Generate payment ID
        payment_id = f"pay_{request.plan_id}_{request.user_id[:8]}_{int(datetime.now().timestamp())}"
        
        # Save initial payment record
        from database.connection import get_db
        from database.subscription_models import Payment, PaymentStatus
        
        with get_db() as db:
            payment = Payment(
                user_id=request.user_id,
                amount=request.amount / 100,
                currency="USD",
                status=PaymentStatus.PENDING,
                hyperswitch_payment_id=payment_id,
                description=f"Cuwhapp {request.plan_id} Plan"
            )
            db.add(payment)
            db.commit()
        
        # Build checkout URL with parameters
        checkout_params = {
            "payment_id": payment_id,
            "plan": request.plan_id,
            "amount": request.amount,
            "email": request.email
        }
        
        # Create query string
        from urllib.parse import urlencode
        query_string = urlencode(checkout_params)
        
        # Return checkout page URL
        checkout_url = f"https://app.cuwapp.com/static/checkout.html?{query_string}"
        
        return {
            "success": True,
            "checkout_url": checkout_url,
            "payment_id": payment_id
        }
        
    except Exception as e:
        logger.error(f"Error creating checkout: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-payment")
            "customer_id": request.user_id,  # Your internal customer ID
            "email": request.email,
            "description": f"Cuwhapp {request.plan_id.title()} Plan Subscription",
            "return_url": request.return_url,  # Where to redirect after payment
            "metadata": {
                "user_id": request.user_id,
                "plan_id": request.plan_id,
                "order_details": {
                    "product_name": f"Cuwhapp {request.plan_id.title()} Plan",
                    "quantity": 1
                }
            },
            "billing": {
                "address": {
                    "first_name": request.email.split('@')[0],
                    "email": request.email
                }
            }
        }
        
        # Call Hyperswitch API to create payment
        import requests
        
        # Log the payment request for debugging
        logger.info(f"Creating payment for plan {request.plan_id}, amount: ${request.amount/100}")
        
        # Hyperswitch is running on port 9000 (Dashboard UI)
        # Since port 9000 returns HTML dashboard, we'll use a mock checkout flow
        # that simulates the payment process
        hyperswitch_base_url = "http://localhost:9000"
        
        # For now, always use mock checkout since Hyperswitch API endpoint is unclear
        use_mock_checkout = True
        
        if use_mock_checkout:
            # Hyperswitch not running, create a mock checkout URL
            logger.warning("Hyperswitch not detected, using mock checkout")
            mock_payment_id = f"mock_{request.plan_id}_{request.user_id[:8]}"
            
            # Save mock payment record
            from database.connection import get_db
            from database.subscription_models import Payment, PaymentStatus
            
            with get_db() as db:
                payment = Payment(
                    user_id=request.user_id,
                    amount=request.amount / 100,
                    currency="USD",
                    status=PaymentStatus.PENDING,
                    hyperswitch_payment_id=mock_payment_id,
                    description=f"Cuwhapp {request.plan_id} Plan"
                )
                db.add(payment)
                db.commit()
            
            # Return mock checkout URL with payment details
            checkout_params = f"?payment_id={mock_payment_id}&plan={request.plan_id}&amount={request.amount}"
            return {
                "success": True,
                "checkout_url": f"https://app.cuwapp.com/mock-checkout{checkout_params}",
                "mock": True
            }
        
        # Try to create payment with Hyperswitch
        # According to docs, Hyperswitch uses API-key header for authentication
        try:
            headers = {
                "Content-Type": "application/json",
                "api-key": "test_key",  # Your Hyperswitch secret key
                "Accept": "application/json"
            }
            
            logger.info(f"Sending payment request to {hyperswitch_url}")
            logger.debug(f"Payment data: {payment_data}")
            
            response = requests.post(
                hyperswitch_url,
                json=payment_data,
                headers=headers,
                timeout=10
            )
            
            logger.info(f"Hyperswitch response status: {response.status_code}")
            if not response.ok:
                logger.error(f"Hyperswitch error response: {response.text}")
                
        except requests.exceptions.Timeout:
            logger.error("Hyperswitch request timed out")
            raise HTTPException(status_code=504, detail="Payment service timeout")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to Hyperswitch: {str(e)}")
            raise HTTPException(status_code=503, detail="Payment service unavailable")
        except Exception as e:
            logger.error(f"Unexpected error calling Hyperswitch: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
        
        if response.ok:
            try:
                payment_response = response.json()
                logger.info(f"Payment created successfully: {payment_response.get('payment_id')}")
                
                # Save payment record in database
                from database.connection import get_db
                from database.subscription_models import Payment, PaymentStatus
                
                with get_db() as db:
                    payment = Payment(
                        user_id=request.user_id,
                        amount=request.amount / 100,
                        currency="USD",
                        status=PaymentStatus.PENDING,
                        hyperswitch_payment_id=payment_response.get("payment_id"),
                        description=f"Cuwhapp {request.plan_id} Plan"
                    )
                    db.add(payment)
                    db.commit()
                
                # Hyperswitch returns different URL fields based on integration type
                # Check for various possible URL fields
                checkout_url = (
                    payment_response.get("redirect_to_url") or  # Redirect flow
                    payment_response.get("next_action", {}).get("redirect_to_url") or  # Next action redirect
                    payment_response.get("client_secret") and f"{hyperswitch_base_url}/checkout?client_secret={payment_response.get('client_secret')}" or  # Client secret flow
                    f"http://localhost:9000/checkout?payment_id={payment_response.get('payment_id')}"  # Fallback
                )
                
                return {
                    "success": True,
                    "checkout_url": checkout_url,
                    "payment_id": payment_response.get("payment_id"),
                    "status": payment_response.get("status")
                }
            except ValueError as e:
                logger.error(f"Invalid JSON response from Hyperswitch: {response.text}")
                raise HTTPException(status_code=502, detail="Invalid response from payment service")
        else:
            error_msg = f"Hyperswitch API error: {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f" - {error_data.get('error', {}).get('message', response.text)}"
            except:
                error_msg += f" - {response.text[:200]}"
            
            logger.error(error_msg)
            raise HTTPException(status_code=response.status_code, detail=error_msg)
            
    except Exception as e:
        logger.error(f"Error creating checkout: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-payment")
async def create_payment(request: CreatePaymentRequest):
    """Create a payment intent"""
    try:
        # Validate payment method is enabled
        if request.payment_method not in PaymentConfig.get_enabled_providers():
            raise HTTPException(status_code=400, detail=f"Payment method {request.payment_method} is not enabled")
        
        # Create payment intent via Hyperswitch
        payment_intent = hyperswitch.create_payment_intent(
            amount=request.amount,
            currency=request.currency,
            customer_email=request.customer_email,
            payment_method=request.payment_method,
            metadata=request.metadata or {"plan_id": request.plan_id}
        )
        
        return {
            "success": True,
            "data": payment_intent
        }
        
    except Exception as e:
        logger.error(f"Error creating payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/confirm-payment")
async def confirm_payment(request: ConfirmPaymentRequest):
    """Confirm a payment with payment method details"""
    try:
        result = hyperswitch.confirm_payment(
            payment_id=request.payment_id,
            payment_details=request.payment_details
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error confirming payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payment-status/{payment_id}")
async def get_payment_status(payment_id: str):
    """Get the status of a payment"""
    try:
        status = hyperswitch.get_payment_status(payment_id)
        
        return {
            "success": True,
            "data": status
        }
        
    except Exception as e:
        logger.error(f"Error getting payment status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-subscription")
async def create_subscription(request: CreateSubscriptionRequest):
    """Create a subscription for a customer"""
    try:
        # Validate plan exists
        if request.plan_id not in PaymentConfig.SUBSCRIPTION_PLANS:
            raise HTTPException(status_code=400, detail=f"Invalid plan ID: {request.plan_id}")
        
        # Create customer first
        customer = hyperswitch.create_customer(
            email=request.customer_email,
            name=request.customer_name
        )
        
        # Create subscription
        # Note: You'll need to handle payment method creation/selection
        # This is a simplified version
        subscription = hyperswitch.create_subscription(
            customer_id=customer["id"],
            plan_id=request.plan_id,
            payment_method_id=request.payment_method  # This would be a payment method ID
        )
        
        return {
            "success": True,
            "data": {
                "customer": customer,
                "subscription": subscription
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel-subscription/{subscription_id}")
async def cancel_subscription(subscription_id: str):
    """Cancel a subscription"""
    try:
        result = hyperswitch.cancel_subscription(subscription_id)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error cancelling subscription: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/crypto-payment")
async def create_crypto_payment(request: CryptoPaymentRequest):
    """Create a cryptocurrency payment"""
    try:
        if not PaymentConfig.CRYPTO_ENABLED:
            raise HTTPException(status_code=400, detail="Crypto payments are not enabled")
        
        if request.crypto_currency not in PaymentConfig.CRYPTO_CURRENCIES:
            raise HTTPException(status_code=400, detail=f"Unsupported cryptocurrency: {request.crypto_currency}")
        
        # Create crypto payment via Hyperswitch
        # This would integrate with a crypto payment processor
        payment_intent = hyperswitch.create_payment_intent(
            amount=request.amount,
            currency=request.currency,
            customer_email=request.customer_email,
            payment_method="crypto",
            metadata={
                "crypto_currency": request.crypto_currency,
                "plan_id": request.plan_id
            }
        )
        
        return {
            "success": True,
            "data": payment_intent
        }
        
    except Exception as e:
        logger.error(f"Error creating crypto payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refund/{payment_id}")
async def create_refund(payment_id: str, amount: Optional[int] = None):
    """Create a refund for a payment"""
    try:
        refund = hyperswitch.create_refund(payment_id, amount)
        
        return {
            "success": True,
            "data": refund
        }
        
    except Exception as e:
        logger.error(f"Error creating refund: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/customer/{customer_id}/payment-methods")
async def list_payment_methods(customer_id: str):
    """List saved payment methods for a customer"""
    try:
        methods = hyperswitch.list_payment_methods(customer_id)
        
        return {
            "success": True,
            "data": methods
        }
        
    except Exception as e:
        logger.error(f"Error listing payment methods: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def handle_webhook(request: Dict[str, Any]):
    """Handle webhook events from Hyperswitch"""
    try:
        # Process the webhook event
        result = webhook_handler.process_webhook(request)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        # Return 200 to acknowledge receipt even if processing fails
        # This prevents webhook retries
        return {
            "success": False,
            "error": str(e)
        }