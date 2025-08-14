#!/usr/bin/env python3
"""
Sync WhatsApp sessions between WAHA and database
Fixes mismatched counters
"""

import sqlite3
import json
import subprocess

def get_waha_sessions():
    """Get all sessions from WAHA"""
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:4500/api/sessions"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            sessions = json.loads(result.stdout)
            return [s['name'] for s in sessions if isinstance(s, dict) and 'name' in s]
    except:
        pass
    return []

def sync_sessions():
    """Sync sessions and fix counters"""
    print("🔄 Syncing WhatsApp Sessions...")
    
    # Get WAHA sessions
    waha_sessions = get_waha_sessions()
    print(f"📱 Found {len(waha_sessions)} sessions in WAHA: {waha_sessions}")
    
    # Connect to database
    conn = sqlite3.connect("data/wagent.db")
    cursor = conn.cursor()
    
    # Get database sessions
    cursor.execute("SELECT session_name, user_id FROM user_whatsapp_sessions")
    db_sessions = cursor.fetchall()
    print(f"💾 Found {len(db_sessions)} sessions in database")
    
    # Find orphaned sessions (in DB but not in WAHA)
    orphaned = []
    for session_name, user_id in db_sessions:
        if session_name not in waha_sessions:
            orphaned.append((session_name, user_id))
            print(f"  ❌ Orphaned: {session_name} (user: {user_id[:20]}...)")
    
    # Delete orphaned sessions
    if orphaned:
        print(f"\n🗑️  Deleting {len(orphaned)} orphaned sessions...")
        for session_name, _ in orphaned:
            cursor.execute("DELETE FROM user_whatsapp_sessions WHERE session_name = ?", (session_name,))
        conn.commit()
    
    # Update all user counters
    print("\n📊 Updating session counters...")
    cursor.execute("""
        SELECT DISTINCT user_id 
        FROM user_subscriptions
    """)
    users = cursor.fetchall()
    
    for (user_id,) in users:
        # Count actual sessions
        cursor.execute("""
            SELECT COUNT(*) 
            FROM user_whatsapp_sessions 
            WHERE user_id = ? 
            AND status IN ('created', 'started', 'scan', 'active')
        """, (user_id,))
        actual_count = cursor.fetchone()[0]
        
        # Update counter
        cursor.execute("""
            UPDATE user_subscriptions 
            SET current_sessions = ? 
            WHERE user_id = ?
        """, (actual_count, user_id))
        
        # Get user info
        cursor.execute("""
            SELECT email, plan_type, max_sessions 
            FROM user_subscriptions 
            WHERE user_id = ?
        """, (user_id,))
        email, plan, max_sessions = cursor.fetchone()
        
        if actual_count > 0:
            print(f"  ✅ {email}: {actual_count}/{max_sessions} sessions ({plan})")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Sync complete!")

if __name__ == "__main__":
    sync_sessions()