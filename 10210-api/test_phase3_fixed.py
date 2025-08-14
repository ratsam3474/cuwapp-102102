"""
Test Phase 3 Implementation - Fixed Version
Tests the enhanced campaign features
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "https://app.cuwapp.com"

async def test_file_upload():
    """Test file upload functionality"""
    print("\n1. Testing File Upload...")
    
    # Create a test CSV file
    csv_content = """phone_number,name,company,message_samples
1234567890,John Doe,ABC Corp,Hi {name}! Welcome to {company}
9876543210,Jane Smith,XYZ Ltd,Hello {name}! Great to have you at {company}
5555555555,Bob Johnson,Tech Inc,Hey {name}! {company} is excited to connect
"""
    
    with open("test_contacts.csv", "w") as f:
        f.write(csv_content)
    
    # Upload file
    async with aiohttp.ClientSession() as session:
        with open("test_contacts.csv", "rb") as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename='test_contacts.csv', content_type='text/csv')
            
            async with session.post(f"{BASE_URL}/api/files/upload", data=data) as resp:
                result = await resp.json()
                
                if result.get("success"):
                    print("✅ File upload successful!")
                    print(f"   - Total rows: {result['data']['total_rows']}")
                    print(f"   - Headers: {result['data']['headers']}")
                    print(f"   - File path: {result['data']['file_path']}")
                    return result['data']['file_path']
                else:
                    print("❌ File upload failed:", result.get("detail"))
                    return None

async def test_data_validation(file_path):
    """Test data validation"""
    print("\n2. Testing Data Validation...")
    
    validation_data = {
        "file_path": file_path,
        "column_mapping": json.dumps({"phone_number": "phone_number", "name": "name", "company": "company"}),
        "start_row": 1,
        "end_row": 3
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/api/files/validate", data=validation_data) as resp:
            result = await resp.json()
            
            if result.get("success"):
                print("✅ Data validation successful!")
                validation = result['data']['validation_result']
                print(f"   - Valid rows: {validation.get('valid_rows', 'N/A')}")
                print(f"   - Invalid rows: {validation.get('invalid_rows', 'N/A')}")
                print(f"   - Success rate: {validation.get('success_rate', 'N/A')}%")
                if validation.get('errors'):
                    print(f"   - Errors: {validation['errors'][:3]}...")  # Show first 3 errors
                return True
            else:
                print("❌ Data validation failed:", result.get("detail"))
                return False

async def test_campaign_creation(file_path):
    """Test campaign creation with uploaded file"""
    print("\n3. Testing Campaign Creation...")
    
    # First, get sessions to find a WORKING one
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/sessions") as resp:
            sessions_result = await resp.json()
            if sessions_result.get("success"):
                sessions = sessions_result.get("data", [])
                working_sessions = [s for s in sessions if s.get("status") == "WORKING"]
                
                if not working_sessions:
                    print("❌ No WORKING sessions found. Please connect a WhatsApp session first.")
                    return None
                
                session_name = working_sessions[0]["name"]
                print(f"   Using session: {session_name}")
            else:
                print("❌ Could not get sessions")
                return None
    
    campaign_data = {
        "campaign_name": f"Test Campaign {datetime.now().strftime('%H:%M:%S')}",  # Fixed field name
        "session_name": session_name,
        "file_path": file_path,
        "column_mapping": json.dumps({"phone_number": "phone_number", "name": "name", "company": "company"}),
        "message_mode": "multiple",
        "message_samples": json.dumps([
            {"text": "Hi {name}! 👋 Welcome to {company}!"},
            {"text": "Hello {name}! 🌟 Great to have you at {company}!"},
            {"text": "Hey {name}! 🎉 {company} is excited to connect with you!"}
        ]),
        "use_csv_samples": "false",  # Form data needs string
        "start_row": "1",
        "end_row": "3",
        "delay_seconds": "5",
        "retry_attempts": "3",
        "max_daily_messages": "1000"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/api/files/create-campaign", data=campaign_data) as resp:
            if resp.status == 200:
                result = await resp.json()
                if result.get("success"):
                    print("✅ Campaign created successfully!")
                    campaign = result['data']
                    print(f"   - Campaign ID: {campaign['id']}")
                    print(f"   - Campaign Name: {campaign['name']}")
                    print(f"   - Status: {campaign['status']}")
                    print(f"   - Total rows: {campaign['total_rows']}")
                    return campaign['id']
                else:
                    print("❌ Campaign creation failed:", result.get("detail"))
            else:
                error_text = await resp.text()
                print(f"❌ Campaign creation failed with status {resp.status}: {error_text}")
    
    return None

async def test_campaign_start(campaign_id):
    """Test starting campaign processing"""
    print("\n4. Testing Campaign Start...")
    
    # Start via main campaigns endpoint
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/api/campaigns/{campaign_id}/start") as resp:
            if resp.status == 200:
                result = await resp.json()
                if result.get("success"):
                    print("✅ Campaign started!")
                    
                    # Check processing status
                    await asyncio.sleep(2)  # Wait a bit
                    
                    # Get campaign status
                    async with session.get(f"{BASE_URL}/api/campaigns/{campaign_id}") as status_resp:
                        if status_resp.status == 200:
                            status_result = await status_resp.json()
                            if status_result.get("success"):
                                campaign = status_result['data']
                                print(f"   - Status: {campaign['status']}")
                                print(f"   - Processed: {campaign['processed_rows']}/{campaign['total_rows']}")
                    
                    return True
                else:
                    print("❌ Campaign start failed:", result.get("detail"))
            else:
                error_text = await resp.text()
                print(f"❌ Campaign start failed with status {resp.status}: {error_text}")
    
    return False

async def test_analytics(campaign_id):
    """Test campaign analytics"""
    print("\n5. Testing Analytics...")
    
    async with aiohttp.ClientSession() as session:
        # Get campaign stats
        async with session.get(f"{BASE_URL}/api/campaigns/stats") as resp:
            if resp.status == 200:
                result = await resp.json()
                if result.get("success"):
                    print("✅ Campaign stats retrieved!")
                    stats = result['data']
                    print(f"   - Total campaigns: {stats['total_campaigns']}")
                    print(f"   - Active campaigns: {stats['active_campaigns']}")
                    print(f"   - Total messages sent: {stats['total_messages_sent']}")
            else:
                print("❌ Stats endpoint failed")
        
        # Get specific campaign analytics
        async with session.get(f"{BASE_URL}/api/files/campaigns/{campaign_id}/analytics") as resp:
            if resp.status == 200:
                result = await resp.json()
                if result.get("success"):
                    print("✅ Campaign analytics retrieved!")
                    analytics = result.get('data', [])
                    if analytics:
                        print(f"   - Analytics records: {len(analytics)}")
                else:
                    print("❌ Analytics data not available")
            else:
                print("❌ Analytics endpoint not found")

async def test_processing_status():
    """Test processing status endpoint"""
    print("\n6. Testing Processing Status...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/files/processing/status") as resp:
            if resp.status == 200:
                result = await resp.json()
                if result.get("success"):
                    print("✅ Processing status retrieved!")
                    data = result['data']
                    print(f"   - Processor active campaigns: {data['processor']['total_active']}")
                    print(f"   - Scheduler running: {data['scheduler']['running']}")
                    return True
            else:
                print("❌ Processing status endpoint failed")
    
    return False

async def main():
    print("="*60)
    print("🧪 PHASE 3 IMPLEMENTATION TEST - FIXED VERSION")
    print("="*60)
    
    # Test file upload
    file_path = await test_file_upload()
    if not file_path:
        print("\n❌ Cannot proceed without successful file upload")
        return
    
    # Test data validation
    await test_data_validation(file_path)
    
    # Test campaign creation
    campaign_id = await test_campaign_creation(file_path)
    if not campaign_id:
        print("\n⚠️  Cannot test campaign operations without a campaign")
    else:
        # Test campaign start
        await test_campaign_start(campaign_id)
        
        # Test analytics
        await test_analytics(campaign_id)
    
    # Test processing status
    await test_processing_status()
    
    print("\n" + "="*60)
    print("✅ PHASE 3 TESTS COMPLETE!")
    print("="*60)
    
    print("\n📝 Notes:")
    print("- WebSocket real-time updates are not implemented yet")
    print("- Campaign will process in the background")
    print("- Check the dashboard for real-time status")
    print("- View deliveries at: /api/files/campaigns/{campaign_id}/deliveries")

if __name__ == "__main__":
    asyncio.run(main())
