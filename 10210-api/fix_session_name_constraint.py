#!/usr/bin/env python3
"""
Fix session_name unique constraint to be per-user instead of global
This allows multiple users to have sessions with the same display name
"""

import logging
import sqlite3
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_session_name_constraint():
    """Remove global unique constraint and add per-user unique constraint"""
    try:
        # Connect directly to SQLite database
        db_path = os.path.join(os.path.dirname(__file__), "data", "wagent.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # 1. Drop the old unique constraint on session_name (if it exists)
            logger.info("Dropping old unique constraint on session_name...")
            try:
                cursor.execute("DROP INDEX IF EXISTS ix_user_whatsapp_sessions_session_name")
                logger.info("Dropped old index")
            except Exception as e:
                logger.warning(f"Could not drop index (might not exist): {e}")
            
            # 2. Create new composite unique constraint
            logger.info("Creating new composite unique constraint (user_id + session_name)...")
            try:
                cursor.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS _user_session_name_uc 
                    ON user_whatsapp_sessions(user_id, session_name)
                """)
                logger.info("Successfully created composite unique constraint")
            except Exception as e:
                logger.warning(f"Constraint might already exist: {e}")
            
            # 3. Verify the change
            cursor.execute("""
                SELECT sql FROM sqlite_master 
                WHERE type='index' AND tbl_name='user_whatsapp_sessions'
            """)
            
            logger.info("Current indexes on user_whatsapp_sessions:")
            for row in cursor.fetchall():
                logger.info(f"  - {row[0]}")
            
            conn.commit()
            logger.info("Database constraint fixed successfully!")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error during migration, rolling back: {e}")
            raise
        finally:
            conn.close()
                
    except Exception as e:
        logger.error(f"Failed to fix constraint: {e}")
        raise

if __name__ == "__main__":
    print("Fixing session_name unique constraint...")
    fix_session_name_constraint()
    print("Done! Multiple users can now have sessions with the same display name.")