#!/usr/bin/env python3
"""
Add archive columns to warmer_sessions table
This allows warmers to be soft-deleted while preserving analytics data
"""

import logging
import sqlite3
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_archive_columns():
    """Add is_archived and archived_at columns to warmer_sessions"""
    try:
        # Connect directly to SQLite database
        db_path = os.path.join(os.path.dirname(__file__), "data", "wagent.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # 1. Add is_archived column
            logger.info("Adding is_archived column...")
            try:
                cursor.execute("""
                    ALTER TABLE warmer_sessions 
                    ADD COLUMN is_archived BOOLEAN DEFAULT 0
                """)
                logger.info("Added is_archived column")
            except Exception as e:
                logger.warning(f"Column might already exist: {e}")
            
            # 2. Add archived_at column
            logger.info("Adding archived_at column...")
            try:
                cursor.execute("""
                    ALTER TABLE warmer_sessions 
                    ADD COLUMN archived_at DATETIME
                """)
                logger.info("Added archived_at column")
            except Exception as e:
                logger.warning(f"Column might already exist: {e}")
            
            # 3. Create index on is_archived for faster queries
            logger.info("Creating index on is_archived...")
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS ix_warmer_sessions_is_archived 
                    ON warmer_sessions(is_archived)
                """)
                logger.info("Created index on is_archived")
            except Exception as e:
                logger.warning(f"Index might already exist: {e}")
            
            # 4. Update any existing warmers to not be archived
            cursor.execute("""
                UPDATE warmer_sessions 
                SET is_archived = 0 
                WHERE is_archived IS NULL
            """)
            
            conn.commit()
            logger.info("Archive columns added successfully!")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error during migration, rolling back: {e}")
            raise
        finally:
            conn.close()
                
    except Exception as e:
        logger.error(f"Failed to add archive columns: {e}")
        raise

if __name__ == "__main__":
    print("Adding archive columns to warmer_sessions table...")
    add_archive_columns()
    print("Done! Warmers can now be archived instead of deleted, preserving analytics.")