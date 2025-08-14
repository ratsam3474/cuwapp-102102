import requests
import base64
from typing import List, Dict, Optional, Union
import json
import logging
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WAHAClient:
    def __init__(self, base_url: str = None, api_key: Optional[str] = None):
        # Allow dynamic base_url to be passed for multi-instance support
        if base_url is None:
            # Fallback to environment variable for backward compatibility
            base_url = os.getenv("WAHA_BASE_URL", "http://localhost:4500")
        self.base_url = base_url.rstrip('/')
        self.headers = {"X-API-KEY": api_key} if api_key else {}
        self.headers["Content-Type"] = "application/json"
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {method} {url} - {str(e)}")
            raise

    # ==================== SESSION MANAGEMENT ====================
    
    def get_sessions(self) -> List[Dict]:
        """Get all active WhatsApp sessions"""
        response = self._make_request("GET", "/api/sessions")
        return response.json()
    
    def create_session(self, session_name: str, config: Optional[Dict] = None) -> Dict:
        """Create new WhatsApp session"""
        # Use provided config or default
        if config is None:
            config = {
                "proxy": None,
                "webhooks": [],
                "debug": False
            }
        
        payload = {
            "name": session_name,
            "config": config
        }
        response = self._make_request("POST", "/api/sessions", json=payload)
        return response.json()
    
    def get_session_info(self, session_name: str) -> Dict:
        """Get session information"""
        response = self._make_request("GET", f"/api/sessions/{session_name}")
        return response.json()
    
    def start_session(self, session_name: str) -> Dict:
        """Start session"""
        response = self._make_request("POST", f"/api/sessions/{session_name}/start")
        return response.json()
    
    def stop_session(self, session_name: str) -> Dict:
        """Stop session"""
        response = self._make_request("POST", f"/api/sessions/{session_name}/stop")
        return response.json()
    
    def restart_session(self, session_name: str) -> Dict:
        """Restart session"""
        response = self._make_request("POST", f"/api/sessions/{session_name}/restart")
        return response.json()
    
    def logout_session(self, session_name: str) -> Dict:
        """Logout session"""
        response = self._make_request("POST", f"/api/sessions/{session_name}/logout")
        return response.json()
    
    def delete_session(self, session_name: str) -> Dict:
        """Delete session"""
        response = self._make_request("DELETE", f"/api/sessions/{session_name}")
        try:
            return response.json()
        except:
            return {"status": "deleted"}

    # ==================== AUTHENTICATION ====================
    
    def get_qr_code(self, session_name: str, max_wait_seconds: int = 60) -> bytes:
        """
        Get QR code for session authentication with intelligent session state handling
        
        Args:
            session_name: WhatsApp session name
            max_wait_seconds: Maximum time to wait for session to be ready
            
        Returns:
            bytes: PNG image data of QR code
            
        Raises:
            requests.exceptions.RequestException: If unable to get QR code
        """
        import time
        
        def get_session_status_internal():
            """Get current session status"""
            try:
                response = self._make_request("GET", f"/api/sessions/{session_name}")
                session_info = response.json()
                status = session_info.get('status', 'UNKNOWN')
                logger.info(f"Session {session_name} status: {status}")
                return status, session_info
            except requests.exceptions.RequestException as e:
                if "404" in str(e):
                    logger.info(f"Session {session_name} doesn't exist")
                    return "NOT_EXISTS", {}
                raise
        
        def create_and_start_session_internal():
            """Create and start session"""
            logger.info(f"Creating session {session_name}...")
            payload = {
                "name": session_name,
                "start": True,
                "config": {
                    "proxy": None,
                    "webhooks": [],
                    "debug": False
                }
            }
            self._make_request("POST", "/api/sessions", json=payload)
            logger.info(f"Session {session_name} created and starting...")
        
        def start_existing_session_internal():
            """Start existing session"""
            logger.info(f"Starting session {session_name}...")
            self._make_request("POST", f"/api/sessions/{session_name}/start")
            logger.info(f"Session {session_name} start command sent")
        
        def wait_for_qr_ready_state_internal():
            """Wait for session to reach QR-ready state"""
            logger.info(f"Waiting for session {session_name} to be ready for QR code...")
            
            start_time = time.time()
            while time.time() - start_time < max_wait_seconds:
                status, _ = get_session_status_internal()
                
                if status == "SCAN_QR_CODE":
                    logger.info(f"Session {session_name} is ready for QR code!")
                    return
                elif status in ["STARTING", "WORKING"]:
                    logger.info(f"Session {session_name} is {status}, waiting...")
                    time.sleep(2)
                else:
                    logger.warning(f"Session {session_name} in unexpected state: {status}")
                    time.sleep(2)
            
            raise requests.exceptions.RequestException(f"Session did not reach QR-ready state within {max_wait_seconds} seconds")
        
        def fetch_qr_code_internal():
            """Fetch QR code binary data"""
            logger.info("Fetching QR code...")
            # Corrected the endpoint path and moved the format parameter
            response = self._make_request("GET", f"/api/{session_name}/auth/qr?format=image")
            
            if response.headers.get('content-type') != 'image/png':
                logger.warning(f"Unexpected content type: {response.headers.get('content-type')}")
            
            qr_data = response.content
            logger.info(f"QR code fetched successfully ({len(qr_data)} bytes)")
            return qr_data
        
        # =============================================================================
        # MAIN LOGIC
        # =============================================================================
        
        try:
            logger.info(f"Getting QR code for session '{session_name}'...")
            
            # Step 1: Check current session status
            status, session_info = get_session_status_internal()
            
            # Step 2: Handle session state intelligently
            if status == "SCAN_QR_CODE":
                logger.info("Session already in QR scan mode!")
            
            elif status == "STARTING":
                logger.info("Session is starting, waiting for QR scan mode...")
                wait_for_qr_ready_state_internal()
            
            elif status == "NOT_EXISTS":
                logger.error(f"Session {session_name} doesn't exist! Cannot get QR code for non-existent session.")
                raise ValueError(f"Session {session_name} not found. Please create the session first.")
            
            elif status in ["STOPPED", "FAILED", "WORKING"]:
                logger.info(f"Session is {status}, starting session...")
                start_existing_session_internal()
                wait_for_qr_ready_state_internal()
            
            else:
                logger.warning(f"Unknown session status: {status}, attempting to start...")
                start_existing_session_internal()
                wait_for_qr_ready_state_internal()
            
            # Step 3: Fetch QR code
            qr_data = fetch_qr_code_internal()
            
            logger.info("QR code retrieved successfully!")
            return qr_data
            
        except Exception as e:
            logger.error(f"Failed to get QR code: {e}")
            raise
    
    def request_auth_code(self, session_name: str, phone_number: str) -> Dict:
        """Request authentication code via SMS"""
        payload = {"phoneNumber": phone_number}
        response = self._make_request("POST", f"/api/{session_name}/auth/request-code", json=payload)
        return response.json()

    # ==================== MESSAGING ====================
    
    def send_text(self, session: str, chat_id: str, text: str) -> Dict:
        """Send text message"""
        payload = {
            "chatId": chat_id,
            "text": text,
            "session": session
        }
        response = self._make_request("POST", "/api/sendText", json=payload)
        return response.json()
    
    def send_image(self, session: str, chat_id: str, file_data: Dict, caption: str = "") -> Dict:
        """Send image message"""
        payload = {
            "chatId": chat_id,
            "file": file_data,
            "caption": caption,
            "session": session
        }
        response = self._make_request("POST", "/api/sendImage", json=payload)
        return response.json()
    
    def send_file(self, session: str, chat_id: str, file_data: Dict) -> Dict:
        """Send file"""
        payload = {
            "chatId": chat_id,
            "file": file_data,
            "session": session
        }
        response = self._make_request("POST", "/api/sendFile", json=payload)
        return response.json()
    
    def send_voice(self, session: str, chat_id: str, file_data: Dict) -> Dict:
        """Send voice message"""
        payload = {
            "chatId": chat_id,
            "file": file_data,
            "session": session
        }
        response = self._make_request("POST", "/api/sendVoice", json=payload)
        return response.json()
    
    def send_video(self, session: str, chat_id: str, file_data: Dict, caption: str = "") -> Dict:
        """Send video message"""
        payload = {
            "chatId": chat_id,
            "file": file_data,
            "caption": caption,
            "session": session
        }
        response = self._make_request("POST", "/api/sendVideo", json=payload)
        return response.json()
    
    def send_location(self, session: str, chat_id: str, latitude: float, longitude: float, title: str = "") -> Dict:
        """Send location"""
        payload = {
            "chatId": chat_id,
            "latitude": latitude,
            "longitude": longitude,
            "title": title,
            "session": session
        }
        response = self._make_request("POST", "/api/sendLocation", json=payload)
        return response.json()
    
    def send_contact_vcard(self, session: str, chat_id: str, contact_data: Dict) -> Dict:
        """Send contact VCard"""
        payload = {
            "chatId": chat_id,
            "session": session,
            **contact_data
        }
        response = self._make_request("POST", "/api/sendContactVcard", json=payload)
        return response.json()
    
    def mark_as_seen(self, session: str, chat_id: str, message_id: str) -> Dict:
        """Mark message as seen"""
        payload = {
            "chatId": chat_id,
            "messageId": message_id,
            "session": session
        }
        response = self._make_request("POST", "/api/sendSeen", json=payload)
        return response.json()
    
    def start_typing(self, session: str, chat_id: str) -> Dict:
        """Start typing indicator"""
        payload = {
            "chatId": chat_id,
            "session": session
        }
        response = self._make_request("POST", "/api/startTyping", json=payload)
        return response.json()
    
    def stop_typing(self, session: str, chat_id: str) -> Dict:
        """Stop typing indicator"""
        payload = {
            "chatId": chat_id,
            "session": session
        }
        response = self._make_request("POST", "/api/stopTyping", json=payload)
        return response.json()
    
    def react_to_message(self, session: str, message_id: str, reaction: str) -> Dict:
        """React to message"""
        payload = {
            "messageId": message_id,
            "reaction": reaction,
            "session": session
        }
        response = self._make_request("PUT", "/api/reaction", json=payload)
        return response.json()
    
    def star_message(self, session: str, message_id: str, star: bool = True) -> Dict:
        """Star/unstar message"""
        payload = {
            "messageId": message_id,
            "star": star,
            "session": session
        }
        response = self._make_request("PUT", "/api/star", json=payload)
        return response.json()

    # ==================== CHATS ====================
    
    def get_chats(self, session: str) -> List[Dict]:
        """Get all chats"""
        response = self._make_request("GET", f"/api/{session}/chats")
        return response.json()
    
    def get_chat_messages(self, session: str, chat_id: str, limit: int = 50) -> List[Dict]:
        """Get chat messages"""
        response = self._make_request("GET", f"/api/{session}/chats/{chat_id}/messages?limit={limit}")
        return response.json()
    
    def delete_chat(self, session: str, chat_id: str) -> Dict:
        """Delete chat"""
        response = self._make_request("DELETE", f"/api/{session}/chats/{chat_id}")
        return response.json()
    
    def mark_chat_as_read(self, session: str, chat_id: str) -> Dict:
        """Mark chat messages as read"""
        response = self._make_request("POST", f"/api/{session}/chats/{chat_id}/messages/read")
        return response.json()
    
    def clear_chat_messages(self, session: str, chat_id: str) -> Dict:
        """Clear all messages in chat"""
        response = self._make_request("DELETE", f"/api/{session}/chats/{chat_id}/messages")
        return response.json()
    
    def archive_chat(self, session: str, chat_id: str) -> Dict:
        """Archive chat"""
        response = self._make_request("POST", f"/api/{session}/chats/{chat_id}/archive")
        return response.json()
    
    def unarchive_chat(self, session: str, chat_id: str) -> Dict:
        """Unarchive chat"""
        response = self._make_request("POST", f"/api/{session}/chats/{chat_id}/unarchive")
        return response.json()

    # ==================== CONTACTS ====================
    
    def get_all_contacts(self, session: str) -> List[Dict]:
        """Get all contacts"""
        response = self._make_request("GET", f"/api/contacts/all?session={session}")
        return response.json()
    
    def create_or_update_contact(self, session: str, chat_id: str, name: str) -> Dict:
        """Create or update contact"""
        payload = {
            "name": name
        }
        response = self._make_request("PUT", f"/api/{session}/contacts/{chat_id}", json=payload)
        return response.json()
    
    def check_number_exists(self, session: str, phone: str) -> Dict:
        """Check if number exists on WhatsApp"""
        response = self._make_request("GET", f"/api/contacts/check-exists?session={session}&phone={phone}")
        return response.json()
    
    def get_contact_info(self, session: str, contact_id: str) -> Dict:
        """Get contact info"""
        response = self._make_request("GET", f"/api/contacts?session={session}&contactId={contact_id}")
        return response.json()
    
    def block_contact(self, session: str, contact_id: str) -> Dict:
        """Block contact"""
        payload = {
            "contactId": contact_id,
            "session": session
        }
        response = self._make_request("POST", "/api/contacts/block", json=payload)
        return response.json()
    
    def unblock_contact(self, session: str, contact_id: str) -> Dict:
        """Unblock contact"""
        payload = {
            "contactId": contact_id,
            "session": session
        }
        response = self._make_request("POST", "/api/contacts/unblock", json=payload)
        return response.json()

    # ==================== GROUPS ====================
    
    def get_groups(self, session: str) -> List[Dict]:
        """Get all groups"""
        response = self._make_request("GET", f"/api/{session}/groups")
        return response.json()
    
    def create_group(self, session: str, name: str, participants: List[str]) -> Dict:
        """Create group"""
        # Format participants as objects with id field
        formatted_participants = []
        for p in participants:
            # Ensure phone number has @c.us suffix
            if "@" not in p:
                phone_id = f"{p}@c.us"
            else:
                phone_id = p
            formatted_participants.append({"id": phone_id})
        
        payload = {
            "name": name,
            "participants": formatted_participants
        }
        
        # Log the request for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Creating group with payload: {payload}")
        
        response = self._make_request("POST", f"/api/{session}/groups", json=payload)
        return response.json()
    
    def get_group_info(self, session: str, group_id: str) -> Dict:
        """Get group info"""
        response = self._make_request("GET", f"/api/{session}/groups/{group_id}")
        return response.json()
    
    def delete_group(self, session: str, group_id: str) -> Dict:
        """Delete group"""
        response = self._make_request("DELETE", f"/api/{session}/groups/{group_id}")
        return response.json()
    
    def leave_group(self, session: str, group_id: str) -> Dict:
        """Leave group"""
        response = self._make_request("POST", f"/api/{session}/groups/{group_id}/leave")
        return response.json()
    
    def join_group_by_link(self, session: str, invite_link: str) -> Dict:
        """Join group using invite link"""
        payload = {
            "code": invite_link
        }
        response = self._make_request("POST", f"/api/{session}/groups/join", json=payload)
        return response.json()
    
    def update_group_description(self, session: str, group_id: str, description: str) -> Dict:
        """Update group description"""
        payload = {"description": description}
        response = self._make_request("PUT", f"/api/{session}/groups/{group_id}/description", json=payload)
        return response.json()
    
    def update_group_name(self, session: str, group_id: str, name: str) -> Dict:
        """Update group name"""
        payload = {"subject": name}
        response = self._make_request("PUT", f"/api/{session}/groups/{group_id}/subject", json=payload)
        return response.json()
    
    def add_group_participants(self, session: str, group_id: str, participants: List[str]) -> Dict:
        """Add participants to group"""
        payload = {"participants": participants}
        response = self._make_request("POST", f"/api/{session}/groups/{group_id}/participants/add", json=payload)
        return response.json()
    
    def remove_group_participants(self, session: str, group_id: str, participants: List[str]) -> Dict:
        """Remove participants from group"""
        payload = {"participants": participants}
        response = self._make_request("POST", f"/api/{session}/groups/{group_id}/participants/remove", json=payload)
        return response.json()
    
    def promote_group_admin(self, session: str, group_id: str, participants: List[str]) -> Dict:
        """Promote participants to admin"""
        payload = {"participants": participants}
        response = self._make_request("POST", f"/api/{session}/groups/{group_id}/admin/promote", json=payload)
        return response.json()
    
    def demote_group_admin(self, session: str, group_id: str, participants: List[str]) -> Dict:
        """Demote admin participants"""
        payload = {"participants": participants}
        response = self._make_request("POST", f"/api/{session}/groups/{group_id}/admin/demote", json=payload)
        return response.json()

    # ==================== PRESENCE ====================
    
    def set_presence(self, session: str, presence: str, chat_id: Optional[str] = None) -> Dict:
        """Set presence status"""
        payload = {
            "presence": presence,  # available, unavailable, composing, recording
            "session": session
        }
        if chat_id:
            payload["chatId"] = chat_id
        response = self._make_request("POST", f"/api/{session}/presence", json=payload)
        return response.json()
    
    def get_presence(self, session: str, chat_id: str) -> Dict:
        """Get presence status"""
        response = self._make_request("GET", f"/api/{session}/presence/{chat_id}")
        return response.json()

    # ==================== STATUS (STORIES) ====================
    
    def send_text_status(self, session: str, text: str, background_color: str = "#000000") -> Dict:
        """Send text status"""
        payload = {
            "text": text,
            "backgroundColor": background_color
        }
        response = self._make_request("POST", f"/api/{session}/status/text", json=payload)
        return response.json()
    
    def send_image_status(self, session: str, file_data: Dict, caption: str = "") -> Dict:
        """Send image status"""
        payload = {
            "file": file_data,
            "caption": caption
        }
        response = self._make_request("POST", f"/api/{session}/status/image", json=payload)
        return response.json()
    
    def send_video_status(self, session: str, file_data: Dict, caption: str = "") -> Dict:
        """Send video status"""
        payload = {
            "file": file_data,
            "caption": caption
        }
        response = self._make_request("POST", f"/api/{session}/status/video", json=payload)
        return response.json()

    # ==================== SERVER INFO ====================
    
    def get_server_version(self) -> Dict:
        """Get server version"""
        response = self._make_request("GET", "/api/server/version")
        return response.json()
    
    def get_server_environment(self) -> Dict:
        """Get server environment info"""
        response = self._make_request("GET", "/api/server/environment")
        return response.json()
    
    def get_server_status(self) -> Dict:
        """Get server status"""
        response = self._make_request("GET", "/api/server/status")
        return response.json()
    
    def ping_server(self) -> str:
        """Ping server"""
        response = self._make_request("GET", "/ping")
        return response.text
    
    def health_check(self) -> Dict:
        """Health check"""
        response = self._make_request("GET", "/health")
        return response.json()

    # ==================== UTILITY FUNCTIONS ====================
    
    def encode_file_to_base64(self, file_path: str) -> Dict:
        """Encode file to base64 for sending"""
        import mimetypes
        import os
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"
        
        # Read and encode file
        with open(file_path, 'rb') as f:
            file_data = base64.b64encode(f.read()).decode('utf-8')
        
        return {
            "mimetype": mime_type,
            "filename": os.path.basename(file_path),
            "data": file_data
        }

    def get_screenshot(self, session: str) -> bytes:
        """Get screenshot"""
        # Use the correct WAHA API endpoint format for screenshots
        response = self._make_request("GET", f"/api/screenshot?session={session}")
        return response.content
    
    # ==================== ENHANCED GROUP FUNCTIONS ====================
    
    def get_group_participants_details(self, session: str, group_id: str) -> List[Dict]:
        """
        Get detailed information for all participants in a group
        
        Args:
            session: WhatsApp session name
            group_id: Group ID (format: xxxxx@g.us or just xxxxx)
            
        Returns:
            List of participant details with contact info and last message
        """
        try:
            # Clean up group_id if needed (remove @g.us if present)
            if '@g.us' in group_id:
                group_id_clean = group_id
            else:
                group_id_clean = f"{group_id}@g.us"
            
            # First, get the group info with participants
            group_info = self.get_group_info(session, group_id_clean)
            
            # Handle WAHA response structure - participants are in groupMetadata.participants
            if isinstance(group_info, dict) and 'groupMetadata' in group_info:
                participants = group_info['groupMetadata'].get('participants', [])
            else:
                participants = group_info.get('participants', [])
            
            detailed_participants = []
            all_contacts = {}
            
            # Get all contacts once to avoid multiple API calls
            try:
                contacts_list = self.get_all_contacts(session)
                # Create a lookup dict by phone number
                for contact in contacts_list:
                    if 'id' in contact:
                        # Extract phone number from different ID formats
                        contact_id = contact['id']
                        if isinstance(contact_id, dict) and '_serialized' in contact_id:
                            phone_key = contact_id['_serialized']
                        elif isinstance(contact_id, str):
                            phone_key = contact_id
                        else:
                            continue
                        all_contacts[phone_key] = contact
            except Exception as e:
                logger.warning(f"Could not fetch all contacts: {e}")
            
            for participant in participants:
                try:
                    # Handle WAHA participant structure
                    participant_id = None
                    phone_number = None
                    
                    if isinstance(participant, dict):
                        if 'id' in participant:
                            if isinstance(participant['id'], dict):
                                # WAHA structure: {"id": {"_serialized": "xxx@c.us", "user": "xxx"}}
                                participant_id = participant['id'].get('_serialized', '')
                                phone_number = participant['id'].get('user', '')
                            elif isinstance(participant['id'], str):
                                participant_id = participant['id']
                                phone_number = participant['id'].replace('@c.us', '')
                    
                    # Skip if no valid ID
                    if not participant_id:
                        continue
                    
                    # Get contact info from our lookup
                    contact_info = all_contacts.get(participant_id, {})
                    
                    # Get last message/interaction if possible
                    last_message = {}
                    last_msg_text = ''
                    last_msg_date = ''
                    last_msg_type = ''
                    last_msg_status = ''
                    
                    try:
                        # Try to get recent messages from this contact
                        chat_messages = self.get_chat_messages(session, participant_id, limit=1)
                        if chat_messages and len(chat_messages) > 0:
                            last_msg = chat_messages[0]
                            last_message = last_msg
                            last_msg_text = last_msg.get('body', '') or '[Media]'
                            last_msg_date = datetime.fromtimestamp(last_msg.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S') if last_msg.get('timestamp') else ''
                            last_msg_type = last_msg.get('type', '')
                            last_msg_status = 'sent' if last_msg.get('fromMe') else 'received'
                    except Exception as e:
                        logger.debug(f"Could not get messages for {participant_id}: {e}")
                    
                    # Extract saved name and push name
                    saved_name = contact_info.get('name', '')
                    public_name = contact_info.get('pushname', '') or participant.get('pushname', '')
                    
                    # Business and contact status
                    is_business = contact_info.get('isBusiness', False)
                    is_my_contact = contact_info.get('isMyContact', False)
                    is_blocked = contact_info.get('isBlocked', False)
                    labels = contact_info.get('labels', [])
                    
                    # Format phone number
                    formatted_phone = self._format_phone_number(phone_number) if phone_number else participant_id
                    
                    # Combine all information
                    detailed_participant = {
                        'phone_number': phone_number or participant_id.replace('@c.us', ''),
                        'formatted_phone': formatted_phone,
                        'country_code': self._extract_country_code(phone_number) if phone_number else '',
                        'country_name': self._get_country_name(phone_number) if phone_number else 'Unknown',
                        'saved_name': saved_name,
                        'public_name': public_name,
                        'is_admin': participant.get('isAdmin', False),
                        'is_super_admin': participant.get('isSuperAdmin', False),
                        'is_my_contact': is_my_contact,
                        'is_business': is_business,
                        'is_blocked': is_blocked,
                        'labels': ', '.join(labels) if labels else '',
                        'last_msg_text': last_msg_text[:100] if last_msg_text else '',  # Limit to 100 chars
                        'last_msg_date': last_msg_date,
                        'last_msg_type': last_msg_type,
                        'last_msg_status': last_msg_status
                    }
                    
                    detailed_participants.append(detailed_participant)
                    
                except Exception as e:
                    logger.warning(f"Error processing participant {participant}: {e}")
                    continue
            
            return detailed_participants
            
        except Exception as e:
            logger.error(f"Failed to get detailed participants for group {group_id}: {str(e)}")
            raise
    
    def _extract_country_code(self, phone_number: str) -> str:
        """Extract country code from phone number"""
        # Common country codes - expanded list
        country_codes = {
            '1': 'US/CA',
            '7': 'RU/KZ',
            '20': 'EG',
            '27': 'ZA',
            '30': 'GR',
            '31': 'NL',
            '32': 'BE',
            '33': 'FR',
            '34': 'ES',
            '36': 'HU',
            '39': 'IT',
            '40': 'RO',
            '41': 'CH',
            '43': 'AT',
            '44': 'GB',
            '45': 'DK',
            '46': 'SE',
            '47': 'NO',
            '48': 'PL',
            '49': 'DE',
            '51': 'PE',
            '52': 'MX',
            '53': 'CU',
            '54': 'AR',
            '55': 'BR',
            '56': 'CL',
            '57': 'CO',
            '58': 'VE',
            '60': 'MY',
            '61': 'AU',
            '62': 'ID',
            '63': 'PH',
            '64': 'NZ',
            '65': 'SG',
            '66': 'TH',
            '81': 'JP',
            '82': 'KR',
            '84': 'VN',
            '86': 'CN',
            '90': 'TR',
            '91': 'IN',
            '92': 'PK',
            '93': 'AF',
            '94': 'LK',
            '95': 'MM',
            '98': 'IR',
            '212': 'MA',
            '213': 'DZ',
            '216': 'TN',
            '218': 'LY',
            '220': 'GM',
            '221': 'SN',
            '222': 'MR',
            '223': 'ML',
            '224': 'GN',
            '225': 'CI',
            '226': 'BF',
            '227': 'NE',
            '228': 'TG',
            '229': 'BJ',
            '230': 'MU',
            '231': 'LR',
            '232': 'SL',
            '233': 'GH',
            '234': 'NG',
            '235': 'TD',
            '236': 'CF',
            '237': 'CM',
            '238': 'CV',
            '239': 'ST',
            '240': 'GQ',
            '241': 'GA',
            '242': 'CG',
            '243': 'CD',
            '244': 'AO',
            '245': 'GW',
            '246': 'IO',
            '248': 'SC',
            '249': 'SD',
            '250': 'RW',
            '251': 'ET',
            '252': 'SO',
            '253': 'DJ',
            '254': 'KE',
            '255': 'TZ',
            '256': 'UG',
            '257': 'BI',
            '258': 'MZ',
            '260': 'ZM',
            '261': 'MG',
            '262': 'RE',
            '263': 'ZW',
            '264': 'NA',
            '265': 'MW',
            '266': 'LS',
            '267': 'BW',
            '268': 'SZ',
            '269': 'KM',
            '351': 'PT',
            '352': 'LU',
            '353': 'IE',
            '354': 'IS',
            '355': 'AL',
            '356': 'MT',
            '357': 'CY',
            '358': 'FI',
            '359': 'BG',
            '370': 'LT',
            '371': 'LV',
            '372': 'EE',
            '373': 'MD',
            '374': 'AM',
            '375': 'BY',
            '376': 'AD',
            '377': 'MC',
            '378': 'SM',
            '380': 'UA',
            '381': 'RS',
            '382': 'ME',
            '383': 'XK',
            '385': 'HR',
            '386': 'SI',
            '387': 'BA',
            '389': 'MK',
            '420': 'CZ',
            '421': 'SK',
            '423': 'LI',
            '501': 'BZ',
            '502': 'GT',
            '503': 'SV',
            '504': 'HN',
            '505': 'NI',
            '506': 'CR',
            '507': 'PA',
            '509': 'HT',
            '590': 'GP',
            '591': 'BO',
            '592': 'GY',
            '593': 'EC',
            '594': 'GF',
            '595': 'PY',
            '596': 'MQ',
            '597': 'SR',
            '598': 'UY',
            '599': 'CW',
            '670': 'TL',
            '672': 'NF',
            '673': 'BN',
            '674': 'NR',
            '675': 'PG',
            '676': 'TO',
            '677': 'SB',
            '678': 'VU',
            '679': 'FJ',
            '680': 'PW',
            '681': 'WF',
            '682': 'CK',
            '683': 'NU',
            '685': 'WS',
            '686': 'KI',
            '687': 'NC',
            '688': 'TV',
            '689': 'PF',
            '690': 'TK',
            '691': 'FM',
            '692': 'MH',
            '850': 'KP',
            '852': 'HK',
            '853': 'MO',
            '855': 'KH',
            '856': 'LA',
            '880': 'BD',
            '886': 'TW',
            '960': 'MV',
            '961': 'LB',
            '962': 'JO',
            '963': 'SY',
            '964': 'IQ',
            '965': 'KW',
            '966': 'SA',
            '967': 'YE',
            '968': 'OM',
            '970': 'PS',
            '971': 'AE',
            '972': 'IL',
            '973': 'BH',
            '974': 'QA',
            '975': 'BT',
            '976': 'MN',
            '977': 'NP',
            '992': 'TJ',
            '993': 'TM',
            '994': 'AZ',
            '995': 'GE',
            '996': 'KG',
            '998': 'UZ'
        }
        
        # Try to match country code (check up to 4 digits for special cases)
        for length in [4, 3, 2, 1]:
            prefix = phone_number[:length]
            if prefix in country_codes:
                return prefix
        
        return ''
    
    def _get_country_name(self, phone_number: str) -> str:
        """Get country name from phone number"""
        country_names = {
            '1': 'United States/Canada',
            '7': 'Russia/Kazakhstan', 
            '20': 'Egypt',
            '27': 'South Africa',
            '30': 'Greece',
            '31': 'Netherlands',
            '32': 'Belgium',
            '33': 'France',
            '34': 'Spain',
            '36': 'Hungary',
            '39': 'Italy',
            '40': 'Romania',
            '41': 'Switzerland',
            '43': 'Austria',
            '44': 'United Kingdom',
            '45': 'Denmark',
            '46': 'Sweden',
            '47': 'Norway',
            '48': 'Poland',
            '49': 'Germany',
            '51': 'Peru',
            '52': 'Mexico',
            '53': 'Cuba',
            '54': 'Argentina',
            '55': 'Brazil',
            '56': 'Chile',
            '57': 'Colombia',
            '58': 'Venezuela',
            '60': 'Malaysia',
            '61': 'Australia',
            '62': 'Indonesia',
            '63': 'Philippines',
            '64': 'New Zealand',
            '65': 'Singapore',
            '66': 'Thailand',
            '81': 'Japan',
            '82': 'South Korea',
            '84': 'Vietnam',
            '86': 'China',
            '90': 'Turkey',
            '91': 'India',
            '92': 'Pakistan',
            '93': 'Afghanistan',
            '94': 'Sri Lanka',
            '95': 'Myanmar',
            '98': 'Iran',
            '212': 'Morocco',
            '213': 'Algeria',
            '216': 'Tunisia',
            '218': 'Libya',
            '220': 'Gambia',
            '221': 'Senegal',
            '222': 'Mauritania',
            '223': 'Mali',
            '224': 'Guinea',
            '225': 'Ivory Coast',
            '226': 'Burkina Faso',
            '227': 'Niger',
            '228': 'Togo',
            '229': 'Benin',
            '230': 'Mauritius',
            '231': 'Liberia',
            '232': 'Sierra Leone',
            '233': 'Ghana',
            '234': 'Nigeria',
            '235': 'Chad',
            '236': 'Central African Republic',
            '237': 'Cameroon',
            '238': 'Cape Verde',
            '239': 'São Tomé and Príncipe',
            '240': 'Equatorial Guinea',
            '241': 'Gabon',
            '242': 'Republic of the Congo',
            '243': 'Democratic Republic of the Congo',
            '244': 'Angola',
            '245': 'Guinea-Bissau',
            '246': 'British Indian Ocean Territory',
            '248': 'Seychelles',
            '249': 'Sudan',
            '250': 'Rwanda',
            '251': 'Ethiopia',
            '252': 'Somalia',
            '253': 'Djibouti',
            '254': 'Kenya',
            '255': 'Tanzania',
            '256': 'Uganda',
            '257': 'Burundi',
            '258': 'Mozambique',
            '260': 'Zambia',
            '261': 'Madagascar',
            '262': 'Réunion',
            '263': 'Zimbabwe',
            '264': 'Namibia',
            '265': 'Malawi',
            '266': 'Lesotho',
            '267': 'Botswana',
            '268': 'Eswatini',
            '269': 'Comoros',
            '351': 'Portugal',
            '352': 'Luxembourg',
            '353': 'Ireland',
            '354': 'Iceland',
            '355': 'Albania',
            '356': 'Malta',
            '357': 'Cyprus',
            '358': 'Finland',
            '359': 'Bulgaria',
            '370': 'Lithuania',
            '371': 'Latvia',
            '372': 'Estonia',
            '373': 'Moldova',
            '374': 'Armenia',
            '375': 'Belarus',
            '376': 'Andorra',
            '377': 'Monaco',
            '378': 'San Marino',
            '380': 'Ukraine',
            '381': 'Serbia',
            '382': 'Montenegro',
            '383': 'Kosovo',
            '385': 'Croatia',
            '386': 'Slovenia',
            '387': 'Bosnia and Herzegovina',
            '389': 'North Macedonia',
            '420': 'Czech Republic',
            '421': 'Slovakia',
            '423': 'Liechtenstein',
            '501': 'Belize',
            '502': 'Guatemala',
            '503': 'El Salvador',
            '504': 'Honduras',
            '505': 'Nicaragua',
            '506': 'Costa Rica',
            '507': 'Panama',
            '509': 'Haiti',
            '590': 'Guadeloupe',
            '591': 'Bolivia',
            '592': 'Guyana',
            '593': 'Ecuador',
            '594': 'French Guiana',
            '595': 'Paraguay',
            '596': 'Martinique',
            '597': 'Suriname',
            '598': 'Uruguay',
            '599': 'Curaçao',
            '670': 'Timor-Leste',
            '672': 'Norfolk Island',
            '673': 'Brunei',
            '674': 'Nauru',
            '675': 'Papua New Guinea',
            '676': 'Tonga',
            '677': 'Solomon Islands',
            '678': 'Vanuatu',
            '679': 'Fiji',
            '680': 'Palau',
            '681': 'Wallis and Futuna',
            '682': 'Cook Islands',
            '683': 'Niue',
            '685': 'Samoa',
            '686': 'Kiribati',
            '687': 'New Caledonia',
            '688': 'Tuvalu',
            '689': 'French Polynesia',
            '690': 'Tokelau',
            '691': 'Micronesia',
            '692': 'Marshall Islands',
            '850': 'North Korea',
            '852': 'Hong Kong',
            '853': 'Macau',
            '855': 'Cambodia',
            '856': 'Laos',
            '880': 'Bangladesh',
            '886': 'Taiwan',
            '960': 'Maldives',
            '961': 'Lebanon',
            '962': 'Jordan',
            '963': 'Syria',
            '964': 'Iraq',
            '965': 'Kuwait',
            '966': 'Saudi Arabia',
            '967': 'Yemen',
            '968': 'Oman',
            '970': 'Palestine',
            '971': 'UAE',
            '972': 'Israel',
            '973': 'Bahrain',
            '974': 'Qatar',
            '975': 'Bhutan',
            '976': 'Mongolia',
            '977': 'Nepal',
            '992': 'Tajikistan',
            '993': 'Turkmenistan',
            '994': 'Azerbaijan',
            '995': 'Georgia',
            '996': 'Kyrgyzstan',
            '998': 'Uzbekistan'
        }
        
        code = self._extract_country_code(phone_number)
        return country_names.get(code, 'Unknown')
    
    def _format_phone_number(self, phone_number: str) -> str:
        """Format phone number with country code"""
        code = self._extract_country_code(phone_number)
        if code:
            return f"+{code} {phone_number[len(code):]}"
        return phone_number