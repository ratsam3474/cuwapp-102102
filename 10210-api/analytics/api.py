"""
Analytics API endpoints for campaign and warmer analytics
"""

import logging
import csv
import io
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

# Import database models and connection
from database.connection import get_db
from database.models import Campaign, Delivery  # Contact doesn't exist
from warmer.models import WarmerSession, WarmerConversation, MessageType
from waha_functions import WAHAClient

logger = logging.getLogger(__name__)
router = APIRouter()

class AnalyticsRequest(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    campaign_ids: Optional[List[int]] = None
    warmer_ids: Optional[List[int]] = None
    phone_numbers: Optional[List[str]] = None

class ResponseRateTracker:
    """Track response rates for phone numbers in real-time"""
    
    def __init__(self, waha_client = None):
        try:
            self.waha = waha_client if waha_client else WAHAClient()
        except Exception as e:
            logger.warning(f"Could not initialize WAHA client: {e}")
            self.waha = None
        self.logger = logger
        
    async def calculate_response_rate(self, session_name: str, phone_number: str, campaign_id: Optional[int] = None) -> Dict[str, Any]:
        """Calculate response rate for a phone number"""
        try:
            # Get messages from WAHA for this phone number if available
            chat_id = f"{phone_number}@c.us" if "@" not in phone_number else phone_number
            
            try:
                if not self.waha:
                    raise Exception("WAHA client not available")
                messages = self.waha.get_messages(session_name, chat_id, limit=100)
                
                # Count sent and received messages
                sent_count = 0
                received_count = 0
                last_interaction = None
                
                for msg in messages:
                    if msg.get("fromMe"):
                        sent_count += 1
                    else:
                        received_count += 1
                        if not last_interaction or msg.get("timestamp") > last_interaction:
                            last_interaction = msg.get("timestamp")
                
                response_rate = (received_count / sent_count * 100) if sent_count > 0 else 0
                
                return {
                    "phone_number": phone_number,
                    "session": session_name,
                    "sent_messages": sent_count,
                    "received_messages": received_count,
                    "response_rate": round(response_rate, 2),
                    "last_interaction": last_interaction,
                    "status": "live"
                }
                
            except Exception as e:
                # Fallback to database data
                self.logger.warning(f"Could not get live data for {phone_number}: {e}")
                return self._get_cached_response_rate(phone_number, session_name, campaign_id)
                
        except Exception as e:
            self.logger.error(f"Error calculating response rate: {e}")
            return {
                "phone_number": phone_number,
                "session": session_name,
                "response_rate": 0,
                "status": "error",
                "error": str(e)
            }
    
    def _get_cached_response_rate(self, phone_number: str, session_name: str, campaign_id: Optional[int] = None) -> Dict[str, Any]:
        """Get cached response rate from database"""
        with get_db() as db:
            # Query deliveries for this phone number
            query = db.query(Delivery).filter(
                Delivery.phone_number == phone_number
            )
            
            if campaign_id:
                query = query.filter(Delivery.campaign_id == campaign_id)
            
            deliveries = query.all()
            
            if deliveries:
                sent_count = len(deliveries)
                responded_count = len([d for d in deliveries if d.response_received])
                response_rate = (responded_count / sent_count * 100) if sent_count > 0 else 0
                
                # Try to get the session's phone number
                session_phone = None
                try:
                    if self.waha and session_name:
                        sessions = self.waha.get_sessions()
                        for session in sessions:
                            if session.get('name') == session_name:
                                # Get the phone number from the session's 'me' field
                                me_info = session.get('me', {})
                                if me_info:
                                    session_phone = me_info.get('id', '').replace('@c.us', '')
                                break
                except:
                    pass
                
                return {
                    "phone_number": phone_number,
                    "session": session_name,
                    "sent_messages": sent_count,
                    "received_messages": responded_count,
                    "response_rate": round(response_rate, 2),
                    "status": "cached"
                }
            
            return {
                "phone_number": phone_number,
                "session": session_name,
                "response_rate": 0,
                "status": "no_data"
            }

# Initialize response tracker
response_tracker = ResponseRateTracker()

@router.get("/analytics/campaign/overview")
async def get_campaign_overview(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    user_id: str = Query(..., description="User ID is required")
):
    """Get campaign analytics overview"""
    try:
        with get_db() as db:
            # Get lifetime metrics if user_id provided
            if user_id:
                from database.user_metrics import UserMetrics
                user_metrics = db.query(UserMetrics).filter(UserMetrics.user_id == user_id).first()
                
                # If user has lifetime metrics, use those
                if user_metrics:
                    return {
                        "overview": {
                            "total_campaigns": user_metrics.total_campaigns_created,
                            "total_sent": user_metrics.total_messages_sent,
                            "total_delivered": user_metrics.total_messages_delivered,
                            "total_failed": user_metrics.total_messages_failed,
                            "total_read": user_metrics.total_messages_read,
                            "total_responded": user_metrics.total_messages_responded,
                            "average_delivery_rate": round((user_metrics.total_messages_delivered / user_metrics.total_messages_sent * 100) if user_metrics.total_messages_sent > 0 else 0, 2),
                            "average_read_rate": round((user_metrics.total_messages_read / user_metrics.total_messages_sent * 100) if user_metrics.total_messages_sent > 0 else 0, 2),
                            "average_response_rate": round((user_metrics.total_messages_responded / user_metrics.total_messages_sent * 100) if user_metrics.total_messages_sent > 0 else 0, 2),
                            "lifetime_stats": True
                        },
                        "period": {
                            "start_date": start_date.isoformat() if start_date else None,
                            "end_date": end_date.isoformat() if end_date else None
                        }
                    }
            
            # Fallback to calculating from current campaigns
            # Base query
            query = db.query(Campaign)
            
            # Filter by user_id if provided
            if user_id:
                query = query.filter(Campaign.user_id == user_id)
            
            if start_date:
                query = query.filter(Campaign.created_at >= start_date)
            if end_date:
                query = query.filter(Campaign.created_at <= end_date)
            
            campaigns = query.all()
            
            # Calculate overall metrics
            total_campaigns = len(campaigns)
            total_sent = 0
            total_delivered = 0
            total_failed = 0
            total_read = 0
            total_responded = 0
            
            for campaign in campaigns:
                deliveries = db.query(Delivery).filter(
                    Delivery.campaign_id == campaign.id
                ).all()
                
                for delivery in deliveries:
                    total_sent += 1
                    if delivery.status == "sent":
                        total_delivered += 1
                    elif delivery.status == "failed":
                        total_failed += 1
                    
                    # Check for optional fields that may not exist yet
                    if hasattr(delivery, 'read_at') and delivery.read_at:
                        total_read += 1
                    if hasattr(delivery, 'response_received') and delivery.response_received:
                        total_responded += 1
            
            # Calculate rates
            delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
            read_rate = (total_read / total_delivered * 100) if total_delivered > 0 else 0
            response_rate = (total_responded / total_delivered * 100) if total_delivered > 0 else 0
            
            return {
                "overview": {
                    "total_campaigns": total_campaigns,
                    "total_sent": total_sent,
                    "total_delivered": total_delivered,
                    "total_failed": total_failed,
                    "total_read": total_read,
                    "total_responded": total_responded,
                    "average_delivery_rate": round(delivery_rate, 2),
                    "average_read_rate": round(read_rate, 2),
                    "average_response_rate": round(response_rate, 2)
                },
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting campaign overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/campaign/detailed")
async def get_campaign_detailed(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    campaign_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    user_id: str = Query(..., description="User ID is required")
):
    """Get detailed campaign analytics with pagination"""
    try:
        with get_db() as db:
            # Base query for deliveries
            # Build query without the new columns that may not exist yet
            query = db.query(
                Delivery.phone_number,
                Delivery.recipient_name,
                Campaign.name.label("campaign_name"),
                Campaign.file_path.label("source_file"),
                Delivery.status,
                Delivery.sent_at,
                Delivery.delivered_at,
                Campaign.id.label("campaign_id"),
                Campaign.user_id
            ).join(Campaign)
            
            # Filter by user_id if provided
            if user_id:
                query = query.filter(Campaign.user_id == user_id)
            
            if campaign_id:
                query = query.filter(Campaign.id == campaign_id)
            
            if search:
                # Simple search filter without SQLAlchemy or_
                deliveries = []
                all_deliveries = query.all()
                for d in all_deliveries:
                    if (search in (d.phone_number or '') or 
                        search in (d.recipient_name or '') or 
                        search in (d.campaign_name or '')):
                        deliveries.append(d)
                query = deliveries
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            offset = (page - 1) * page_size
            items = query.offset(offset).limit(page_size).all()
            
            # Calculate response rates for each phone number
            detailed_items = []
            for item in items:
                # Get response rate for this phone number
                session_name = db.query(Campaign).filter(
                    Campaign.id == item.campaign_id
                ).first().session_name
                
                response_data = await response_tracker.calculate_response_rate(
                    session_name,
                    item.phone_number,
                    item.campaign_id
                )
                
                detailed_items.append({
                    "phone_number": item.phone_number,
                    "contact_name": item.recipient_name,
                    "campaign_name": item.campaign_name,
                    "source_file": item.source_file,
                    "status": item.status,
                    "sent_at": item.sent_at.isoformat() if item.sent_at else None,
                    "delivered_at": item.delivered_at.isoformat() if item.delivered_at else None,
                    "read_at": getattr(item, 'read_at', None).isoformat() if hasattr(item, 'read_at') and item.read_at else None,
                    "responded": getattr(item, 'response_received', False),
                    "response_rate": response_data.get("response_rate", 0),
                    "response_status": response_data.get("status", "unknown"),
                    "warning": response_data.get("warning")
                })
            
            return {
                "items": detailed_items,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_items": total_count,
                    "total_pages": (total_count + page_size - 1) // page_size
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting detailed analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/campaign/export")
async def export_campaign_analytics(
    format: str = Query("csv", regex="^(csv|json)$"),
    campaign_id: Optional[int] = Query(None),
    user_id: str = Query(..., description="User ID is required")
):
    """Export campaign analytics report"""
    try:
        with get_db() as db:
            # Get campaign data
            query = db.query(
                Delivery.phone_number,
                Delivery.recipient_name,
                Campaign.name.label("campaign_name"),
                Campaign.file_path.label("source_file"),
                Delivery.status,
                Delivery.sent_at,
                Delivery.delivered_at,
                Delivery.final_message_content
            ).join(Campaign)
            
            # Filter by user_id if provided
            if user_id:
                query = query.filter(Campaign.user_id == user_id)
            
            if campaign_id:
                query = query.filter(Campaign.id == campaign_id)
            
            items = query.all()
            
            if format == "csv":
                # Create CSV
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=[
                    "phone_number", "contact_name", "campaign_name", "source_file",
                    "status", "sent_at", "delivered_at", "read_at", "responded", "message"
                ])
                writer.writeheader()
                
                for item in items:
                    writer.writerow({
                        "phone_number": item.phone_number,
                        "contact_name": item.recipient_name,
                        "campaign_name": item.campaign_name,
                        "source_file": item.source_file,
                        "status": item.status,
                        "sent_at": item.sent_at.isoformat() if item.sent_at else "",
                        "delivered_at": item.delivered_at.isoformat() if item.delivered_at else "",
                        "read_at": getattr(item, 'read_at', None).isoformat() if hasattr(item, 'read_at') and item.read_at else "",
                        "responded": "Yes" if getattr(item, 'response_received', False) else "No",
                        "message": item.final_message_content[:100] if item.final_message_content else ""
                    })
                
                return Response(
                    content=output.getvalue(),
                    media_type="text/csv",
                    headers={
                        "Content-Disposition": f"attachment; filename=campaign_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    }
                )
            else:
                # Return JSON
                data = []
                for item in items:
                    data.append({
                        "phone_number": item.phone_number,
                        "contact_name": item.recipient_name,
                        "campaign_name": item.campaign_name,
                        "source_file": item.source_file,
                        "status": item.status,
                        "sent_at": item.sent_at.isoformat() if item.sent_at else None,
                        "delivered_at": item.delivered_at.isoformat() if item.delivered_at else None,
                        "read_at": getattr(item, 'read_at', None).isoformat() if hasattr(item, 'read_at') and item.read_at else None,
                        "responded": getattr(item, 'response_received', False),
                        "message": item.final_message_content
                    })
                
                return data
                
    except Exception as e:
        logger.error(f"Error exporting campaign analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/warmer/overview")
async def get_warmer_overview(user_id: Optional[str] = Query(None), include_archived: bool = Query(True)):
    """Get warmer analytics overview (includes archived by default for historical data)"""
    try:
        with get_db() as db:
            # Filter by user_id if provided
            query = db.query(WarmerSession)
            # SECURITY: No admin mode
            if user_id == 'admin':
                raise HTTPException(status_code=403, detail="Admin access not allowed")
            if user_id:
                query = query.filter(WarmerSession.user_id == user_id)
            
            # By default, include archived warmers in analytics
            if not include_archived:
                query = query.filter((WarmerSession.is_archived == False) | (WarmerSession.is_archived == None))
            
            warmers = query.all()
            
            total_messages = 0
            total_group_messages = 0
            total_direct_messages = 0
            active_groups = 0
            failed_messages = 0
            total_duration_minutes = 0
            total_sessions = 0
            
            for warmer in warmers:
                total_messages += warmer.total_messages_sent
                total_group_messages += warmer.total_group_messages
                total_direct_messages += warmer.total_direct_messages
                
                # Calculate duration in minutes
                if warmer.duration_minutes:
                    total_duration_minutes += warmer.duration_minutes
                
                # Count sessions
                if hasattr(warmer, 'all_sessions') and warmer.all_sessions:
                    total_sessions += len(warmer.all_sessions)
                else:
                    total_sessions += 1  # At least one session per warmer
                
                # Count active groups
                group_conversations = db.query(WarmerConversation.group_id).filter(
                    WarmerConversation.warmer_session_id == warmer.id,
                    WarmerConversation.group_id.isnot(None)
                ).distinct().all()
                active_groups += len(group_conversations)
            
            # Get messages per session
            session_stats = []
            for warmer in warmers:
                try:
                    sessions = warmer.all_sessions if hasattr(warmer, 'all_sessions') else []
                    for session in sessions:
                        # Count messages sent by this session
                        sent_count = db.query(WarmerConversation).filter(
                            WarmerConversation.warmer_session_id == warmer.id,
                            WarmerConversation.sender_session == session
                        ).count()
                        
                        session_stats.append({
                            "session": session,
                            "warmer_name": warmer.name,
                            "messages_sent": sent_count
                        })
                except Exception as e:
                    logger.warning(f"Error processing warmer {warmer.id}: {e}")
            
            return {
                "overview": {
                    "total_messages_sent": total_messages,
                    "total_group_messages": total_group_messages,
                    "total_direct_messages": total_direct_messages,
                    "active_groups": active_groups,
                    "failed_messages": failed_messages,
                    "total_duration_minutes": total_duration_minutes,
                    "total_sessions": total_sessions,
                    "total_warmers": len(warmers)
                },
                "session_stats": session_stats
            }
            
    except Exception as e:
        logger.error(f"Error getting warmer overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/warmer/transcripts/{warmer_id}")
async def export_warmer_transcripts(
    warmer_id: int,
    format: str = Query("json", regex="^(json|txt)$")
):
    """Export all chat transcripts from a warmer session"""
    try:
        with get_db() as db:
            warmer = db.query(WarmerSession).filter(
                WarmerSession.id == warmer_id
            ).first()
            
            if not warmer:
                raise HTTPException(status_code=404, detail="Warmer session not found")
            
            # Get all conversations
            conversations = db.query(WarmerConversation).filter(
                WarmerConversation.warmer_session_id == warmer_id
            ).order_by(WarmerConversation.sent_at).all()
            
            if format == "txt":
                # Create text transcript
                output = io.StringIO()
                output.write(f"WhatsApp Warmer Transcript - {warmer.name}\\n")
                output.write(f"Generated: {datetime.now().isoformat()}\\n")
                output.write("=" * 80 + "\\n\\n")
                
                current_chat = None
                for conv in conversations:
                    chat_id = conv.group_id or conv.recipient_session
                    
                    if chat_id != current_chat:
                        output.write(f"\\n--- Chat: {chat_id} ---\\n")
                        current_chat = chat_id
                    
                    timestamp = conv.sent_at.strftime("%Y-%m-%d %H:%M:%S") if conv.sent_at else "Unknown"
                    output.write(f"[{timestamp}] {conv.sender_session}: {conv.message_content}\\n")
                
                return Response(
                    content=output.getvalue(),
                    media_type="text/plain",
                    headers={
                        "Content-Disposition": f"attachment; filename=warmer_transcript_{warmer_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    }
                )
            else:
                # Return JSON transcript
                transcript = {
                    "warmer_name": warmer.name,
                    "warmer_id": warmer_id,
                    "generated_at": datetime.now().isoformat(),
                    "conversations": []
                }
                
                # Group by chat
                chats = {}
                for conv in conversations:
                    chat_id = conv.group_id or conv.recipient_session or "unknown"
                    
                    if chat_id not in chats:
                        chats[chat_id] = {
                            "chat_id": chat_id,
                            "type": "group" if conv.group_id else "direct",
                            "messages": []
                        }
                    
                    chats[chat_id]["messages"].append({
                        "sender": conv.sender_session,
                        "message": conv.message_content,
                        "timestamp": conv.sent_at.isoformat() if conv.sent_at else None,
                        "message_type": conv.message_type
                    })
                
                transcript["conversations"] = list(chats.values())
                return transcript
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting warmer transcripts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/warmer/detailed")
async def get_warmer_detailed(
    warmer_id: Optional[int] = Query(None),
    user_id: str = Query(..., description="User ID is required"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """Get detailed warmer analytics"""
    try:
        with get_db() as db:
            # Get warmer sessions
            query = db.query(WarmerSession)
            if warmer_id:
                query = query.filter(WarmerSession.id == warmer_id)
            # Filter by user_id if provided
            # SECURITY: No admin mode
            if user_id == 'admin':
                raise HTTPException(status_code=403, detail="Admin access not allowed")
            if user_id:
                query = query.filter(WarmerSession.user_id == user_id)
            
            warmers = query.all()
            
            detailed_data = []
            for warmer in warmers:
                # Get conversation stats
                total_conversations = db.query(WarmerConversation).filter(
                    WarmerConversation.warmer_session_id == warmer.id
                ).count()
                
                # Get unique groups
                group_convs = db.query(WarmerConversation.group_id).filter(
                    WarmerConversation.warmer_session_id == warmer.id,
                    WarmerConversation.group_id.isnot(None)
                ).distinct().all()
                unique_groups = len(group_convs)
                
                # Get per-session stats
                session_stats = []
                for session in warmer.all_sessions:
                    sent = db.query(WarmerConversation).filter(
                        WarmerConversation.warmer_session_id == warmer.id,
                        WarmerConversation.sender_session == session
                    ).count()
                    
                    received = db.query(WarmerConversation).filter(
                        WarmerConversation.warmer_session_id == warmer.id,
                        WarmerConversation.recipient_session == session
                    ).count()
                    
                    session_stats.append({
                        "session": session,
                        "sent": sent,
                        "received": received
                    })
                
                detailed_data.append({
                    "warmer_id": warmer.id,
                    "warmer_name": warmer.name,
                    "status": warmer.status,
                    "total_messages": warmer.total_messages_sent,
                    "group_messages": warmer.total_group_messages,
                    "direct_messages": warmer.total_direct_messages,
                    "duration_minutes": warmer.duration_minutes,
                    "unique_groups": unique_groups,
                    "total_conversations": total_conversations,
                    "session_stats": session_stats,
                    "created_at": warmer.created_at.isoformat() if warmer.created_at else None,
                    "started_at": warmer.started_at.isoformat() if warmer.started_at else None,
                    "stopped_at": warmer.stopped_at.isoformat() if warmer.stopped_at else None
                })
            
            # Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_data = detailed_data[start_idx:end_idx]
            
            return {
                "items": paginated_data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_items": len(detailed_data),
                    "total_pages": (len(detailed_data) + page_size - 1) // page_size
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting detailed warmer analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))