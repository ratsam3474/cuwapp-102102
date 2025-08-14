"""
Test Phase 3 Implementation
Tests the enhanced campaign features with real-time monitoring
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "https://app.cuwapp.com"
WS_URL = "ws://localhost:8000/ws/campaigns"

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
                    return result['data']['file_path']
                else:
                    print("❌ File upload failed:", result.get("detail"))
                    return None

async def test_websocket_connection():
    """Test WebSocket connection"""
    print("\n2. Testing WebSocket Connection...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(WS_URL) as ws:
                print("✅ WebSocket connected!")
                
                # Send ping
                await ws.send_json({"action": "ping"})
                
                # Wait for pong
                msg = await ws.receive_json()
                if msg.get("type") == "pong":
                    print("✅ WebSocket communication working!")
                
                await ws.close()
                
    except Exception as e:
        print(f"❌ WebSocket connection failed: {str(e)}")

async def test_campaign_creation(file_path):
    """Test campaign creation with uploaded file"""
    print("\n3. Testing Campaign Creation...")
    
    campaign_data = {
        "name": f"Test Campaign {datetime.now().strftime('%H:%M:%S')}",
        "session_name": "default",
        "file_path": file_path,
        "column_mapping": json.dumps({"phone_number": "phone_number", "name": "name"}),
        "message_mode": "multiple",
        "message_samples": json.dumps([
            {"text": "Hi {name}! 👋 Welcome to our service!"},
            {"text": "Hello {name}! 🌟 Great to have you here!"},
            {"text": "Hey {name}! 🎉 Thanks for joining us!"}
        ]),
        "use_csv_samples": False,
        "start_row": 1,
        "end_row": 3,
        "delay_seconds": 5,
        "retry_attempts": 3,
        "max_daily_messages": 1000
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/api/files/create-campaign", data=campaign_data) as resp:
            result = await resp.json()
            
            if result.get("success"):
                print("✅ Campaign created successfully!")
                print(f"   - Campaign ID: {result['data']['id']}")
                print(f"   - Campaign Name: {result['data']['name']}")
                return result['data']['id']
            else:
                print("❌ Campaign creation failed:", result.get("detail"))
                return None

async def test_realtime_monitoring(campaign_id):
    """Test real-time campaign monitoring"""
    print(f"\n4. Testing Real-time Monitoring for Campaign {campaign_id}...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Subscribe to campaign updates
            async with session.ws_connect(WS_URL) as ws:
                # Subscribe to specific campaign
                await ws.send_json({
                    "action": "subscribe",
                    "campaign_id": campaign_id
                })
                
                print("✅ Subscribed to campaign updates")
                print("   Waiting for real-time updates...")
                
                # Listen for updates (timeout after 30 seconds)
                start_time = time.time()
                update_count = 0
                
                while time.time() - start_time < 30:
                    try:
                        msg = await asyncio.wait_for(ws.receive_json(), timeout=1.0)
                        update_count += 1
                        
                        if msg.get("type") == "delivery_update":
                            print(f"   📨 Delivery: {msg['delivery']['phone']} - {msg['delivery']['status']}")
                        elif msg.get("type") == "campaign_progress":
                            print(f"   📊 Progress: {msg['progress']['percentage']}% ({msg['progress']['processed']}/{msg['progress']['total']})")
                        else:
                            print(f"   📡 Update: {msg.get('type')}")
                            
                    except asyncio.TimeoutError:
                        continue
                
                print(f"\n✅ Received {update_count} real-time updates!")
                
    except Exception as e:
        print(f"❌ Real-time monitoring failed: {str(e)}")

async def test_analytics():
    """Test analytics endpoint"""
    print("\n5. Testing Analytics...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/campaigns/analytics/realtime") as resp:
            if resp.status == 200:
                result = await resp.json()
                print("✅ Analytics endpoint working!")
                print(f"   - Active campaigns: {result['data']['active_campaigns']}")
                print(f"   - Recent deliveries: {result['data']['recent_deliveries']}")
            else:
                print("❌ Analytics endpoint failed")

async def main():
    """Run all Phase 3 tests"""
    print("=" * 60)
    print("🧪 PHASE 3 IMPLEMENTATION TEST")
    print("=" * 60)
    
    # Test 1: File Upload
    file_path = await test_file_upload()
    if not file_path:
        print("\n⚠️  Cannot continue without file upload. Please check the API.")
        return
    
    # Test 2: WebSocket
    await test_websocket_connection()
    
    # Test 3: Campaign Creation
    campaign_id = await test_campaign_creation(file_path)
    
    # Test 4: Real-time Monitoring (if campaign created)
    if campaign_id:
        # Start the campaign first
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BASE_URL}/api/campaigns/{campaign_id}/start") as resp:
                if resp.status == 200:
                    print(f"\n✅ Started campaign {campaign_id}")
                    await test_realtime_monitoring(campaign_id)
    
    # Test 5: Analytics
    await test_analytics()
    
    print("\n" + "=" * 60)
    print("✅ PHASE 3 TESTS COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    print("\n⚠️  Prerequisites:")
    print("1. Make sure WAHA is running on port 4500")
    print("2. Make sure the FastAPI server is running on port 8000")
    print("3. Make sure you have at least one WORKING session")
    print("\nPress Enter to start tests...")
    input()
    
    asyncio.run(main())
