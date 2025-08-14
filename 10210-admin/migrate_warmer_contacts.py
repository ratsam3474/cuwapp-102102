#!/usr/bin/env python3
"""
Migration script to add missing columns to warmer_contacts table
"""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    """Add missing columns to warmer_contacts table"""
    db_path = "data/wagent.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Checking current warmer_contacts schema...")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(warmer_contacts)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"Current columns: {column_names}")
        
        # Add saved_to_whatsapp column if missing
        if 'saved_to_whatsapp' not in column_names:
            print("➕ Adding saved_to_whatsapp column...")
            cursor.execute("""
                ALTER TABLE warmer_contacts 
                ADD COLUMN saved_to_whatsapp BOOLEAN DEFAULT 0
            """)
            print("✅ saved_to_whatsapp column added")
        else:
            print("✓ saved_to_whatsapp column already exists")
        
        # Add whatsapp_saved_at column if missing
        if 'whatsapp_saved_at' not in column_names:
            print("➕ Adding whatsapp_saved_at column...")
            cursor.execute("""
                ALTER TABLE warmer_contacts 
                ADD COLUMN whatsapp_saved_at DATETIME
            """)
            print("✅ whatsapp_saved_at column added")
        else:
            print("✓ whatsapp_saved_at column already exists")
        
        # Commit changes
        conn.commit()
        
        # Verify changes
        cursor.execute("PRAGMA table_info(warmer_contacts)")
        new_columns = cursor.fetchall()
        new_column_names = [col[1] for col in new_columns]
        print(f"\n📋 Updated columns: {new_column_names}")
        
        conn.close()
        print("\n✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("WhatsApp Warmer Contacts Migration")
    print("=" * 60)
    print()
    
    migrate_database()