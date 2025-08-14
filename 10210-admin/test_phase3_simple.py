"""
Simple Phase 3 Test - Core Functionality Only
"""

import asyncio
import aiohttp
import json
from datetime import datetime

BASE_URL = "https://app.cuwapp.com"

async def test_basic_flow():
    """Test basic campaign flow without complex validation"""
    print("\n🧪 TESTING BASIC CAMPAIGN FLOW\n")
    
    # Step 1: Create test file
    csv_content = """phone_number,name,message
1234567890,Test User,Hello {name}!
9876543210,Another User,Hi {name}!
"""
    
    with open("simple_test.csv", "w") as f:
        f.write(csv_content)
    
    async with aiohttp.ClientSession() as session:
        # Step 2: Upload file
        print("1. Uploading file...")
        with open("simple_test.csv", "rb") as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename='simple_test.csv', content_type='text/csv')
            
            async with session.post(f"{BASE_URL}/api/files/upload", data=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("success"):
                        print("✅ File uploaded!")
                        file_path = result['data']['file_path']
                    else:
                        print("❌ Upload failed:", result)
                        return
                else:
                    print(f"❌ Upload failed with status {resp.status}")
                    return
        
        # Step 3: Get sessions
        print("\n2. Getting sessions...")
        async with session.get(f"{BASE_URL}/api/sessions") as resp:
            if resp.status == 200:
                result = await resp.json()
                sessions = result.get("data", [])
                working_sessions = [s for s in sessions if s.get("status") == "WORKING"]
                
                if working_sessions:
                    session_name = working_sessions[0]["name"]
                    print(f"✅ Found working session: {session_name}")
                else:
                    print("❌ No working sessions found")
                    print("   Please connect a WhatsApp session first!")
                    return
            else:
                print("❌ Could not get sessions")
                return
        
        # Step 4: Create campaign (simplified)
        print("\n3. Creating campaign...")
        campaign_data = {
            "campaign_name": f"Simple Test {datetime.now().strftime('%H:%M:%S')}",
            "session_name": session_name,
            "file_path": file_path,
            "column_mapping": json.dumps({"phone_number": "phone_number", "name": "name"}),
            "message_mode": "single",
            "message_samples": json.dumps([{"text": "Test message: {name}"}]),
            "use_csv_samples": "false",
            "start_row": "1",
            "end_row": "2",
            "delay_seconds": "3",
            "retry_attempts": "3",
            "max_daily_messages": "100"
        }
        
        async with session.post(f"{BASE_URL}/api/files/create-campaign", data=campaign_data) as resp:
            if resp.status == 200:
                result = await resp.json()
                if result.get("success"):
                    campaign_id = result['data']['id']
                    print(f"✅ Campaign created! ID: {campaign_id}")
                else:
                    print("❌ Campaign creation failed:", result)
                    return
            else:
                error = await resp.text()
                print(f"❌ Campaign creation failed: {error}")
                return
        
        # Step 5: Check campaign stats
        print("\n4. Checking campaign stats...")
        async with session.get(f"{BASE_URL}/api/campaigns/stats") as resp:
            if resp.status == 200:
                result = await resp.json()
                if result.get("success"):
                    stats = result['data']
                    print("✅ Campaign stats:")
                    print(f"   - Total campaigns: {stats.get('total_campaigns', 0)}")
                    print(f"   - Active campaigns: {stats.get('active_campaigns', 0)}")
        
        # Step 6: Start campaign
        print(f"\n5. Starting campaign {campaign_id}...")
        async with session.post(f"{BASE_URL}/api/campaigns/{campaign_id}/start") as resp:
            if resp.status == 200:
                result = await resp.json()
                if result.get("success"):
                    print("✅ Campaign started!")
                else:
                    print("❌ Campaign start failed:", result)
            else:
                print(f"❌ Campaign start failed with status {resp.status}")
        
        # Step 7: Check status after a moment
        print("\n6. Waiting 3 seconds...")
        await asyncio.sleep(3)
        
        print("7. Checking campaign status...")
        async with session.get(f"{BASE_URL}/api/campaigns/{campaign_id}") as resp:
            if resp.status == 200:
                result = await resp.json()
                if result.get("success"):
                    campaign = result['data']
                    print(f"✅ Campaign status: {campaign.get('status')}")
                    print(f"   - Processed: {campaign.get('processed_rows', 0)}/{campaign.get('total_rows', 0)}")
                    print(f"   - Success: {campaign.get('success_count', 0)}")
                    print(f"   - Errors: {campaign.get('error_count', 0)}")
    
    print("\n✅ BASIC TEST COMPLETE!")
    print(f"\n📝 View full campaign details at:")
    print(f"   - Dashboard: https://app.cuwapp.com")
    print(f"   - API: https://app.cuwapp.com/api/campaigns/{campaign_id}")

if __name__ == "__main__":
    asyncio.run(test_basic_flow())
