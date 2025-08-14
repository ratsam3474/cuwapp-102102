"""
Test with Real CSV File
Tests the campaign system with the user's actual data file
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime

BASE_URL = "https://app.cuwapp.com"
REAL_CSV_FILE = r"C:\Users\leg\Downloads\new_leads_complete.csv"

async def test_with_real_file():
    """Test campaign with real data file"""
    print("\n🚀 TESTING WITH REAL CSV FILE\n")
    
    # Check if file exists
    if not os.path.exists(REAL_CSV_FILE):
        print(f"❌ File not found: {REAL_CSV_FILE}")
        return
    
    print(f"✅ Found file: {os.path.basename(REAL_CSV_FILE)}")
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Upload file
        print("\n1. Uploading file...")
        with open(REAL_CSV_FILE, "rb") as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=os.path.basename(REAL_CSV_FILE), content_type='text/csv')
            
            async with session.post(f"{BASE_URL}/api/files/upload", data=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("success"):
                        print("✅ File uploaded successfully!")
                        upload_data = result['data']
                        file_path = upload_data['file_path']
                        print(f"   - Total rows: {upload_data['total_rows']}")
                        print(f"   - Headers: {upload_data['headers']}")
                        print(f"   - File size: {upload_data['file_size']} bytes")
                        
                        # Show suggested mapping
                        if 'suggested_mapping' in upload_data:
                            print(f"   - Suggested mapping: {upload_data['suggested_mapping']}")
                        
                        # Show sample data
                        if 'sample_data' in upload_data and upload_data['sample_data']:
                            print("\n   Sample data (first 3 rows):")
                            for i, row in enumerate(upload_data['sample_data'][:3]):
                                print(f"   Row {i+1}: {row}")
                    else:
                        print("❌ Upload failed:", result)
                        return
                else:
                    print(f"❌ Upload failed with status {resp.status}")
                    return
        
        # Step 2: Validate data with auto-detected mapping
        print("\n2. Validating data...")
        suggested_mapping = upload_data.get('suggested_mapping', {})
        
        # Ensure we have phone_number mapping
        if 'phone_number' not in suggested_mapping:
            # Try to find a phone column
            headers = upload_data['headers']
            phone_columns = [h for h in headers if 'phone' in h.lower() or 'mobile' in h.lower() or 'contact' in h.lower()]
            if phone_columns:
                suggested_mapping['phone_number'] = phone_columns[0]
            else:
                print("❌ No phone number column detected. Please specify manually.")
                print(f"   Available columns: {headers}")
                return
        
        validation_data = {
            "file_path": file_path,
            "column_mapping": json.dumps(suggested_mapping),
            "start_row": 1,
            "end_row": 10  # Validate first 10 rows
        }
        
        async with session.post(f"{BASE_URL}/api/files/validate", data=validation_data) as resp:
            if resp.status == 200:
                result = await resp.json()
                if result.get("success"):
                    validation = result['data']['validation_result']
                    print("✅ Data validation complete!")
                    print(f"   - Valid rows: {validation.get('valid_rows', 0)}")
                    print(f"   - Invalid rows: {validation.get('invalid_rows', 0)}")
                    print(f"   - Success rate: {validation.get('success_rate', 0)}%")
                    
                    # Show validation issues if any
                    if validation.get('summary', {}).get('common_errors'):
                        print("\n   Common validation errors:")
                        for error, count in validation['summary']['common_errors'][:3]:
                            print(f"   - {error}: {count} occurrences")
            else:
                print("❌ Validation failed")
        
        # Step 3: Get working session
        print("\n3. Getting WhatsApp sessions...")
        async with session.get(f"{BASE_URL}/api/sessions") as resp:
            if resp.status == 200:
                result = await resp.json()
                sessions = result.get("data", [])
                working_sessions = [s for s in sessions if s.get("status") == "WORKING"]
                
                if not working_sessions:
                    print("❌ No WORKING sessions found.")
                    print("   Please connect a WhatsApp session first!")
                    print("\n   Available sessions:")
                    for s in sessions:
                        print(f"   - {s['name']}: {s['status']}")
                    return
                
                session_name = working_sessions[0]["name"]
                print(f"✅ Found working session: {session_name}")
            else:
                print("❌ Could not get sessions")
                return
        
        # Step 4: Ask for confirmation before creating campaign
        total_rows = upload_data['total_rows']
        print(f"\n⚠️  Ready to create campaign with {total_rows} contacts")
        print("   This will send real WhatsApp messages!")
        
        # For safety, let's create a test campaign with just first 5 rows
        print("\n4. Creating TEST campaign (first 5 rows only)...")
        
        # Prepare message templates based on available fields
        available_fields = list(suggested_mapping.keys())
        message_templates = []
        
        if 'name' in available_fields:
            message_templates.append({"text": "Hi {name}! 👋 This is a test message from our automated system."})
            message_templates.append({"text": "Hello {name}! 🌟 Thank you for your interest in our services."})
        else:
            message_templates.append({"text": "Hi there! 👋 This is a test message from our automated system."})
            message_templates.append({"text": "Hello! 🌟 Thank you for your interest in our services."})
        
        campaign_data = {
            "campaign_name": f"Test Campaign - {os.path.basename(REAL_CSV_FILE)} - {datetime.now().strftime('%H:%M')}",
            "session_name": session_name,
            "file_path": file_path,
            "column_mapping": json.dumps(suggested_mapping),
            "message_mode": "multiple" if len(message_templates) > 1 else "single",
            "message_samples": json.dumps(message_templates),
            "use_csv_samples": "false",
            "start_row": "1",
            "end_row": "5",  # Only first 5 rows for testing
            "delay_seconds": "10",  # 10 seconds between messages
            "retry_attempts": "3",
            "max_daily_messages": "1000"
        }
        
        async with session.post(f"{BASE_URL}/api/files/create-campaign", data=campaign_data) as resp:
            if resp.status == 200:
                result = await resp.json()
                if result.get("success"):
                    campaign = result['data']
                    print("✅ Campaign created successfully!")
                    print(f"   - Campaign ID: {campaign['id']}")
                    print(f"   - Campaign Name: {campaign['name']}")
                    print(f"   - Status: {campaign['status']}")
                    print(f"   - Total rows: {campaign['total_rows']}")
                    print(f"   - Message mode: {campaign['message_mode']}")
                    
                    campaign_id = campaign['id']
                else:
                    print("❌ Campaign creation failed:", result)
                    return
            else:
                error = await resp.text()
                print(f"❌ Campaign creation failed: {error}")
                return
        
        # Step 5: Show campaign details and ask for confirmation to start
        print(f"\n5. Campaign ready to start")
        print(f"   ⚠️  This will send {campaign['total_rows']} WhatsApp messages")
        print(f"   📱 Using session: {session_name}")
        print(f"   ⏱️  Delay between messages: {campaign['delay_seconds']} seconds")
        print(f"   📊 Estimated completion time: {campaign['total_rows'] * campaign['delay_seconds'] / 60:.1f} minutes")
        
        # For automatic testing, we'll start it
        print("\n6. Starting campaign...")
        async with session.post(f"{BASE_URL}/api/campaigns/{campaign_id}/start") as resp:
            if resp.status == 200:
                result = await resp.json()
                if result.get("success"):
                    print("✅ Campaign started!")
                    print("   Messages will be sent in the background.")
                else:
                    print("❌ Campaign start failed:", result)
            else:
                print(f"❌ Campaign start failed with status {resp.status}")
        
        # Step 6: Monitor progress for a bit
        print("\n7. Monitoring campaign progress...")
        for i in range(3):
            await asyncio.sleep(5)  # Wait 5 seconds
            
            async with session.get(f"{BASE_URL}/api/campaigns/{campaign_id}") as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("success"):
                        campaign = result['data']
                        print(f"\n   Progress update {i+1}:")
                        print(f"   - Status: {campaign['status']}")
                        print(f"   - Processed: {campaign['processed_rows']}/{campaign['total_rows']}")
                        print(f"   - Success: {campaign['success_count']}")
                        print(f"   - Errors: {campaign['error_count']}")
                        print(f"   - Progress: {campaign.get('progress_percentage', 0):.1f}%")
                        
                        if campaign['status'] == 'COMPLETED':
                            print("\n   ✅ Campaign completed!")
                            break
        
        # Step 7: Get final stats
        print("\n8. Getting campaign statistics...")
        async with session.get(f"{BASE_URL}/api/campaigns/stats") as resp:
            if resp.status == 200:
                result = await resp.json()
                if result.get("success"):
                    stats = result['data']
                    print("✅ Overall statistics:")
                    print(f"   - Total campaigns: {stats['total_campaigns']}")
                    print(f"   - Active campaigns: {stats['active_campaigns']}")
                    print(f"   - Completed campaigns: {stats['completed_campaigns']}")
                    print(f"   - Total messages sent: {stats['total_messages_sent']}")
                    print(f"   - Overall success rate: {stats['overall_success_rate']}%")
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETE!")
    print("="*60)
    print(f"\n📝 Campaign Details:")
    print(f"   - Campaign ID: {campaign_id}")
    print(f"   - Dashboard: https://app.cuwapp.com")
    print(f"   - API Status: https://app.cuwapp.com/api/campaigns/{campaign_id}")
    print(f"   - Deliveries: https://app.cuwapp.com/api/files/campaigns/{campaign_id}/deliveries")
    print("\n💡 Note: The campaign is processing only the first 5 rows as a safety measure.")
    print("   To process the full file, create a new campaign with the desired row range.")

if __name__ == "__main__":
    asyncio.run(test_with_real_file())
