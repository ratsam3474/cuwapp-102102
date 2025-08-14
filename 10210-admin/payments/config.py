"""
Payment Configuration for Cuwhapp
Supports: Hyperswitch (Stripe, PayPal, Paystack, Crypto)
"""

import os
from typing import Dict, Any

class PaymentConfig:
    """Payment provider configuration"""
    
    # Hyperswitch Configuration - Cloud Sandbox
    HYPERSWITCH_BASE_URL = os.getenv("HYPERSWITCH_BASE_URL", "https://sandbox.hyperswitch.io")
    HYPERSWITCH_API_KEY = os.getenv("HYPERSWITCH_API_KEY", "snd_MF6Nc4A5FY42UMtEN1BbdVFHhVC8pXYYATFZNgEIbiFTrA827lCTNO8FldzsBSeR")
    HYPERSWITCH_PUBLISHABLE_KEY = os.getenv("HYPERSWITCH_PUBLISHABLE_KEY", "pk_snd_68a3be601ff24b82a4b163a8b3d046b2")
    HYPERSWITCH_MERCHANT_ID = os.getenv("HYPERSWITCH_MERCHANT_ID", "merchant_1754725141")
    HYPERSWITCH_PROFILE_ID = os.getenv("HYPERSWITCH_PROFILE_ID", "pro_ja9RttZER7X829FB4iAM")
    HYPERSWITCH_RESPONSE_KEY = os.getenv("HYPERSWITCH_RESPONSE_KEY", "WoSmgjJdbIgQBJJfBwX4825gC0ppX7rzcuEUl4g4joWTihkCT5WEjpqoEthYydAz")
    
    # Stripe Configuration (via Hyperswitch)
    STRIPE_ENABLED = os.getenv("STRIPE_ENABLED", "true").lower() == "true"
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_test_51RuJ4jFCIs90iDto2sVwVShL2cJUbPLqclAdrv2pd9dAKswfGkBHGtXOtQdN0NI5ada6Lkq3CWmuF5icFXG22jwM00ZmOTBFoy")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "YOUR_STRIPE_SECRET_KEY_HERE")
    
    # PayPal Configuration (via Hyperswitch)
    PAYPAL_ENABLED = os.getenv("PAYPAL_ENABLED", "true").lower() == "true"
    PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
    PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
    PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox")  # sandbox or live
    
    # Paystack Configuration (via Hyperswitch)
    PAYSTACK_ENABLED = os.getenv("PAYSTACK_ENABLED", "true").lower() == "true"
    PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY", "")
    PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
    
    # Crypto Configuration
    CRYPTO_ENABLED = os.getenv("CRYPTO_ENABLED", "true").lower() == "true"
    # Supported cryptocurrencies
    CRYPTO_CURRENCIES = ["BTC", "ETH", "USDT", "USDC", "BNB"]
    
    # Subscription Plans
    SUBSCRIPTION_PLANS = {
        "free": {
            "name": "Free",
            "price": 0,
            "currency": "USD",
            "features": {
                "sessions": 1,
                "messages_per_month": 100,
                "contacts_export": 100,  # Contact + group file download limit
                "campaigns": 1,
                "warmer_duration": None,  # Not available
                "support": "community"
            }
        },
        "starter": {
            "name": "Starter",
            "price": 7,
            "currency": "USD",
            "features": {
                "sessions": 1,
                "messages_per_month": 1000,
                "contacts_export": -1,  # Unlimited
                "campaigns": -1,  # Unlimited
                "warmer_duration": None,  # Not available
                "support": "email"
            }
        },
        "hobby": {
            "name": "Hobby",
            "price": 20,
            "currency": "USD",
            "features": {
                "sessions": 3,
                "messages_per_month": 10000,
                "contacts_export": -1,  # Unlimited
                "campaigns": -1,  # Unlimited
                "warmer_duration": 24,  # 24 hours
                "support": "email"
            }
        },
        "pro": {
            "name": "Pro",
            "price": 45,
            "currency": "USD",
            "features": {
                "sessions": 10,
                "messages_per_month": 30000,
                "contacts_export": -1,  # Unlimited
                "campaigns": -1,  # Unlimited
                "warmer_duration": 96,  # 4 days (96 hours)
                "support": "priority"
            }
        },
        "premium": {
            "name": "Premium",
            "price": 99,
            "currency": "USD",
            "features": {
                "sessions": 30,
                "messages_per_month": -1,  # Unlimited
                "contacts_export": -1,  # Unlimited
                "campaigns": -1,  # Unlimited
                "warmer_duration": 360,  # 15 days (360 hours)
                "support": "dedicated"
            }
        }
    }
    
    @classmethod
    def get_enabled_providers(cls) -> list:
        """Get list of enabled payment providers"""
        providers = []
        if cls.STRIPE_ENABLED:
            providers.append("stripe")
        if cls.PAYPAL_ENABLED:
            providers.append("paypal")
        if cls.PAYSTACK_ENABLED:
            providers.append("paystack")
        if cls.CRYPTO_ENABLED:
            providers.append("crypto")
        return providers
    
    @classmethod
    def get_plan_details(cls, plan_name: str) -> Dict[str, Any]:
        """Get details for a subscription plan"""
        return cls.SUBSCRIPTION_PLANS.get(plan_name, cls.SUBSCRIPTION_PLANS["free"])