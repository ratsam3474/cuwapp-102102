"""
Pydantic models for campaign management
Input/output validation for campaign operations
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class CampaignStatus(str, Enum):
    """Campaign status enumeration"""
    CREATED = "created"
    SCHEDULED = "scheduled"  # Scheduled to start at a specific time
    QUEUED = "queued"  # Waiting in queue for sequential execution
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class MessageMode(str, Enum):
    """Message mode enumeration"""
    SINGLE = "single"
    MULTIPLE = "multiple"

class DeliveryStatus(str, Enum):
    """Delivery status enumeration"""
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"

class MessageSample(BaseModel):
    """Message sample model"""
    text: str = Field(..., min_length=1, max_length=4096, description="Message template text")
    variables: List[str] = Field(default=[], description="List of variables used in this sample")
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError("Message text cannot be empty")
        return v.strip()

class CampaignCreate(BaseModel):
    """Campaign creation model"""
    name: str = Field(..., min_length=1, max_length=255, description="Campaign name")
    session_name: str = Field(..., min_length=1, max_length=100, description="WhatsApp session display name")
    waha_session_name: Optional[str] = Field(None, description="Actual WAHA session name (UUID)")
    user_id: Optional[str] = Field(None, description="User ID for tracking ownership")
    
    # File configuration
    file_path: Optional[str] = Field(None, description="Path to CSV/Excel file")
    column_mapping: Optional[Dict[str, str]] = Field(None, description="Column mapping for data fields")
    start_row: int = Field(1, ge=1, description="Starting row number")
    end_row: Optional[int] = Field(None, ge=1, description="Ending row number")
    
    # Message configuration
    message_mode: MessageMode = Field(MessageMode.SINGLE, description="Message mode")
    message_samples: List[MessageSample] = Field(default=[], description="Message samples")
    use_csv_samples: bool = Field(False, description="Use samples from CSV file")
    
    # Processing configuration
    delay_seconds: int = Field(5, ge=1, le=300, description="Delay between messages")
    retry_attempts: int = Field(3, ge=0, le=10, description="Number of retry attempts")
    max_daily_messages: int = Field(1000, ge=1, le=10000, description="Maximum messages per day")
    
    # Condition filters
    exclude_my_contacts: bool = Field(False, description="Exclude contacts saved in phone")
    exclude_previous_conversations: bool = Field(False, description="Exclude contacts with previous conversations")
    save_contact_before_message: bool = Field(False, description="Save contact before sending message")
    
    # Scheduling configuration
    scheduled_start_time: Optional[datetime] = Field(None, description="When to start the campaign")
    is_scheduled: bool = Field(False, description="Whether this is a scheduled campaign")
    
    @validator('end_row')
    def validate_end_row(cls, v, values):
        if v is not None and 'start_row' in values and v < values['start_row']:
            raise ValueError("End row must be greater than or equal to start row")
        return v
    
    @validator('message_samples')
    def validate_message_samples(cls, v, values):
        if values.get('message_mode') == MessageMode.MULTIPLE and not v:
            raise ValueError("Message samples are required for multiple message mode")
        return v

class CampaignUpdate(BaseModel):
    """Campaign update model"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[CampaignStatus] = None
    delay_seconds: Optional[int] = Field(None, ge=1, le=300)
    retry_attempts: Optional[int] = Field(None, ge=0, le=10)
    max_daily_messages: Optional[int] = Field(None, ge=1, le=10000)
    total_rows: Optional[int] = Field(None, ge=0, description="Total number of rows to process")

class CampaignResponse(BaseModel):
    """Campaign response model"""
    id: int
    name: str
    session_name: str
    session_display: Optional[str] = None  # Display name with phone number
    user_id: Optional[str] = None  # Add user_id field
    status: CampaignStatus
    file_path: Optional[str]
    start_row: int
    end_row: Optional[int]
    message_mode: MessageMode
    message_samples: List[dict]
    use_csv_samples: bool
    delay_seconds: int
    retry_attempts: int
    max_daily_messages: int
    total_rows: int
    processed_rows: int
    success_count: int
    error_count: int
    progress_percentage: float
    success_rate: float
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_completion_time: Optional[datetime]
    scheduled_start_time: Optional[datetime] = None
    is_scheduled: bool = False

class DeliveryResponse(BaseModel):
    """Delivery response model"""
    id: int
    campaign_id: int
    row_number: int
    phone_number: str
    recipient_name: Optional[str]
    selected_sample_index: Optional[int]
    selected_sample_text: Optional[str]
    final_message_content: Optional[str]
    variable_data: Dict[str, Any]
    status: DeliveryStatus
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    error_message: Optional[str]
    whatsapp_message_id: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: datetime

class CampaignAnalyticsResponse(BaseModel):
    """Campaign analytics response model"""
    id: int
    campaign_id: int
    sample_index: Optional[int]
    sample_text: Optional[str]
    usage_count: int
    success_count: int
    delivery_count: int
    response_count: int
    error_count: int
    success_rate: float
    delivery_rate: float
    response_rate: Optional[float]
    avg_delivery_time: Optional[float]
    created_at: datetime
    updated_at: datetime

class FileUploadResponse(BaseModel):
    """File upload response model"""
    filename: str
    file_path: str
    file_size: int
    total_rows: int
    headers: List[str]
    sample_data: List[Dict[str, Any]]
    validation_errors: List[str]
    is_valid: bool

class CampaignProgressUpdate(BaseModel):
    """Real-time campaign progress update model"""
    campaign_id: int
    status: CampaignStatus
    processed_rows: int
    total_rows: int
    success_count: int
    error_count: int
    progress_percentage: float
    current_message: Optional[str]
    estimated_completion_time: Optional[datetime]
    last_updated: datetime

class CampaignStats(BaseModel):
    """Campaign statistics model"""
    total_campaigns: int
    active_campaigns: int
    completed_campaigns: int
    failed_campaigns: int
    total_messages_sent: int
    total_messages_delivered: int
    total_messages: int = Field(default=0, description="Total messages across all campaigns")
    overall_success_rate: float
    avg_delivery_time: Optional[float]

class MessagePreview(BaseModel):
    """Message preview model for testing templates"""
    original_template: str
    sample_data: Dict[str, Any]
    rendered_message: str
    variables_used: List[str]
    variables_missing: List[str]
    is_valid: bool
    
class BulkOperationRequest(BaseModel):
    """Bulk operation request model"""
    campaign_ids: List[int] = Field(..., min_items=1, description="List of campaign IDs")
    operation: str = Field(..., description="Operation to perform")
    
class BulkOperationResponse(BaseModel):
    """Bulk operation response model"""
    total_requested: int
    successful: int
    failed: int
    errors: List[str]
    campaign_ids_processed: List[int]
