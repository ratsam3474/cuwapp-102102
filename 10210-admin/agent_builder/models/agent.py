"""
Agent Model and Configuration
"""
from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

Base = declarative_base()

class AgentStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"

class TriggerType(str, Enum):
    # Message Events
    MESSAGE = "message"
    MESSAGE_ANY = "message.any"
    MESSAGE_ACK = "message.ack"
    MESSAGE_WAITING = "message.waiting"
    MESSAGE_REVOKED = "message.revoked"
    MESSAGE_REACTION = "message.reaction"
    
    # Group Events V2
    GROUP_JOIN = "group.v2.join"
    GROUP_LEAVE = "group.v2.leave"
    GROUP_UPDATE = "group.v2.update"
    GROUP_PARTICIPANTS = "group.v2.participants"
    
    # Legacy Group Events
    GROUP_JOIN_LEGACY = "group.join"
    GROUP_LEAVE_LEGACY = "group.leave"
    
    # Session/System Events
    SESSION_STATUS = "session.status"
    STATE_CHANGE = "state.change"
    ENGINE_EVENT = "engine.event"
    
    # Call Events
    CALL_RECEIVED = "call.received"
    CALL_ACCEPTED = "call.accepted"
    CALL_REJECTED = "call.rejected"
    
    # Label Events
    LABEL_UPSERT = "label.upsert"
    LABEL_DELETED = "label.deleted"
    LABEL_CHAT_ADDED = "label.chat.added"
    LABEL_CHAT_DELETED = "label.chat.deleted"
    
    # Poll Events
    POLL_VOTE = "poll.vote"
    POLL_VOTE_FAILED = "poll.vote.failed"
    
    # Other Events
    PRESENCE_UPDATE = "presence.update"
    CHAT_ARCHIVE = "chat.archive"
    EVENT_RESPONSE = "event.response"
    EVENT_RESPONSE_FAILED = "event.response.failed"

# Database Model
class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default=AgentStatus.DRAFT)
    
    # Configuration
    triggers = Column(JSON)  # List of TriggerType values
    trigger_instructions = Column(JSON)  # Dict mapping trigger -> instructions
    additional_instructions = Column(Text)  # General instructions
    
    # Tools configuration
    waha_tools = Column(JSON)  # List of selected WAHA endpoint IDs
    mcp_tools = Column(JSON)  # List of MCP tool configurations
    custom_tools = Column(JSON)  # List of custom function definitions
    builtin_tools = Column(JSON)  # List of built-in ADK tools
    
    # Knowledge base
    knowledge_base = Column(JSON)  # References to knowledge documents
    
    # Runtime configuration
    model = Column(String, default="gemini-2.0-flash")
    temperature = Column(String, default="0.7")
    max_tokens = Column(Integer)
    
    # Deployment info
    port = Column(Integer)  # Assigned port when active
    container_id = Column(String)  # Docker container ID when running
    webhook_url = Column(String)  # Registered webhook URL
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String)
    whatsapp_session = Column(String, default="default")  # Which WAHA session

# Pydantic Models for API
class TriggerInstruction(BaseModel):
    trigger: TriggerType
    instruction: str

class ToolSelection(BaseModel):
    waha_tools: List[str] = Field(default_factory=list)
    mcp_tools: List[Dict] = Field(default_factory=list)
    custom_tools: List[Dict] = Field(default_factory=list)
    builtin_tools: List[str] = Field(default_factory=list)

class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    triggers: List[TriggerType]
    trigger_instructions: Dict[str, str]  # trigger -> instruction mapping
    additional_instructions: Optional[str] = None
    tools: ToolSelection
    knowledge_base: Optional[List[str]] = Field(default_factory=list)
    model: str = "gemini-2.0-flash"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    whatsapp_session: str = "default"

class AgentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: AgentStatus
    triggers: List[TriggerType]
    trigger_instructions: Dict[str, str]
    additional_instructions: Optional[str]
    tools: ToolSelection
    model: str
    temperature: float
    port: Optional[int]
    webhook_url: Optional[str]
    created_at: datetime
    updated_at: datetime

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    triggers: Optional[List[TriggerType]] = None
    trigger_instructions: Optional[Dict[str, str]] = None
    additional_instructions: Optional[str] = None
    tools: Optional[ToolSelection] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None