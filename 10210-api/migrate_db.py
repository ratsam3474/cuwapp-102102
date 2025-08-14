"""
Quick database migration to add column_mapping field
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)

def add_column_mapping_field():
    """Add column_mapping field to campaigns table"""
    try:
        # Connect to database
        conn = sqlite3.connect('campaign_database.db')
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(campaigns)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'column_mapping' not in columns:
            # Add the column
            cursor.execute("""
                ALTER TABLE campaigns
                ADD COLUMN column_mapping TEXT
            """)
            conn.commit()
            print("✅ Added column_mapping field to campaigns table")
        else:
            print("ℹ️ column_mapping field already exists")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")

if __name__ == "__main__":
    add_column_mapping_field()
