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
from .crypto_handler import CryptoPaymentHandler

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

# Initialize clients
hyperswitch = HyperswitchClient()
crypto_handler = CryptoPaymentHandler()

@router.post("/test-coinbase")
async def test_coinbase_connection():
    """Test if Coinbase Commerce connector is working"""
    import requests
    
    try:
        # Create a test crypto payment
        payment_data = {
            "amount": 1000,  # $10 test
            "currency": "USD",
            "confirm": False,
            "capture_method": "automatic",
            "customer_id": "crypto_test_customer",
            "email": "crypto@test.com",
            "description": "Crypto Connection Test",
            "return_url": f"{os.getenv('API_GATEWAY_URL', 'https://app.cuwapp.com')}/success",
            "profile_id": PaymentConfig.HYPERSWITCH_PROFILE_ID,
            "payment_method": "crypto",
            "payment_method_type": "crypto_currency",
            "payment_method_data": {
                "crypto": {
                    "type": "crypto_currency"
                }
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "api-key": PaymentConfig.HYPERSWITCH_API_KEY
        }
        
        response = requests.post(
            f"{PaymentConfig.HYPERSWITCH_BASE_URL}/payments",
            json=payment_data,
            headers=headers,
            timeout=10
        )
        
        result = {
            "success": response.ok,
            "status_code": response.status_code,
            "coinbase_configured": False
        }
        
        if response.ok:
            data = response.json()
            result["payment_id"] = data.get("payment_id")
            result["client_secret"] = data.get("client_secret", "")[:50] + "..." if data.get("client_secret") else None
            
            # Check if crypto payment methods are available
            if "payment_methods" in data:
                crypto_methods = [m for m in data["payment_methods"] if "crypto" in str(m).lower()]
                result["crypto_available"] = len(crypto_methods) > 0
                result["coinbase_configured"] = len(crypto_methods) > 0
        else:
            result["error"] = response.text[:500]
            
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "note": "Coinbase Commerce may not be properly configured in Hyperswitch"
        }

