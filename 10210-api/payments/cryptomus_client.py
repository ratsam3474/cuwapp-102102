"""
Cryptomus Integration for CuWhapp
Handles cryptocurrency payments via Cryptomus API
"""

import os
import json
import hashlib
import hmac
import base64
import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class CryptomusClient:
    """Cryptomus API client for crypto payments"""
    
    def __init__(self):
        self.api_key = os.getenv("CRYPTOMUS_API_KEY", "your_api_key")
        self.merchant_id = os.getenv("CRYPTOMUS_MERCHANT_ID", "your_merchant_id")
        self.api_secret = os.getenv("CRYPTOMUS_API_SECRET", "your_api_secret")
        self.base_url = "https://api.cryptomus.com/v1"
        
    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """Generate HMAC signature for Cryptomus API"""
        # Sort data by keys
        sorted_data = dict(sorted(data.items()))
        # Create JSON string
        json_str = json.dumps(sorted_data, separators=(',', ':'))
        # Generate HMAC SHA256
        signature = hmac.new(
            self.api_secret.encode(),
            json_str.encode(),
            hashlib.sha256
        ).digest()
        # Return base64 encoded signature
        return base64.b64encode(signature).decode()
    
    def create_invoice(
        self,
        amount: str,  # Amount in USD
        order_id: str,
        user_id: str,
        email: str,
        plan_id: str,
        success_url: str,
        fail_url: str
    ) -> Dict[str, Any]:
        """
        Create a Cryptomus payment invoice
        
        Args:
            amount: Amount in USD as string
            order_id: Unique order ID
            user_id: User ID
            email: Customer email
            plan_id: Subscription plan ID
            success_url: Redirect URL on success
            fail_url: Redirect URL on failure
            
        Returns:
            Invoice details with payment URL
        """
        try:
            # Prepare request data
            data = {
                "amount": amount,
                "currency": "USD",
                "order_id": order_id,
                "url_success": success_url,
                "url_callback": f"{os.getenv('BASE_URL', 'https://app.cuwapp.com')}/api/payments/cryptomus/webhook",
                "url_return": fail_url,
                "is_payment_multiple": True,  # Allow partial payments
                "lifetime": 3600,  # 1 hour expiration
                "additional_data": json.dumps({
                    "user_id": user_id,
                    "plan_id": plan_id,
                    "email": email
                })
            }
            
            # Generate signature
            signature = self._generate_signature(data)
            
            # Prepare headers
            headers = {
                "merchant": self.merchant_id,
                "sign": signature,
                "Content-Type": "application/json"
            }
            
            # Make API request
            response = requests.post(
                f"{self.base_url}/payment",
                json=data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("state") == 0:  # Success state
                    invoice_data = result.get("result", {})
                    return {
                        "success": True,
                        "payment_url": invoice_data.get("url"),
                        "invoice_id": invoice_data.get("uuid"),
                        "order_id": invoice_data.get("order_id"),
                        "amount": invoice_data.get("amount"),
                        "expire_at": invoice_data.get("expired_at")
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("message", "Unknown error")
                    }
            else:
                logger.error(f"Cryptomus API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Cryptomus invoice creation error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_payment_status(self, order_id: str) -> Dict[str, Any]:
        """
        Check the status of a Cryptomus payment
        
        Args:
            order_id: Order ID to check
            
        Returns:
            Payment status details
        """
        try:
            data = {
                "order_id": order_id
            }
            
            signature = self._generate_signature(data)
            
            headers = {
                "merchant": self.merchant_id,
                "sign": signature,
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.base_url}/payment/info",
                json=data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("state") == 0:
                    payment_data = result.get("result", {})
                    return {
                        "success": True,
                        "status": payment_data.get("status"),  # paid, pending, failed, etc.
                        "amount_paid": payment_data.get("payer_amount"),
                        "currency": payment_data.get("payer_currency"),
                        "txid": payment_data.get("txid"),
                        "is_final": payment_data.get("is_final")
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("message", "Unknown error")
                    }
            else:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Cryptomus status check error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_webhook(self, request_body: str, signature: str) -> bool:
        """
        Verify Cryptomus webhook signature
        
        Args:
            request_body: Raw request body
            signature: Signature from webhook headers
            
        Returns:
            True if signature is valid
        """
        try:
            # Generate expected signature
            expected_signature = hmac.new(
                self.api_secret.encode(),
                request_body.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Webhook verification error: {str(e)}")
            return False