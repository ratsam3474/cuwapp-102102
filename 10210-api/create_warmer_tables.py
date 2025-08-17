#!/usr/bin/env python3
"""
Create warmer tables in production database
This script creates all necessary tables for the warmer feature
"""

import logging
import sqlite3
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_warmer_tables():
    """Create all warmer-related tables"""
    try:
        # Connect directly to SQLite database
        db_path = os.path.join(os.path.dirname(__file__), "data", "wagent.db")
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # 1. Create warmer_sessions table
            logger.info("Creating warmer_sessions table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS warmer_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    user_id VARCHAR(255),
                    orchestrator_session VARCHAR(100) NOT NULL,
                    participant_sessions TEXT NOT NULL,
                    status VARCHAR(50) DEFAULT 'inactive',
                    group_message_delay_min INTEGER DEFAULT 30,
                    group_message_delay_max INTEGER DEFAULT 120,
                    direct_message_delay_min INTEGER DEFAULT 45,
                    direct_message_delay_max INTEGER DEFAULT 180,
                    total_groups_created INTEGER DEFAULT 0,
                    total_messages_sent INTEGER DEFAULT 0,
                    total_group_messages INTEGER DEFAULT 0,
                    total_direct_messages INTEGER DEFAULT 0,
                    total_duration_minutes FLOAT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    started_at DATETIME,
                    stopped_at DATETIME,
                    updated_at DATETIME,
                    is_archived BOOLEAN DEFAULT 0,
                    archived_at DATETIME
                )
            """)
            logger.info("Created warmer_sessions table")
            
            # 2. Create warmer_groups table
            logger.info("Creating warmer_groups table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS warmer_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    warmer_session_id INTEGER NOT NULL,
                    group_id VARCHAR(255) NOT NULL,
                    group_name VARCHAR(255),
                    members TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    message_count INTEGER DEFAULT 0,
                    last_message_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (warmer_session_id) REFERENCES warmer_sessions(id)
                )
            """)
            logger.info("Created warmer_groups table")
            
            # 3. Create warmer_conversations table
            logger.info("Creating warmer_conversations table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS warmer_conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    warmer_session_id INTEGER NOT NULL,
                    message_id VARCHAR(255) UNIQUE,
                    sender_session VARCHAR(100),
                    recipient_session VARCHAR(100),
                    group_id VARCHAR(255),
                    message_type VARCHAR(20),
                    message_content TEXT,
                    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (warmer_session_id) REFERENCES warmer_sessions(id)
                )
            """)
            logger.info("Created warmer_conversations table")
            
            # 4. Create warmer_contacts table
            logger.info("Creating warmer_contacts table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS warmer_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    warmer_session_id INTEGER NOT NULL,
                    session_name VARCHAR(100),
                    contact_phone VARCHAR(50),
                    contact_name VARCHAR(255),
                    is_saved BOOLEAN DEFAULT 0,
                    saved_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (warmer_session_id) REFERENCES warmer_sessions(id)
                )
            """)
            logger.info("Created warmer_contacts table")
            
            # 5. Create indexes for better performance
            logger.info("Creating indexes...")
            
            # Index for warmer_sessions
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_warmer_sessions_user_id 
                ON warmer_sessions(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_warmer_sessions_status 
                ON warmer_sessions(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_warmer_sessions_is_archived 
                ON warmer_sessions(is_archived)
            """)
            
            # Index for warmer_groups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_warmer_groups_warmer_id 
                ON warmer_groups(warmer_session_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_warmer_groups_group_id 
                ON warmer_groups(group_id)
            """)
            
            # Index for warmer_conversations
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_warmer_conv_warmer_id 
                ON warmer_conversations(warmer_session_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_warmer_conv_group_id 
                ON warmer_conversations(group_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_warmer_conv_sender 
                ON warmer_conversations(sender_session)
            """)
            
            # Index for warmer_contacts
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_warmer_contacts_warmer_id 
                ON warmer_contacts(warmer_session_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_warmer_contacts_session 
                ON warmer_contacts(session_name)
            """)
            
            logger.info("Created all indexes")
            
            # 6. Verify tables were created
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE 'warmer_%'
            """)
            tables = cursor.fetchall()
            logger.info(f"Warmer tables in database: {[t[0] for t in tables]}")
            
            conn.commit()
            logger.info("All warmer tables created successfully!")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error during table creation, rolling back: {e}")
            raise
        finally:
            conn.close()
                
    except Exception as e:
        logger.error(f"Failed to create warmer tables: {e}")
        raise

if __name__ == "__main__":
    print("Creating warmer tables in production database...")
    create_warmer_tables()
    print("Done! All warmer tables have been created.")
    print("\nTables created:")
    print("  - warmer_sessions (with archive columns)")
    print("  - warmer_groups")
    print("  - warmer_conversations")
    print("  - warmer_contacts")
    print("\nYou can now run the other migration scripts.")