@router.post("/test-hyperswitch")
async def test_hyperswitch_connection():
    """Test Hyperswitch API connection"""
    import requests
    
    try:
        # Test payment data
        payment_data = {
            "amount": 1000,  # $10 test
            "currency": "USD",
            "confirm": False,
            "capture_method": "automatic",
            "customer_id": "test_customer",
            "email": "test@example.com",
            "description": "Connection Test",
            "return_url": f"{os.getenv('API_GATEWAY_URL', 'https://app.cuwapp.com')}/success",
            "profile_id": PaymentConfig.HYPERSWITCH_PROFILE_ID
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "api-key": PaymentConfig.HYPERSWITCH_API_KEY
        }
        
        # Try to create a test payment
        response = requests.post(
            f"{PaymentConfig.HYPERSWITCH_BASE_URL}/payments",
            json=payment_data,
            headers=headers,
            timeout=10
        )
        
        return {
            "success": response.ok,
            "status_code": response.status_code,
            "response": response.json() if response.ok else response.text,
            "api_url": PaymentConfig.HYPERSWITCH_BASE_URL,
            "has_client_secret": "client_secret" in response.json() if response.ok else False
        }
        
    except requests.exceptions.ConnectionError as e:
        return {
            "success": False,
            "error": "Connection failed",
            "details": str(e),
            "api_url": PaymentConfig.HYPERSWITCH_BASE_URL
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "api_url": PaymentConfig.HYPERSWITCH_BASE_URL
        }

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
    """Create a Hyperswitch payment intent using v2 API and return client secret"""
    try:
        from .config import PaymentConfig
        import requests
        from datetime import datetime
        
        # Hyperswitch API v2 configuration
        api_url = PaymentConfig.HYPERSWITCH_BASE_URL  # https://sandbox.hyperswitch.io
        api_key = PaymentConfig.HYPERSWITCH_API_KEY  # Your actual API key
        profile_id = PaymentConfig.HYPERSWITCH_PROFILE_ID  # Your profile ID
        
        # Create payment request for Hyperswitch v1 API
        payment_data = {
            "amount": request.amount,  # Amount in cents
            "currency": "USD",
            "confirm": False,  # Will be confirmed from frontend
            "capture_method": "automatic",
            "customer_id": request.user_id,
            "email": request.email,
            "description": f"Cuwhapp {request.plan_id.title()} Plan Subscription",
            "return_url": request.return_url,
            "setup_future_usage": "off_session",
            # Payment methods configured in Hyperswitch Dashboard
            # Connector IDs:
            # - Stripe: mca_qQpy0TEv2xr9YUubYgmE (cards)
            # - PayPal: mca_qprBvJeihdVRFJgRsTw7
            # - Paystack: mca_Qc02HtgNxsEp5RXG8zYS (African payments)
            # - Coinbase: mca_0gSm9Sm8vfe9gXgl7zNo (crypto)
            "allowed_payment_method_types": [
                "credit",           # Stripe
                "debit",            # Stripe  
                "paypal",           # PayPal
                "crypto_currency",  # Coinbase Commerce (BTC, ETH, USDC, etc.)
                # Note: Paystack is configured but uses standard card types
                # "google_pay",     # Requires additional setup
                # "apple_pay",      # Requires merchant certificate
            ],
            # Optional: Specify connector for routing (useful for multi-connector setup)
            # "routing": {
            #     "type": "single",
            #     "data": "stripe"  # Default to Stripe for cards
            # },
            "metadata": {
                "user_id": request.user_id,
                "plan_id": request.plan_id
            },
            "profile_id": profile_id  # Add profile ID to ensure correct configuration
        }
        
        # Headers for v1 API
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "api-key": api_key
        }
        
        # Try to create payment with Hyperswitch
        logger.info(f"Creating payment intent for {request.email}, plan: {request.plan_id}")
        
        try:
            # Using v1 API endpoint which works with your local instance
            logger.info(f"Calling Hyperswitch API: {api_url}/payments")
            logger.info(f"Request data: {payment_data}")
            
            response = requests.post(
                f"{api_url}/payments",
                json=payment_data,
                headers=headers,
                timeout=10
            )
            
            logger.info(f"Hyperswitch response status: {response.status_code}")
            
            if response.ok:
                payment_response = response.json()
                client_secret = payment_response.get("client_secret")
                payment_id = payment_response.get("payment_id")
                
                logger.info(f"Payment created successfully: {payment_id}")
                
                # Save payment record
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
                
                return {
                    "success": True,
                    "clientSecret": client_secret,
                    "payment_id": payment_id
                }
            else:
                error_text = response.text[:500]  # Limit error text length
                logger.error(f"Hyperswitch API error: {response.status_code} - {error_text}")
                # Fall back to test mode
                test_payment_id = f"test_pay_{request.plan_id}_{request.user_id[:8]}"
                return {
                    "success": True,
                    "clientSecret": f"test_secret_{test_payment_id}",
                    "payment_id": test_payment_id,
                    "test_mode": True
                }
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Cannot connect to Hyperswitch: {str(e)}. Using test mode.")
            # Return test client secret for development
            test_payment_id = f"test_pay_{request.plan_id}_{request.user_id[:8]}"
            return {
                "success": True,
                "clientSecret": f"test_secret_{test_payment_id}",
                "payment_id": test_payment_id,
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
        base_url = os.getenv('API_GATEWAY_URL', 'https://app.cuwapp.com')
        checkout_url = f"{base_url}/static/checkout.html?{query_string}"
        
        return {
            "success": True,
            "checkout_url": checkout_url,
            "payment_id": payment_id
        }
        
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

@router.post("/crypto/coingate")
async def create_coingate_payment(request: CryptoPaymentRequest):
    """Create a CoinGate crypto payment"""
    try:
        import uuid
        order_id = str(uuid.uuid4())[:8]
        
        payment = crypto_handler.create_coingate_payment(
            amount=request.amount / 100,  # Convert from cents
            currency=request.currency,
            crypto_currency=request.crypto_currency,
            order_id=order_id,
            customer_email=request.customer_email,
            success_url=f"{os.getenv('API_GATEWAY_URL', 'https://app.cuwapp.com')}/payment-success?provider=coingate",
            cancel_url=f"{os.getenv('API_GATEWAY_URL', 'https://app.cuwapp.com')}/payment-cancelled?provider=coingate"
        )
        
        return {
            "success": payment["success"],
            "data": payment.get("data"),
            "payment_url": payment.get("payment_url"),
            "error": payment.get("error")
        }
        
    except Exception as e:
        logger.error(f"Error creating CoinGate payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/crypto/bitpay")
async def create_bitpay_payment(request: CryptoPaymentRequest):
    """Create a BitPay crypto invoice"""
    try:
        import uuid
        order_id = str(uuid.uuid4())[:8]
        
        invoice = crypto_handler.create_bitpay_invoice(
            amount=request.amount / 100,  # Convert from cents
            currency=request.currency,
            order_id=order_id,
            customer_email=request.customer_email,
            redirect_url=f"{os.getenv('API_GATEWAY_URL', 'https://app.cuwapp.com')}/payment-success?provider=bitpay"
        )
        
        return {
            "success": invoice["success"],
            "data": invoice.get("data"),
            "payment_url": invoice.get("payment_url"),
            "error": invoice.get("error")
        }
        
    except Exception as e:
        logger.error(f"Error creating BitPay invoice: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/crypto/currencies")
async def get_crypto_currencies():
    """Get supported cryptocurrencies for all providers"""
    try:
        currencies = crypto_handler.get_supported_cryptocurrencies()
        return {
            "success": True,
            "data": currencies
        }
    except Exception as e:
        logger.error(f"Error getting crypto currencies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/crypto/webhook")
async def handle_crypto_webhook(request: Dict[str, Any]):
    """Handle crypto payment webhooks from providers like CoinGate"""
    try:
        # Process crypto payment webhook
        provider = request.get("provider", "unknown")
        logger.info(f"Received crypto webhook from {provider}: {request}")
        
        # Update payment status in database
        from database.connection import get_db
        from database.subscription_models import Payment, PaymentStatus
        
        with get_db() as db:
            if provider == "coingate":
                order_id = request.get("order_id")
                status = request.get("status")
                
                # Find payment by order_id in metadata or external reference
                payment = db.query(Payment).filter(
                    Payment.hyperswitch_payment_id.contains(order_id)
                ).first()
                
                if payment:
                    if status == "paid":
                        payment.status = PaymentStatus.SUCCEEDED
                    elif status == "cancelled":
                        payment.status = PaymentStatus.FAILED
                    
                    db.commit()
        
        return {"success": True, "message": "Webhook processed"}
        
    except Exception as e:
        logger.error(f"Error handling crypto webhook: {str(e)}")
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