"""
Test script for group export functionality
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://app.cuwapp.com"
SESSION_NAME = "default"  # Change this to your active session
GROUP_ID = "120363419421019089@g.us"  # Change this to your test group ID

def test_export():
    """Test the group export functionality"""
    
    print("Testing Group Export Functionality")
    print("=" * 50)
    
    # Test 1: Get groups
    print("\n1. Getting all groups...")
    response = requests.get(f"{BASE_URL}/api/groups/{SESSION_NAME}")
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            groups = result.get('data', [])
            print(f"   ✓ Found {len(groups)} groups")
            
            # Display first few groups
            for i, group in enumerate(groups[:3]):
                group_id = group.get('id', {}).get('_serialized', 'Unknown')
                group_name = group.get('name', 'Unknown')
                participants = group.get('groupMetadata', {}).get('participants', [])
                print(f"   - {group_name} ({group_id}): {len(participants)} members")
            
            if groups and not GROUP_ID:
                # Use first group for testing
                test_group = groups[0]
                test_group_id = test_group.get('id', {}).get('_serialized')
                test_group_name = test_group.get('name', 'Unknown')
            else:
                test_group_id = GROUP_ID
                test_group_name = "Test Group"
        else:
            print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")
            return
    else:
        print(f"   ✗ HTTP Error: {response.status_code}")
        return
    
    # Test 2: Export specific group
    if test_group_id:
        print(f"\n2. Exporting group: {test_group_name} ({test_group_id})...")
        
        # URL encode the group ID if needed
        import urllib.parse
        encoded_group_id = urllib.parse.quote(test_group_id, safe='')
        
        response = requests.get(f"{BASE_URL}/api/groups/{SESSION_NAME}/{encoded_group_id}/export")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                export_data = result.get('data', {})
                print(f"   ✓ Export successful!")
                print(f"   - Participants: {export_data.get('participant_count', 0)}")
                print(f"   - JSON URL: {export_data.get('json_url', 'N/A')}")
                print(f"   - Excel URL: {export_data.get('excel_url', 'N/A')}")
                
                # Test 3: Download exported files
                print("\n3. Testing file downloads...")
                
                # Test JSON download
                json_url = export_data.get('json_url')
                if json_url:
                    json_response = requests.get(f"{BASE_URL}/static{json_url}")
                    if json_response.status_code == 200:
                        json_data = json_response.json()
                        print(f"   ✓ JSON file downloaded successfully")
                        print(f"   - Total participants in JSON: {json_data.get('total_participants', 0)}")
                        
                        # Show sample participant data
                        participants = json_data.get('participants', [])
                        if participants:
                            print("\n   Sample participant data:")
                            sample = participants[0]
                            for key, value in sample.items():
                                print(f"     - {key}: {value}")
                    else:
                        print(f"   ✗ Failed to download JSON: {json_response.status_code}")
                
                # Test Excel download
                excel_url = export_data.get('excel_url')
                if excel_url:
                    excel_response = requests.get(f"{BASE_URL}/static{excel_url}")
                    if excel_response.status_code == 200:
                        print(f"   ✓ Excel file downloaded successfully")
                        print(f"   - File size: {len(excel_response.content)} bytes")
                    else:
                        print(f"   ✗ Failed to download Excel: {excel_response.status_code}")
                        
            else:
                print(f"   ✗ Export failed: {result.get('error', 'Unknown error')}")
                error_details = result.get('detail', result.get('message', ''))
                if error_details:
                    print(f"   - Details: {error_details}")
        else:
            print(f"   ✗ HTTP Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   - Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"   - Response: {response.text}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_export()
