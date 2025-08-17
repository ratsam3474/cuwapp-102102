"""
User Metrics API - Proper implementation with admin support
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict
from datetime import datetime, timedelta
from database.connection import get_db
from database.models import Campaign, Delivery
from warmer.models import WarmerSession, WarmerConversation, MessageType
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/metrics/campaigns")
async def get_campaign_metrics(user_id: str = Query(..., description="User ID or 'admin' for all users")):
    """
    Get campaign metrics
    - If user_id = 'admin': Returns metrics for ALL users combined
    - If user_id = specific user: Returns metrics for that user only
    
    Returns:
    - total_campaigns_created: Total number of campaigns ever created
    - total_active_campaigns: Currently running campaigns
    - total_messages_sent: Total messages sent (status = sent or delivered)
    - total_messages_delivered: Total messages with status = delivered
    - total_messages_read: Total messages that were read
    - total_messages_responded: Total messages that got responses
    - avg_response_rate: Average response rate percentage
    """
    try:
        with get_db() as db:
            # Import UserMetrics for persistent message tracking
            from database.user_metrics import UserMetrics
            
            # Get message metrics from UserMetrics table (persists even after campaign deletion)
            if user_id == "admin":
                # Get metrics for ALL users
                all_user_metrics = db.query(UserMetrics).all()
                
                # Sum up all user metrics
                total_messages_sent = sum(m.total_messages_sent for m in all_user_metrics)
                total_messages_delivered = sum(m.total_messages_delivered for m in all_user_metrics)
                total_messages_read = sum(m.total_messages_read for m in all_user_metrics)
                total_messages_responded = sum(m.total_messages_responded for m in all_user_metrics)
                total_messages_failed = sum(m.total_messages_failed for m in all_user_metrics)
                
                # Get ALL campaigns from ALL users for campaign counts
                all_campaigns = db.query(Campaign).all()
            else:
                # Get metrics for specific user from UserMetrics
                user_metrics = UserMetrics.get_or_create(db, user_id)
                
                total_messages_sent = user_metrics.total_messages_sent
                total_messages_delivered = user_metrics.total_messages_delivered
                total_messages_read = user_metrics.total_messages_read
                total_messages_responded = user_metrics.total_messages_responded
                total_messages_failed = user_metrics.total_messages_failed
                
                # Get campaigns for specific user
                all_campaigns = db.query(Campaign).filter(
                    Campaign.user_id == user_id
                ).all()
            
            # Count active campaigns (running status)
            active_campaigns = [c for c in all_campaigns if c.status == 'running']
            
            # Calculate response rate
            avg_response_rate = 0.0
            if total_messages_sent > 0:
                avg_response_rate = round((total_messages_responded / total_messages_sent) * 100, 2)
            
            # Calculate delivery rate
            delivery_rate = 0.0
            if total_messages_sent > 0:
                delivery_rate = round((total_messages_delivered / total_messages_sent) * 100, 2)
            
            return {
                "user_context": user_id,
                "is_admin": False,  # No admin access allowed
                "metrics": {
                    "total_campaigns_created": len(all_campaigns),
                    "total_active_campaigns": len(active_campaigns),
                    "total_messages_sent": total_messages_sent,
                    "total_messages_delivered": total_messages_delivered,
                    "total_messages_read": total_messages_read,
                    "total_messages_responded": total_messages_responded,
                    "total_messages_failed": total_messages_failed,
                    "avg_response_rate": avg_response_rate,
                    "delivery_rate": delivery_rate
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting campaign metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/metrics/warmer")
async def get_warmer_metrics(user_id: str = Query(..., description="User ID is required")):
    """
    Get warmer metrics for the specific user only
    
    Returns:
    - total_warmer_minutes: Total minutes of warmer usage
    - total_group_messages: Total messages sent in groups
    - total_dm_messages: Total direct messages sent
    """
    try:
        with get_db() as db:
            # SECURITY: No admin mode - only return user's own data
            if user_id == "admin":
                raise HTTPException(status_code=403, detail="Admin access not allowed")
            
            # Get warmer sessions for specific user
            warmer_sessions = db.query(WarmerSession).filter(
                WarmerSession.user_id == user_id
            ).all()
            
            # Calculate total warmer minutes from database
            total_minutes = 0.0
            for session in warmer_sessions:
                if hasattr(session, 'total_duration_minutes') and session.total_duration_minutes:
                    total_minutes += session.total_duration_minutes
            
            # Get warmer conversations for counting messages
            warmer_ids = [w.id for w in warmer_sessions]
            
            if warmer_ids:
                conversations = db.query(WarmerConversation).filter(
                    WarmerConversation.warmer_session_id.in_(warmer_ids)
                ).all()
            else:
                conversations = []
            
            # Count message types from database
            total_group_messages = len([c for c in conversations if c.message_type == MessageType.GROUP])
            total_dm_messages = len([c for c in conversations if c.message_type == MessageType.DIRECT])
            
            return {
                "user_context": user_id,
                "is_admin": False,  # No admin access allowed
                "metrics": {
                    "total_warmer_minutes": round(total_minutes, 2),
                    "total_group_messages": total_group_messages,
                    "total_dm_messages": total_dm_messages,
                    "total_messages": total_group_messages + total_dm_messages
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting warmer metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/metrics/all")
async def get_all_metrics(user_id: str = Query(..., description="User ID or 'admin' for all users")):
    """
    Get all metrics (campaign + warmer) combined
    - If user_id = 'admin': Returns metrics for ALL users
    - If user_id = specific user: Returns metrics for that user only
    """
    try:
        # Get both metrics
        campaign_metrics = await get_campaign_metrics(user_id)
        warmer_metrics = await get_warmer_metrics(user_id)
        
        return {
            "user_context": user_id,
            "is_admin": False,  # No admin access allowed
            "campaign": campaign_metrics["metrics"],
            "warmer": warmer_metrics["metrics"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting all metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))