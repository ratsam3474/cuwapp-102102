"""
WhatsApp Warmer Data Models
"""

import json
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from database.connection import Base


class WarmerStatus(str, Enum):
    """Warmer session status"""
    INACTIVE = "inactive"
    WARMING = "warming"
    PAUSED = "paused"
    STOPPED = "stopped"


class MessageType(str, Enum):
    """Message type for warmer conversations"""
    GROUP = "group"
    DIRECT = "direct"


class WarmerSession(Base):
    """Warmer session model for managing warming campaigns"""
    __tablename__ = "warmer_sessions"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic information
    name = Column(String(255), nullable=False)
    user_id = Column(String(255), index=True)  # Associated user ID for tracking
    orchestrator_session = Column(String(100), nullable=False)
    _participant_sessions = Column("participant_sessions", Text, nullable=False)  # JSON array
    status = Column(String(50), default=WarmerStatus.INACTIVE.value, index=True)
    
    # Configuration
    group_message_delay_min = Column(Integer, default=30)  # seconds
    group_message_delay_max = Column(Integer, default=1800)  # 30 minutes
    direct_message_delay_min = Column(Integer, default=120)  # 2 minutes
    direct_message_delay_max = Column(Integer, default=1800)  # 30 minutes
    
    # Statistics
    total_groups_created = Column(Integer, default=0)
    total_messages_sent = Column(Integer, default=0)
    total_group_messages = Column(Integer, default=0)
    total_direct_messages = Column(Integer, default=0)
    total_duration_minutes = Column(Float, default=0.0)  # Cumulative duration across all sessions
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    stopped_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    groups = relationship("WarmerGroup", back_populates="warmer_session", cascade="all, delete-orphan")
    conversations = relationship("WarmerConversation", back_populates="warmer_session", cascade="all, delete-orphan")
    contacts = relationship("WarmerContact", back_populates="warmer_session", cascade="all, delete-orphan")
    
    @hybrid_property
    def participant_sessions(self) -> List[str]:
        """Get participant sessions as list"""
        if self._participant_sessions:
            try:
                return json.loads(self._participant_sessions)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    @participant_sessions.setter
    def participant_sessions(self, value: List[str]):
        """Set participant sessions from list"""
        if value:
            self._participant_sessions = json.dumps(value)
        else:
            self._participant_sessions = "[]"
    
    @property
    def all_sessions(self) -> List[str]:
        """Get all sessions including orchestrator"""
        return [self.orchestrator_session] + self.participant_sessions
    
    @property
    def duration_minutes(self) -> Optional[float]:
        """Get total warming duration in minutes (cumulative across all sessions)"""
        total = self.total_duration_minutes or 0.0
        
        # If currently warming, add current session duration
        # Only add if we have a valid started_at and no stopped_at (meaning currently running)
        if self.started_at and self.status == WarmerStatus.WARMING.value and not self.stopped_at:
            current_session_duration = (datetime.utcnow() - self.started_at).total_seconds() / 60
            # Sanity check: don't add negative or extremely large durations
            if 0 < current_session_duration < 10080:  # Max 1 week in minutes
                total += current_session_duration
        
        return round(total, 2) if total > 0 else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "user_id": self.user_id,  # Include user_id for filtering
            "orchestrator_session": self.orchestrator_session,
            "participant_sessions": self.participant_sessions,
            "all_sessions": self.all_sessions,
            "status": self.status,
            "group_message_delay_min": self.group_message_delay_min,
            "group_message_delay_max": self.group_message_delay_max,
            "direct_message_delay_min": self.direct_message_delay_min,
            "direct_message_delay_max": self.direct_message_delay_max,
            "total_groups_created": self.total_groups_created,
            "total_messages_sent": self.total_messages_sent,
            "total_group_messages": self.total_group_messages,
            "total_direct_messages": self.total_direct_messages,
            "duration_minutes": self.duration_minutes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None
        }


class WarmerGroup(Base):
    """Warmer group model for tracking warming groups"""
    __tablename__ = "warmer_groups"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key
    warmer_session_id = Column(Integer, ForeignKey("warmer_sessions.id"), nullable=False, index=True)
    
    # Group information
    group_id = Column(String(255), nullable=False)  # WhatsApp group ID
    group_name = Column(String(255))
    _members = Column("members", Text, nullable=False)  # JSON array
    
    # Activity tracking
    last_message_at = Column(DateTime)
    message_count = Column(Integer, default=0)
    last_speaker = Column(String(100))
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    warmer_session = relationship("WarmerSession", back_populates="groups")
    
    @hybrid_property
    def members(self) -> List[str]:
        """Get members as list"""
        if self._members:
            try:
                return json.loads(self._members)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    @members.setter
    def members(self, value: List[str]):
        """Set members from list"""
        if value:
            self._members = json.dumps(value)
        else:
            self._members = "[]"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "warmer_session_id": self.warmer_session_id,
            "group_id": self.group_id,
            "group_name": self.group_name,
            "members": self.members,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "message_count": self.message_count,
            "last_speaker": self.last_speaker,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class WarmerConversation(Base):
    """Warmer conversation model for tracking messages"""
    __tablename__ = "warmer_conversations"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key
    warmer_session_id = Column(Integer, ForeignKey("warmer_sessions.id"), nullable=False, index=True)
    
    # Message details
    message_id = Column(String(255))
    sender_session = Column(String(100), nullable=False)
    recipient_session = Column(String(100))  # NULL for group messages
    group_id = Column(String(255))  # NULL for direct messages
    message_type = Column(String(20), nullable=False, index=True)  # group, direct
    
    # Content
    message_content = Column(Text, nullable=False)
    context_summary = Column(Text)  # Previous conversation context for LLM
    
    # Timestamps
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    warmer_session = relationship("WarmerSession", back_populates="conversations")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "warmer_session_id": self.warmer_session_id,
            "message_id": self.message_id,
            "sender_session": self.sender_session,
            "recipient_session": self.recipient_session,
            "group_id": self.group_id,
            "message_type": self.message_type,
            "message_content": self.message_content,
            "context_summary": self.context_summary,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None
        }


class WarmerContact(Base):
    """Warmer contact model for tracking saved contacts"""
    __tablename__ = "warmer_contacts"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key
    warmer_session_id = Column(Integer, ForeignKey("warmer_sessions.id"), nullable=False, index=True)
    user_id = Column(String(255), index=True)  # Associated user ID for tracking
    
    # Contact information
    session_name = Column(String(100), nullable=False)
    contact_phone = Column(String(20), nullable=False)
    contact_name = Column(String(255))
    saved_at = Column(DateTime, default=datetime.utcnow)
    saved_to_whatsapp = Column(Boolean, default=False)
    whatsapp_saved_at = Column(DateTime)
    
    # Relationships
    warmer_session = relationship("WarmerSession", back_populates="contacts")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "warmer_session_id": self.warmer_session_id,
            "session_name": self.session_name,
            "contact_phone": self.contact_phone,
            "contact_name": self.contact_name,
            "saved_at": self.saved_at.isoformat() if self.saved_at else None
        }