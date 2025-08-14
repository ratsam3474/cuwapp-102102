"""
Clerk Configuration for Email-Only Authentication
Disables phone number verification for countries with limited support
"""

import os
from typing import Dict, Any

class ClerkConfig:
    """Clerk authentication configuration"""
    
    # Clerk API Keys
    CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "")
    CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
    
    # Authentication Requirements
    AUTHENTICATION_CONFIG = {
        "email": {
            "required": True,
            "verification": "email_link",  # or "email_code"
            "allow_disposable": False
        },
        "phone": {
            "required": False,  # Disabled for Nigerian numbers
            "verification": None,
            "supported_countries": []  # Empty = all disabled
        },
        "username": {
            "required": False,
            "min_length": 3,
            "max_length": 20
        },
        "password": {
            "required": True,
            "min_length": 8,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_numbers": True
        },
        "profile": {
            "first_name": {
                "required": True,
                "min_length": 1,
                "max_length": 50
            },
            "last_name": {
                "required": True,
                "min_length": 1,
                "max_length": 50
            }
        }
    }
    
    # Social Login Providers (No phone required)
    SOCIAL_PROVIDERS = {
        "google": {
            "enabled": True,
            "scopes": ["email", "profile"]
        },
        "github": {
            "enabled": True,
            "scopes": ["user:email"]
        },
        "microsoft": {
            "enabled": True,
            "scopes": ["email", "profile"]
        },
        "discord": {
            "enabled": True,
            "scopes": ["identify", "email"]
        }
    }
    
    # Session Configuration
    SESSION_CONFIG = {
        "lifetime_hours": 24,
        "inactivity_hours": 2,
        "single_session_mode": False
    }
    
    @classmethod
    def get_signup_fields(cls) -> Dict[str, Any]:
        """Get required fields for signup"""
        return {
            "email_address": {
                "required": True,
                "type": "email"
            },
            "password": {
                "required": True,
                "type": "password"
            },
            "first_name": {
                "required": True,
                "type": "text"
            },
            "last_name": {
                "required": True,
                "type": "text"
            },
            "username": {
                "required": False,
                "type": "text"
            }
            # Phone number intentionally excluded
        }
    
    @classmethod
    def validate_email_only(cls, email: str) -> bool:
        """Validate email address without phone requirement"""
        import re
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return False
        
        # Check for disposable emails (optional)
        disposable_domains = [
            'tempmail.com', 'throwaway.email', '10minutemail.com',
            'guerrillamail.com', 'mailinator.com'
        ]
        
        domain = email.split('@')[1].lower()
        if domain in disposable_domains:
            return False
        
        return True