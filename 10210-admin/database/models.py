"""
SQLAlchemy ORM models for campaign management
"""

import json
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from .connection import Base
from typing import List, Dict, Optional

# Import warmer models to ensure they're registered with SQLAlchemy
try:
    from warmer.models import WarmerSession, WarmerGroup, WarmerConversation, WarmerContact
except ImportError:
    pass  # Warmer module not yet available

# Import subscription models to ensure they're registered with SQLAlchemy
try:
    from .subscription_models import UserSubscription, Payment, WebhookEvent, UsageLog
except ImportError:
    pass  # Subscription models not yet available

class Campaign(Base):
    """Campaign model for managing bulk message campaigns"""
    __tablename__ = "campaigns"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic information
    name = Column(String(255), nullable=False, index=True)
    session_name = Column(String(100), nullable=False)  # Display name for UI
    waha_session_name = Column(String(100))  # Actual WAHA session name (UUID)
    user_id = Column(String(255), index=True)  # Associated user ID for tracking
    status = Column(String(50), default="created", index=True)  # created, running, paused, completed, failed
    
    # File information
    file_path = Column(String(500))
    column_mapping = Column(Text)  # JSON string for column mapping
    start_row = Column(Integer, default=1)
    end_row = Column(Integer)
    
    # Message configuration with samples
    message_mode = Column(String(20), default="single")  # 'single' or 'multiple'
    _message_samples = Column("message_samples", Text)  # JSON array of samples
    use_csv_samples = Column(Boolean, default=False)
    
    # Processing configuration
    delay_seconds = Column(Integer, default=5)
    retry_attempts = Column(Integer, default=3)
    max_daily_messages = Column(Integer, default=1000)
    
    # Scheduling fields
    scheduled_start_time = Column(DateTime)  # When to start the campaign
    is_scheduled = Column(Boolean, default=False)  # Whether this is a scheduled campaign
    auto_paused_warmers = Column(Text)  # JSON array of warmer IDs that were paused
    queue_position = Column(Integer)  # Position in Start All queue (for queued campaigns)
    
    # Condition filters
    exclude_my_contacts = Column(Boolean, default=False)
    exclude_previous_conversations = Column(Boolean, default=False)
    save_contact_before_message = Column(Boolean, default=False)
    
    # Progress tracking
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    error_details = Column(Text)  # Store detailed error messages
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    deliveries = relationship("Delivery", back_populates="campaign", cascade="all, delete-orphan")
    analytics = relationship("CampaignAnalytics", back_populates="campaign", cascade="all, delete-orphan")
    
    @hybrid_property
    def column_mapping_dict(self) -> Dict[str, str]:
        """Get column mapping as dictionary"""
        if self.column_mapping:
            try:
                return json.loads(self.column_mapping)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @column_mapping_dict.setter
    def column_mapping_dict(self, value: Dict[str, str]):
        """Set column mapping from dictionary"""
        if value:
            self.column_mapping = json.dumps(value)
        else:
            self.column_mapping = None
    
    @hybrid_property
    def message_samples(self) -> List[str]:
        """Get message samples as list"""
        if self._message_samples:
            try:
                return json.loads(self._message_samples)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    @message_samples.setter
    def message_samples(self, value: List[str]):
        """Set message samples from list"""
        if value:
            self._message_samples = json.dumps(value)
        else:
            self._message_samples = None
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage"""
        if self.total_rows and self.total_rows > 0:
            return round((self.processed_rows / self.total_rows) * 100, 2)
        return 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.processed_rows and self.processed_rows > 0:
            return round((self.success_count / self.processed_rows) * 100, 2)
        return 0.0
    
    @property
    def estimated_completion_time(self) -> Optional[datetime]:
        """Estimate completion time based on current progress"""
        if not self.started_at or self.processed_rows == 0 or self.total_rows == 0:
            return None
        
        elapsed_time = datetime.utcnow() - self.started_at
        remaining_rows = self.total_rows - self.processed_rows
        
        if remaining_rows <= 0:
            return datetime.utcnow()
        
        time_per_row = elapsed_time.total_seconds() / self.processed_rows
        estimated_remaining_seconds = remaining_rows * time_per_row
        
        return datetime.utcnow() + timedelta(seconds=estimated_remaining_seconds)
    
    def to_dict(self) -> Dict:
        """Convert campaign to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "session_name": self.session_name,
            "status": self.status,
            "file_path": self.file_path,
            "column_mapping": self.column_mapping_dict,
            "start_row": self.start_row,
            "end_row": self.end_row,
            "message_mode": self.message_mode,
            "message_samples": self.message_samples,
            "use_csv_samples": self.use_csv_samples,
            "delay_seconds": self.delay_seconds,
            "retry_attempts": self.retry_attempts,
            "exclude_my_contacts": self.exclude_my_contacts,
            "exclude_previous_conversations": self.exclude_previous_conversations,
            "save_contact_before_message": self.save_contact_before_message,
            "scheduled_start_time": self.scheduled_start_time.isoformat() + 'Z' if self.scheduled_start_time else None,
            "is_scheduled": self.is_scheduled,
            "queue_position": self.queue_position,
            "total_rows": self.total_rows,
            "processed_rows": self.processed_rows,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "progress_percentage": self.progress_percentage,
            "success_rate": self.success_rate,
            "error_details": self.error_details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_completion_time": self.estimated_completion_time.isoformat() if self.estimated_completion_time else None
        }

