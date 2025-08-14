#!/usr/bin/env python3
"""Debug script to check if Phase 2 outbound messaging is properly set up"""

import requests
import json

BASE_URL = "https://app.cuwapp.com"

def check_endpoints():
    """Check if all required endpoints are available"""
    print("=== Checking Endpoints ===\n")
    
    endpoints = [
        ("/api/sessions", "GET", "Sessions list"),
        ("/api/campaigns", "GET", "Campaigns list"),
        ("/api/campaigns/stats", "GET", "Campaign statistics"),
        ("/api/files/upload", "POST", "File upload (Phase 2)"),
        ("/api/files/create-campaign", "POST", "Campaign creation (Phase 2)"),
        ("/api/processing/status", "GET", "Processing status"),
    ]
    
    for endpoint, method, description in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            else:
                # Just check if endpoint exists
                response = requests.options(f"{BASE_URL}{endpoint}")
            
            if response.status_code in [200, 204, 405]:  # 405 for OPTIONS on POST endpoints
                print(f"✅ {endpoint} - {description}")
            else:
                print(f"❌ {endpoint} - {description} (Status: {response.status_code})")
        except Exception as e:
            print(f"❌ {endpoint} - {description} (Error: {str(e)})")
    
    print("\n" + "="*50 + "\n")

def check_sessions():
    """Check available WhatsApp sessions"""
    print("=== Checking WhatsApp Sessions ===\n")
    
    try:
        response = requests.get(f"{BASE_URL}/api/sessions")
        if response.status_code == 200:
            data = response.json()
            sessions = data.get('data', []) if data.get('success') else []
            
            if sessions:
                print(f"Found {len(sessions)} session(s):\n")
                for session in sessions:
                    status_icon = "✅" if session.get('status') == 'WORKING' else "⚠️"
                    print(f"{status_icon} {session.get('name')} - Status: {session.get('status')}")
                    if session.get('status') == 'WORKING':
                        print(f"   ✅ This session can be used for campaigns!")
            else:
                print("❌ No sessions found. You need to create a session first.")
        else:
            print(f"❌ Failed to get sessions (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ Error checking sessions: {str(e)}")
    
    print("\n" + "="*50 + "\n")

def check_campaigns():
    """Check existing campaigns"""
    print("=== Checking Campaigns ===\n")
    
    try:
        response = requests.get(f"{BASE_URL}/api/campaigns")
        if response.status_code == 200:
            data = response.json()
            
            # Handle different response formats
            if isinstance(data, dict) and 'data' in data:
                campaigns = data['data']
            elif isinstance(data, list):
                campaigns = data
            else:
                campaigns = []
            
            if campaigns:
                print(f"Found {len(campaigns)} campaign(s):\n")
                for campaign in campaigns:
                    print(f"📋 {campaign.get('name', 'Unnamed')}")
                    print(f"   Status: {campaign.get('status', 'Unknown')}")
                    print(f"   Session: {campaign.get('session_name', 'Unknown')}")
                    print(f"   Progress: {campaign.get('processed_rows', 0)}/{campaign.get('total_rows', 0)}")
                    print()
            else:
                print("No campaigns found. Ready to create your first campaign!")
        else:
            print(f"❌ Failed to get campaigns (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ Error checking campaigns: {str(e)}")

if __name__ == "__main__":
    print("\n🚀 WhatsApp Agent - Outbound Messaging Debug Tool\n")
    print("="*50 + "\n")
    
    check_endpoints()
    check_sessions()
    check_campaigns()
    
    print("\n=== Next Steps ===\n")
    print("1. Make sure you have at least one WORKING WhatsApp session")
    print("2. Go to https://app.cuwapp.com in your browser")
    print("3. Click on 'Outbound Messages' in the navigation")
    print("4. Click 'Create New Campaign' button")
    print("5. The session dropdown should now show your WORKING sessions")
    print("6. Upload the test_campaign.csv file created in this directory")
    print("\nIf you don't see sessions in the dropdown, refresh the page (F5)")
