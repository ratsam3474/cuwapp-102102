#!/usr/bin/env python3
"""
Test WAHA Auto-Scaling based on user plans
"""

import requests
import json
import time
from datetime import datetime

# API endpoints
API_BASE = "https://app.cuwapp.com"
ADMIN_BASE = "https://admin.cuwapp.com"

# Test users with different plans
TEST_USERS = [
    {"user_id": "free_user_1", "plan": "free", "sessions_to_create": 2},
    {"user_id": "starter_user_1", "plan": "starter", "sessions_to_create": 1},
    {"user_id": "hobby_user_1", "plan": "hobby", "sessions_to_create": 3},
    {"user_id": "pro_user_1", "plan": "pro", "sessions_to_create": 10},
    {"user_id": "premium_user_1", "plan": "premium", "sessions_to_create": 30},
    {"user_id": "premium_user_2", "plan": "premium", "sessions_to_create": 30},
    {"user_id": "premium_user_3", "plan": "premium", "sessions_to_create": 30},
]

def setup_test_users():
    """Create test users with different subscription plans"""
    print("🔧 Setting up test users...")
    
    import sqlite3
    conn = sqlite3.connect("data/wagent.db")
    cursor = conn.cursor()
    
    for user in TEST_USERS:
        # Insert user subscription
        cursor.execute("""
            INSERT OR REPLACE INTO user_subscriptions 
            (user_id, email, username, plan_type, status, max_sessions, 
             max_messages_per_month, max_contacts_export, max_campaigns, 
             warmer_duration_hours, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'active', ?, 999999, 999999, 999999, 999999, 
                    datetime('now'), datetime('now'))
        """, (
            user['user_id'],
            f"{user['user_id']}@test.com",
            user['user_id'].replace('_', ' ').title(),
            user['plan'],
            user['sessions_to_create'] if user['plan'] != 'free' else 1
        ))
        print(f"  ✅ Created {user['plan']} user: {user['user_id']}")
    
    conn.commit()
    conn.close()
    print("✅ All test users created\n")

def create_session(user_id, session_number):
    """Create a WAHA session for a user"""
    session_name = f"{user_id}_session_{session_number}"
    
    response = requests.post(
        f"{API_BASE}/api/waha/sessions/start",
        json={
            "user_id": user_id,
            "session_name": session_name
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        return data.get('instance_url', 'Unknown')
    else:
        return f"Error: {response.status_code}"

def monitor_instances():
    """Check current instance status"""
    response = requests.get(f"{ADMIN_BASE}/api/waha/instances")
    if response.status_code == 200:
        return response.json()
    return None

def print_instance_status():
    """Print current instance status"""
    status = monitor_instances()
    if status:
        print("\n📊 Current Instance Status:")
        print(f"  Total Instances: {status['total_instances']}")
        print(f"  Total Capacity: {status['total_capacity']} sessions")
        print(f"  Active Sessions: {status['total_sessions']}")
        print("\n  Instance Details:")
        for instance in status['instances']:
            print(f"    [{instance['type']}] {instance['name']}:")
            print(f"      Port: {instance['port']}")
            print(f"      Sessions: {instance['sessions']}/{instance['capacity']}")
            print(f"      Utilization: {instance['utilization']}")
        print()

def run_scaling_test():
    """Run the auto-scaling test"""
    print("🚀 Starting WAHA Auto-Scaling Test")
    print("=" * 50)
    
    # Setup test users
    setup_test_users()
    
    # Show initial state
    print_instance_status()
    
    # Track session assignments
    session_assignments = {}
    
    print("📝 Creating sessions for each user...")
    print("-" * 50)
    
    for user in TEST_USERS:
        user_id = user['user_id']
        plan = user['plan']
        sessions_to_create = user['sessions_to_create']
        
        print(f"\n👤 User: {user_id} ({plan} plan)")
        print(f"   Creating {sessions_to_create} sessions...")
        
        user_instances = []
        for i in range(1, sessions_to_create + 1):
            instance_url = create_session(user_id, i)
            user_instances.append(instance_url)
            
            # Extract port from URL for display
            if "localhost:" in instance_url:
                port = instance_url.split(":")[-1]
                print(f"     Session {i}: Assigned to port {port}")
            else:
                print(f"     Session {i}: {instance_url}")
            
            # Small delay to see the scaling happen
            if i % 10 == 0:
                time.sleep(1)
                print_instance_status()
        
        session_assignments[user_id] = user_instances
        
        # Show status after each user
        print_instance_status()
    
    print("\n" + "=" * 50)
    print("📈 Final Scaling Results:")
    print("=" * 50)
    
    # Final status
    final_status = monitor_instances()
    if final_status:
        print(f"\n✅ Scaling Summary:")
        print(f"  - Started with: 1 instance (free tier)")
        print(f"  - Scaled to: {final_status['total_instances']} instances")
        print(f"  - Total capacity: {final_status['total_capacity']} sessions")
        print(f"  - Total active sessions: {final_status['total_sessions']}")
        
        if final_status.get('revenue_metrics'):
            metrics = final_status['revenue_metrics']
            print(f"\n💰 Revenue Impact:")
            print(f"  - Estimated monthly revenue: ${metrics['estimated_monthly_revenue']}")
            print(f"  - Infrastructure cost: {metrics['cost_per_instance']}")
    
    print("\n🎯 Session Distribution:")
    for user_id, instances in session_assignments.items():
        unique_instances = set(instances)
        print(f"  {user_id}: {len(instances)} sessions across {len(unique_instances)} instance(s)")

if __name__ == "__main__":
    run_scaling_test()