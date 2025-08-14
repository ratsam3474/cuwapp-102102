"""
Message Processor - Background job processing engine
Handles campaign execution, message sending with random samples, and progress tracking
"""

import asyncio
import logging
import random
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Campaign, Delivery, CampaignAnalytics
from jobs.models import CampaignStatus, DeliveryStatus, MessageMode
from utils.templates import MessageTemplateEngine
import json
from utils.file_handler import FileHandler
from utils.validation import DataValidator
from waha_functions import WAHAClient

logger = logging.getLogger(__name__)

class MessageProcessor:
    """Background message processor for campaign execution"""
    
    def __init__(self, waha_client: WAHAClient = None):
        # Default WAHA client (for backward compatibility)
        self.default_waha = waha_client or WAHAClient()
        
        # Isolated WAHA clients for each campaign
        self.campaign_waha_clients = {}  # campaign_id -> WAHAClient
        
        self.template_engine = MessageTemplateEngine()
        self.file_handler = FileHandler()
        self.validator = DataValidator()
        
        # Processing state
        self.active_campaigns = {}  # campaign_id -> processing_task
        self.stop_flags = {}        # campaign_id -> stop_flag
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
    def _get_campaign_waha_client(self, campaign_id: int) -> WAHAClient:
        """Get or create an isolated WAHA client for a campaign"""
        if campaign_id not in self.campaign_waha_clients:
            self.campaign_waha_clients[campaign_id] = WAHAClient()
            logger.info(f"Created isolated WAHA client for campaign {campaign_id}")
        return self.campaign_waha_clients[campaign_id]
    
    def _cleanup_campaign_waha_client(self, campaign_id: int):
        """Clean up WAHA client for a campaign"""
        if campaign_id in self.campaign_waha_clients:
            del self.campaign_waha_clients[campaign_id]
            logger.info(f"Cleaned up WAHA client for campaign {campaign_id}")
    
    async def start_campaign_processing(self, campaign_id: int) -> bool:
        """Start processing a campaign in background"""
        try:
            # Get campaign first
            with get_db() as db:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if not campaign:
                    logger.error(f"Campaign {campaign_id} not found")
                    return False
                
                if campaign.status != CampaignStatus.RUNNING.value:
                    logger.error(f"Campaign {campaign_id} is not in RUNNING status")
                    return False
            
            # Use lock to ensure thread-safe operations
            async with self._lock:
                # Check if already running
                if campaign_id in self.active_campaigns:
                    logger.warning(f"Campaign {campaign_id} is already being processed")
                    return False
                
                # Create stop flag
                self.stop_flags[campaign_id] = False
                
                # Start background task
                task = asyncio.create_task(self._process_campaign(campaign_id))
                self.active_campaigns[campaign_id] = task
            
            logger.info(f"Started processing campaign {campaign_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start campaign processing {campaign_id}: {str(e)}")
            return False
    
    async def stop_campaign_processing(self, campaign_id: int) -> bool:
        """Stop processing a campaign"""
        try:
            if campaign_id in self.stop_flags:
                self.stop_flags[campaign_id] = True
                logger.info(f"Stop signal sent to campaign {campaign_id}")
                return True
            else:
                logger.warning(f"Campaign {campaign_id} is not being processed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to stop campaign processing {campaign_id}: {str(e)}")
            return False
    
    async def _process_campaign(self, campaign_id: int):
        """Main campaign processing loop"""
        try:
            logger.info(f"🚀 Starting campaign processing: {campaign_id}")
            
            # Load campaign and file data
            campaign_data = await self._load_campaign_data(campaign_id)
            if not campaign_data:
                await self._mark_campaign_failed(campaign_id, "Failed to load campaign data")
                return
            
            campaign = campaign_data['campaign']
            file_data = campaign_data['file_data']
            
            # Validate campaign before processing
            validation_errors = []
            
            # Check if we have data to process
            if not file_data or len(file_data) == 0:
                validation_errors.append("No data found in file to process")
                logger.error(f"Campaign {campaign_id}: No data rows found in file")
            
            # Check if message samples exist
            if not campaign.get('message_samples') or len(campaign['message_samples']) == 0:
                validation_errors.append("No message templates configured")
                logger.error(f"Campaign {campaign_id}: No message samples/templates provided")
            else:
                logger.info(f"Campaign {campaign_id}: Found {len(campaign['message_samples'])} message templates: {campaign['message_samples']}")
            
            # Check session availability early (use WAHA session name)
            waha_session_name = campaign.get('waha_session_name') or campaign.get('session_name', 'default')
            display_name = campaign.get('session_name', 'default')
            if not await self._check_session_health(waha_session_name, campaign_id):
                validation_errors.append(f"WhatsApp session '{display_name}' is not available or not connected")
                logger.error(f"Campaign {campaign_id}: Session '{display_name}' (WAHA: {waha_session_name}) health check failed")
            
            # If validation fails, mark campaign as failed with details
            if validation_errors:
                error_message = "Campaign validation failed: " + "; ".join(validation_errors)
                await self._mark_campaign_failed(campaign_id, error_message)
                return
            
            # Process each row
            for i, row_data in enumerate(file_data):
                # Check stop flag
                if self.stop_flags.get(campaign_id, False):
                    logger.info(f"Campaign {campaign_id} processing stopped by user")
                    break
                
                # Check if campaign was paused due to limits
                with get_db() as db:
                    current_campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                    if current_campaign and current_campaign.status == CampaignStatus.PAUSED.value:
                        logger.info(f"Campaign {campaign_id} is paused (likely due to message limits)")
                        break
                
                try:
                    # Process single message
                    await self._process_single_message(campaign, row_data, i + campaign["start_row"])
                    
                    # Update progress
                    await self._update_campaign_progress(campaign_id)
                    
                    # Rate limiting delay
                    await asyncio.sleep(campaign["delay_seconds"])
                    
                except Exception as e:
                    logger.error(f"Error processing row {i} in campaign {campaign_id}: {str(e)}")
                    await self._record_delivery_error(campaign_id, i + campaign["start_row"], str(e))
                    # Continue processing other rows
            
            # Mark campaign as completed
            await self._mark_campaign_completed(campaign_id)
            
        except Exception as e:
            logger.error(f"Campaign processing failed {campaign_id}: {str(e)}")
            await self._mark_campaign_failed(campaign_id, str(e))
        
        finally:
            # Cleanup
            if campaign_id in self.active_campaigns:
                del self.active_campaigns[campaign_id]
            if campaign_id in self.stop_flags:
                del self.stop_flags[campaign_id]
            
            # Clean up isolated WAHA client
            self._cleanup_campaign_waha_client(campaign_id)
            
            logger.info(f"✅ Campaign processing finished: {campaign_id}")
    
    async def _load_campaign_data(self, campaign_id: int) -> Optional[Dict[str, Any]]:
        """Load campaign and associated file data"""
        try:
            with get_db() as db:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if not campaign:
                    return None
                
                # Use the stored waha_session_name if available, otherwise convert
                if hasattr(campaign, 'waha_session_name') and campaign.waha_session_name:
                    waha_session_name = campaign.waha_session_name
                else:
                    # Fallback: Get the WAHA session name for this campaign's session
                    from database.user_sessions import UserWhatsAppSession
                    user_session = db.query(UserWhatsAppSession).filter(
                        UserWhatsAppSession.session_name == campaign.session_name
                    ).first()
                    
                    waha_session_name = user_session.waha_session_name if user_session and user_session.waha_session_name else campaign.session_name
                
                # Extract all campaign attributes while session is active
                campaign_dict = {
                    "id": campaign.id,
                    "name": campaign.name,
                    "user_id": campaign.user_id,  # IMPORTANT: Include user_id for metrics tracking
                    "session_name": campaign.session_name,  # Keep display name for UI
                    "waha_session_name": waha_session_name,  # Add WAHA session name for API calls
                    "file_path": campaign.file_path,
                    "column_mapping": campaign.column_mapping_dict,
                    "start_row": campaign.start_row,
                    "end_row": campaign.end_row,
                    "message_mode": campaign.message_mode,
                    "message_samples": campaign.message_samples,
                    "use_csv_samples": campaign.use_csv_samples,
                    "delay_seconds": campaign.delay_seconds,
                    "retry_attempts": campaign.retry_attempts,
                    "max_daily_messages": campaign.max_daily_messages,
                    "exclude_my_contacts": campaign.exclude_my_contacts,
                    "exclude_previous_conversations": campaign.exclude_previous_conversations,
                    "save_contact_before_message": campaign.save_contact_before_message,
                    "total_rows": campaign.total_rows
                }
                
                # Load file data
                if not campaign_dict["file_path"]:
                    logger.warning(f"Campaign {campaign_id} has no file path configured")
                    return {"campaign": campaign_dict, "file_data": []}
                
                # Check if file exists
                if not os.path.exists(campaign_dict["file_path"]):
                    logger.error(f"Campaign {campaign_id}: File not found: {campaign_dict['file_path']}")
                    return None
                
                try:
                    processor = self.file_handler.get_processor(campaign_dict["file_path"])
                    file_data = processor.read_data(
                        campaign_dict["file_path"],
                        start_row=campaign_dict["start_row"],
                        end_row=campaign_dict["end_row"]
                    )
                    logger.info(f"Campaign {campaign_id}: Loaded {len(file_data)} rows from file")
                except Exception as file_error:
                    logger.error(f"Campaign {campaign_id}: Failed to read file: {str(file_error)}")
                    return None
                
                # Update total rows if not set
                if campaign_dict["total_rows"] == 0:
                    campaign.total_rows = len(file_data)
                    campaign_dict["total_rows"] = len(file_data)
                    db.commit()
                
                return {
                    "campaign": campaign_dict,
                    "file_data": file_data
                }
                
        except Exception as e:
            logger.error(f"Failed to load campaign data {campaign_id}: {str(e)}")
            return None
    
    async def _process_single_message(self, campaign: Dict[str, Any], row_data: Dict[str, Any], row_number: int):
        """Process and send a single message"""
        try:
            # Apply column mapping to transform raw data
            mapped_data = self._apply_column_mapping(row_data, campaign.get("column_mapping", {}))
            
            # Check conditions before processing
            if campaign.get("exclude_my_contacts", False):
                # Check if contact is saved in phone
                if mapped_data.get("is_my_contact") in [True, "true", "True", "yes", "Yes", "1", 1]:
                    logger.info(f"Skipping row {row_number}: Contact is saved in phone")
                    await self._record_delivery_error(campaign["id"], row_number, "Skipped: Contact is saved in phone")
                    return
            
            if campaign.get("exclude_previous_conversations", False):
                # Check if there's previous conversation (last_msg_status not empty)
                if mapped_data.get("last_msg_status") and str(mapped_data.get("last_msg_status")).strip():
                    logger.info(f"Skipping row {row_number}: Previous conversation exists")
                    await self._record_delivery_error(campaign["id"], row_number, "Skipped: Previous conversation exists")
                    return
            
            # Validate mapped data
            validation_result = self.validator.validate_row(mapped_data, row_number)
            if not validation_result["valid"]:
                error_msg = "; ".join(validation_result["errors"])
                await self._record_delivery_error(campaign["id"], row_number, f"Validation failed: {error_msg}")
                return
            
            processed_data = validation_result["processed_data"]
            
            # Check required fields
            if 'phone_number' not in processed_data:
                error_msg = f"Missing phone number in row. Available columns: {list(processed_data.keys())}"
                logger.warning(f"Campaign {campaign['id']}, Row {row_number}: {error_msg}")
                await self._record_delivery_error(campaign["id"], row_number, error_msg)
                return
            
            phone_number = processed_data['phone_number']
            recipient_name = processed_data.get('name', '')
            
            # Format phone number to match expected format (with space after country code)
            # This handles both formats: "+16176596898" and "+1 6176596898"
            if phone_number and not ' ' in phone_number:
                # Add space after country code if missing
                if phone_number.startswith('+1') and len(phone_number) > 2:
                    phone_number = f"+1 {phone_number[2:]}"
                elif phone_number.startswith('+234') and len(phone_number) > 4:
                    phone_number = f"+234 {phone_number[4:]}"
                elif phone_number.startswith('+91') and len(phone_number) > 3:
                    phone_number = f"+91 {phone_number[3:]}"
                elif phone_number.startswith('+44') and len(phone_number) > 3:
                    phone_number = f"+44 {phone_number[3:]}"
                # Add more country codes as needed
            
            # Generate message content
            message_result = await self._generate_message_content(campaign, processed_data)
            if not message_result["success"]:
                await self._record_delivery_error(campaign["id"], row_number, message_result["error"])
                return
            
            sample_index = message_result["sample_index"]
            sample_text = message_result["sample_text"]
            final_message = message_result["final_message"]
            
            # Create delivery record
            delivery_id = await self._create_delivery_record(
                campaign["id"], row_number, phone_number, recipient_name,
                sample_index, sample_text, final_message, processed_data
            )
            
            # Check session health (use WAHA session name)
            if not await self._check_session_health(campaign.get("waha_session_name", campaign["session_name"]), campaign["id"]):
                await self._update_delivery_status(delivery_id, DeliveryStatus.FAILED, "Session not available")
                return
            
            # Save contact if enabled (use WAHA session name)
            if campaign.get("save_contact_before_message", False):
                contact_saved = await self._save_contact_before_send(
                    campaign["id"], campaign.get("waha_session_name", campaign["session_name"]), phone_number, row_data
                )
                if not contact_saved:
                    logger.warning(f"Could not save contact {phone_number}, but continuing with message")
            
            # Send message (use WAHA session name)
            send_result = await self._send_whatsapp_message(
                campaign["id"], campaign.get("waha_session_name", campaign["session_name"]), phone_number, final_message
            )
            
            if send_result["success"]:
                # Update delivery as sent
                # Ensure we only pass a string for the message ID
                message_id = send_result.get("message_id", "")
                if not isinstance(message_id, str):
                    message_id = str(message_id) if message_id else ""
                    
                await self._update_delivery_status(
                    delivery_id, 
                    DeliveryStatus.SENT, 
                    None,
                    whatsapp_message_id=message_id
                )
                
                # Update analytics
                await self._update_sample_analytics(campaign["id"], sample_index, success=True)
                
                # Update user metrics
                if campaign.get("user_id"):
                    from database.user_metrics import UserMetrics
                    from database.connection import get_db
                    with get_db() as db:
                        metrics = UserMetrics.get_or_create(db, campaign["user_id"])
                        metrics.add_messages(db, sent=1)
                
                logger.debug(f"Message sent successfully to {phone_number}")
                
            else:
                # Update delivery as failed
                await self._update_delivery_status(delivery_id, DeliveryStatus.FAILED, send_result["error"])
                await self._update_sample_analytics(campaign["id"], sample_index, success=False)
                
                # Update user metrics
                if campaign.get("user_id"):
                    from database.user_metrics import UserMetrics
                    from database.connection import get_db
                    with get_db() as db:
                        metrics = UserMetrics.get_or_create(db, campaign["user_id"])
                        metrics.add_messages(db, failed=1)
                
                logger.warning(f"Failed to send message to {phone_number}: {send_result['error']}")
            
        except Exception as e:
            logger.error(f"Error processing message for row {row_number}: {str(e)}")
            await self._record_delivery_error(campaign["id"], row_number, f"Processing error: {str(e)}")
    
    async def _generate_message_content(self, campaign: Dict[str, Any], row_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate message content with random sample selection"""
        try:
            # Get available samples
            campaign_samples = None
            csv_samples_column = None
            
            # Extract campaign samples for both SINGLE and MULTIPLE modes
            if campaign["message_samples"]:
                # For both SINGLE and MULTIPLE modes, we need the samples
                campaign_samples = []
                for sample in campaign["message_samples"]:
                    # Handle both dict format and direct string format
                    if isinstance(sample, dict) and "text" in sample:
                        campaign_samples.append(sample["text"])
                    elif isinstance(sample, str):
                        campaign_samples.append(sample)
                
                # If no samples were extracted, log error
                if not campaign_samples:
                    logger.error(f"No valid samples found in campaign {campaign['id']} message_samples")
                else:
                    logger.debug(f"Campaign {campaign['id']}: Found {len(campaign_samples)} message templates")
            
            # Handle CSV samples if enabled
            if campaign["use_csv_samples"]:
                csv_samples_column = "message_samples"
            
            # Process message with template engine
            sample_index, sample_text, final_message = self.template_engine.process_message_with_samples(
                row_data=row_data,
                campaign_samples=campaign_samples,
                csv_samples_column=csv_samples_column
            )
            
            return {
                "success": True,
                "sample_index": sample_index,
                "sample_text": sample_text,
                "final_message": final_message
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sample_index": None,
                "sample_text": None,
                "final_message": None
            }
    
    async def _save_contact_before_send(self, campaign_id: int, session_name: str, phone_number: str, row_data: Dict[str, Any]) -> bool:
        """Save contact to WhatsApp before sending message"""
        try:
            # Get isolated WAHA client for this campaign
            waha_client = self._get_campaign_waha_client(campaign_id)
            
            # Extract contact name from row data
            contact_name = None
            # Try common name fields
            for field in ['name', 'Name', 'first_name', 'last_name', 'contact_name', 'full_name']:
                if field in row_data and row_data[field]:
                    contact_name = str(row_data[field])
                    break
            
            # If no name found, use phone number as name
            if not contact_name:
                contact_name = phone_number
            
            # Format phone for saving (ensure it's just the number)
            clean_phone = phone_number.replace('+', '').replace('-', '').replace(' ', '')
            
            # Save contact using WAHA API (using PUT to /api/{session}/contacts/{chatId})
            try:
                # Format chat ID for contact
                chat_id = f"{clean_phone}@c.us"
                
                # Create/update contact using the correct endpoint
                result = waha_client._make_request(
                    "PUT",
                    f"/api/{session_name}/contacts/{chat_id}",
                    json={
                        "firstName": contact_name,
                        "lastName": ""
                    }
                )
                
                logger.info(f"Contact saved: {contact_name} ({phone_number})")
                return True
                
            except Exception as e:
                logger.warning(f"Failed to save contact {phone_number}: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Error in save_contact_before_send: {str(e)}")
            return False
    
    async def _send_whatsapp_message(self, campaign_id: int, session_name: str, phone_number: str, message: str) -> Dict[str, Any]:
        """Send WhatsApp message via WAHA with subscription limit enforcement"""
        try:
            # CHECK MESSAGE LIMITS BEFORE SENDING
            from database.subscription_models import UserSubscription
            
            with get_db() as db:
                # Get campaign to find user_id
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if campaign and campaign.user_id:
                    # Get user subscription
                    user_sub = db.query(UserSubscription).filter(
                        UserSubscription.user_id == campaign.user_id
                    ).first()
                    
                    if user_sub:
                        # Check if user has reached message limit
                        if not user_sub.is_within_limits("messages"):
                            error_msg = f"Monthly message limit reached ({user_sub.messages_sent_this_month}/{user_sub.max_messages_per_month}). Upgrade to {self._get_next_plan(user_sub.plan_type.value)} plan for more messages."
                            logger.warning(f"Campaign {campaign_id} stopped: {error_msg}")
                            
                            # Stop the campaign and store error message
                            campaign.status = CampaignStatus.PAUSED.value
                            campaign.error_details = error_msg
                            campaign.updated_at = datetime.utcnow()
                            db.commit()
                            
                            return {
                                "success": False,
                                "error": error_msg,
                                "message_id": None,
                                "limit_reached": True
                            }
            
            # Format chat ID based on whether it's a group or individual
            # Groups have IDs ending with @g.us or containing 'g.us'
            if '@g.us' in phone_number or '-' in phone_number:
                # It's already a group ID or looks like a group ID
                if '@g.us' not in phone_number:
                    chat_id = f"{phone_number}@g.us"
                else:
                    chat_id = phone_number
            else:
                # It's an individual user
                chat_id = f"{phone_number}@c.us"
            
            # Get isolated WAHA client for this campaign
            waha_client = self._get_campaign_waha_client(campaign_id)
            
            # Send message
            result = waha_client.send_text(session_name, chat_id, message)
            
            # Extract just the ID string from the response
            message_id = result.get("id") if isinstance(result.get("id"), str) else str(result.get("id", ""))
            
            # INCREMENT MESSAGE COUNTER AFTER SUCCESSFUL SEND
            with get_db() as db:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if campaign and campaign.user_id:
                    user_sub = db.query(UserSubscription).filter(
                        UserSubscription.user_id == campaign.user_id
                    ).first()
                    
                    if user_sub:
                        user_sub.messages_sent_this_month += 1
                        db.commit()
                        logger.debug(f"User {campaign.user_id} message count: {user_sub.messages_sent_this_month}/{user_sub.max_messages_per_month}")
            
            return {
                "success": True,
                "message_id": message_id,
                "response": result
            }
            
        except Exception as e:
            logger.error(f"WAHA send error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message_id": None
            }
    
    def _get_next_plan(self, current_plan: str) -> str:
        """Get the next plan for upgrade suggestion"""
        plan_hierarchy = {
            "free": "Starter",
            "starter": "Hobby",
            "hobby": "Pro",
            "pro": "Premium",
            "premium": "Premium"
        }
        return plan_hierarchy.get(current_plan, "Premium")
    
    async def _check_session_health(self, session_name: str, campaign_id: Optional[int] = None) -> bool:
        """Check if WhatsApp session is healthy and ready"""
        try:
            # Use campaign-specific client if campaign_id provided, otherwise use default
            waha_client = self._get_campaign_waha_client(campaign_id) if campaign_id else self.default_waha
            sessions = waha_client.get_sessions()
            logger.debug(f"Available sessions: {[s.get('name') for s in sessions]}")
            
            for session in sessions:
                if session.get("name") == session_name:
                    status = session.get("status")
                    logger.info(f"Session '{session_name}' status: {status}")
                    if status != "WORKING":
                        logger.warning(f"Session '{session_name}' is not in WORKING state, current status: {status}")
                    return status == "WORKING"
            
            logger.error(f"Session '{session_name}' not found in available sessions")
            return False
        except Exception as e:
            logger.error(f"Session health check failed: {str(e)}")
            return False
    
    async def _create_delivery_record(
        self, 
        campaign_id: int, 
        row_number: int, 
        phone_number: str, 
        recipient_name: str,
        sample_index: Optional[int],
        sample_text: Optional[str],
        final_message: str,
        variable_data: Dict[str, Any]
    ) -> int:
        """Create delivery record in database"""
        try:
            with get_db() as db:
                delivery = Delivery(
                    campaign_id=campaign_id,
                    row_number=row_number,
                    phone_number=phone_number,
                    recipient_name=recipient_name,
                    selected_sample_index=sample_index,
                    selected_sample_text=sample_text,
                    final_message_content=final_message,
                    variable_data=variable_data,
                    status=DeliveryStatus.SENDING.value
                )
                
                db.add(delivery)
                db.flush()
                delivery_id = delivery.id
                db.commit()
                
                return delivery_id
                
        except Exception as e:
            logger.error(f"Failed to create delivery record: {str(e)}")
            raise
    
    async def _update_delivery_status(
        self, 
        delivery_id: int, 
        status: DeliveryStatus, 
        error_message: Optional[str] = None,
        whatsapp_message_id: Optional[str] = None
    ):
        """Update delivery status"""
        try:
            with get_db() as db:
                delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
                if delivery:
                    delivery.status = status.value
                    delivery.error_message = error_message
                    delivery.whatsapp_message_id = whatsapp_message_id
                    
                    if status == DeliveryStatus.SENT:
                        delivery.sent_at = datetime.utcnow()
                    elif status == DeliveryStatus.DELIVERED:
                        delivery.delivered_at = datetime.utcnow()
                    
                    db.commit()
                    
        except Exception as e:
            logger.error(f"Failed to update delivery status: {str(e)}")
    
    async def _record_delivery_error(self, campaign_id: int, row_number: int, error_message: str):
        """Record delivery error"""
        try:
            with get_db() as db:
                delivery = Delivery(
                    campaign_id=campaign_id,
                    row_number=row_number,
                    phone_number="",
                    status=DeliveryStatus.FAILED.value,
                    error_message=error_message
                )
                
                db.add(delivery)
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to record delivery error: {str(e)}")
    
    async def _update_campaign_progress(self, campaign_id: int):
        """Update campaign progress based on delivery records"""
        try:
            with get_db() as db:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if not campaign:
                    return
                
                # Count deliveries
                total_deliveries = db.query(Delivery).filter(Delivery.campaign_id == campaign_id).count()
                successful_deliveries = db.query(Delivery).filter(
                    Delivery.campaign_id == campaign_id,
                    Delivery.status.in_([DeliveryStatus.SENT.value, DeliveryStatus.DELIVERED.value])
                ).count()
                failed_deliveries = db.query(Delivery).filter(
                    Delivery.campaign_id == campaign_id,
                    Delivery.status == DeliveryStatus.FAILED.value
                ).count()
                
                # Update campaign
                campaign.processed_rows = total_deliveries
                campaign.success_count = successful_deliveries
                campaign.error_count = failed_deliveries
                
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to update campaign progress: {str(e)}")
    
    async def _update_sample_analytics(self, campaign_id: int, sample_index: Optional[int], success: bool):
        """Update sample analytics"""
        if sample_index is None:
            return
        
        try:
            with get_db() as db:
                analytics = db.query(CampaignAnalytics).filter(
                    CampaignAnalytics.campaign_id == campaign_id,
                    CampaignAnalytics.sample_index == sample_index
                ).first()
                
                if analytics:
                    analytics.usage_count += 1
                    if success:
                        analytics.success_count += 1
                    else:
                        analytics.error_count += 1
                    
                    db.commit()
                    
        except Exception as e:
            logger.error(f"Failed to update sample analytics: {str(e)}")
    
    async def _mark_campaign_completed(self, campaign_id: int):
        """Mark campaign as completed"""
        try:
            with get_db() as db:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if campaign:
                    campaign.status = CampaignStatus.COMPLETED.value
                    campaign.completed_at = datetime.utcnow()
                    db.commit()
                    
                    logger.info(f"Campaign {campaign_id} marked as completed")
                    
                    # Resume any paused warmers
                    await self._resume_warmers_after_campaign(campaign)
                    
        except Exception as e:
            logger.error(f"Failed to mark campaign completed: {str(e)}")
    
    async def _mark_campaign_failed(self, campaign_id: int, error_message: str):
        """Mark campaign as failed"""
        try:
            with get_db() as db:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if campaign:
                    campaign.status = CampaignStatus.FAILED.value
                    campaign.completed_at = datetime.utcnow()
                    campaign.error_details = error_message  # Store the error details
                    db.commit()
                    
                    logger.error(f"Campaign {campaign_id} marked as failed: {error_message}")
                    
                    # Resume any paused warmers
                    await self._resume_warmers_after_campaign(campaign)
                    
        except Exception as e:
            logger.error(f"Failed to mark campaign failed: {str(e)}")
    
    async def _resume_warmers_after_campaign(self, campaign: Campaign):
        """Resume warmers that were paused for a campaign"""
        try:
            if not campaign.auto_paused_warmers:
                return
                
            # Check if there are other queued or running campaigns
            with get_db() as db:
                # Check for any campaigns that are running or queued
                from jobs.models import CampaignStatus
                active_campaigns = db.query(Campaign).filter(
                    Campaign.id != campaign.id,
                    Campaign.status.in_([
                        CampaignStatus.RUNNING.value,
                        CampaignStatus.QUEUED.value
                    ])
                ).count()
                
                if active_campaigns > 0:
                    logger.info(f"Not resuming warmers - {active_campaigns} campaigns still active/queued")
                    return
                
            # Import warmer models only if available
            try:
                from warmer.models import WarmerSession
                from warmer.orchestrator import warmer_orchestrator
                
                paused_warmer_ids = json.loads(campaign.auto_paused_warmers)
                
                with get_db() as db:
                    resumed_count = 0
                    for warmer_id in paused_warmer_ids:
                        warmer = db.query(WarmerSession).filter(
                            WarmerSession.id == warmer_id
                        ).first()
                        
                        if warmer and warmer.status == 'paused_for_campaign':
                            logger.info(f"Resuming warmer {warmer.id} after campaign {campaign.id}")
                            
                            # Resume the warmer
                            warmer.status = 'warming'
                            warmer.paused_reason = None
                            resumed_count += 1
                            
                            # Restart the warmer processing
                            if hasattr(warmer_orchestrator, 'resume_warmer'):
                                await warmer_orchestrator.resume_warmer(warmer.id)
                    
                    # Clear the paused warmers list
                    campaign.auto_paused_warmers = None
                    db.commit()
                    
                    logger.info(f"Resumed {resumed_count} warmers after campaign {campaign.id}")
                    
            except ImportError:
                logger.debug("Warmer module not available, skipping warmer resume")
                
        except Exception as e:
            logger.error(f"Error resuming warmers after campaign {campaign.id}: {str(e)}")
    
    def _apply_column_mapping(self, row_data: Dict[str, Any], column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Apply column mapping to transform raw data"""
        if not column_mapping:
            return row_data
        
        mapped_data = {}
        
        # Map specified columns
        for target_field, source_column in column_mapping.items():
            if source_column in row_data:
                mapped_data[target_field] = row_data[source_column]
        
        # Include all original data as well (for template variables)
        mapped_data.update(row_data)
        
        return mapped_data
    
    def get_processing_status(self) -> Dict[str, Any]:
        """Get current processing status"""
        return {
            "active_campaigns": list(self.active_campaigns.keys()),
            "total_active": len(self.active_campaigns),
            "processor_health": "healthy"
        }

# Global processor instance
message_processor = MessageProcessor()
