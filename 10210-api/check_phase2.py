#!/usr/bin/env python3
"""Check Phase 2 imports and dependencies"""

import sys
print("Python version:", sys.version)
print("\nChecking Phase 2 imports...\n")

# Check each import
imports_to_check = [
    ("jobs.manager", "CampaignManager"),
    ("jobs.models", "CampaignCreate, CampaignUpdate, MessageSample, MessageMode"),
    ("database.connection", "init_database, get_database_info"),
    ("utils.templates", "MessageTemplateEngine"),
    ("jobs.scheduler", "campaign_scheduler"),
    ("api_extensions", "router as file_router"),
]

for module_path, items in imports_to_check:
    try:
        if "as" in items:
            exec(f"from {module_path} import {items}")
        else:
            exec(f"from {module_path} import {items}")
        print(f"✅ Successfully imported: {module_path}")
    except ImportError as e:
        print(f"❌ Failed to import {module_path}: {str(e)}")
    except Exception as e:
        print(f"❌ Error with {module_path}: {type(e).__name__}: {str(e)}")

print("\n" + "="*50 + "\n")

# Check if campaign endpoints would be enabled
try:
    from jobs.manager import CampaignManager
    from jobs.models import CampaignCreate, CampaignUpdate, MessageSample, MessageMode
    from database.connection import init_database, get_database_info
    from utils.templates import MessageTemplateEngine
    from jobs.scheduler import campaign_scheduler
    from api_extensions import router as file_router
    PHASE_2_ENABLED = True
    print("✅ PHASE_2_ENABLED would be True")
except ImportError as e:
    PHASE_2_ENABLED = False
    print("❌ PHASE_2_ENABLED would be False")
    print(f"   Reason: {str(e)}")

print("\n" + "="*50 + "\n")

# Try to get active sessions from WAHA
try:
    from waha_functions import WAHAClient
    waha = WAHAClient()
    sessions = waha.get_sessions()
    print(f"✅ Found {len(sessions)} sessions:")
    for session in sessions:
        print(f"   - {session['name']}: {session['status']}")
        if session['status'] == 'WORKING':
            print(f"     ✅ This session is available for campaigns")
except Exception as e:
    print(f"❌ Failed to get sessions: {str(e)}")
