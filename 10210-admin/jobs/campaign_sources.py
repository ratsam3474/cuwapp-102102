"""
Campaign Source Models - Handles different contact sources for campaigns
Supports: CSV upload, WhatsApp groups, and direct contacts
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any, Union, Literal
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class SourceType(str, Enum):
    """Contact source types"""
    CSV_UPLOAD = "csv_upload"
    WHATSAPP_GROUP = "whatsapp_group"
    USER_CONTACTS = "user_contacts"

class GroupDeliveryMethod(str, Enum):
    """Delivery method when using WhatsApp groups as source"""
    INDIVIDUAL_DMS = "individual_dms"  # Extract members and send DMs
    GROUP_MESSAGE = "group_message"     # Send directly to group

class ContactSource(BaseModel):
    """Base model for contact sources"""
    source_type: SourceType = Field(..., description="Type of contact source")
    
class CSVSource(ContactSource):
    """CSV file upload source - existing functionality"""
    source_type: Literal[SourceType.CSV_UPLOAD] = Field(default=SourceType.CSV_UPLOAD)
    file_path: str = Field(..., description="Path to uploaded CSV file")
    column_mapping: Optional[Dict[str, str]] = Field(None, description="Column mapping")
    start_row: int = Field(1, ge=1, description="Starting row")
    end_row: Optional[int] = Field(None, description="Ending row")

class WhatsAppGroupSource(ContactSource):
    """WhatsApp group source"""
    source_type: Literal[SourceType.WHATSAPP_GROUP] = Field(default=SourceType.WHATSAPP_GROUP)
    group_ids: List[str] = Field(..., min_items=1, description="List of group IDs")
    delivery_method: GroupDeliveryMethod = Field(..., description="How to send messages")
    auto_join: bool = Field(True, description="Auto-join groups if not member")
    
    @validator('group_ids')
    def validate_group_ids(cls, v):
        # Ensure group IDs have proper format
        validated = []
        for group_id in v:
            if not group_id.endswith('@g.us'):
                validated.append(f"{group_id}@g.us")
            else:
                validated.append(group_id)
        return validated

class UserContactsSource(ContactSource):
    """User's WhatsApp contacts source"""
    source_type: Literal[SourceType.USER_CONTACTS] = Field(default=SourceType.USER_CONTACTS)
    contact_selection: Union[List[str], str] = Field(
        ..., 
        description="List of contact IDs or 'all' for all contacts"
    )
    filter_only_my_contacts: bool = Field(
        True,
        description="Only include saved contacts"
    )

class CampaignSourceCreate(BaseModel):
    """
    Enhanced campaign creation with flexible source selection
    """
    # Campaign basics (same as before)
    name: str = Field(..., min_length=1, max_length=255, description="Campaign name")
    session_name: str = Field(..., min_length=1, max_length=100, description="WhatsApp session")
    
    # Contact source - can be any of the source types
    source: Union[CSVSource, WhatsAppGroupSource, UserContactsSource] = Field(
        ..., 
        discriminator='source_type',
        description="Contact source configuration"
    )
    
    # Message configuration (from existing CampaignCreate)
    message_mode: str = Field("single", description="Message mode: single or multiple")
    message_samples: List[Dict[str, Any]] = Field(default=[], description="Message templates")
    use_csv_samples: bool = Field(False, description="Use samples from CSV")
    
    # Processing configuration (from existing)
    delay_seconds: int = Field(5, ge=1, le=300, description="Delay between messages")
    retry_attempts: int = Field(3, ge=0, le=10, description="Retry attempts")
    max_daily_messages: int = Field(1000, ge=1, le=10000, description="Max daily messages")
    
    # Filters and options (from existing)
    exclude_my_contacts: bool = Field(False, description="Exclude saved contacts")
    exclude_previous_conversations: bool = Field(False, description="Exclude previous chats")
    save_contact_before_message: bool = Field(False, description="Save before sending")
    
    # New option for deduplication
    remove_duplicates: bool = Field(True, description="Remove duplicate phone numbers")
    
    class Config:
        schema_extra = {
            "examples": [
                {
                    "name": "CSV Campaign",
                    "session_name": "business_account",
                    "source": {
                        "source_type": "csv_upload",
                        "file_path": "/path/to/file.csv",
                        "start_row": 1,
                        "end_row": 100
                    },
                    "message_mode": "single",
                    "message_samples": [{"text": "Hi {{name}}!"}],
                    "delay_seconds": 5
                },
                {
                    "name": "Group DM Campaign",
                    "session_name": "business_account",
                    "source": {
                        "source_type": "whatsapp_group",
                        "group_ids": ["120363123456789@g.us"],
                        "delivery_method": "individual_dms",
                        "auto_join": True
                    },
                    "message_mode": "single",
                    "message_samples": [{"text": "Hi {{name}}!"}],
                    "delay_seconds": 5
                },
                {
                    "name": "Contact Campaign",
                    "session_name": "business_account",
                    "source": {
                        "source_type": "user_contacts",
                        "contact_selection": "all",
                        "filter_only_my_contacts": True
                    },
                    "message_mode": "single",
                    "message_samples": [{"text": "Hi!"}],
                    "delay_seconds": 5
                }
            ]
        }