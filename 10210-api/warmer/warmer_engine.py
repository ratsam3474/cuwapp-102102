"""
WhatsApp Warmer Engine
Main engine that coordinates the warming process
"""

import logging
import asyncio
import random
from typing import List, Dict, Optional, Set, Any
from datetime import datetime
from sqlalchemy.orm import Session
from database.connection import get_db
from warmer.models import WarmerSession, WarmerGroup, WarmerStatus, MessageType
from warmer.contact_manager import ContactManager
from warmer.group_manager import GroupManager
from warmer.orchestrator import ConversationOrchestrator
from waha_functions import WAHAClient

logger = logging.getLogger(__name__)


class WarmerEngine:
    """Main engine for WhatsApp account warming"""
    
    def __init__(self, waha_client: WAHAClient = None):
        self.waha = waha_client or WAHAClient()
        self.logger = logger
        self.contact_manager = ContactManager(waha_client)
        self.group_manager = GroupManager(waha_client)
        self.orchestrator = ConversationOrchestrator()
        
        # Active warming tasks
        self.active_warmers: Dict[int, asyncio.Task] = {}
        self.stop_flags: Dict[int, bool] = {}
    
    async def create_warmer_session(
        self,
        name: str,
        orchestrator_session: str,
        participant_sessions: List[str],
        config: Optional[Dict] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new warmer session"""
        try:
            # Validate sessions
            if len(participant_sessions) < 1:
                raise ValueError("At least one participant session required")
            
            if orchestrator_session in participant_sessions:
                raise ValueError("Orchestrator cannot be in participant list")
            
            all_sessions = [orchestrator_session] + participant_sessions
            
            # Verify all sessions are working
            for session in all_sessions:
                if not await self._verify_session(session):
                    raise ValueError(f"Session '{session}' is not available or not working")
            
            # Create warmer session in database
            with get_db() as db:
                warmer = WarmerSession(
                    name=name,
                    user_id=user_id,  # Track ownership
                    orchestrator_session=orchestrator_session,
                    participant_sessions=participant_sessions,
                    status=WarmerStatus.INACTIVE.value
                )
                
                # Apply custom configuration if provided
                if config:
                    if "group_message_delay_min" in config:
                        warmer.group_message_delay_min = config["group_message_delay_min"]
                    if "group_message_delay_max" in config:
                        warmer.group_message_delay_max = config["group_message_delay_max"]
                    if "direct_message_delay_min" in config:
                        warmer.direct_message_delay_min = config["direct_message_delay_min"]
                    if "direct_message_delay_max" in config:
                        warmer.direct_message_delay_max = config["direct_message_delay_max"]
                
                db.add(warmer)
                db.commit()
                db.refresh(warmer)
                
                warmer_id = warmer.id
            
            self.logger.info(f"Created warmer session '{name}' with ID {warmer_id}")
            
            return {
                "success": True,
                "warmer_id": warmer_id,
                "name": name,
                "orchestrator": orchestrator_session,
                "participants": participant_sessions,
                "total_sessions": len(all_sessions)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create warmer session: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def start_warming(self, warmer_session_id: int) -> Dict[str, Any]:
        """Start the warming process"""
        try:
            # Check if already warming
            if warmer_session_id in self.active_warmers:
                return {
                    "success": False,
                    "error": "Warmer session is already active"
                }
            
            # Update status
            with get_db() as db:
                warmer = db.query(WarmerSession).filter(
                    WarmerSession.id == warmer_session_id
                ).first()
                
                if not warmer:
                    return {
                        "success": False,
                        "error": f"Warmer session {warmer_session_id} not found"
                    }
                
                # Simply start a new session - duration is already saved when stopped
                warmer.status = WarmerStatus.WARMING.value
                warmer.started_at = datetime.utcnow()
                warmer.stopped_at = None  # Clear stopped_at for new session
                db.commit()
            
            # Initialize warming
            self.logger.info(f"Initializing warmer session {warmer_session_id}")
            
            # Step 1: Save all contacts
            contact_result = await self.contact_manager.save_all_contacts(warmer_session_id)
            self.logger.info(f"Saved {contact_result['total_contacts_saved']} contacts")
            
            # Step 2: Ensure common groups
            group_result = await self.group_manager.ensure_common_groups(warmer_session_id)
            self.logger.info(f"Ensured {group_result['total_common_groups']} common groups")
            
            # Step 3: Start warming task
            self.stop_flags[warmer_session_id] = False
            task = asyncio.create_task(self._warming_loop(warmer_session_id))
            self.active_warmers[warmer_session_id] = task
            
            return {
                "success": True,
                "message": "Warming started successfully",
                "contacts_saved": contact_result["total_contacts_saved"],
                "groups_ready": group_result["total_common_groups"]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to start warming: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def stop_warming(self, warmer_session_id: int) -> Dict[str, Any]:
        """Stop the warming process"""
        try:
            # Set stop flag
            if warmer_session_id in self.stop_flags:
                self.stop_flags[warmer_session_id] = True
            
            # Cancel task if exists
            if warmer_session_id in self.active_warmers:
                task = self.active_warmers[warmer_session_id]
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                del self.active_warmers[warmer_session_id]
            
            # Update status
            with get_db() as db:
                warmer = db.query(WarmerSession).filter(
                    WarmerSession.id == warmer_session_id
                ).first()
                
                if warmer:
                    warmer.status = WarmerStatus.STOPPED.value
                    warmer.stopped_at = datetime.utcnow()
                    
                    # Calculate session duration and add to total
                    if warmer.started_at and warmer.stopped_at:
                        session_duration = (warmer.stopped_at - warmer.started_at).total_seconds() / 60
                        if warmer.total_duration_minutes is None:
                            warmer.total_duration_minutes = 0.0
                        
                        self.logger.info(f"Stopping warmer: Session duration={session_duration:.2f}min, "
                                       f"Previous total={warmer.total_duration_minutes:.2f}min")
                        
                        warmer.total_duration_minutes += session_duration
                        
                        self.logger.info(f"New total duration={warmer.total_duration_minutes:.2f}min")
                    
                    db.commit()
            
            # Clean up stop flag
            if warmer_session_id in self.stop_flags:
                del self.stop_flags[warmer_session_id]
            
            self.logger.info(f"Stopped warmer session {warmer_session_id}")
            
            return {
                "success": True,
                "message": "Warming stopped successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to stop warming: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _warming_loop(self, warmer_session_id: int):
        """Main warming loop"""
        try:
            self.logger.info(f"Starting warming loop for session {warmer_session_id}")
            last_limit_check = asyncio.get_event_loop().time()
            check_interval = 60  # Check every 60 seconds
            
            while not self.stop_flags.get(warmer_session_id, True):
                # Check if time limit exceeded (every 60 seconds)
                current_time = asyncio.get_event_loop().time()
                if current_time - last_limit_check >= check_interval:
                    if await self._check_time_limit_exceeded(warmer_session_id):
                        self.logger.warning(f"Warmer {warmer_session_id} exceeded time limit, stopping automatically")
                        
                        # Update warmer status with notification
                        with get_db() as db:
                            warmer = db.query(WarmerSession).filter(WarmerSession.id == warmer_session_id).first()
                            if warmer:
                                warmer.status = WarmerStatus.INACTIVE.value
                                warmer.stopped_at = datetime.utcnow()
                                # Store notification in database or status field
                                db.commit()
                        
                        await self.stop_warming(warmer_session_id)
                        break
                    last_limit_check = current_time
                try:
                    # Get active groups
                    groups = await self.group_manager.get_active_groups(warmer_session_id)
                    
                    if not groups:
                        self.logger.warning(f"No active groups for warmer {warmer_session_id}")
                        await asyncio.sleep(60)
                        continue
                    
                    # Randomly decide between group and direct message
                    # 70% chance for group message, 30% for direct message
                    if random.random() < 0.7 and groups:
                        # Send group message
                        await self._send_group_message(warmer_session_id, groups)
                    else:
                        # Send direct message
                        await self._send_direct_message(warmer_session_id)
                    
                    # Wait before next message
                    delay = self.orchestrator.get_random_delay(
                        is_group=True,  # Use group delay as default
                        warmer_session_id=warmer_session_id
                    )
                    
                    self.logger.debug(f"Waiting {delay} seconds before next message")
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    self.logger.error(f"Error in warming loop: {str(e)}")
                    await asyncio.sleep(30)  # Wait before retrying
            
            self.logger.info(f"Warming loop ended for session {warmer_session_id}")
            
        except asyncio.CancelledError:
            self.logger.info(f"Warming loop cancelled for session {warmer_session_id}")
            raise
        except Exception as e:
            self.logger.error(f"Fatal error in warming loop: {str(e)}")
    
    async def _send_group_message(self, warmer_session_id: int, groups: List[Dict]):
        """Send a message to a random group"""
        try:
            # Choose random group
            group = random.choice(groups)
            group_id = group["group_id"]
            
            # Decide next speaker
            speaker, message_type = await self.orchestrator.decide_next_speaker(
                warmer_session_id,
                group_id
            )
            
            # Generate message
            message = await self.orchestrator.generate_message(
                warmer_session_id,
                speaker,
                message_type,
                group_id=group_id
            )
            
            # Get WAHA session name and send message
            from database.user_sessions import UserWhatsAppSession
            
            waha_session_name = speaker
            with get_db() as db:
                user_session = db.query(UserWhatsAppSession).filter(
                    UserWhatsAppSession.session_name == speaker
                ).first()
                if user_session and user_session.waha_session_name:
                    waha_session_name = user_session.waha_session_name
            
            # Send message via WAHA
            result = self.waha.send_text(waha_session_name, group_id, message)
            
            if result and "id" in result:
                # Extract message ID from nested structure
                message_id = result["id"]
                if isinstance(message_id, dict):
                    message_id = message_id.get("_serialized") or message_id.get("id", str(message_id))
                else:
                    message_id = str(message_id)
                
                # Save conversation
                await self.orchestrator.save_conversation(
                    warmer_session_id,
                    message_id,
                    speaker,
                    message,
                    MessageType.GROUP,
                    group_id=group_id
                )
                
                # Update group activity
                await self.group_manager.update_group_activity(
                    warmer_session_id,
                    group_id,
                    speaker
                )
                
                # Update statistics
                await self._update_statistics(warmer_session_id, MessageType.GROUP)
                
                self.logger.info(f"Sent group message from {speaker} to {group_id[:10]}...")
            else:
                self.logger.error(f"Failed to send group message: {result}")
                
        except Exception as e:
            self.logger.error(f"Error sending group message: {str(e)}")
    
    async def _send_direct_message(self, warmer_session_id: int):
        """Send a direct message between two sessions"""
        try:
            with get_db() as db:
                warmer = db.query(WarmerSession).filter(
                    WarmerSession.id == warmer_session_id
                ).first()
                
                if not warmer or len(warmer.all_sessions) < 2:
                    return
                
                # Choose sender and recipient
                sessions = warmer.all_sessions
                sender = random.choice(sessions)
                recipient = random.choice([s for s in sessions if s != sender])
            
            # Get recipient phone number
            recipient_info = await self.contact_manager._get_session_phone_numbers([recipient])
            recipient_phone = recipient_info.get(recipient, {}).get("phone")
            
            if not recipient_phone:
                self.logger.error(f"Could not get phone number for {recipient}")
                return
            
            # Generate message
            message = await self.orchestrator.generate_message(
                warmer_session_id,
                sender,
                "response",
                recipient_session=recipient
            )
            
            # Get WAHA session name
            from database.user_sessions import UserWhatsAppSession
            
            waha_session_name = sender
            with get_db() as db:
                user_session = db.query(UserWhatsAppSession).filter(
                    UserWhatsAppSession.session_name == sender
                ).first()
                if user_session and user_session.waha_session_name:
                    waha_session_name = user_session.waha_session_name
            
            # Send message via WAHA
            chat_id = f"{recipient_phone}@c.us"
            result = self.waha.send_text(waha_session_name, chat_id, message)
            
            if result and "id" in result:
                # Extract message ID from nested structure
                message_id = result["id"]
                if isinstance(message_id, dict):
                    message_id = message_id.get("_serialized") or message_id.get("id", str(message_id))
                else:
                    message_id = str(message_id)
                
                # Save contact to WhatsApp after first message
                # Use the recipient's name from the session info we already have
                recipient_name = recipient_info.get(recipient, {}).get("name", recipient)
                
                # Save the contact with the proper name (use WAHA session name)
                await self.contact_manager.save_contact_after_message(
                    session_name=waha_session_name,
                    chat_id=chat_id,
                    contact_name=recipient_name,
                    warmer_session_id=warmer_session_id
                )
                
                # Save conversation
                await self.orchestrator.save_conversation(
                    warmer_session_id,
                    message_id,
                    sender,
                    message,
                    MessageType.DIRECT,
                    recipient_session=recipient
                )
                
                # Update statistics
                await self._update_statistics(warmer_session_id, MessageType.DIRECT)
                
                self.logger.info(f"Sent direct message from {sender} to {recipient}")
            else:
                self.logger.error(f"Failed to send direct message: {result}")
                
        except Exception as e:
            self.logger.error(f"Error sending direct message: {str(e)}")
    
    async def _update_statistics(self, warmer_session_id: int, message_type: MessageType):
        """Update warmer statistics"""
        try:
            with get_db() as db:
                warmer = db.query(WarmerSession).filter(
                    WarmerSession.id == warmer_session_id
                ).first()
                
                if warmer:
                    warmer.total_messages_sent += 1
                    if message_type == MessageType.GROUP:
                        warmer.total_group_messages += 1
                    else:
                        warmer.total_direct_messages += 1
                    
                    db.commit()
                    
        except Exception as e:
            self.logger.error(f"Failed to update statistics: {str(e)}")
    
    async def _check_time_limit_exceeded(self, warmer_session_id: int) -> bool:
        """Check if warmer has exceeded its time limit"""
        try:
            from database.subscription_models import UserSubscription
            from datetime import datetime
            
            with get_db() as db:
                # Get warmer session
                warmer = db.query(WarmerSession).filter(
                    WarmerSession.id == warmer_session_id
                ).first()
                
                if not warmer or not warmer.user_id:
                    return False
                
                # Get user subscription
                user_subscription = db.query(UserSubscription).filter(
                    UserSubscription.user_id == warmer.user_id
                ).first()
                
                if not user_subscription:
                    return False
                
                # Calculate current session duration
                if warmer.started_at:
                    current_session_minutes = (datetime.utcnow() - warmer.started_at).total_seconds() / 60
                    total_minutes = (warmer.total_duration_minutes or 0) + current_session_minutes
                    
                    # Check if exceeded limit
                    max_minutes = user_subscription.warmer_duration_hours * 60
                    
                    if max_minutes > 0 and total_minutes >= max_minutes:
                        self.logger.warning(f"Warmer {warmer_session_id} has used {total_minutes:.2f} minutes, "
                                          f"exceeding limit of {max_minutes} minutes")
                        return True
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking time limit: {str(e)}")
            return False
    
    async def _verify_session(self, session_name: str) -> bool:
        """Verify if a session is working"""
        try:
            # Get the WAHA session name if this is a display name
            from database.user_sessions import UserWhatsAppSession
            
            waha_session_name = session_name
            with get_db() as db:
                user_session = db.query(UserWhatsAppSession).filter(
                    UserWhatsAppSession.session_name == session_name
                ).first()
                if user_session and user_session.waha_session_name:
                    waha_session_name = user_session.waha_session_name
            
            sessions = self.waha.get_sessions()
            for session in sessions:
                if session.get("name") == waha_session_name:
                    return session.get("status") == "WORKING"
            return False
        except Exception as e:
            self.logger.error(f"Failed to verify session {session_name}: {str(e)}")
            return False
    
    def get_warmer_status(self, warmer_session_id: int) -> Dict[str, Any]:
        """Get current status of warmer session"""
        try:
            with get_db() as db:
                warmer = db.query(WarmerSession).filter(
                    WarmerSession.id == warmer_session_id
                ).first()
                
                if not warmer:
                    return {"error": "Warmer session not found"}
                
                return {
                    "id": warmer.id,
                    "name": warmer.name,
                    "status": warmer.status,
                    "is_active": warmer_session_id in self.active_warmers,
                    "statistics": {
                        "total_messages": warmer.total_messages_sent,
                        "group_messages": warmer.total_group_messages,
                        "direct_messages": warmer.total_direct_messages,
                        "groups_created": warmer.total_groups_created,
                        "duration_minutes": warmer.duration_minutes
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get warmer status: {str(e)}")
            return {"error": str(e)}
    
    def get_all_warmers(self) -> List[Dict[str, Any]]:
        """Get all warmer sessions"""
        try:
            with get_db() as db:
                warmers = db.query(WarmerSession).all()
                return [
                    {
                        **warmer.to_dict(),
                        "is_active": warmer.id in self.active_warmers
                    }
                    for warmer in warmers
                ]
        except Exception as e:
            self.logger.error(f"Failed to get all warmers: {str(e)}")
            return []


# Global warmer engine instance
warmer_engine = WarmerEngine()