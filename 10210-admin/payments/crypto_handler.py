"""
Crypto Payment Handler for CuWhapp
Supports multiple crypto payment providers
"""

import os
import requests
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from .config import PaymentConfig

logger = logging.getLogger(__name__)

class CryptoPaymentHandler:
    """Handles cryptocurrency payments through various providers"""
    
    def __init__(self):
        self.coingate_api_key = os.getenv("COINGATE_API_KEY")
        self.coingate_mode = os.getenv("COINGATE_MODE", "sandbox")
        self.bitpay_token = os.getenv("BITPAY_API_TOKEN")
        self.bitpay_env = os.getenv("BITPAY_ENVIRONMENT", "test")
        
    def create_coingate_payment(
        self,
        amount: float,
        currency: str,
        crypto_currency: str,
        order_id: str,
        customer_email: str,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """Create a CoinGate payment"""
        try:
            base_url = "https://api-sandbox.coingate.com" if self.coingate_mode == "sandbox" else "https://api.coingate.com"
            
            payload = {
                "order_id": order_id,
                "price_amount": amount,
                "price_currency": currency,
                "receive_currency": crypto_currency,
                "callback_url": f"{os.getenv('BASE_URL', 'https://app.cuwapp.com')}/api/payments/crypto/webhook",
                "cancel_url": cancel_url,
                "success_url": success_url,
                "title": "CuWhapp Subscription",
                "description": f"CuWhapp subscription payment - Order #{order_id}"
            }
            
            headers = {
                "Authorization": f"Token {self.coingate_api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{base_url}/v2/orders",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json(),
                    "payment_url": response.json().get("payment_url")
                }
            else:
                logger.error(f"CoinGate payment creation failed: {response.text}")
                return {
                    "success": False,
                    "error": f"CoinGate error: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"CoinGate payment error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_bitpay_invoice(
        self,
        amount: float,
        currency: str,
        order_id: str,
        customer_email: str,
        redirect_url: str
    ) -> Dict[str, Any]:
        """Create a BitPay invoice"""
        try:
            base_url = "https://test.bitpay.com" if self.bitpay_env == "test" else "https://bitpay.com"
            
            payload = {
                "price": amount,
                "currency": currency,
                "orderId": order_id,
                "notificationURL": f"{os.getenv('BASE_URL', 'https://app.cuwapp.com')}/api/payments/crypto/bitpay-webhook",
                "redirectURL": redirect_url,
                "buyer": {
                    "email": customer_email
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.bitpay_token}",
                "Content-Type": "application/json",
                "X-Accept-Version": "2.0.0"
            }
            
            response = requests.post(
                f"{base_url}/invoices",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                invoice_data = response.json()["data"]
                return {
                    "success": True,
                    "data": invoice_data,
                    "payment_url": invoice_data.get("url")
                }
            else:
                logger.error(f"BitPay invoice creation failed: {response.text}")
                return {
                    "success": False,
                    "error": f"BitPay error: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"BitPay payment error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_supported_cryptocurrencies(self) -> Dict[str, Any]:
        """Get list of supported cryptocurrencies"""
        return {
            "coingate": [
                "BTC", "ETH", "LTC", "BCH", "XRP", "ADA", "DOT", "LINK",
                "USDT", "USDC", "DAI", "BNB", "MATIC", "AVAX"
            ],
            "bitpay": [
                "BTC", "BCH", "ETH", "USDC", "PAX", "BUSD", "DOGE", "LTC", "XRP"
            ],
            "hyperswitch_native": PaymentConfig.CRYPTO_CURRENCIES
        }
    
    def validate_crypto_address(self, address: str, currency: str) -> bool:
        """Validate cryptocurrency address format"""
        # Basic validation - you might want to use a proper validation library
        if currency == "BTC":
            return len(address) >= 26 and len(address) <= 35
        elif currency == "ETH":
            return len(address) == 42 and address.startswith("0x")
        elif currency in ["USDT", "USDC"]:
            return len(address) == 42 and address.startswith("0x")
        return True  # Basic fallback