#!/usr/bin/env python3
"""
Fix warmer tables - add missing columns
"""

import logging
import sqlite3
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_warmer_tables():
    """Add missing columns to warmer tables"""
    try:
        # Connect directly to SQLite database
        db_path = os.path.join(os.path.dirname(__file__), "data", "wagent.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Check if warmer_sessions table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='warmer_sessions'
            """)
            if not cursor.fetchone():
                logger.error("warmer_sessions table doesn't exist!")
                return False
            
            # Check which columns exist
            cursor.execute("PRAGMA table_info(warmer_sessions)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            logger.info(f"Existing columns: {column_names}")
            
            # Add missing columns
            if 'is_archived' not in column_names:
                logger.info("Adding is_archived column...")
                cursor.execute("""
                    ALTER TABLE warmer_sessions 
                    ADD COLUMN is_archived BOOLEAN DEFAULT 0
                """)
                logger.info("Added is_archived column")
            
            if 'archived_at' not in column_names:
                logger.info("Adding archived_at column...")
                cursor.execute("""
                    ALTER TABLE warmer_sessions 
                    ADD COLUMN archived_at DATETIME
                """)
                logger.info("Added archived_at column")
            
            # Create indexes (won't fail if they already exist)
            logger.info("Creating indexes...")
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_warmer_sessions_user_id 
                ON warmer_sessions(user_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_warmer_sessions_status 
                ON warmer_sessions(status)
            """)
            
            # Don't create index on is_archived yet - add it after column is confirmed
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_warmer_sessions_archived 
                ON warmer_sessions(is_archived)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_warmer_groups_warmer_id 
                ON warmer_groups(warmer_session_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_warmer_conv_warmer_id 
                ON warmer_conversations(warmer_session_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_warmer_contacts_warmer_id 
                ON warmer_contacts(warmer_session_id)
            """)
            
            logger.info("Created all indexes")
            
            # Update any NULL values
            cursor.execute("""
                UPDATE warmer_sessions 
                SET is_archived = 0 
                WHERE is_archived IS NULL
            """)
            
            # Verify final structure
            cursor.execute("PRAGMA table_info(warmer_sessions)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            logger.info(f"Final columns: {column_names}")
            
            conn.commit()
            logger.info("Warmer tables fixed successfully!")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error during fixing tables: {e}")
            raise
        finally:
            conn.close()
                
    except Exception as e:
        logger.error(f"Failed to fix warmer tables: {e}")
        raise

if __name__ == "__main__":
    print("Fixing warmer tables...")
    success = fix_warmer_tables()
    if success:
        print("✅ Done! Warmer tables have been fixed.")
        print("Archive columns added: is_archived, archived_at")
    else:
        print("❌ Failed to fix warmer tables")