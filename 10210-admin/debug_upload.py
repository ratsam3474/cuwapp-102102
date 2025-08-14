"""
Debug test for file upload
"""

import aiohttp
import asyncio
import os

BASE_URL = "https://app.cuwapp.com"
TEST_FILE = r"C:\Users\leg\Downloads\new_leads_complete.csv"

async def debug_upload():
    """Test file upload with error details"""
    print("🔍 DEBUG: Testing file upload\n")
    
    # First, check if file exists and size
    if not os.path.exists(TEST_FILE):
        print(f"❌ File not found: {TEST_FILE}")
        return
    
    file_size = os.path.getsize(TEST_FILE)
    print(f"✅ File found: {os.path.basename(TEST_FILE)}")
    print(f"   Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    # Create a small test CSV first
    print("\n1. Testing with small CSV file first...")
    test_csv = "phone_number,name\n2348012345678,Test User\n"
    
    with open("small_test.csv", "w") as f:
        f.write(test_csv)
    
    async with aiohttp.ClientSession() as session:
        # Test with small file
        with open("small_test.csv", "rb") as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename='small_test.csv', content_type='text/csv')
            
            async with session.post(f"{BASE_URL}/api/files/upload", data=data) as resp:
                print(f"   Response status: {resp.status}")
                if resp.status == 200:
                    result = await resp.json()
                    print("   ✅ Small file upload successful!")
                else:
                    error_text = await resp.text()
                    print(f"   ❌ Error: {error_text}")
        
        # Now test with the real file
        print(f"\n2. Testing with real file ({os.path.basename(TEST_FILE)})...")
        
        # Check file size limit (50MB)
        if file_size > 50 * 1024 * 1024:
            print(f"   ⚠️  File is larger than 50MB limit!")
            return
        
        try:
            with open(TEST_FILE, "rb") as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename=os.path.basename(TEST_FILE), content_type='text/csv')
                
                async with session.post(f"{BASE_URL}/api/files/upload", data=data) as resp:
                    print(f"   Response status: {resp.status}")
                    
                    if resp.status == 200:
                        result = await resp.json()
                        print("   ✅ Upload successful!")
                        print(f"   Response: {result}")
                    else:
                        # Get detailed error
                        content_type = resp.headers.get('content-type', '')
                        if 'application/json' in content_type:
                            error_json = await resp.json()
                            print(f"   ❌ Error (JSON): {error_json}")
                        else:
                            error_text = await resp.text()
                            print(f"   ❌ Error (Text): {error_text}")
                            
        except Exception as e:
            print(f"   ❌ Exception during upload: {type(e).__name__}: {str(e)}")
    
    # Also test if we can read the file locally
    print(f"\n3. Testing local file reading...")
    try:
        import pandas as pd
        df = pd.read_csv(TEST_FILE, nrows=5)
        print(f"   ✅ Can read file with pandas")
        print(f"   Columns: {list(df.columns)}")
        print(f"   Shape: {df.shape}")
    except Exception as e:
        print(f"   ❌ Error reading file: {e}")

if __name__ == "__main__":
    asyncio.run(debug_upload())
