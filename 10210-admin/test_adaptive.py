"""
Adaptive test script that tests available features
"""
import asyncio
import aiohttp
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "https://app.cuwapp.com"

async def test_basic_api():
    """Test basic API connectivity"""
    print("\n1. Testing API Connection...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/sessions") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print("✅ API is working!")
                    sessions = data.get('data', [])
                    print(f"   Found {len(sessions)} sessions")
                    
                    # Find working session
                    working_sessions = [s for s in sessions if s.get('status') == 'WORKING']
                    if working_sessions:
                        print(f"✅ Found {len(working_sessions)} WORKING session(s)")
                        return working_sessions[0]['name']
                    else:
                        print("⚠️  No WORKING sessions found")
                        return None
                else:
                    print(f"❌ API error: {resp.status}")
                    return None
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
        return None

async def test_message_send(session_name):
    """Test sending a message"""
    print(f"\n2. Testing Message Send with session '{session_name}'...")
    
    # You'll need to replace this with a real phone number
    test_number = "1234567890"  # Replace with your test number (without +)
    
    message_data = {
        "chatId": f"{test_number}@c.us",
        "text": f"Test message from WhatsApp Agent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "session": session_name
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BASE_URL}/api/messages/text",
                json=message_data
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print("✅ Message sent successfully!")
                    return True
                else:
                    error = await resp.text()
                    print(f"⚠️  Message send failed: {error}")
                    return False
    except Exception as e:
        print(f"❌ Error sending message: {str(e)}")
        return False

async def test_phase2_availability():
    """Check if Phase 2 features are available"""
    print("\n3. Checking Phase 2/3 Features...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test campaigns endpoint
            async with session.get(f"{BASE_URL}/api/campaigns") as resp:
                if resp.status == 200:
                    print("✅ Phase 2 campaign features are available!")
                    return True
                elif resp.status == 503:
                    print("⚠️  Phase 2 features not available (libmagic issue)")
                    return False
                else:
                    print(f"⚠️  Unexpected status: {resp.status}")
                    return False
    except Exception as e:
        print(f"❌ Error checking Phase 2: {str(e)}")
        return False

async def test_file_upload_simple():
    """Test file upload with simple CSV"""
    print("\n4. Testing File Upload (if available)...")
    
    # Create a simple test CSV
    csv_content = """phone_number,name,message
1234567890,Test User,Hello from test
"""
    
    with open("test_simple.csv", "w") as f:
        f.write(csv_content)
    
    try:
        async with aiohttp.ClientSession() as session:
            with open("test_simple.csv", "rb") as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename='test_simple.csv', content_type='text/csv')
                
                async with session.post(f"{BASE_URL}/api/files/upload", data=data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        print("✅ File upload endpoint is working!")
                        return True
                    else:
                        print(f"⚠️  File upload not available (status: {resp.status})")
                        return False
    except Exception as e:
        print(f"⚠️  File upload not available: {str(e)}")
        return False

async def main():
    print("="*60)
    print("🧪 ADAPTIVE WHATSAPP AGENT TEST")
    print("="*60)
    
    # Test basic API
    session_name = await test_basic_api()
    
    if session_name:
        # Ask if user wants to test message sending
        print(f"\n💡 Found working session: '{session_name}'")
        print("   To test message sending, update the phone number in the script")
        # await test_message_send(session_name)
    
    # Check Phase 2 availability
    phase2_available = await test_phase2_availability()
    
    if phase2_available:
        # Try file upload
        await test_file_upload_simple()
        print("\n✅ You can run test_phase3.py for full Phase 3 testing!")
    else:
        print("\n📝 To enable Phase 2/3 features:")
        print("   1. Stop the server (Ctrl+C)")
        print("   2. Run: pip install python-magic-bin==0.4.14")
        print("   3. Restart: python start.py")
        print("   4. Run: python test_phase3.py")
    
    print("\n" + "="*60)
    print("✅ Test Complete!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
