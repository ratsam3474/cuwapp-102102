"""
Triggers API - List available WhatsApp event triggers
"""
from fastapi import APIRouter
from typing import List, Dict

from agent_builder.models.agent import TriggerType

router = APIRouter(prefix="/api/triggers", tags=["triggers"])

# Trigger metadata with descriptions and categories
TRIGGER_METADATA = {
    # Message Events
    TriggerType.MESSAGE: {
        "category": "Messages",
        "description": "New incoming message received",
        "icon": "💬"
    },
    TriggerType.MESSAGE_ANY: {
        "category": "Messages", 
        "description": "Any message created (sent or received)",
        "icon": "📨"
    },
    TriggerType.MESSAGE_ACK: {
        "category": "Messages",
        "description": "Message delivery/read acknowledgment",
        "icon": "✓"
    },
    TriggerType.MESSAGE_WAITING: {
        "category": "Messages",
        "description": "Message waiting to be delivered",
        "icon": "⏳"
    },
    TriggerType.MESSAGE_REVOKED: {
        "category": "Messages",
        "description": "Message deleted/revoked",
        "icon": "🗑️"
    },
    TriggerType.MESSAGE_REACTION: {
        "category": "Messages",
        "description": "Reaction added to message",
        "icon": "👍"
    },
    
    # Group Events
    TriggerType.GROUP_JOIN: {
        "category": "Groups",
        "description": "Someone joined a group",
        "icon": "➕"
    },
    TriggerType.GROUP_LEAVE: {
        "category": "Groups",
        "description": "Someone left a group",
        "icon": "➖"
    },
    TriggerType.GROUP_UPDATE: {
        "category": "Groups",
        "description": "Group info updated (name, description, etc)",
        "icon": "✏️"
    },
    TriggerType.GROUP_PARTICIPANTS: {
        "category": "Groups",
        "description": "Group participants changed",
        "icon": "👥"
    },
    
    # Call Events
    TriggerType.CALL_RECEIVED: {
        "category": "Calls",
        "description": "Incoming call received",
        "icon": "📞"
    },
    TriggerType.CALL_ACCEPTED: {
        "category": "Calls",
        "description": "Call accepted",
        "icon": "✅"
    },
    TriggerType.CALL_REJECTED: {
        "category": "Calls",
        "description": "Call rejected/declined",
        "icon": "❌"
    },
    
    # Session Events
    TriggerType.SESSION_STATUS: {
        "category": "System",
        "description": "WhatsApp session status changed",
        "icon": "🔄"
    },
    TriggerType.STATE_CHANGE: {
        "category": "System",
        "description": "Connection state changed",
        "icon": "🔌"
    },
    
    # Other Events
    TriggerType.PRESENCE_UPDATE: {
        "category": "Status",
        "description": "Contact online/offline status",
        "icon": "🟢"
    },
    TriggerType.CHAT_ARCHIVE: {
        "category": "Chats",
        "description": "Chat archived/unarchived",
        "icon": "📁"
    },
    TriggerType.POLL_VOTE: {
        "category": "Polls",
        "description": "Someone voted in a poll",
        "icon": "📊"
    },
    TriggerType.POLL_VOTE_FAILED: {
        "category": "Polls",
        "description": "Poll vote failed",
        "icon": "⚠️"
    },
    
    # Label Events
    TriggerType.LABEL_UPSERT: {
        "category": "Labels",
        "description": "Label created or updated",
        "icon": "🏷️"
    },
    TriggerType.LABEL_DELETED: {
        "category": "Labels",
        "description": "Label deleted",
        "icon": "🗑️"
    },
    TriggerType.LABEL_CHAT_ADDED: {
        "category": "Labels",
        "description": "Label added to chat",
        "icon": "🏷️"
    },
    TriggerType.LABEL_CHAT_DELETED: {
        "category": "Labels",
        "description": "Label removed from chat",
        "icon": "🏷️"
    }
}

@router.get("/")
async def list_triggers():
    """List all available triggers grouped by category"""
    # Group triggers by category
    categories = {}
    
    for trigger in TriggerType:
        metadata = TRIGGER_METADATA.get(trigger, {
            "category": "Other",
            "description": trigger.value,
            "icon": "📌"
        })
        
        category = metadata["category"]
        if category not in categories:
            categories[category] = []
        
        categories[category].append({
            "id": trigger.value,
            "name": trigger.name,
            "description": metadata["description"],
            "icon": metadata["icon"]
        })
    
    return categories

@router.get("/flat")
async def list_triggers_flat():
    """List all triggers as a flat array"""
    triggers = []
    
    for trigger in TriggerType:
        metadata = TRIGGER_METADATA.get(trigger, {
            "category": "Other",
            "description": trigger.value,
            "icon": "📌"
        })
        
        triggers.append({
            "id": trigger.value,
            "name": trigger.name,
            "category": metadata["category"],
            "description": metadata["description"],
            "icon": metadata["icon"]
        })
    
    return triggers