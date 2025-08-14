"""
Test with guaranteed working CSV
"""

import asyncio
import aiohttp
import pandas as pd
import os

BASE_URL = "https://app.cuwapp.com"

async def test_working_csv():
    """Create and test with a CSV that should definitely work"""
    print("🧪 Creating test CSV with WhatsApp contacts...\n")
    
    # Create a simple CSV with Nigerian phone numbers
    test_data = {
        'phone_number': ['2348012345678', '2348023456789', '2347034567890', '2348145678901', '2349056789012'],
        'name': ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown', 'Charlie Wilson'],
        'message': ['Hello {name}!', 'Hi {name}!', 'Hey {name}!', 'Greetings {name}!', 'Welcome {name}!']
    }
    
    df = pd.DataFrame(test_data)
    df.to_csv('working_test.csv', index=False)
    print(f"✅ Created working_test.csv with {len(df)} rows")
    print(f"   Columns: {list(df.columns)}")
    
    async with aiohttp.ClientSession() as session:
        # Upload the working test file
        print("\n1. Uploading working test file...")
        with open('working_test.csv', 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename='working_test.csv', content_type='text/csv')
            
            async with session.post(f"{BASE_URL}/api/files/upload", data=data) as resp:
                print(f"   Response status: {resp.status}")
                if resp.status == 200:
                    result = await resp.json()
                    print("   ✅ Upload successful!")
                    print(f"   File path: {result['data']['file_path']}")
                    file_path = result['data']['file_path']
                else:
                    error = await resp.text()
                    print(f"   ❌ Error: {error}")
                    return
        
        # If successful, try with the real file again
        print("\n2. Now trying with your real CSV...")
        real_csv = r"C:\Users\leg\Downloads\new_leads_complete.csv"
        
        if os.path.exists(real_csv):
            # First, create a subset of the real file
            print("   Creating subset of real file...")
            try:
                # Read original file
                df_real = pd.read_csv(real_csv, encoding='utf-8', nrows=5)
                
                # Select only essential columns if they exist
                essential_cols = ['phone_number', 'saved_name', 'country_name']
                available = [col for col in essential_cols if col in df_real.columns]
                
                if available:
                    df_subset = df_real[available]
                    # Rename columns to match expected format
                    if 'saved_name' in df_subset.columns:
                        df_subset = df_subset.rename(columns={'saved_name': 'name'})
                    
                    df_subset.to_csv('real_subset.csv', index=False)
                    print(f"   ✅ Created real_subset.csv with columns: {list(df_subset.columns)}")
                    
                    # Upload subset
                    with open('real_subset.csv', 'rb') as f:
                        data = aiohttp.FormData()
                        data.add_field('file', f, filename='real_subset.csv', content_type='text/csv')
                        
                        async with session.post(f"{BASE_URL}/api/files/upload", data=data) as resp:
                            print(f"   Response status: {resp.status}")
                            if resp.status == 200:
                                result = await resp.json()
                                print("   ✅ Real data subset upload successful!")
                                return result['data']['file_path']
                            else:
                                error = await resp.text()
                                print(f"   ❌ Error: {error}")
                
            except Exception as e:
                print(f"   ❌ Error processing real file: {e}")
    
    return file_path

async def main():
    file_path = await test_working_csv()
    
    if file_path:
        print(f"\n✅ SUCCESS! File uploaded: {file_path}")
        print("\n📝 Next steps:")
        print("1. You can now create a campaign with this file")
        print("2. Or use the dashboard at https://app.cuwapp.com")
        print("3. Navigate to 'Outbound Messages' section")

if __name__ == "__main__":
    asyncio.run(main())
