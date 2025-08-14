#!/usr/bin/env python3
"""
Free User Session Manager
Tracks activity and auto-deletes inactive free user sessions after 30 minutes
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional
from waha_functions import WAHAClient

logger = logging.getLogger(__name__)

class FreeUserSessionManager:
    def __init__(self, db_path: str = "data/wagent.db"):
        self.db_path = db_path
        self.free_instance_url = "http://localhost:4500"
        self.inactivity_timeout = timedelta(minutes=30)
        self.check_interval = 60  # Check every minute
        self.running = False
        
    def get_db_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def record_activity(self, user_id: str, session_name: str):
        """Record user activity to reset the 30-minute timer"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Update last_activity timestamp
            cursor.execute("""
                UPDATE waha_sessions 
                SET last_activity = ? 
                WHERE user_id = ? 
                AND session_name = ? 
                AND waha_instance_url = ?
                AND is_active = 1
            """, (datetime.now(), user_id, session_name, self.free_instance_url))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Activity recorded for free user {user_id} session {session_name}")
            
        except Exception as e:
            logger.error(f"Failed to record activity: {e}")
        finally:
            conn.close()
    
    def is_free_user(self, user_id: str) -> bool:
        """Check if user is on free plan"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT plan_type 
                FROM user_subscriptions 
                WHERE user_id = ? AND status = 'active'
            """, (user_id,))
            
            result = cursor.fetchone()
            
            # No subscription or free plan = free user
            return result is None or result[0].lower() == 'free'
            
        finally:
            conn.close()
    
    def cleanup_inactive_sessions(self):
        """Check and cleanup inactive free user sessions"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cutoff_time = datetime.now() - self.inactivity_timeout
            
            # Find inactive free user sessions
            cursor.execute("""
                SELECT user_id, session_name, 
                       COALESCE(last_activity, created_at) as last_active
                FROM waha_sessions 
                WHERE waha_instance_url = ? 
                AND is_active = 1
                AND COALESCE(last_activity, created_at) < ?
            """, (self.free_instance_url, cutoff_time))
            
            inactive_sessions = cursor.fetchall()
            
            if not inactive_sessions:
                return
            
            logger.info(f"Found {len(inactive_sessions)} inactive free sessions to cleanup")
            
            # Initialize WAHA client for free instance
            waha_client = WAHAClient(base_url=self.free_instance_url)
            
            for user_id, session_name, last_active in inactive_sessions:
                try:
                    # Check if this is actually a free user
                    if not self.is_free_user(user_id):
                        continue
                    
                    time_inactive = datetime.now() - datetime.fromisoformat(last_active)
                    logger.info(f"Cleaning up session {session_name} (inactive for {time_inactive})")
                    
                    # Try to logout from WhatsApp
                    try:
                        waha_client.logout_session(session_name)
                        logger.info(f"Logged out session {session_name}")
                    except Exception as e:
                        logger.warning(f"Failed to logout {session_name}: {e}")
                    
                    # Try to delete from WAHA
                    try:
                        waha_client.delete_session(session_name)
                        logger.info(f"Deleted session {session_name} from WAHA")
                    except Exception as e:
                        logger.warning(f"Failed to delete {session_name} from WAHA: {e}")
                    
                    # Mark as inactive in database
                    cursor.execute("""
                        UPDATE waha_sessions 
                        SET is_active = 0,
                            deleted_at = ?,
                            deletion_reason = ?
                        WHERE user_id = ? AND session_name = ?
                    """, (datetime.now(), "Inactivity timeout (30 minutes)", 
                          user_id, session_name))
                    
                    conn.commit()
                    logger.info(f"Successfully cleaned up inactive session {session_name}")
                    
                except Exception as e:
                    logger.error(f"Error cleaning up session {session_name}: {e}")
            
        except Exception as e:
            logger.error(f"Error in cleanup process: {e}")
        finally:
            conn.close()
    
    async def cleanup_loop(self):
        """Background task that runs cleanup periodically"""
        logger.info("Starting free user session cleanup loop")
        
        while self.running:
            try:
                self.cleanup_inactive_sessions()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
            
            # Wait before next check
            await asyncio.sleep(self.check_interval)
    
    def start(self):
        """Start the cleanup background task"""
        if not self.running:
            self.running = True
            asyncio.create_task(self.cleanup_loop())
            logger.info("Free session manager started")
    
    def stop(self):
        """Stop the cleanup background task"""
        self.running = False
        logger.info("Free session manager stopped")
    
    def get_stats(self) -> Dict:
        """Get statistics about free user sessions"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Count active free sessions
            cursor.execute("""
                SELECT COUNT(*) 
                FROM waha_sessions 
                WHERE waha_instance_url = ? AND is_active = 1
            """, (self.free_instance_url,))
            active_count = cursor.fetchone()[0]
            
            # Count total free sessions (including deleted)
            cursor.execute("""
                SELECT COUNT(*) 
                FROM waha_sessions 
                WHERE waha_instance_url = ?
            """, (self.free_instance_url,))
            total_count = cursor.fetchone()[0]
            
            # Count sessions deleted due to inactivity
            cursor.execute("""
                SELECT COUNT(*) 
                FROM waha_sessions 
                WHERE waha_instance_url = ? 
                AND deletion_reason LIKE '%timeout%'
            """, (self.free_instance_url,))
            timeout_count = cursor.fetchone()[0]
            
            return {
                "active_free_sessions": active_count,
                "total_free_sessions": total_count,
                "sessions_deleted_for_inactivity": timeout_count,
                "inactivity_timeout_minutes": int(self.inactivity_timeout.total_seconds() / 60),
                "check_interval_seconds": self.check_interval
            }
            
        finally:
            conn.close()

# Global instance
free_session_manager = FreeUserSessionManager()

# Decorator for tracking free user activity
def track_free_user_activity(func):
    """Decorator to track free user activity on API calls"""
    def wrapper(*args, **kwargs):
        # Try to extract user_id and session_name
        user_id = kwargs.get('user_id')
        session_name = kwargs.get('session_name')
        
        if user_id and session_name:
            # Check if free user and record activity
            if free_session_manager.is_free_user(user_id):
                free_session_manager.record_activity(user_id, session_name)
        
        # Execute original function
        return func(*args, **kwargs)
    
    return wrapper