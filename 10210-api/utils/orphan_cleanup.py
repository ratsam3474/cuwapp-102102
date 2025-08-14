"""
Cleanup orphaned WAHA sessions that don't have database records
"""

import logging
import requests
from database.connection import get_db
from database.user_sessions import UserWhatsAppSession
from datetime import datetime

logger = logging.getLogger(__name__)

class OrphanedSessionCleaner:
    """Manages cleanup of orphaned WAHA sessions"""
    
    def __init__(self, waha_url="http://localhost:4500"):
        self.waha_url = waha_url
        
    def find_orphaned_sessions(self):
        """Find WAHA sessions that don't have database records"""
        orphaned = []
        
        try:
            # Get all WAHA sessions
            response = requests.get(f"{self.waha_url}/api/sessions")
            if not response.ok:
                logger.error(f"Failed to get WAHA sessions: {response.status_code}")
                return orphaned
                
            waha_sessions = response.json()
            
            # Get all database session names (both display and WAHA names)
            db_session_names = set()
            with get_db() as db:
                all_sessions = db.query(UserWhatsAppSession).all()
                for session in all_sessions:
                    # Add both display name and WAHA name to the set
                    db_session_names.add(session.session_name)
                    if session.waha_session_name:
                        db_session_names.add(session.waha_session_name)
            
            # Find orphaned sessions
            for waha_session in waha_sessions:
                waha_name = waha_session.get('name')
                if waha_name not in db_session_names:
                    orphaned.append({
                        'name': waha_name,
                        'status': waha_session.get('status'),
                        'me': waha_session.get('me')
                    })
                    logger.warning(f"Found orphaned WAHA session: {waha_name}")
                    
        except Exception as e:
            logger.error(f"Error finding orphaned sessions: {e}")
            
        return orphaned
    
    def delete_orphaned_session(self, session_name):
        """Delete a single orphaned session from WAHA"""
        try:
            response = requests.delete(f"{self.waha_url}/api/sessions/{session_name}")
            if response.ok:
                logger.info(f"Deleted orphaned session: {session_name}")
                return True
            else:
                logger.error(f"Failed to delete session {session_name}: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error deleting session {session_name}: {e}")
            return False
    
    def cleanup_orphaned_sessions(self, auto_delete=False):
        """
        Find and optionally delete orphaned sessions
        
        Args:
            auto_delete: If True, automatically delete orphaned sessions.
                        If False, only report them.
        
        Returns:
            Dictionary with cleanup results
        """
        orphaned = self.find_orphaned_sessions()
        
        if not orphaned:
            logger.info("No orphaned sessions found")
            return {
                'found': 0,
                'deleted': 0,
                'sessions': []
            }
        
        deleted_count = 0
        
        for session in orphaned:
            session_name = session['name']
            
            # Skip certain system/test sessions
            if session_name in ['first', 'second']:
                logger.info(f"Skipping system/test session: {session_name}")
                continue
            
            if auto_delete:
                if self.delete_orphaned_session(session_name):
                    deleted_count += 1
            else:
                logger.info(f"Would delete orphaned session: {session_name} (auto_delete=False)")
        
        return {
            'found': len(orphaned),
            'deleted': deleted_count,
            'sessions': orphaned
        }
    
    def assign_orphaned_to_user(self, session_name, user_id):
        """
        Assign an orphaned WAHA session to a user by creating a database record
        
        Args:
            session_name: The WAHA session name
            user_id: The user ID to assign the session to
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with get_db() as db:
                # Check if session already exists for this user
                existing = db.query(UserWhatsAppSession).filter(
                    UserWhatsAppSession.user_id == user_id,
                    UserWhatsAppSession.waha_session_name == session_name
                ).first()
                
                if existing:
                    logger.info(f"Session {session_name} already assigned to user {user_id}")
                    return True
                
                # Create new session record
                new_session = UserWhatsAppSession(
                    user_id=user_id,
                    session_name=f"Recovered_{session_name}",
                    waha_session_name=session_name,
                    display_name=f"Recovered_{session_name}",
                    status="active",
                    is_primary=False
                )
                
                db.add(new_session)
                db.commit()
                
                logger.info(f"Assigned orphaned session {session_name} to user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error assigning session {session_name} to user {user_id}: {e}")
            return False


# Singleton instance
orphan_cleaner = OrphanedSessionCleaner()