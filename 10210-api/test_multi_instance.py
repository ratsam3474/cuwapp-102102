#!/usr/bin/env python3
"""
Test script for WAHA multi-instance implementation
"""

import sys
import time
from datetime import datetime
from waha_pool_manager import waha_pool
from free_session_manager import free_session_manager
from waha_session_manager import waha_session_manager

def test_pool_manager():
    """Test the WAHA pool manager"""
    print("\n=== Testing WAHA Pool Manager ===")
    
    # Check pool status
    status = waha_pool.get_pool_status()
    print(f"Total instances: {status['total_instances']}")
    print(f"Total capacity: {status['total_capacity']}")
    print(f"Total sessions: {status['total_sessions']}")
    
    for instance in status['instances']:
        print(f"  Instance {instance['id']}: {instance['url']} - {instance['sessions']}/{instance['capacity']} sessions ({instance['utilization']})")
    
    return True

def test_user_assignment():
    """Test user assignment logic"""
    print("\n=== Testing User Assignment ===")
    
    # Test free user
    free_user_id = "free_user_123"
    free_session = "free_test_session"
    
    print(f"Testing free user: {free_user_id}")
    instance_url = waha_pool.get_or_create_instance_for_user(free_user_id, free_session)
    print(f"  Assigned to: {instance_url}")
    assert instance_url == "http://localhost:4500", "Free user should get default instance"
    
    # Test paid user (simulate by adding subscription)
    paid_user_id = "paid_user_456"
    paid_session = "paid_test_session"
    
    print(f"Testing paid user: {paid_user_id}")
    # Note: In real scenario, user would have subscription in DB
    instance_url = waha_pool.get_or_create_instance_for_user(paid_user_id, paid_session)
    print(f"  Assigned to: {instance_url}")
    
    return True

def test_free_user_cleanup():
    """Test free user session cleanup"""
    print("\n=== Testing Free User Cleanup ===")
    
    # Get initial stats
    stats = free_session_manager.get_stats()
    print(f"Active free sessions: {stats['active_free_sessions']}")
    print(f"Total free sessions: {stats['total_free_sessions']}")
    print(f"Timeout: {stats['inactivity_timeout_minutes']} minutes")
    
    # Create a test free session
    test_user = "test_free_user"
    test_session = f"test_session_{int(time.time())}"
    
    print(f"\nCreating test session: {test_session}")
    waha_session_manager.save_session_assignment(test_user, test_session, "http://localhost:4500")
    
    # Record activity
    print("Recording activity...")
    free_session_manager.record_activity(test_user, test_session)
    
    # Check if it's being tracked
    print("Session is now being tracked for inactivity")
    
    return True

def test_session_manager():
    """Test the session manager"""
    print("\n=== Testing Session Manager ===")
    
    test_user = "test_user_789"
    test_session = f"test_session_{int(time.time())}"
    
    print(f"Creating session for user: {test_user}")
    
    # Get WAHA client for session
    try:
        client = waha_session_manager.get_waha_client_for_session(test_user, test_session)
        print(f"  Got WAHA client with base URL: {client.base_url}")
        
        # Check instance URL was saved
        saved_url = waha_session_manager.get_session_instance_url(test_user, test_session)
        print(f"  Saved instance URL: {saved_url}")
        
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False

def test_activity_tracking():
    """Test activity tracking for free users"""
    print("\n=== Testing Activity Tracking ===")
    
    test_user = "free_test_user"
    test_session = "activity_test_session"
    
    # Save as free user session
    waha_session_manager.save_session_assignment(test_user, test_session, "http://localhost:4500")
    
    print(f"Tracking activity for session: {test_session}")
    
    # Track some activities
    for i in range(3):
        print(f"  Activity {i+1} at {datetime.now()}")
        waha_session_manager.track_activity(test_user, test_session)
        time.sleep(1)
    
    print("Activity tracking successful")
    return True

def main():
    """Run all tests"""
    print("=" * 50)
    print("WAHA Multi-Instance Implementation Test")
    print("=" * 50)
    
    tests = [
        ("Pool Manager", test_pool_manager),
        ("User Assignment", test_user_assignment),
        ("Free User Cleanup", test_free_user_cleanup),
        ("Session Manager", test_session_manager),
        ("Activity Tracking", test_activity_tracking)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, "✅ PASSED" if result else "❌ FAILED"))
        except Exception as e:
            print(f"\nError in {name}: {e}")
            results.append((name, "❌ ERROR"))
    
    print("\n" + "=" * 50)
    print("TEST RESULTS")
    print("=" * 50)
    for name, result in results:
        print(f"{name}: {result}")
    
    # Final pool status
    print("\n" + "=" * 50)
    print("FINAL POOL STATUS")
    print("=" * 50)
    status = waha_pool.get_pool_status()
    print(f"Total instances: {status['total_instances']}")
    print(f"Total capacity: {status['total_capacity']}")
    print(f"Total sessions: {status['total_sessions']}")
    
    for instance in status['instances']:
        print(f"  Instance {instance['id']} ({instance['type']}): {instance['sessions']}/{instance['capacity']} sessions")

if __name__ == "__main__":
    main()