#!/usr/bin/env python3
"""
Test Hyperswitch API connection
"""

import requests
import json

# Configuration
HYPERSWITCH_BASE_URL = "https://sandbox.hyperswitch.io"
HYPERSWITCH_API_KEY = "snd_MF6Nc4A5FY42UMtEN1BbdVFHhVC8pXYYATFZNgEIbiFTrA827lCTNO8FldzsBSeR"
HYPERSWITCH_PROFILE_ID = "pro_ja9RttZER7X829FB4iAM"

print("Testing Hyperswitch API Connection")
print("="*50)
print(f"URL: {HYPERSWITCH_BASE_URL}")
print(f"API Key: {HYPERSWITCH_API_KEY[:20]}...")
print(f"Profile ID: {HYPERSWITCH_PROFILE_ID}")
print("="*50)

# Test creating a payment
payment_data = {
    "amount": 4500,  # $45 in cents
    "currency": "USD",
    "confirm": False,
    "capture_method": "automatic",
    "customer_id": "test_customer_123",
    "email": "test@example.com",
    "description": "Test Payment",
    "return_url": "https://app.cuwapp.com/success",
    "profile_id": HYPERSWITCH_PROFILE_ID,
    "metadata": {
        "test": "true"
    }
}

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "api-key": HYPERSWITCH_API_KEY
}

print("\nTesting payment creation...")
print(f"Request URL: {HYPERSWITCH_BASE_URL}/payments")
print(f"Request data: {json.dumps(payment_data, indent=2)}")

try:
    response = requests.post(
        f"{HYPERSWITCH_BASE_URL}/payments",
        json=payment_data,
        headers=headers,
        timeout=10
    )
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.ok:
        data = response.json()
        print(f"\nSuccess! Payment created:")
        print(f"Payment ID: {data.get('payment_id')}")
        print(f"Client Secret: {data.get('client_secret')[:50]}..." if data.get('client_secret') else "No client secret")
        print(f"Status: {data.get('status')}")
        print(f"\nFull response:")
        print(json.dumps(data, indent=2))
    else:
        print(f"\nError Response:")
        print(response.text)
        
        # Try to parse error
        try:
            error_data = response.json()
            print(f"\nError details:")
            print(json.dumps(error_data, indent=2))
        except:
            pass
            
except requests.exceptions.ConnectionError as e:
    print(f"\n❌ Connection Error: Cannot connect to {HYPERSWITCH_BASE_URL}")
    print(f"Error: {e}")
    
except requests.exceptions.Timeout:
    print(f"\n❌ Timeout: Request took too long")
    
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")

print("\n" + "="*50)
print("Test complete!")