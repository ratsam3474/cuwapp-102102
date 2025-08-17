#!/usr/bin/env python3
"""
Create user_infrastructure table for tracking user containers
"""

import sqlite3
import sys
from datetime import datetime

def create_infrastructure_table():
    """Create the user_infrastructure table"""
    
    # Connect to database
    conn = sqlite3.connect('data/wagent.db')
    cursor = conn.cursor()
    
    try:
        # Create user_infrastructure table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_infrastructure (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(255) UNIQUE NOT NULL,
                container_id VARCHAR(255),
                container_name VARCHAR(255),
                api_url VARCHAR(255),
                warmer_url VARCHAR(255),
                campaign_url VARCHAR(255),
                app_port INTEGER,
                plan_type VARCHAR(50),
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                auto_stop_at TIMESTAMP
            )
        """)
        
        # Create indexes separately (SQLite syntax)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON user_infrastructure(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON user_infrastructure(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_port ON user_infrastructure(app_port)")
        
        print("✓ Created user_infrastructure table")
        
        # Add waha_instance_url column to user_whatsapp_sessions if it doesn't exist
        cursor.execute("PRAGMA table_info(user_whatsapp_sessions)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'waha_instance_url' not in columns:
            cursor.execute("""
                ALTER TABLE user_whatsapp_sessions 
                ADD COLUMN waha_instance_url VARCHAR(255)
            """)
            print("✓ Added waha_instance_url column to user_whatsapp_sessions")
        else:
            print("✓ waha_instance_url column already exists")
        
        # Commit changes
        conn.commit()
        print("\n✅ Database schema updated successfully!")
        
        # Show current tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\nCurrent tables: {[t[0] for t in tables]}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    create_infrastructure_table()