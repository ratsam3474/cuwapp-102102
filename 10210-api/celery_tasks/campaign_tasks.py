"""
Celery tasks for campaign processing
Handles message sending, delivery tracking, and campaign analytics
"""

import logging
from celery import shared_task
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import random

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_campaign_message(self, campaign_id: int, phone_number: str, message_content: str, session_name: str):
    """
    Send a single campaign message
    This task is retryable and rate-limited
    """
    try:
        from waha_functions import WAHAClient
        from database.connection import get_db
        from database.models import Campaign, Delivery
        
        logger.info(f"Sending message for campaign {campaign_id} to {phone_number}")
        
        # Initialize WAHA client
        waha = WAHAClient()
        
        # Send message
        chat_id = f"{phone_number}@c.us"
        result = waha.send_text(session_name, chat_id, message_content)
        
        # Update delivery status
        with get_db() as db:
            delivery = db.query(Delivery).filter(
                Delivery.campaign_id == campaign_id,
                Delivery.phone_number == phone_number
            ).first()
            
            if delivery:
                if result and "id" in result:
                    delivery.status = "sent"
                    delivery.sent_at = datetime.utcnow()
                    delivery.message_id = result.get("id")
                    logger.info(f"Message sent successfully to {phone_number}")
                else:
                    delivery.status = "failed"
                    delivery.error_message = str(result)
                    logger.error(f"Failed to send message to {phone_number}: {result}")
                
                db.commit()
        
        return {"success": True, "phone": phone_number, "result": result}
        
    except Exception as e:
        logger.error(f"Error sending campaign message: {str(e)}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

@shared_task
def process_campaign_batch(campaign_id: int, phone_numbers: List[str], message_template: str, session_name: str):
    """
    Process a batch of campaign messages
    Splits them into individual tasks for parallel processing
    """
    try:
        from database.connection import get_db
        from database.models import Campaign
        
        logger.info(f"Processing batch of {len(phone_numbers)} messages for campaign {campaign_id}")
        
        # Update campaign status
        with get_db() as db:
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if campaign:
                campaign.status = "running"
                campaign.started_at = datetime.utcnow()
                db.commit()
        
        # Create individual tasks for each message
        for phone in phone_numbers:
            # Personalize message if needed
            message = message_template  # TODO: Add personalization logic
            
            # Add random delay between messages (1-5 seconds)
            delay = random.randint(1, 5)
            send_campaign_message.apply_async(
                args=[campaign_id, phone, message, session_name],
                countdown=delay
            )
        
        logger.info(f"Queued {len(phone_numbers)} messages for campaign {campaign_id}")
        return {"success": True, "queued": len(phone_numbers)}
        
    except Exception as e:
        logger.error(f"Error processing campaign batch: {str(e)}")
        return {"success": False, "error": str(e)}

@shared_task
def process_campaign_queue():
    """
    Periodic task to process pending campaigns
    Runs every minute via Celery Beat
    """
    try:
        from database.connection import get_db
        from database.models import Campaign, Delivery
        
        with get_db() as db:
            # Find campaigns that need processing
            pending_campaigns = db.query(Campaign).filter(
                Campaign.status.in_(["pending", "scheduled"]),
                Campaign.scheduled_time <= datetime.utcnow()
            ).all()
            
            for campaign in pending_campaigns:
                # Get pending deliveries
                pending_deliveries = db.query(Delivery).filter(
                    Delivery.campaign_id == campaign.id,
                    Delivery.status == "pending"
                ).limit(100).all()  # Process 100 at a time
                
                if pending_deliveries:
                    phone_numbers = [d.phone_number for d in pending_deliveries]
                    
                    # Queue batch processing
                    process_campaign_batch.delay(
                        campaign.id,
                        phone_numbers,
                        campaign.message_template,
                        campaign.session_name
                    )
                    
                    logger.info(f"Queued {len(phone_numbers)} messages for campaign {campaign.id}")
        
        return {"success": True, "processed_campaigns": len(pending_campaigns)}
        
    except Exception as e:
        logger.error(f"Error processing campaign queue: {str(e)}")
        return {"success": False, "error": str(e)}

@shared_task
def update_campaign_analytics(campaign_id: int):
    """
    Update analytics for a campaign
    Calculates delivery rates, response rates, etc.
    """
    try:
        from database.connection import get_db
        from database.models import Campaign, Delivery
        
        with get_db() as db:
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                return {"success": False, "error": "Campaign not found"}
            
            # Get delivery statistics
            deliveries = db.query(Delivery).filter(
                Delivery.campaign_id == campaign_id
            ).all()
            
            total = len(deliveries)
            sent = len([d for d in deliveries if d.status == "sent"])
            failed = len([d for d in deliveries if d.status == "failed"])
            read = len([d for d in deliveries if hasattr(d, 'read_at') and d.read_at])
            responded = len([d for d in deliveries if hasattr(d, 'response_received') and d.response_received])
            
            # Update campaign statistics
            campaign.total_recipients = total
            campaign.messages_sent = sent
            campaign.messages_failed = failed
            
            # Calculate rates
            delivery_rate = (sent / total * 100) if total > 0 else 0
            read_rate = (read / sent * 100) if sent > 0 else 0
            response_rate = (responded / sent * 100) if sent > 0 else 0
            
            # Check if campaign is complete
            if sent + failed == total and total > 0:
                campaign.status = "completed"
                campaign.completed_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Updated analytics for campaign {campaign_id}: {sent}/{total} sent, {failed} failed")
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "statistics": {
                    "total": total,
                    "sent": sent,
                    "failed": failed,
                    "read": read,
                    "responded": responded,
                    "delivery_rate": delivery_rate,
                    "read_rate": read_rate,
                    "response_rate": response_rate
                }
            }
            
    except Exception as e:
        logger.error(f"Error updating campaign analytics: {str(e)}")
        return {"success": False, "error": str(e)}

@shared_task
def check_message_status(campaign_id: int, message_ids: List[str]):
    """
    Check delivery status of messages via WAHA API
    Updates read receipts and delivery confirmations
    """
    try:
        from waha_functions import WAHAClient
        from database.connection import get_db
        from database.models import Delivery
        
        waha = WAHAClient()
        
        with get_db() as db:
            for message_id in message_ids:
                delivery = db.query(Delivery).filter(
                    Delivery.message_id == message_id,
                    Delivery.campaign_id == campaign_id
                ).first()
                
                if delivery:
                    # Check message status via WAHA
                    # This would need to be implemented in WAHA client
                    # For now, we'll simulate it
                    
                    # Update delivery confirmation
                    if delivery.status == "sent" and not delivery.delivered_at:
                        delivery.delivered_at = datetime.utcnow()
                    
                    # TODO: Check for read receipts and responses
                    
            db.commit()
        
        # Schedule analytics update
        update_campaign_analytics.delay(campaign_id)
        
        return {"success": True, "checked": len(message_ids)}
        
    except Exception as e:
        logger.error(f"Error checking message status: {str(e)}")
        return {"success": False, "error": str(e)}