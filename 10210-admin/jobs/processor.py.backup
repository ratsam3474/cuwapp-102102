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
from utils.file_handler import FileHandler
from utils.validation import DataValidator
from waha_functions import WAHAClient

logger = logging.getLogger(__name__)

class MessageProcessor:
    """Background message processor for campaign execution"""
    
    def __init__(self, waha_client: WAHAClient = None):
        self.waha = waha_client or WAHAClient()
        self.template_engine = MessageTemplateEngine()
        self.file_handler = FileHandler()
        self.validator = DataValidator()
        
        # Processing state
        self.active_campaigns = {}  # campaign_id -> processing_task
        self.stop_flags = {}        # campaign_id -> stop_flag
        
    async def start_campaign_processing(self, campaign_id: int) -> bool:
        """Start processing a campaign in background"""
        try:
            # Check if already running
            if campaign_id in self.active_campaigns:
                logger.warning(f"Campaign {campaign_id} is already being processed")
                return False
            
            # Get campaign
            with get_db() as db:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if not campaign:
                    logger.error(f"Campaign {campaign_id} not found")
                    return False
                
                if campaign.status != CampaignStatus.RUNNING.value:
                    logger.error(f"Campaign {campaign_id} is not in RUNNING status")
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
            
            # Check session availability early
            session_name = campaign.get('session_name', 'default')
            if not await self._check_session_health(session_name):
                validation_errors.append(f"WhatsApp session '{session_name}' is not available or not connected")
                logger.error(f"Campaign {campaign_id}: Session '{session_name}' health check failed")
            
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
            
            logger.info(f"✅ Campaign processing finished: {campaign_id}")
    
    async def _load_campaign_data(self, campaign_id: int) -> Optional[Dict[str, Any]]:
        """Load campaign and associated file data"""
        try:
            with get_db() as db:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if not campaign:
                    return None
                
                # Extract all campaign attributes while session is active
                campaign_dict = {
                    "id": campaign.id,
                    "name": campaign.name,
                    "session_name": campaign.session_name,
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
            
            # Check session health
            if not await self._check_session_health(campaign["session_name"]):
                await self._update_delivery_status(delivery_id, DeliveryStatus.FAILED, "Session not available")
                return
            
            # Send message
            send_result = await self._send_whatsapp_message(
                campaign["session_name"], phone_number, final_message
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
                
                logger.debug(f"Message sent successfully to {phone_number}")
                
            else:
                # Update delivery as failed
                await self._update_delivery_status(delivery_id, DeliveryStatus.FAILED, send_result["error"])
                await self._update_sample_analytics(campaign["id"], sample_index, success=False)
                
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
    
    async def _send_whatsapp_message(self, session_name: str, phone_number: str, message: str) -> Dict[str, Any]:
        """Send WhatsApp message via WAHA"""
        try:
            # Format chat ID (WhatsApp format: phone@c.us)
            chat_id = f"{phone_number}@c.us"
            
            # Send message
            result = self.waha.send_text(session_name, chat_id, message)
            
            # Extract just the ID string from the response
            message_id = result.get("id") if isinstance(result.get("id"), str) else str(result.get("id", ""))
            
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
    
    async def _check_session_health(self, session_name: str) -> bool:
        """Check if WhatsApp session is healthy and ready"""
        try:
            sessions = self.waha.get_sessions()
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
                    
        except Exception as e:
            logger.error(f"Failed to mark campaign failed: {str(e)}")
    
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
