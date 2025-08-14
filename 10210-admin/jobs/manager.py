"""
Campaign Manager - Handles campaign lifecycle and operations
"""

import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_, func

from database.connection import get_db, get_session
from database.models import Campaign, Delivery, CampaignAnalytics
from .models import (
    CampaignCreate, CampaignUpdate, CampaignResponse, 
    CampaignStatus, MessageMode, CampaignStats
)

logger = logging.getLogger(__name__)

class CampaignManager:
    """Manages campaign operations and lifecycle"""
    
    def __init__(self):
        self.logger = logger
    
    def create_campaign(self, campaign_data: CampaignCreate) -> CampaignResponse:
        """Create a new campaign"""
        try:
            with get_db() as db:
                # Track user metrics
                if campaign_data.user_id:
                    from database.user_metrics import UserMetrics
                    metrics = UserMetrics.get_or_create(db, campaign_data.user_id)
                    metrics.increment_campaigns(db, 'created')
                
                # Create campaign instance
                campaign = Campaign(
                    name=campaign_data.name,
                    session_name=campaign_data.session_name,  # Display name for UI
                    waha_session_name=getattr(campaign_data, 'waha_session_name', None),  # Actual WAHA name
                    user_id=campaign_data.user_id,  # Include user_id
                    file_path=campaign_data.file_path,
                    column_mapping_dict=campaign_data.column_mapping or {},
                    start_row=campaign_data.start_row,
                    end_row=campaign_data.end_row,
                    message_mode=campaign_data.message_mode.value,
                    message_samples=[sample.dict() if hasattr(sample, 'dict') else sample for sample in campaign_data.message_samples],
                    use_csv_samples=campaign_data.use_csv_samples,
                    delay_seconds=campaign_data.delay_seconds,
                    retry_attempts=campaign_data.retry_attempts,
                    max_daily_messages=campaign_data.max_daily_messages,
                    exclude_my_contacts=campaign_data.exclude_my_contacts,
                    exclude_previous_conversations=campaign_data.exclude_previous_conversations,
                    save_contact_before_message=campaign_data.save_contact_before_message,
                    scheduled_start_time=campaign_data.scheduled_start_time,
                    is_scheduled=campaign_data.is_scheduled,
                    status=CampaignStatus.SCHEDULED.value if campaign_data.is_scheduled else CampaignStatus.CREATED.value
                )
                
                db.add(campaign)
                db.flush()  # Get the ID
                
                # Create initial analytics records for each sample
                if campaign_data.message_mode == MessageMode.MULTIPLE:
                    for idx, sample in enumerate(campaign_data.message_samples):
                        analytics = CampaignAnalytics(
                            campaign_id=campaign.id,
                            sample_index=idx,
                            sample_text=sample.text
                        )
                        db.add(analytics)
                
                db.commit()
                
                self.logger.info(f"Campaign '{campaign.name}' created with ID {campaign.id}")
                return self._campaign_to_response(campaign)
                
        except Exception as e:
            self.logger.error(f"Failed to create campaign: {str(e)}")
            raise
    
    def get_campaign(self, campaign_id: int) -> Optional[CampaignResponse]:
        """Get campaign by ID"""
        try:
            with get_db() as db:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if campaign:
                    return self._campaign_to_response(campaign)
                return None
        except Exception as e:
            self.logger.error(f"Failed to get campaign {campaign_id}: {str(e)}")
            raise
    
    def get_campaigns(
        self, 
        status: Optional[str] = None,  # Changed to str to support string status values
        session_name: Optional[str] = None,
        is_scheduled: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[CampaignResponse]:
        """Get campaigns with optional filtering"""
        try:
            with get_db() as db:
                query = db.query(Campaign)
                
                # Apply filters
                if status:
                    # Handle both string and enum values
                    status_value = status.value if hasattr(status, 'value') else status
                    query = query.filter(Campaign.status == status_value)
                if session_name:
                    query = query.filter(Campaign.session_name == session_name)
                if is_scheduled is not None:
                    query = query.filter(Campaign.is_scheduled == is_scheduled)
                
                # Apply pagination and ordering
                campaigns = query.order_by(desc(Campaign.created_at)).offset(offset).limit(limit).all()
                
                return [self._campaign_to_response(campaign) for campaign in campaigns]
                
        except Exception as e:
            self.logger.error(f"Failed to get campaigns: {str(e)}")
            raise
    
    def update_campaign(self, campaign_id: int, update_data: Any) -> Optional[CampaignResponse]:
        """Update campaign - accepts both CampaignUpdate or dict"""
        try:
            with get_db() as db:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if not campaign:
                    return None
                
                # Handle both CampaignUpdate and dict
                if isinstance(update_data, dict):
                    update_dict = update_data
                else:
                    update_dict = update_data.dict(exclude_unset=True)
                    
                for field, value in update_dict.items():
                    if hasattr(campaign, field):
                        setattr(campaign, field, value)
                
                db.commit()
                
                self.logger.info(f"Campaign {campaign_id} updated")
                return self._campaign_to_response(campaign)
                
        except Exception as e:
            self.logger.error(f"Failed to update campaign {campaign_id}: {str(e)}")
            raise
    
    def delete_campaign(self, campaign_id: int) -> bool:
        """Delete campaign and all related data"""
        try:
            with get_db() as db:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if not campaign:
                    return False
                
                # Check if campaign is running
                if campaign.status == CampaignStatus.RUNNING.value:
                    raise ValueError("Cannot delete a running campaign. Stop it first.")
                
                # Delete associated file if exists
                if campaign.file_path and os.path.exists(campaign.file_path):
                    try:
                        os.remove(campaign.file_path)
                    except OSError:
                        pass  # File deletion failure shouldn't stop campaign deletion
                
                db.delete(campaign)
                db.commit()
                
                self.logger.info(f"Campaign {campaign_id} deleted")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to delete campaign {campaign_id}: {str(e)}")
            raise
    
    def start_campaign(self, campaign_id: int) -> bool:
        """Start campaign processing"""
        try:
            with get_db() as db:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if not campaign:
                    return False
                
                if campaign.status not in [CampaignStatus.CREATED.value, CampaignStatus.SCHEDULED.value, CampaignStatus.PAUSED.value]:
                    raise ValueError(f"Cannot start campaign in status: {campaign.status}")
                
                campaign.status = CampaignStatus.RUNNING.value
                if not campaign.started_at:
                    campaign.started_at = datetime.utcnow()
                
                # Clear scheduling fields if starting a scheduled campaign
                if campaign.is_scheduled:
                    campaign.is_scheduled = False
                    campaign.scheduled_start_time = None
                
                db.commit()
                
                self.logger.info(f"Campaign {campaign_id} started")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to start campaign {campaign_id}: {str(e)}")
            raise
    
    def pause_campaign(self, campaign_id: int) -> bool:
        """Pause campaign processing"""
        try:
            with get_db() as db:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if not campaign:
                    return False
                
                if campaign.status != CampaignStatus.RUNNING.value:
                    raise ValueError(f"Cannot pause campaign in status: {campaign.status}")
                
                campaign.status = CampaignStatus.PAUSED.value
                db.commit()
                
                self.logger.info(f"Campaign {campaign_id} paused")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to pause campaign {campaign_id}: {str(e)}")
            raise
    
    def stop_campaign(self, campaign_id: int) -> bool:
        """Stop campaign processing"""
        try:
            with get_db() as db:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if not campaign:
                    return False
                
                # Allow stopping queued campaigns (remove from queue)
                if campaign.status == CampaignStatus.QUEUED.value:
                    campaign.status = CampaignStatus.CREATED.value
                    campaign.queue_position = None
                    db.commit()
                    self.logger.info(f"Campaign {campaign_id} removed from queue")
                    return True
                
                if campaign.status not in [CampaignStatus.RUNNING.value, CampaignStatus.PAUSED.value]:
                    raise ValueError(f"Cannot stop campaign in status: {campaign.status}")
                
                campaign.status = CampaignStatus.CANCELLED.value
                campaign.completed_at = datetime.utcnow()
                db.commit()
                
                self.logger.info(f"Campaign {campaign_id} stopped")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to stop campaign {campaign_id}: {str(e)}")
            raise
    
    def complete_campaign(self, campaign_id: int) -> bool:
        """Mark campaign as completed"""
        try:
            with get_db() as db:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if not campaign:
                    return False
                
                campaign.status = CampaignStatus.COMPLETED.value
                campaign.completed_at = datetime.utcnow()
                db.commit()
                
                self.logger.info(f"Campaign {campaign_id} completed")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to complete campaign {campaign_id}: {str(e)}")
            raise
    
    def get_campaign_stats(self) -> CampaignStats:
        """Get overall campaign statistics"""
        try:
            with get_db() as db:
                # Count campaigns by status
                total_campaigns = db.query(Campaign).count()
                active_campaigns = db.query(Campaign).filter(
                    Campaign.status.in_([CampaignStatus.RUNNING.value, CampaignStatus.PAUSED.value])
                ).count()
                completed_campaigns = db.query(Campaign).filter(
                    Campaign.status == CampaignStatus.COMPLETED.value
                ).count()
                failed_campaigns = db.query(Campaign).filter(
                    Campaign.status == CampaignStatus.FAILED.value
                ).count()
                
                # Get message statistics
                total_sent = db.query(Campaign).with_entities(
                    func.sum(Campaign.success_count)
                ).scalar() or 0
                
                total_processed = db.query(Campaign).with_entities(
                    func.sum(Campaign.processed_rows)
                ).scalar() or 0
                
                # Calculate overall success rate
                overall_success_rate = (total_sent / total_processed * 100) if total_processed > 0 else 0
                
                return CampaignStats(
                    total_campaigns=total_campaigns,
                    active_campaigns=active_campaigns,
                    completed_campaigns=completed_campaigns,
                    failed_campaigns=failed_campaigns,
                    total_messages_sent=int(total_sent),  # Ensure int type
                    total_messages_delivered=int(total_sent),  # For now, assume sent = delivered
                    total_messages=int(total_sent),  # Add total_messages field
                    overall_success_rate=round(overall_success_rate, 2),
                    avg_delivery_time=None  # TODO: Calculate from delivery data
                )
                
        except Exception as e:
            self.logger.error(f"Failed to get campaign stats: {str(e)}")
            raise
    
    def get_active_campaigns(self) -> List[CampaignResponse]:
        """Get all active (running/paused) campaigns"""
        return self.get_campaigns(status=None)  # Will filter for active in query
    
    def cleanup_old_campaigns(self, days_old: int = 30) -> int:
        """Clean up old completed campaigns"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            with get_db() as db:
                old_campaigns = db.query(Campaign).filter(
                    and_(
                        Campaign.status.in_([CampaignStatus.COMPLETED.value, CampaignStatus.FAILED.value]),
                        Campaign.completed_at < cutoff_date
                    )
                ).all()
                
                count = 0
                for campaign in old_campaigns:
                    # Delete associated file
                    if campaign.file_path and os.path.exists(campaign.file_path):
                        try:
                            os.remove(campaign.file_path)
                        except OSError:
                            pass
                    
                    db.delete(campaign)
                    count += 1
                
                db.commit()
                
                self.logger.info(f"Cleaned up {count} old campaigns")
                return count
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old campaigns: {str(e)}")
            raise
    
    def _campaign_to_response(self, campaign: Campaign) -> CampaignResponse:
        """Convert Campaign model to response model"""
        # Get phone number for session display
        session_display = campaign.session_name
        if campaign.user_id and campaign.session_name:
            from database.user_sessions import UserWhatsAppSession
            from database.connection import get_db
            with get_db() as db:
                user_session = db.query(UserWhatsAppSession).filter(
                    UserWhatsAppSession.user_id == campaign.user_id,
                    UserWhatsAppSession.session_name == campaign.session_name
                ).first()
                if user_session and user_session.phone_number:
                    session_display = f"{campaign.session_name} / {user_session.phone_number}"
        
        return CampaignResponse(
            id=campaign.id,
            name=campaign.name,
            session_name=campaign.session_name,
            session_display=session_display,  # Add display name with phone
            user_id=campaign.user_id,  # Include user_id in response
            status=CampaignStatus(campaign.status),
            file_path=campaign.file_path,
            start_row=campaign.start_row,
            end_row=campaign.end_row,
            message_mode=MessageMode(campaign.message_mode),
            message_samples=campaign.message_samples,
            use_csv_samples=campaign.use_csv_samples,
            delay_seconds=campaign.delay_seconds,
            retry_attempts=campaign.retry_attempts,
            max_daily_messages=campaign.max_daily_messages,
            total_rows=campaign.total_rows,
            processed_rows=campaign.processed_rows,
            success_count=campaign.success_count,
            error_count=campaign.error_count,
            progress_percentage=campaign.progress_percentage,
            success_rate=campaign.success_rate,
            created_at=campaign.created_at,
            started_at=campaign.started_at,
            completed_at=campaign.completed_at,
            estimated_completion_time=campaign.estimated_completion_time,
            scheduled_start_time=getattr(campaign, 'scheduled_start_time', None),
            is_scheduled=getattr(campaign, 'is_scheduled', False)
        )
