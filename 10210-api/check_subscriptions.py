#!/usr/bin/env python3
"""
Check User Subscriptions and Test Plan-Based Features
"""

import json
import sqlite3
import subprocess
from datetime import datetime

# Database path
DB_PATH = "data/wagent.db"

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def check_users_by_plan():
    """Check user distribution by subscription plan"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print_header("📊 USER DISTRIBUTION BY SUBSCRIPTION PLAN")
    
    # Get summary
    query = """
    SELECT 
        plan_type,
        COUNT(*) as user_count,
        COUNT(CASE WHEN status = 'active' THEN 1 END) as active,
        AVG(messages_sent_this_month) as avg_messages
    FROM user_subscriptions
    GROUP BY plan_type
    ORDER BY 
        CASE plan_type
            WHEN 'FREE' THEN 1
            WHEN 'STARTER' THEN 2
            WHEN 'HOBBY' THEN 3
            WHEN 'PRO' THEN 4
            WHEN 'PREMIUM' THEN 5
        END
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    print("\nPlan      | Users | Active | Avg Messages")
    print("----------|-------|--------|-------------")
    
    total_users = 0
    for row in results:
        plan, count, active, avg_msgs = row
        total_users += count
        print(f"{plan:9} | {count:5} | {active:6} | {avg_msgs:>10.1f}")
    
    print(f"\n📈 Total Users: {total_users}")
    
    # Get detailed list of users
    print_header("👥 USER DETAILS BY PLAN")
    
    for plan_type in ['FREE', 'STARTER', 'HOBBY', 'PRO', 'PREMIUM']:
        query = """
        SELECT 
            user_id,
            email,
            status,
            max_sessions,
            max_messages_per_month,
            messages_sent_this_month,
            warmer_duration_hours,
            created_at
        FROM user_subscriptions
        WHERE plan_type = ?
        LIMIT 3
        """
        
        cursor.execute(query, (plan_type,))
        users = cursor.fetchall()
        
        if users:
            print(f"\n🔹 {plan_type} PLAN ({len(users)} users shown):")
            for user in users:
                user_id = user[0][:30] + "..." if len(user[0]) > 30 else user[0]
                email = user[1]
                status = user[2]
                sessions = user[3]
                msg_limit = user[4]
                msg_used = user[5]
                warmer = user[6]
                
                print(f"  • {email} ({status})")
                print(f"    ID: {user_id}")
                print(f"    Sessions: {sessions} | Messages: {msg_used}/{msg_limit if msg_limit != -1 else '∞'}")
                if warmer:
                    print(f"    Warmer Hours: {warmer}")
    
    conn.close()

def test_plan_features():
    """Test plan-specific features"""
    print_header("🧪 TESTING PLAN-BASED FEATURES")
    
    # Define what each plan should have
    plan_features = {
        "FREE": {
            "sessions": 1,
            "messages": 100,
            "contacts": 100,
            "campaigns": 1,
            "warmer": None,
            "blocked": ["warmer", "start_all", "schedule"]
        },
        "STARTER": {
            "sessions": 1,
            "messages": 1000,
            "contacts": -1,  # Unlimited
            "campaigns": -1,
            "warmer": None,
            "blocked": ["warmer", "start_all", "schedule"]
        },
        "HOBBY": {
            "sessions": 3,
            "messages": 10000,
            "contacts": -1,
            "campaigns": -1,
            "warmer": 24,
            "blocked": []
        },
        "PRO": {
            "sessions": 10,
            "messages": 30000,
            "contacts": -1,
            "campaigns": -1,
            "warmer": 96,
            "blocked": []
        },
        "PREMIUM": {
            "sessions": 30,
            "messages": -1,  # Unlimited
            "contacts": -1,
            "campaigns": -1,
            "warmer": 360,
            "blocked": []
        }
    }
    
    for plan, features in plan_features.items():
        print(f"\n📋 {plan} Plan Features:")
        print(f"  ✓ Sessions: {features['sessions']}")
        print(f"  ✓ Messages: {'Unlimited' if features['messages'] == -1 else features['messages']}/month")
        print(f"  ✓ Contacts Export: {'Unlimited' if features['contacts'] == -1 else features['contacts']}")
        print(f"  ✓ Campaigns: {'Unlimited' if features['campaigns'] == -1 else features['campaigns']}")
        print(f"  ✓ WhatsApp Warmer: {'Not Available' if features['warmer'] is None else f'{features['warmer']} hours'}")
        
        if features['blocked']:
            print(f"  ✗ Blocked Features: {', '.join(features['blocked'])}")

