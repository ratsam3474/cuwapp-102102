"""
Email API endpoints that work with Clerk authentication
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict
from datetime import datetime
import logging

from .service import email_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/email", tags=["email"])

# Request models
class NewsletterSubscribe(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    source: str = "dashboard"

class WaitlistSignup(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    feature: str = "Chat"

class CampaignReminder(BaseModel):
    email: EmailStr
    name: str
    campaign_name: str
    unprocessed_rows: int
    total_rows: int

@router.post("/newsletter/subscribe")
async def subscribe_newsletter(request: NewsletterSubscribe, background_tasks: BackgroundTasks):
    """Subscribe to newsletter (can be called from landing page or dashboard)"""
    try:
        # Send welcome email in background
        background_tasks.add_task(
            email_service.send_newsletter_welcome,
            request.email,
            request.name
        )
        
        return {
            "success": True,
            "message": "Successfully subscribed! Check your email for confirmation."
        }
    except Exception as e:
        logger.error(f"Newsletter subscription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/waitlist/join")
async def join_waitlist(request: WaitlistSignup, background_tasks: BackgroundTasks):
    """Join feature waitlist"""
    try:
        # Send confirmation in background
        background_tasks.add_task(
            email_service.send_waitlist_confirmation,
            request.email,
            request.name,
            request.feature
        )
        
        return {
            "success": True,
            "message": f"You're on the {request.feature} waitlist!"
        }
    except Exception as e:
        logger.error(f"Waitlist signup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/campaign-reminder")
async def send_campaign_reminder(request: CampaignReminder, background_tasks: BackgroundTasks):
    """Send campaign reminder (called by scheduler or manually)"""
    try:
        campaign_data = {
            "campaign_name": request.campaign_name,
            "unprocessed_rows": request.unprocessed_rows,
            "total_rows": request.total_rows
        }
        
        # Send reminder in background
        background_tasks.add_task(
            email_service.send_campaign_reminder,
            request.email,
            request.name,
            campaign_data
        )
        
        return {
            "success": True,
            "message": "Campaign reminder sent"
        }
    except Exception as e:
        logger.error(f"Campaign reminder error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_email_stats():
    """Get email statistics"""
    try:
        from pathlib import Path
        import json
        
        import os
        base_path = os.getenv("DATA_PATH", "data")
        storage_path = Path(base_path) / "email"
        stats = {
            "newsletter_subscribers": 0,
            "waitlist_chat": 0,
            "emails_queued": 0
        }
        
        # Count newsletter subscribers
        newsletter_file = storage_path / "newsletter_subscribers.json"
        if newsletter_file.exists():
            with open(newsletter_file, 'r') as f:
                subscribers = json.load(f)
                stats["newsletter_subscribers"] = len(subscribers)
        
        # Count waitlist
        waitlist_file = storage_path / "waitlist_chat.json"
        if waitlist_file.exists():
            with open(waitlist_file, 'r') as f:
                waitlist = json.load(f)
                stats["waitlist_chat"] = len(waitlist)
        
        # Count email queue
        queue_file = storage_path / "email_queue.json"
        if queue_file.exists():
            with open(queue_file, 'r') as f:
                queue = json.load(f)
                stats["emails_queued"] = len([e for e in queue if e.get("status") == "pending"])
        
        return stats
    except Exception as e:
        logger.error(f"Error getting email stats: {e}")
        return {
            "newsletter_subscribers": 0,
            "waitlist_chat": 0,
            "emails_queued": 0
        }