#!/usr/bin/env python3
"""
WAHA Session Manager
Central management for WAHA sessions with multi-instance support
"""

import logging
import sqlite3
from typing import Optional
from waha_functions import WAHAClient
from waha_pool_manager import waha_pool
from free_session_manager import free_session_manager

logger = logging.getLogger(__name__)

class WAHASessionManager:
    def __init__(self, db_path: str = "data/wagent.db"):
        self.db_path = db_path
        
    def get_db_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def get_waha_client_for_session(self, user_id: str, session_name: str) -> WAHAClient:
        """Get WAHA client with correct instance URL for a session"""
        
        # Check if session exists and get its instance URL
        instance_url = self.get_session_instance_url(user_id, session_name)
        
        if instance_url:
            # Session exists, use its assigned instance
            logger.debug(f"Using existing instance {instance_url} for session {session_name}")
            return WAHAClient(base_url=instance_url)
        
        # Session doesn't exist yet, determine where it should go
        instance_url = waha_pool.get_or_create_instance_for_user(user_id, session_name)
        
        # Save the assignment
        self.save_session_assignment(user_id, session_name, instance_url)
        
        logger.info(f"Assigned new session {session_name} to instance {instance_url}")
        return WAHAClient(base_url=instance_url)
    
    def get_session_instance_url(self, user_id: str, session_name: str) -> Optional[str]:
        """Get the WAHA instance URL for an existing session"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT waha_instance_url 
                FROM waha_sessions 
                WHERE user_id = ? AND session_name = ? AND is_active = 1
            """, (user_id, session_name))
            
            result = cursor.fetchone()
            return result[0] if result else None
            
        finally:
            conn.close()
    
    def save_session_assignment(self, user_id: str, session_name: str, instance_url: str):
        """Save or update the WAHA instance assignment for a session"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Extract instance ID from URL
            port = int(instance_url.split(':')[-1])
            instance_id = port - 4500
            
            # Check if session exists
            cursor.execute("""
                SELECT id FROM waha_sessions 
                WHERE user_id = ? AND session_name = ?
            """, (user_id, session_name))
            
            if cursor.fetchone():
                # Update existing session
                cursor.execute("""
                    UPDATE waha_sessions 
                    SET waha_instance_url = ?, 
                        waha_instance_id = ?,
                        last_activity = datetime('now')
                    WHERE user_id = ? AND session_name = ?
                """, (instance_url, instance_id, user_id, session_name))
            else:
                # Insert new session
                cursor.execute("""
                    INSERT INTO waha_sessions 
                    (user_id, session_name, waha_instance_url, waha_instance_id, 
                     is_active, created_at, last_activity)
                    VALUES (?, ?, ?, ?, 1, datetime('now'), datetime('now'))
                """, (user_id, session_name, instance_url, instance_id))
            
            conn.commit()
            logger.info(f"Saved session assignment: {session_name} -> {instance_url}")
            
        except Exception as e:
            logger.error(f"Failed to save session assignment: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def track_activity(self, user_id: str, session_name: str):
        """Track activity for a session (mainly for free users)"""
        
        # Check if free user
        if free_session_manager.is_free_user(user_id):
            free_session_manager.record_activity(user_id, session_name)
        
        # Update last_activity for all users
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE waha_sessions 
                SET last_activity = datetime('now')
                WHERE user_id = ? AND session_name = ? AND is_active = 1
            """, (user_id, session_name))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to track activity: {e}")
        finally:
            conn.close()
    
    def create_session(self, user_id: str, session_name: str, config: dict = None) -> dict:
        """Create a new WhatsApp session with instance assignment"""
        
        # Get the right WAHA client for this user
        waha_client = self.get_waha_client_for_session(user_id, session_name)
        
        # Create the session
        result = waha_client.create_session(session_name, config)
        
        # Track activity for free users
        self.track_activity(user_id, session_name)
        
        return result
    
    def send_text(self, user_id: str, session_name: str, chat_id: str, text: str) -> dict:
        """Send text message using correct instance"""
        
        # Get the right WAHA client
        waha_client = self.get_waha_client_for_session(user_id, session_name)
        
        # Send message
        result = waha_client.send_text({
            "session": session_name,
            "chatId": chat_id,
            "text": text
        })
        
        # Track activity
        self.track_activity(user_id, session_name)
        
        return result
    
    def get_session_info(self, user_id: str, session_name: str) -> dict:
        """Get session info from correct instance"""
        
        # Get the right WAHA client
        waha_client = self.get_waha_client_for_session(user_id, session_name)
        
        # Get session info
        result = waha_client.get_session(session_name)
        
        # Track activity
        self.track_activity(user_id, session_name)
        
        return result
    
    def delete_session(self, user_id: str, session_name: str):
        """Delete session from correct instance and database"""
        
        # Get the right WAHA client
        waha_client = self.get_waha_client_for_session(user_id, session_name)
        
        # Delete from WAHA
        try:
            waha_client.logout_session(session_name)
            waha_client.delete_session(session_name)
        except Exception as e:
            logger.error(f"Error deleting session from WAHA: {e}")
        
        # Mark as inactive in database
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE waha_sessions 
                SET is_active = 0,
                    deleted_at = datetime('now'),
                    deletion_reason = 'User requested'
                WHERE user_id = ? AND session_name = ?
            """, (user_id, session_name))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to mark session as deleted: {e}")
        finally:
            conn.close()

# Global instance
waha_session_manager = WAHASessionManager()