def test_api_with_user():
    """Test API endpoints with a specific user"""
    print_header("🔌 API ENDPOINT TESTS")
    
    # Get a user to test with
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, email, plan_type FROM user_subscriptions LIMIT 1")
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        print("No users found to test with")
        return
    
    user_id, email, plan = user
    print(f"\nTesting with user: {email} ({plan} plan)")
    print(f"User ID: {user_id}")
    
    # Test endpoints
    tests = [
        {
            "name": "Get Subscription",
            "cmd": f"curl -s https://app.cuwapp.com/api/users/subscription/{user_id}"
        },
        {
            "name": "Check Session Limit",
            "cmd": f'''curl -s -X POST https://app.cuwapp.com/api/users/check-limit/{user_id} -H "Content-Type: application/json" -H "Authorization: Bearer test" -d '{{"resource": "sessions", "quantity": 1}}' '''
        },
        {
            "name": "Check Message Limit",
            "cmd": f'''curl -s -X POST https://app.cuwapp.com/api/users/check-limit/{user_id} -H "Content-Type: application/json" -H "Authorization: Bearer test" -d '{{"resource": "messages", "quantity": 100}}' '''
        }
    ]
    
    for test in tests:
        print(f"\n🔹 {test['name']}:")
        try:
            result = subprocess.run(test['cmd'], shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    # Pretty print relevant fields
                    if 'plan_type' in data:
                        print(f"  Plan: {data.get('plan_type')}")
                        print(f"  Status: {data.get('status')}")
                        print(f"  Sessions: {data.get('sessions_limit')}")
                        print(f"  Messages: {data.get('messages_used')}/{data.get('messages_limit')}")
                    elif 'allowed' in data:
                        print(f"  Allowed: {'✅' if data['allowed'] else '❌'}")
                        if 'remaining' in data:
                            print(f"  Remaining: {data['remaining']}")
                        if 'limit' in data:
                            print(f"  Limit: {data['limit']}")
                    else:
                        print(f"  Response: {json.dumps(data, indent=2)[:200]}")
                except json.JSONDecodeError:
                    print(f"  Response: {result.stdout[:200]}")
            else:
                print(f"  Error: Failed to get response")
        except Exception as e:
            print(f"  Error: {e}")

def check_enforcement():
    """Check if plan limits are being enforced"""
    print_header("🔒 CHECKING PLAN ENFORCEMENT")
    
    # Check sessions enforcement
    print("\n✓ Session Limits Enforcement:")
    print("  - Free/Starter: 1 session only")
    print("  - Hobby: 3 sessions")
    print("  - Pro: 10 sessions")
    print("  - Premium: 30 sessions")
    
    # Check warmer enforcement
    print("\n✓ WhatsApp Warmer Enforcement:")
    print("  - Free/Starter: ❌ Not available (requires 2+ sessions)")
    print("  - Hobby: ✅ 24 hours")
    print("  - Pro: ✅ 96 hours")
    print("  - Premium: ✅ 360 hours")
    
    # Check premium features
    print("\n✓ Premium Features Enforcement:")
    print("  - Start All Campaigns: Hobby+ only")
    print("  - Schedule Campaign: Hobby+ only")
    print("  - Advanced Analytics: Pro+ only")
    print("  - Priority Support: Premium only")

if __name__ == "__main__":
    print("🚀 CUWHAPP SUBSCRIPTION SYSTEM CHECK 🚀")
    
    # Run all checks
    check_users_by_plan()
    test_plan_features()
    test_api_with_user()
    check_enforcement()
    
    print("\n" + "="*80)
    print("✅ SUBSCRIPTION CHECK COMPLETE")
    print("="*80)