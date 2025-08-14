"""
User Session Management
Links WhatsApp sessions to Clerk users
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.connection import Base
import json


class UserWhatsAppSession(Base):
    """Maps WhatsApp sessions to users"""
    __tablename__ = "user_whatsapp_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)  # Clerk user ID
    session_name = Column(String(255), nullable=False, unique=True, index=True)  # Display name shown to user
    waha_session_name = Column(String(255), nullable=True, unique=True, index=True)  # Actual WAHA session name
    
    # Session details
    phone_number = Column(String(50), nullable=True)
    display_name = Column(String(255), nullable=True)
    status = Column(String(50), default="inactive")  # active, inactive, scanning, failed
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_primary = Column(Boolean, default=False)  # User's primary session
    
    # Statistics
    messages_sent = Column(Integer, default=0)
    campaigns_run = Column(Integer, default=0)
    contacts_imported = Column(Integer, default=0)
    
    # Configuration
    config = Column(Text, default="{}")  # JSON configuration
    
    def get_config(self):
        """Get configuration as dictionary"""
        return json.loads(self.config) if self.config else {}
    
    def set_config(self, config_dict):
        """Set configuration from dictionary"""
        self.config = json.dumps(config_dict)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_name": self.session_name,
            "phone_number": self.phone_number,
            "display_name": self.display_name,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "is_primary": self.is_primary,
            "messages_sent": self.messages_sent,
            "campaigns_run": self.campaigns_run,
            "contacts_imported": self.contacts_imported
        }


class UserSessionActivity(Base):
    """Track user session activity"""
    __tablename__ = "user_session_activity"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    session_name = Column(String(255), nullable=False, index=True)
    
    # Activity details
    activity_type = Column(String(50), nullable=False)  # login, scan_qr, send_message, create_campaign, etc.
    activity_data = Column(Text, default="{}")  # JSON data
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    def get_data(self):
        """Get activity data as dictionary"""
        return json.loads(self.activity_data) if self.activity_data else {}
    
    def set_data(self, data_dict):
        """Set activity data from dictionary"""
        self.activity_data = json.dumps(data_dict)