class Delivery(Base):
    """Delivery model for tracking individual message deliveries"""
    __tablename__ = "deliveries"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    
    # Contact information
    phone_number = Column(String(20), nullable=False, index=True)
    recipient_name = Column(String(255))
    
    # Sample selection tracking
    selected_sample_index = Column(Integer)
    selected_sample_text = Column(Text)
    final_message_content = Column(Text)
    
    # Variable data (JSON)
    _variable_data = Column("variable_data", Text)
    
    # Delivery status
    status = Column(String(50), default="pending", index=True)  # pending, sending, sent, delivered, failed
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    error_message = Column(Text)
    whatsapp_message_id = Column(String(255))
    retry_count = Column(Integer, default=0)
    
    # Response tracking
    read_at = Column(DateTime)
    response_received = Column(Boolean, default=False)
    response_time = Column(DateTime)
    response_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="deliveries")
    
    @hybrid_property
    def variable_data(self) -> Dict:
        """Get variable data as dictionary"""
        if self._variable_data:
            try:
                return json.loads(self._variable_data)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @variable_data.setter
    def variable_data(self, value: Dict):
        """Set variable data from dictionary"""
        if value:
            self._variable_data = json.dumps(value)
        else:
            self._variable_data = None
    
    def to_dict(self) -> Dict:
        """Convert delivery to dictionary"""
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "row_number": self.row_number,
            "phone_number": self.phone_number,
            "recipient_name": self.recipient_name,
            "selected_sample_index": self.selected_sample_index,
            "selected_sample_text": self.selected_sample_text,
            "final_message_content": self.final_message_content,
            "variable_data": self.variable_data,
            "status": self.status,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "error_message": self.error_message,
            "whatsapp_message_id": self.whatsapp_message_id,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class CampaignAnalytics(Base):
    """Analytics model for tracking campaign and sample performance"""
    __tablename__ = "campaign_analytics"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    
    # Sample tracking
    sample_index = Column(Integer)
    sample_text = Column(Text)
    
    # Usage statistics
    usage_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    delivery_count = Column(Integer, default=0)
    response_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    
    # Performance metrics
    avg_delivery_time = Column(Float)  # Average delivery time in seconds
    response_rate = Column(Float)      # Response rate percentage
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="analytics")
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.usage_count and self.usage_count > 0:
            return round((self.success_count / self.usage_count) * 100, 2)
        return 0.0
    
    @property
    def delivery_rate(self) -> float:
        """Calculate delivery rate percentage"""
        if self.success_count and self.success_count > 0:
            return round((self.delivery_count / self.success_count) * 100, 2)
        return 0.0
    
    def to_dict(self) -> Dict:
        """Convert analytics to dictionary"""
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "sample_index": self.sample_index,
            "sample_text": self.sample_text,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "delivery_count": self.delivery_count,
            "response_count": self.response_count,
            "error_count": self.error_count,
            "success_rate": self.success_rate,
            "delivery_rate": self.delivery_rate,
            "response_rate": self.response_rate,
            "avg_delivery_time": self.avg_delivery_time,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
