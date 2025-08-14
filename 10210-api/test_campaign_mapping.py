"""
Test campaign creation with column mapping
"""

import requests
import json

# Configuration
BASE_URL = "https://app.cuwapp.com"
SESSION_NAME = "default"

# Test data
test_campaign = {
    "campaign_name": "Test Campaign with Mapping",
    "session_name": SESSION_NAME,
    "file_path": "static/uploads/campaigns/Anon Arbers_participants (2)_20250802_235914.xlsx",
    "column_mapping": json.dumps({
        "phone_number": "Phone Number",  # Map "Phone Number" column to phone_number field
        "name": "Public Name"            # Map "Public Name" column to name field
    }),
    "message_mode": "single",
    "message_samples": json.dumps([
        {"text": "Hello {name}! This is a test message from our WhatsApp campaign."}
    ]),
    "use_csv_samples": False,
    "start_row": 1,
    "end_row": 3,  # Just test with first 3 rows
    "delay_seconds": 5,
    "retry_attempts": 2,
    "max_daily_messages": 1000
}

def test_create_campaign():
    """Test creating a campaign with column mapping"""
    print("Creating campaign with column mapping...")
    
    response = requests.post(
        f"{BASE_URL}/api/files/create-campaign",
        data=test_campaign
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Campaign created successfully!")
        print(f"   Campaign ID: {result['data']['id']}")
        print(f"   Column mapping: {result['data'].get('column_mapping', {})}")
        return result['data']['id']
    else:
        print(f"❌ Failed to create campaign: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def test_start_campaign(campaign_id):
    """Test starting a campaign"""
    print(f"\nStarting campaign {campaign_id}...")
    
    response = requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/start")
    
    if response.status_code == 200:
        print(f"✅ Campaign started successfully!")
    else:
        print(f"❌ Failed to start campaign: {response.status_code}")
        print(f"   Error: {response.text}")

def check_campaign_status(campaign_id):
    """Check campaign status"""
    print(f"\nChecking campaign {campaign_id} status...")
    
    response = requests.get(f"{BASE_URL}/api/campaigns/{campaign_id}")
    
    if response.status_code == 200:
        result = response.json()
        campaign = result['data']
        print(f"✅ Campaign Status:")
        print(f"   Status: {campaign['status']}")
        print(f"   Progress: {campaign['processed_rows']}/{campaign['total_rows']}")
        print(f"   Success: {campaign['success_count']}")
        print(f"   Errors: {campaign['error_count']}")
    else:
        print(f"❌ Failed to get campaign status: {response.status_code}")

if __name__ == "__main__":
    # Run migration first
    print("Running database migration...")
    import migrate_db
    migrate_db.add_column_mapping_field()
    
    print("\n" + "="*50 + "\n")
    
    # Test campaign creation
    campaign_id = test_create_campaign()
    
    if campaign_id:
        # Start campaign
        test_start_campaign(campaign_id)
        
        # Wait a bit
        import time
        time.sleep(2)
        
        # Check status
        check_campaign_status(campaign_id)
