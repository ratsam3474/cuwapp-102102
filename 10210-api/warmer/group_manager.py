"""
Group Manager for WhatsApp Warmer
Handles creating and managing warming groups
"""

import logging
import asyncio
from typing import List, Dict, Optional, Set, Any
from datetime import datetime
from sqlalchemy.orm import Session
from database.connection import get_db
from warmer.models import WarmerSession, WarmerGroup
from waha_functions import WAHAClient

logger = logging.getLogger(__name__)


class GroupManager:
    """Manages WhatsApp groups for warming sessions"""
    
    def __init__(self, waha_client: WAHAClient = None):
        self.waha = waha_client or WAHAClient()
        self.logger = logger
        self.target_group_count = 5  # Target number of common groups
    
    def _get_waha_client_for_session(self, session_name: str, user_id: str = None) -> WAHAClient:
        """Get WAHA client with correct instance URL for a session"""
        from database.connection import get_db
        from database.user_sessions import UserWhatsAppSession
        
        with get_db() as db:
            query = db.query(UserWhatsAppSession).filter(
                UserWhatsAppSession.session_name == session_name
            )
            if user_id:
                query = query.filter(UserWhatsAppSession.user_id == user_id)
            
            user_session = query.first()
            if user_session and hasattr(user_session, 'waha_instance_url') and user_session.waha_instance_url:
                self.logger.info(f"Using WAHA instance {user_session.waha_instance_url} for session {session_name}")
                return WAHAClient(base_url=user_session.waha_instance_url)
        
        # Fallback to default client
        self.logger.warning(f"No WAHA instance URL for session {session_name}, using default")
        return self.waha
    
    def _get_waha_session_name(self, session_name: str, user_id: str = None) -> str:
        """Convert display name to WAHA session name"""
        from database.user_sessions import UserWhatsAppSession
        from database.connection import get_db
        
        self.logger.info(f"Looking up session '{session_name}' for user_id='{user_id}'")
        
        waha_session_name = session_name
        with get_db() as db:
            query = db.query(UserWhatsAppSession).filter(
                UserWhatsAppSession.session_name == session_name
            )
            
            # CRITICAL: Always filter by user_id to avoid cross-user session conflicts
            if user_id:
                query = query.filter(UserWhatsAppSession.user_id == user_id)
                self.logger.info(f"Filtering by user_id: {user_id}")
            else:
                self.logger.warning(f"NO USER_ID PROVIDED - may get wrong user's session!")
            
            user_session = query.first()
            if user_session and user_session.waha_session_name:
                waha_session_name = user_session.waha_session_name
                self.logger.info(f"✓ Mapped '{session_name}' -> '{waha_session_name}' (user: {user_session.user_id})")
            else:
                self.logger.warning(f"✗ No mapping found for session '{session_name}' user_id='{user_id}'")
        
        return waha_session_name
    
    async def ensure_common_groups(self, warmer_session_id: int) -> Dict[str, Any]:
        """
        Ensure all sessions have the target number of common groups
        
        Args:
            warmer_session_id: ID of the warmer session
            
        Returns:
            Dictionary with results
        """
        try:
            # Get warmer session details
            with get_db() as db:
                warmer = db.query(WarmerSession).filter(WarmerSession.id == warmer_session_id).first()
                if not warmer:
                    raise ValueError(f"Warmer session {warmer_session_id} not found")
                
                orchestrator = warmer.orchestrator_session
                all_sessions = warmer.all_sessions
                user_id = warmer.user_id  # Get user_id from warmer session
            
            self.logger.info(f"Ensuring {self.target_group_count} common groups for {len(all_sessions)} sessions")
            
            # Get existing groups for all sessions
            existing_groups = await self._get_common_groups(all_sessions, user_id)
            common_group_count = len(existing_groups)
            
            results = {
                "existing_common_groups": common_group_count,
                "groups_to_create": max(0, self.target_group_count - common_group_count),
                "created_groups": [],
                "errors": []
            }
            
            # Create additional groups if needed
            if common_group_count < self.target_group_count:
                groups_needed = self.target_group_count - common_group_count
                self.logger.info(f"Need to create {groups_needed} more groups")
                
                for i in range(groups_needed):
                    group_name = f"Warmer Group {datetime.now().strftime('%Y%m%d_%H%M%S')}_{i+1}"
                    
                    try:
                        # Create group with orchestrator
                        group_result = await self._create_group(
                            orchestrator,
                            group_name,
                            all_sessions,
                            user_id
                        )
                        
                        if group_result["success"]:
                            # Save group to database
                            await self._save_group_to_db(
                                warmer_session_id,
                                group_result["group_id"],
                                group_name,
                                all_sessions
                            )
                            
                            results["created_groups"].append({
                                "group_id": group_result["group_id"],
                                "group_name": group_name
                            })
                            
                            # Update warmer statistics
                            with get_db() as db:
                                warmer = db.query(WarmerSession).filter(
                                    WarmerSession.id == warmer_session_id
                                ).first()
                                if warmer:
                                    warmer.total_groups_created += 1
                                    db.commit()
                        else:
                            results["errors"].append(group_result["error"])
                            
                        # Small delay between group creations
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        error_msg = f"Failed to create group {group_name}: {str(e)}"
                        self.logger.error(error_msg)
                        results["errors"].append(error_msg)
            else:
                self.logger.info(f"Already have {common_group_count} common groups, no need to create more")
                
                # Save existing groups to database if not already saved
                for group_id in existing_groups:
                    await self._ensure_group_in_db(warmer_session_id, group_id, all_sessions)
            
            results["total_common_groups"] = common_group_count + len(results["created_groups"])
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to ensure common groups: {str(e)}")
            raise
    
    async def _get_common_groups(self, sessions: List[str], user_id: str = None) -> Set[str]:
        """Get groups that all sessions are members of"""
        try:
            session_groups = {}
            
            # Get groups for each session
            for session in sessions:
                try:
                    # Convert display name to WAHA session name
                    waha_session_name = self._get_waha_session_name(session, user_id)
                    # Get WAHA client for this session
                    waha_client = self._get_waha_client_for_session(session, user_id)
                    groups = waha_client.get_groups(waha_session_name)
                    if isinstance(groups, list):
                        group_ids = set()
                        for g in groups:
                            if isinstance(g, dict) and "id" in g:
                                # Extract the _serialized field from the id object
                                id_obj = g.get("id", {})
                                if isinstance(id_obj, dict) and "_serialized" in id_obj:
                                    group_ids.add(id_obj["_serialized"])
                                elif isinstance(id_obj, str):
                                    # Fallback if id is already a string
                                    group_ids.add(id_obj)
                    else:
                        group_ids = set()
                    session_groups[session] = group_ids
                    self.logger.info(f"Session {session} is in {len(group_ids)} groups")
                except Exception as e:
                    self.logger.error(f"Failed to get groups for session {session}: {str(e)}")
                    session_groups[session] = set()
            
            # Find intersection of all groups
            if not session_groups:
                return set()
            
            common_groups = set.intersection(*session_groups.values()) if session_groups else set()
            self.logger.info(f"Found {len(common_groups)} common groups across all sessions")
            
            return common_groups
            
        except Exception as e:
            self.logger.error(f"Failed to get common groups: {str(e)}")
            return set()
    
    async def _create_group(
        self, 
        orchestrator: str, 
        group_name: str,
        all_sessions: List[str],
        user_id: str = None
    ) -> Dict[str, Any]:
        """Create a new group and add all sessions"""
        try:
            # Get phone numbers for all sessions except orchestrator
            participant_phones = []
            for session in all_sessions:
                if session != orchestrator:
                    try:
                        # Convert display name to WAHA session name
                        waha_session_name = self._get_waha_session_name(session, user_id)
                        # Get WAHA client for this session
                        waha_client = self._get_waha_client_for_session(session, user_id)
                        info = waha_client.get_session_info(waha_session_name)
                        if info and info.get("me"):
                            phone = info["me"].get("id", "")
                            if phone:
                                # Remove @s.whatsapp.net or @c.us suffix if present
                                phone = phone.split("@")[0]
                                participant_phones.append(phone)
                    except Exception as e:
                        self.logger.error(f"Failed to get phone for session {session}: {str(e)}")
            
            if not participant_phones:
                return {
                    "success": False,
                    "error": "No participant phone numbers found"
                }
            
            # Create group via WAHA API
            self.logger.info(f"Creating group {group_name} with participants: {participant_phones}")
            # Convert orchestrator display name to WAHA session name
            waha_orchestrator = self._get_waha_session_name(orchestrator, user_id)
            # Get WAHA client for orchestrator session
            waha_client = self._get_waha_client_for_session(orchestrator, user_id)
            result = waha_client.create_group(waha_orchestrator, group_name, participant_phones)
            
            if result and "id" in result:
                self.logger.info(f"Created group {group_name} with ID {result['id']}")
                return {
                    "success": True,
                    "group_id": result["id"],
                    "group_name": group_name
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to create group: {result}"
                }
                
        except Exception as e:
            error_msg = f"Error creating group {group_name}: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def _save_group_to_db(
        self,
        warmer_session_id: int,
        group_id: str,
        group_name: str,
        members: List[str]
    ):
        """Save group information to database"""
        try:
            with get_db() as db:
                # Check if group already exists
                existing = db.query(WarmerGroup).filter(
                    WarmerGroup.warmer_session_id == warmer_session_id,
                    WarmerGroup.group_id == group_id
                ).first()
                
                if not existing:
                    group = WarmerGroup(
                        warmer_session_id=warmer_session_id,
                        group_id=group_id,
                        group_name=group_name,
                        members=members,
                        is_active=True
                    )
                    db.add(group)
                    db.commit()
                    self.logger.info(f"Saved group {group_id} to database")
                    
        except Exception as e:
            self.logger.error(f"Failed to save group to database: {str(e)}")
    
    async def _ensure_group_in_db(
        self,
        warmer_session_id: int,
        group_id: str,
        members: List[str]
    ):
        """Ensure existing group is saved in database"""
        try:
            with get_db() as db:
                # Check if already in database
                existing = db.query(WarmerGroup).filter(
                    WarmerGroup.warmer_session_id == warmer_session_id,
                    WarmerGroup.group_id == group_id
                ).first()
                
                if not existing:
                    # Get group info from WAHA
                    # Note: We'd need to get group info from one of the sessions
                    group = WarmerGroup(
                        warmer_session_id=warmer_session_id,
                        group_id=group_id,
                        group_name=f"Existing Group {group_id[:8]}",
                        members=members,
                        is_active=True
                    )
                    db.add(group)
                    db.commit()
                    
        except Exception as e:
            self.logger.error(f"Failed to ensure group in database: {str(e)}")
    
    async def get_active_groups(self, warmer_session_id: int) -> List[Dict[str, Any]]:
        """Get all active groups for a warmer session"""
        try:
            with get_db() as db:
                groups = db.query(WarmerGroup).filter(
                    WarmerGroup.warmer_session_id == warmer_session_id,
                    WarmerGroup.is_active == True
                ).all()
                
                return [group.to_dict() for group in groups]
                
        except Exception as e:
            self.logger.error(f"Failed to get active groups: {str(e)}")
            return []
    
    async def update_group_activity(
        self,
        warmer_session_id: int,
        group_id: str,
        speaker: str
    ):
        """Update group activity after a message"""
        try:
            with get_db() as db:
                group = db.query(WarmerGroup).filter(
                    WarmerGroup.warmer_session_id == warmer_session_id,
                    WarmerGroup.group_id == group_id
                ).first()
                
                if group:
                    group.last_message_at = datetime.utcnow()
                    group.message_count += 1
                    group.last_speaker = speaker
                    db.commit()
                    
        except Exception as e:
            self.logger.error(f"Failed to update group activity: {str(e)}")
    
    async def join_groups_by_links(self, warmer_session_id: int, invite_links: List[str]) -> Dict[str, Any]:
        """
        Join groups using invite links for all sessions
        
        Args:
            warmer_session_id: ID of the warmer session
            invite_links: List of WhatsApp group invite links
            
        Returns:
            Dictionary with results
        """
        try:
            # Get warmer session details
            with get_db() as db:
                warmer = db.query(WarmerSession).filter(WarmerSession.id == warmer_session_id).first()
                if not warmer:
                    raise ValueError(f"Warmer session {warmer_session_id} not found")
                
                all_sessions = warmer.all_sessions
            
            self.logger.info(f"Joining {len(invite_links)} groups for {len(all_sessions)} sessions")
            
            results = {
                "total_links": len(invite_links),
                "sessions": len(all_sessions),
                "joined_groups": [],
                "errors": [],
                "validation_passed": False
            }
            
            # Join each group with each session
            for link_index, invite_link in enumerate(invite_links):
                group_joined_by_all = True
                group_info = {"link": invite_link, "sessions_joined": []}
                
                for session in all_sessions:
                    try:
                        # Join the group
                        self.logger.info(f"Session {session} joining group {link_index + 1}")
                        # Convert display name to WAHA session name
                        waha_session_name = self._get_waha_session_name(session, user_id)
                        # Get WAHA client for this session
                        waha_client = self._get_waha_client_for_session(session, user_id)
                        result = waha_client.join_group_by_link(waha_session_name, invite_link)
                        
                        if result and "id" in result:
                            group_info["sessions_joined"].append(session)
                            group_info["group_id"] = result["id"]
                            self.logger.info(f"Session {session} successfully joined group {result['id']}")
                        else:
                            group_joined_by_all = False
                            error_msg = f"Session {session} failed to join group {link_index + 1}"
                            self.logger.error(error_msg)
                            results["errors"].append(error_msg)
                            
                        # Small delay between join attempts
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        group_joined_by_all = False
                        error_msg = f"Error joining group for session {session}: {str(e)}"
                        self.logger.error(error_msg)
                        results["errors"].append(error_msg)
                
                if group_joined_by_all:
                    results["joined_groups"].append(group_info)
            
            # Validate that all sessions joined all groups
            if len(results["joined_groups"]) == len(invite_links):
                results["validation_passed"] = True
                self.logger.info("All sessions successfully joined all groups")
                
                # Save groups to database
                await self._save_joined_groups_to_db(warmer_session_id, all_sessions)
            else:
                self.logger.warning(f"Only {len(results['joined_groups'])} out of {len(invite_links)} groups were joined by all sessions")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to join groups by links: {str(e)}")
            raise
    
    async def _save_joined_groups_to_db(self, warmer_session_id: int, all_sessions: List[str]):
        """Save joined groups to database after successful joining"""
        try:
            # Get common groups again to save them
            common_groups = await self._get_common_groups(all_sessions)
            
            with get_db() as db:
                for group_id in common_groups:
                    # Check if already in database
                    existing = db.query(WarmerGroup).filter(
                        WarmerGroup.warmer_session_id == warmer_session_id,
                        WarmerGroup.group_id == group_id
                    ).first()
                    
                    if not existing:
                        group = WarmerGroup(
                            warmer_session_id=warmer_session_id,
                            group_id=group_id,
                            group_name=f"Joined Group {group_id[:8]}",
                            members=all_sessions,
                            is_active=True
                        )
                        db.add(group)
                
                db.commit()
                self.logger.info(f"Saved {len(common_groups)} groups to database")
                
        except Exception as e:
            self.logger.error(f"Failed to save joined groups: {str(e)}")