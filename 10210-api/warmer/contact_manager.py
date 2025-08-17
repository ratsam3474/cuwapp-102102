"""
Contact Manager for WhatsApp Warmer
Handles saving contacts between sessions
"""

import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from sqlalchemy.orm import Session
from database.connection import get_db
from warmer.models import WarmerContact, WarmerSession
from waha_functions import WAHAClient

logger = logging.getLogger(__name__)


class ContactManager:
    """Manages contact saving between WhatsApp sessions"""
    
    def __init__(self, waha_client: WAHAClient = None):
        self.waha = waha_client or WAHAClient()
        self.logger = logger
    
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
                return WAHAClient(base_url=user_session.waha_instance_url)
        
        # Fallback to default client
        return self.waha
    
    async def save_all_contacts(self, warmer_session_id: int) -> Dict[str, Any]:
        """
        Save all contacts between all participating sessions
        
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
                
                all_sessions = warmer.all_sessions
            
            results = {
                "total_contacts_saved": 0,
                "total_already_saved": 0,
                "total_newly_saved": 0,
                "errors": [],
                "details": []
            }
            
            # Get phone numbers for each session
            session_phones = await self._get_session_phone_numbers(all_sessions)
            
            # Save contacts between each pair of sessions
            for i, session1 in enumerate(all_sessions):
                for j, session2 in enumerate(all_sessions):
                    if i >= j:  # Skip self and already processed pairs
                        continue
                    
                    # Save session2's contact in session1
                    session2_info = session_phones.get(session2, {})
                    self.logger.info(f"Saving {session2}'s contact ({session2_info.get('name', 'Unknown')}) in {session1}...")
                    result1 = await self._save_contact(
                        warmer_session_id,
                        session1,
                        session2_info
                    )
                    
                    # Save session1's contact in session2
                    session1_info = session_phones.get(session1, {})
                    self.logger.info(f"Saving {session1}'s contact ({session1_info.get('name', 'Unknown')}) in {session2}...")
                    result2 = await self._save_contact(
                        warmer_session_id,
                        session2,
                        session1_info
                    )
                    
                    # Process result1
                    if result1["success"]:
                        results["total_contacts_saved"] += 1
                        if result1.get("already_saved"):
                            results["total_already_saved"] += 1
                            self.logger.info(f"✓ {session2}'s contact was already saved in {session1}")
                        else:
                            results["total_newly_saved"] += 1
                            self.logger.info(f"✓ {session2}'s contact has been saved in {session1}")
                    else:
                        results["errors"].append(result1.get("error", "Unknown error"))
                        self.logger.error(f"✗ Failed to save {session2}'s contact in {session1}: {result1.get('error', 'Unknown error')}")
                    
                    # Process result2
                    if result2["success"]:
                        results["total_contacts_saved"] += 1
                        if result2.get("already_saved"):
                            results["total_already_saved"] += 1
                            self.logger.info(f"✓ {session1}'s contact was already saved in {session2}")
                        else:
                            results["total_newly_saved"] += 1
                            self.logger.info(f"✓ {session1}'s contact has been saved in {session2}")
                    else:
                        results["errors"].append(result2.get("error", "Unknown error"))
                        self.logger.error(f"✗ Failed to save {session1}'s contact in {session2}: {result2.get('error', 'Unknown error')}")
                    
                    results["details"].append({
                        "session1": session1,
                        "session2": session2,
                        "saved_in_session1": result1["success"],
                        "saved_in_session2": result2["success"],
                        "session1_already_saved": result1.get("already_saved", False),
                        "session2_already_saved": result2.get("already_saved", False)
                    })
            
            # Log summary
            self.logger.info(f"\n=== Contact Saving Summary ===")
            self.logger.info(f"Total contacts processed: {results['total_contacts_saved']}")
            self.logger.info(f"Already saved: {results['total_already_saved']}")
            self.logger.info(f"Newly saved: {results['total_newly_saved']}")
            if results['errors']:
                self.logger.info(f"Failed: {len(results['errors'])}")
            self.logger.info(f"==============================\n")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to save all contacts: {str(e)}")
            raise
    
    async def _get_session_phone_numbers(self, sessions: List[str]) -> Dict[str, Dict]:
        """Get phone numbers and names for all sessions"""
        session_info = {}
        
        for session in sessions:
            try:
                # Convert display name to WAHA session name
                from database.user_sessions import UserWhatsAppSession
                from database.connection import get_db
                
                waha_session_name = session
                with get_db() as db:
                    user_session = db.query(UserWhatsAppSession).filter(
                        UserWhatsAppSession.session_name == session
                    ).first()
                    if user_session and user_session.waha_session_name:
                        waha_session_name = user_session.waha_session_name
                
                # Get session info from WAHA using correct instance
                # Need to get user_id from warmer if available
                warmer = None
                with get_db() as db2:
                    # Try to find any warmer with this session to get user_id
                    from warmer.models import WarmerSession
                    warmers = db2.query(WarmerSession).all()
                    for w in warmers:
                        if session in w.all_sessions:
                            warmer = w
                            break
                
                waha_client = self._get_waha_client_for_session(session, warmer.user_id if warmer else None)
                info = waha_client.get_session_info(waha_session_name)
                if info and info.get("me"):
                    phone = info["me"].get("id", "").replace("@c.us", "")
                    name = info["me"].get("pushName", session)
                    
                    session_info[session] = {
                        "phone": phone,
                        "name": name
                    }
                else:
                    self.logger.warning(f"Could not get info for session {session}")
                    
            except Exception as e:
                self.logger.error(f"Error getting session {session} info: {str(e)}")
        
        return session_info
    
    async def _save_contact(
        self, 
        warmer_session_id: int,
        session_name: str, 
        contact_info: Dict[str, str]
    ) -> Dict[str, Any]:
        """Save a single contact in a session"""
        try:
            if not contact_info or not contact_info.get("phone"):
                return {
                    "success": False,
                    "error": f"No phone number for contact"
                }
            
            phone = contact_info["phone"]
            name = contact_info.get("name", phone)
            
            # Check if already saved in database
            with get_db() as db:
                existing = db.query(WarmerContact).filter(
                    WarmerContact.warmer_session_id == warmer_session_id,
                    WarmerContact.session_name == session_name,
                    WarmerContact.contact_phone == phone
                ).first()
                
                if existing:
                    return {
                        "success": True,
                        "message": "Contact already saved",
                        "already_saved": True
                    }
            
            # Note: Contact will be saved to WhatsApp when first message is sent
            # The WAHA API requires an active chat to save contact
            # See save_contact_after_message() method
            
            # Save to database
            with get_db() as db:
                contact = WarmerContact(
                    warmer_session_id=warmer_session_id,
                    session_name=session_name,
                    contact_phone=phone,
                    contact_name=name
                )
                db.add(contact)
                db.commit()
            
            return {
                "success": True,
                "message": f"Contact {name} ({phone}) saved in {session_name}",
                "already_saved": False
            }
            
        except Exception as e:
            error_msg = f"Failed to save contact in {session_name}: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def save_contact_after_message(
        self,
        session_name: str,
        chat_id: str,
        contact_name: str,
        warmer_session_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Save contact to WhatsApp after sending first message"""
        try:
            # Extract phone number from chat_id
            contact_phone = chat_id.replace("@c.us", "")
            
            # Check if already saved to WhatsApp
            already_in_db = False
            if warmer_session_id:
                with get_db() as db:
                    existing = db.query(WarmerContact).filter(
                        WarmerContact.warmer_session_id == warmer_session_id,
                        WarmerContact.session_name == session_name,
                        WarmerContact.contact_phone == contact_phone,
                        WarmerContact.saved_to_whatsapp == True
                    ).first()
                    
                    if existing:
                        already_in_db = True
                        self.logger.info(f"Contact {contact_name} marked as saved in DB, but will try to save to WhatsApp anyway")
            
            # Convert display name to WAHA session name if needed
            from database.user_sessions import UserWhatsAppSession
            waha_session_name = session_name
            with get_db() as db:
                user_session = db.query(UserWhatsAppSession).filter(
                    UserWhatsAppSession.session_name == session_name
                ).first()
                if user_session and user_session.waha_session_name:
                    waha_session_name = user_session.waha_session_name
            
            # Use WAHA API to save contact (requires active chat)
            self.logger.info(f"Attempting to save contact {contact_name} ({chat_id}) in session {waha_session_name}")
            
            # Get the correct WAHA client for this session
            # Try to get user_id from warmer if available
            user_id = None
            if warmer_session_id:
                with get_db() as db2:
                    warmer = db2.query(WarmerSession).filter(
                        WarmerSession.id == warmer_session_id
                    ).first()
                    if warmer:
                        user_id = warmer.user_id
            
            waha_client = self._get_waha_client_for_session(session_name, user_id)
            result = waha_client.create_or_update_contact(
                session=waha_session_name,
                chat_id=chat_id,
                name=contact_name
            )
            
            self.logger.info(f"WAHA contact save result: {result}")
            
            if result:
                # Update or create database record to mark as saved to WhatsApp
                if warmer_session_id:
                    with get_db() as db:
                        contact = db.query(WarmerContact).filter(
                            WarmerContact.warmer_session_id == warmer_session_id,
                            WarmerContact.session_name == session_name,
                            WarmerContact.contact_phone == contact_phone
                        ).first()
                        
                        if contact:
                            contact.saved_to_whatsapp = True
                            contact.whatsapp_saved_at = datetime.utcnow()
                            contact.contact_name = contact_name  # Update name if changed
                        else:
                            # Create new contact record
                            contact = WarmerContact(
                                warmer_session_id=warmer_session_id,
                                session_name=session_name,
                                contact_phone=contact_phone,
                                contact_name=contact_name,
                                saved_to_whatsapp=True,
                                whatsapp_saved_at=datetime.utcnow()
                            )
                            db.add(contact)
                        db.commit()
                
                self.logger.info(f"✓ Contact {contact_name} saved to WhatsApp in session {session_name}")
                return {
                    "success": True,
                    "message": f"Contact saved to WhatsApp"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to save contact to WhatsApp"
                }
                
        except Exception as e:
            self.logger.error(f"Failed to save contact to WhatsApp: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def check_contacts_saved(self, warmer_session_id: int) -> Dict[str, Any]:
        """Check which contacts are saved between sessions"""
        try:
            with get_db() as db:
                warmer = db.query(WarmerSession).filter(WarmerSession.id == warmer_session_id).first()
                if not warmer:
                    raise ValueError(f"Warmer session {warmer_session_id} not found")
                
                all_sessions = warmer.all_sessions
                
                # Get all saved contacts for this warmer
                saved_contacts = db.query(WarmerContact).filter(
                    WarmerContact.warmer_session_id == warmer_session_id
                ).all()
                
                # Build matrix of who has saved whom
                contact_matrix = {}
                for session in all_sessions:
                    contact_matrix[session] = {}
                    for other_session in all_sessions:
                        if session != other_session:
                            contact_matrix[session][other_session] = False
                
                # Mark saved contacts
                for contact in saved_contacts:
                    if contact.session_name in contact_matrix:
                        # Find which session this contact belongs to
                        for session in all_sessions:
                            session_info = await self._get_session_phone_numbers([session])
                            if session_info.get(session, {}).get("phone") == contact.contact_phone:
                                contact_matrix[contact.session_name][session] = True
                                break
                
                # Calculate statistics
                total_expected = len(all_sessions) * (len(all_sessions) - 1)
                total_saved = sum(
                    sum(1 for saved in session_contacts.values() if saved)
                    for session_contacts in contact_matrix.values()
                )
                
                return {
                    "total_sessions": len(all_sessions),
                    "total_expected_contacts": total_expected,
                    "total_saved_contacts": total_saved,
                    "percentage_complete": (total_saved / total_expected * 100) if total_expected > 0 else 0,
                    "contact_matrix": contact_matrix,
                    "all_contacts_saved": total_saved == total_expected
                }
                
        except Exception as e:
            self.logger.error(f"Failed to check contacts: {str(e)}")
            raise