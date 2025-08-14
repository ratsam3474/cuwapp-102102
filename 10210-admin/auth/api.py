"""
Authentication and Email API endpoints
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict
from datetime import datetime, timedelta
import json
from pathlib import Path
import asyncio

from .email_service import email_service
from .session_manager import session_manager
from database.connection import get_db
from database.subscription_models import UserSubscription, PlanType

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Request models
class MagicLinkRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class NewsletterSubscribe(BaseModel):
    email: EmailStr
    source: str = "landing"

class WaitlistSignup(BaseModel):
    email: EmailStr
    feature: str = "Chat"

class PasswordResetRequest(BaseModel):
    email: EmailStr

class VerifyTokenRequest(BaseModel):
    token: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: Optional[str] = None  # For future password auth

class SessionResponse(BaseModel):
    valid: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    plan_type: Optional[str] = None
    time_remaining: Optional[str] = None
    message: Optional[str] = None

# Storage (in production, use a database)
import os
if os.path.exists("/app"):
    STORAGE_PATH = Path("/app/data")
else:
    STORAGE_PATH = Path(__file__).parent.parent / "data"
STORAGE_PATH.mkdir(exist_ok=True, parents=True)

def load_json_file(filename: str) -> Dict:
    """Load JSON data from file"""
    file_path = STORAGE_PATH / filename
    if file_path.exists():
        with open(file_path, 'r') as f:
            return json.load(f)
    return {}

def save_json_file(filename: str, data: Dict):
    """Save JSON data to file"""
    file_path = STORAGE_PATH / filename
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

@router.post("/magic-link")
async def request_magic_link(request: MagicLinkRequest, background_tasks: BackgroundTasks):
    """Request a magic link for passwordless authentication"""
    try:
        # Send magic link email in background
        background_tasks.add_task(
            email_service.send_magic_link,
            request.email,
            request.name
        )
        
        # Log the request
        auth_logs = load_json_file("auth_logs.json")
        if request.email not in auth_logs:
            auth_logs[request.email] = []
        
        auth_logs[request.email].append({
            "type": "magic_link_requested",
            "timestamp": datetime.now().isoformat()
        })
        save_json_file("auth_logs.json", auth_logs)
        
        return {
            "success": True,
            "message": "Magic link sent to your email. Please check your inbox."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/verify-magic-link")
async def verify_magic_link(token: str):
    """Verify a magic link token and authenticate user"""
    try:
        link_data = email_service.verify_magic_link(token)
        
        if not link_data:
            raise HTTPException(status_code=401, detail="Invalid or expired link")
        
        # Create user session
        email = link_data['email']
        users = load_json_file("users.json")
        
        # Create user if doesn't exist
        if email not in users:
            users[email] = {
                "email": email,
                "created_at": datetime.now().isoformat(),
                "subscription": {"plan_type": "free"},
                "campaigns": []
            }
            save_json_file("users.json", users)
        
        # Get user subscription from database
        user_id = email  # Using email as user_id for simplicity
        plan_type = PlanType.FREE
        
        with get_db() as db:
            user_sub = db.query(UserSubscription).filter(
                UserSubscription.user_id == user_id
            ).first()
            
            if user_sub:
                plan_type = user_sub.plan_type
            else:
                # Create free subscription if doesn't exist
                user_sub = UserSubscription(
                    user_id=user_id,
                    email=email,
                    plan_type=PlanType.FREE
                )
                user_sub.update_plan(PlanType.FREE)
                db.add(user_sub)
                db.commit()
        
        # Create session with plan-based timeout
        session_result = session_manager.create_session(user_id, email, plan_type)
        
        if not session_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to create session")
        
        return {
            "success": True,
            "user": users[email],
            "token": session_result["token"],
            "session_id": session_result["session_id"],
            "expires_at": session_result["expires_at"],
            "plan_type": session_result["plan_type"],
            "message": session_result["message"],
            "redirect_url": f"https://app.cuwapp.com?token={session_result['token']}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/newsletter/subscribe")
async def subscribe_newsletter(request: NewsletterSubscribe, background_tasks: BackgroundTasks):
    """Subscribe to newsletter"""
    try:
        # Load existing subscribers
        subscribers = load_json_file("newsletter_subscribers.json")
        
        if request.email in subscribers:
            return {
                "success": True,
                "message": "You're already subscribed!",
                "already_subscribed": True
            }
        
        # Add new subscriber
        subscribers[request.email] = {
            "email": request.email,
            "source": request.source,
            "subscribed_at": datetime.now().isoformat(),
            "active": True
        }
        save_json_file("newsletter_subscribers.json", subscribers)
        
        # Send welcome email in background
        background_tasks.add_task(
            email_service.send_newsletter_welcome,
            request.email
        )
        
        return {
            "success": True,
            "message": "Successfully subscribed! Check your email for a welcome message.",
            "subscriber_count": len(subscribers)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/waitlist/join")
async def join_waitlist(request: WaitlistSignup, background_tasks: BackgroundTasks):
    """Join feature waitlist"""
    try:
        # Load existing waitlist
        waitlist = load_json_file(f"waitlist_{request.feature.lower()}.json")
        
        if request.email in waitlist:
            return {
                "success": True,
                "message": "You're already on the waitlist!",
                "position": list(waitlist.keys()).index(request.email) + 1
            }
        
        # Add to waitlist
        waitlist[request.email] = {
            "email": request.email,
            "feature": request.feature,
            "joined_at": datetime.now().isoformat()
        }
        save_json_file(f"waitlist_{request.feature.lower()}.json", waitlist)
        
        # Send confirmation email in background
        background_tasks.add_task(
            email_service.send_waitlist_confirmation,
            request.email,
            request.feature
        )
        
        return {
            "success": True,
            "message": f"You're on the {request.feature} waitlist!",
            "position": len(waitlist)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/campaign-reminder")
async def send_campaign_reminder(email: str, background_tasks: BackgroundTasks):
    """Send campaign reminder email (called by scheduler)"""
    try:
        # Get user's campaigns
        users = load_json_file("users.json")
        if email not in users:
            return {"success": False, "message": "User not found"}
        
        # Check for campaigns with unprocessed rows
        campaigns = users[email].get("campaigns", [])
        unprocessed_campaigns = []
        
        for campaign in campaigns:
            if campaign.get("status") == "created" and campaign.get("total_rows", 0) > 0:
                unprocessed_campaigns.append({
                    "campaign_name": campaign.get("name"),
                    "unprocessed_rows": campaign.get("total_rows", 0) - campaign.get("processed_rows", 0),
                    "total_rows": campaign.get("total_rows", 0)
                })
        
        if unprocessed_campaigns:
            # Send reminder for the first unprocessed campaign
            background_tasks.add_task(
                email_service.send_daily_campaign_reminder,
                email,
                unprocessed_campaigns[0]
            )
            
            return {
                "success": True,
                "message": f"Reminder sent for {len(unprocessed_campaigns)} campaigns"
            }
        
        return {
            "success": True,
            "message": "No unprocessed campaigns found"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_email_stats():
    """Get email statistics"""
    try:
        newsletter = load_json_file("newsletter_subscribers.json")
        waitlist_chat = load_json_file("waitlist_chat.json")
        auth_logs = load_json_file("auth_logs.json")
        
        return {
            "newsletter_subscribers": len(newsletter),
            "waitlist_chat": len(waitlist_chat),
            "total_logins": sum(len(logs) for logs in auth_logs.values()),
            "active_users": len(auth_logs)
        }
    except Exception as e:
        return {
            "newsletter_subscribers": 0,
            "waitlist_chat": 0,
            "total_logins": 0,
            "active_users": 0
        }

@router.post("/login")
async def login(request: LoginRequest):
    """Login endpoint with plan-based session management"""
    try:
        # For now, we'll use magic link authentication
        # In production, add proper password authentication
        
        # Get user subscription
        user_id = request.email  # Using email as user_id
        plan_type = PlanType.FREE
        
        with get_db() as db:
            user_sub = db.query(UserSubscription).filter(
                UserSubscription.user_id == user_id
            ).first()
            
            if user_sub:
                plan_type = user_sub.plan_type
            else:
                # Create free subscription
                user_sub = UserSubscription(
                    user_id=user_id,
                    email=request.email,
                    plan_type=PlanType.FREE
                )
                user_sub.update_plan(PlanType.FREE)
                db.add(user_sub)
                db.commit()
        
        # Create session with plan-based timeout
        session_result = session_manager.create_session(user_id, request.email, plan_type)
        
        if not session_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to create session")
        
        return session_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/validate")
async def validate_session(authorization: Optional[str] = Header(None)):
    """Validate current session and check for timeout"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="No valid authorization header")
        
        token = authorization.replace("Bearer ", "")
        validation = session_manager.validate_session(token)
        
        if not validation["valid"]:
            # Check if it's a free plan timeout
            if validation.get("plan_type") == "free" and validation.get("reason") == "timeout":
                return {
                    "valid": False,
                    "expired": True,
                    "reason": "free_plan_timeout",
                    "message": validation.get("error"),
                    "upgrade_message": validation.get("upgrade_message")
                }
            
            raise HTTPException(status_code=401, detail=validation.get("error", "Invalid session"))
        
        # Check for timeout warning (free plan)
        warning = session_manager.check_session_timeout_warning(token)
        
        response = {
            "valid": True,
            "user_id": validation["user_id"],
            "email": validation["email"],
            "plan_type": validation["plan_type"],
            "persistent": validation["persistent"],
            "time_remaining": validation["time_remaining"]
        }
        
        if warning:
            response["warning"] = warning
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session/refresh")
async def refresh_session(authorization: Optional[str] = Header(None)):
    """Refresh session (only for paid plans)"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="No valid authorization header")
        
        token = authorization.replace("Bearer ", "")
        result = session_manager.refresh_session(token)
        
        if not result["success"]:
            # Check if it's because of free plan
            if "Free plan" in result.get("error", ""):
                return {
                    "success": False,
                    "error": result["error"],
                    "upgrade_required": True,
                    "upgrade_message": result.get("upgrade_message")
                }
            
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Logout and invalidate session"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return {"success": True, "message": "No session to logout"}
        
        token = authorization.replace("Bearer ", "")
        result = session_manager.logout_session(token)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/status")
async def get_session_status():
    """Get active sessions statistics"""
    try:
        counts = session_manager.get_active_sessions_count()
        total = sum(counts.values())
        
        return {
            "total_active_sessions": total,
            "by_plan": counts,
            "free_plan_sessions": counts.get("free", 0),
            "paid_plan_sessions": total - counts.get("free", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Background task to clean up expired sessions
async def cleanup_sessions_task():
    """Background task to clean up expired sessions every 5 minutes"""
    while True:
        try:
            await asyncio.sleep(300)  # Wait 5 minutes
            expired_count = session_manager.cleanup_expired_sessions()
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired sessions")
        except Exception as e:
            logger.error(f"Session cleanup task error: {str(e)}")

# Start cleanup task on module import
import logging
logger = logging.getLogger(__name__)
asyncio.create_task(cleanup_sessions_task())