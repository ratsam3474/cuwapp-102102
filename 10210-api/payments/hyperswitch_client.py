"""
Hyperswitch Payment Client for Cuwhapp
Handles all payment operations through Hyperswitch
"""

import requests
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from .config import PaymentConfig

logger = logging.getLogger(__name__)

class HyperswitchClient:
    """Hyperswitch API client for payment processing"""
    
    def __init__(self):
        self.base_url = PaymentConfig.HYPERSWITCH_BASE_URL
        self.api_key = PaymentConfig.HYPERSWITCH_API_KEY
        self.merchant_id = PaymentConfig.HYPERSWITCH_MERCHANT_ID
        self.headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }
    
    def create_payment_intent(
        self,
        amount: int,
        currency: str,
        customer_email: str,
        payment_method: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create a payment intent for processing payment
        
        Args:
            amount: Amount in cents (e.g., 2999 for $29.99)
            currency: Currency code (e.g., "USD", "EUR")
            customer_email: Customer email address
            payment_method: Payment method (stripe, paypal, paystack, crypto)
            metadata: Additional metadata for the payment
        
        Returns:
            Payment intent response from Hyperswitch
        """
        try:
            endpoint = f"{self.base_url}/payments"
            
            payload = {
                "amount": amount,
                "currency": currency,
                "confirm": False,
                "capture_method": "automatic",
                "customer": {
                    "email": customer_email
                },
                "billing": {
                    "address": {
                        "line1": "",
                        "city": "",
                        "state": "",
                        "zip": "",
                        "country": ""
                    }
                },
                "shipping": {
                    "address": {
                        "line1": "",
                        "city": "",
                        "state": "",
                        "zip": "",
                        "country": ""
                    }
                },
                "statement_descriptor_name": "Cuwhapp",
                "statement_descriptor_suffix": "Subscription",
                "metadata": metadata or {},
                "routing": {
                    "type": "single",
                    "data": payment_method
                }
            }
            
            response = requests.post(endpoint, json=payload, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating payment intent: {str(e)}")
            raise
    
    def confirm_payment(self, payment_id: str, payment_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Confirm a payment with payment method details
        
        Args:
            payment_id: Hyperswitch payment ID
            payment_details: Payment method specific details
        
        Returns:
            Payment confirmation response
        """
        try:
            endpoint = f"{self.base_url}/payments/{payment_id}/confirm"
            
            response = requests.post(endpoint, json=payment_details, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error confirming payment: {str(e)}")
            raise
    
    def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Get the status of a payment
        
        Args:
            payment_id: Hyperswitch payment ID
        
        Returns:
            Payment status details
        """
        try:
            endpoint = f"{self.base_url}/payments/{payment_id}"
            
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting payment status: {str(e)}")
            raise
    
    def create_customer(self, email: str, name: str = None, phone: str = None) -> Dict[str, Any]:
        """
        Create a customer profile in Hyperswitch
        
        Args:
            email: Customer email
            name: Customer name
            phone: Customer phone number
        
        Returns:
            Customer creation response
        """
        try:
            endpoint = f"{self.base_url}/customers"
            
            payload = {
                "email": email,
                "name": name,
                "phone": phone,
                "description": f"Cuwhapp customer - {email}"
            }
            
            response = requests.post(endpoint, json=payload, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating customer: {str(e)}")
            raise
    
    def create_subscription(
        self,
        customer_id: str,
        plan_id: str,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """
        Create a subscription for a customer
        
        Args:
            customer_id: Hyperswitch customer ID
            plan_id: Subscription plan ID
            payment_method_id: Payment method ID to use
        
        Returns:
            Subscription creation response
        """
        try:
            # Note: Hyperswitch subscription API endpoint might vary
            # This is a placeholder - adjust based on actual Hyperswitch API
            endpoint = f"{self.base_url}/subscriptions"
            
            payload = {
                "customer_id": customer_id,
                "plan_id": plan_id,
                "payment_method_id": payment_method_id,
                "start_date": datetime.now().isoformat(),
                "collection_method": "charge_automatically"
            }
            
            response = requests.post(endpoint, json=payload, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating subscription: {str(e)}")
            raise
    
    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Cancel a subscription
        
        Args:
            subscription_id: Subscription ID to cancel
        
        Returns:
            Cancellation response
        """
        try:
            endpoint = f"{self.base_url}/subscriptions/{subscription_id}/cancel"
            
            response = requests.post(endpoint, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error cancelling subscription: {str(e)}")
            raise
    
    def list_payment_methods(self, customer_id: str) -> Dict[str, Any]:
        """
        List saved payment methods for a customer
        
        Args:
            customer_id: Customer ID
        
        Returns:
            List of payment methods
        """
        try:
            endpoint = f"{self.base_url}/customers/{customer_id}/payment_methods"
            
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing payment methods: {str(e)}")
            raise
    
    def create_refund(self, payment_id: str, amount: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a refund for a payment
        
        Args:
            payment_id: Payment ID to refund
            amount: Amount to refund in cents (None for full refund)
        
        Returns:
            Refund response
        """
        try:
            endpoint = f"{self.base_url}/refunds"
            
            payload = {
                "payment_id": payment_id,
                "amount": amount,
                "reason": "requested_by_customer"
            }
            
            response = requests.post(endpoint, json=payload, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating refund: {str(e)}")
            raise