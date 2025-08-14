"""
WhatsApp Warmer API Endpoints
"""

import logging
from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from warmer.warmer_engine import warmer_engine
from warmer.models import WarmerStatus

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/warmer", tags=["WhatsApp Warmer"])


# Request/Response Models
class CreateWarmerRequest(BaseModel):
    """Request model for creating warmer session"""
    name: str = Field(..., description="Name for the warmer session")
    orchestrator_session: str = Field(..., description="Session that orchestrates the warming")
    participant_sessions: List[str] = Field(..., min_items=1, description="List of participant sessions")
    config: Optional[Dict] = Field(None, description="Optional configuration overrides")
    group_invite_links: Optional[List[str]] = Field(None, description="Optional list of 5 group invite links")


class WarmerResponse(BaseModel):
    """Response model for warmer operations"""
    success: bool
    message: Optional[str] = None
    data: Optional[Dict] = None
    error: Optional[str] = None


class WarmerStatusResponse(BaseModel):
    """Response model for warmer status"""
    id: int
    name: str
    status: str
    is_active: bool
    statistics: Dict
    sessions: Optional[Dict] = None


class JoinGroupsRequest(BaseModel):
    """Request model for joining groups with invite links"""
    invite_links: List[str] = Field(..., min_items=1, max_items=5, description="WhatsApp group invite links (up to 5)")


# API Endpoints
@router.get("/")
async def list_warmers(user_id: Optional[str] = None) -> WarmerResponse:
    """
    List warmer sessions for a specific user
    """
    try:
        # Get all warmers
        all_warmers = warmer_engine.get_all_warmers()
        
        # If no user_id, return all (admin mode)
        if not user_id:
            return WarmerResponse(
                success=True,
                message=f"Found {len(all_warmers)} warmer sessions",
                data={"warmers": all_warmers}
            )
        
        # Filter warmers for this user
        user_warmers = [w for w in all_warmers if w.get('user_id') == user_id]
        
        return WarmerResponse(
            success=True,
            message=f"Found {len(user_warmers)} warmer sessions for user",
            data={"warmers": user_warmers}
        )
    except Exception as e:
        logger.error(f"Error listing warmers: {str(e)}")
        return WarmerResponse(
            success=False,
            error=str(e)
        )


@router.post("/create")
async def create_warmer(request: CreateWarmerRequest, user_id: Optional[str] = None) -> WarmerResponse:
    """
    Create a new warmer session
    
    Requires:
    - At least 2 total sessions (1 orchestrator + 1+ participants)
    - All sessions must be in WORKING state
    - User must have warmer hours available in their plan
    """
    try:
        # Check subscription limits if user_id provided
        if user_id:
            from database.subscription_models import UserSubscription
            from database.connection import get_db
            
            with get_db() as db:
                user_subscription = db.query(UserSubscription).filter(
                    UserSubscription.user_id == user_id
                ).first()
                
                if not user_subscription:
                    return WarmerResponse(
                        success=False,
                        error="No subscription found. Please subscribe to use warmer."
                    )
                
                # Check if user has warmer access
                if user_subscription.warmer_duration_hours <= 0:
                    return WarmerResponse(
                        success=False,
                        error=f"WhatsApp Warmer is not available on {user_subscription.plan_type.value} plan. Please upgrade to Hobby or higher."
                    )
        
        result = await warmer_engine.create_warmer_session(
            name=request.name,
            orchestrator_session=request.orchestrator_session,
            participant_sessions=request.participant_sessions,
            config=request.config,
            user_id=user_id  # Pass user_id to track ownership
        )
        
        if result["success"]:
            return WarmerResponse(
                success=True,
                message="Warmer session created successfully",
                data=result
            )
        else:
            return WarmerResponse(
                success=False,
                error=result.get("error", "Failed to create warmer session")
            )
            
    except Exception as e:
        logger.error(f"Error creating warmer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{warmer_id}/start")
async def start_warmer(warmer_id: int, user_id: Optional[str] = None) -> WarmerResponse:
    """
    Start warming process
    
    This will:
    1. Check if user has remaining warmer hours
    2. Save contacts between all sessions
    3. Ensure 5 common groups exist
    4. Start continuous conversations
    5. Track warmer usage time
    """
    try:
        # Check warmer hours limit if user_id provided
        if user_id:
            from database.subscription_models import UserSubscription
            from database.connection import get_db
            from warmer.models import WarmerSession
            from datetime import datetime
            
            with get_db() as db:
                # Get user subscription
                user_subscription = db.query(UserSubscription).filter(
                    UserSubscription.user_id == user_id
                ).first()
                
                if not user_subscription:
                    return WarmerResponse(
                        success=False,
                        error="No subscription found."
                    )
                
                # Check if user has warmer access
                if user_subscription.warmer_duration_hours <= 0:
                    return WarmerResponse(
                        success=False,
                        error=f"WhatsApp Warmer is not available on {user_subscription.plan_type.value} plan. Please upgrade to Hobby or higher."
                    )
                
                # Get warmer session to track usage
                warmer_session = db.query(WarmerSession).filter(
                    WarmerSession.id == warmer_id,
                    WarmerSession.user_id == user_id
                ).first()
                
                if not warmer_session:
                    return WarmerResponse(
                        success=False,
                        error="Warmer session not found or you don't have permission."
                    )
                
                # Check if user has exceeded warmer hours
                # Note: total_duration_minutes is cumulative across all sessions
                if warmer_session.total_duration_minutes >= (user_subscription.warmer_duration_hours * 60):
                    return WarmerResponse(
                        success=False,
                        error=f"Warmer hours limit reached. Your {user_subscription.plan_type.value} plan allows {user_subscription.warmer_duration_hours} hours. Total used: {warmer_session.total_duration_minutes / 60:.2f} hours."
                    )
                
                # Update started_at timestamp for tracking
                warmer_session.started_at = datetime.utcnow()
                warmer_session.stopped_at = None  # Clear stopped_at when restarting
                db.commit()
        
        result = await warmer_engine.start_warming(warmer_id)
        
        if result["success"]:
            return WarmerResponse(
                success=True,
                message=result["message"],
                data={
                    "warmer_id": warmer_id,
                    "contacts_saved": result.get("contacts_saved", 0),
                    "groups_ready": result.get("groups_ready", 0)
                }
            )
        else:
            return WarmerResponse(
                success=False,
                error=result.get("error", "Failed to start warming")
            )
            
    except Exception as e:
        logger.error(f"Error starting warmer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{warmer_id}/stop")
async def stop_warmer(warmer_id: int, user_id: Optional[str] = None) -> WarmerResponse:
    """Stop warming process and update usage time"""
    try:
        # Note: Duration tracking is now handled entirely in warmer_engine.stop_warming() 
        # to avoid double-counting the time
        
        result = await warmer_engine.stop_warming(warmer_id)
        
        if result["success"]:
            return WarmerResponse(
                success=True,
                message=result["message"]
            )
        else:
            return WarmerResponse(
                success=False,
                error=result.get("error", "Failed to stop warming")
            )
            
    except Exception as e:
        logger.error(f"Error stopping warmer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{warmer_id}/status")
async def get_warmer_status(warmer_id: int) -> WarmerStatusResponse:
    """Get current status of warmer session"""
    try:
        status = warmer_engine.get_warmer_status(warmer_id)
        
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        
        return WarmerStatusResponse(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting warmer status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_warmers_alt(user_id: Optional[str] = None) -> List[Dict]:
    """Get warmer sessions for a specific user"""
    try:
        all_warmers = warmer_engine.get_all_warmers()
        
        # If no user_id, return all (admin mode)
        if not user_id:
            return all_warmers
        
        # Filter warmers for this user
        user_warmers = [w for w in all_warmers if w.get('user_id') == user_id]
        return user_warmers
        
    except Exception as e:
        logger.error(f"Error listing warmers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{warmer_id}")
async def get_warmer(warmer_id: int) -> Dict:
    """Get specific warmer details"""
    try:
        from database.connection import get_db
        from warmer.models import WarmerSession
        
        with get_db() as db:
            warmer = db.query(WarmerSession).filter(WarmerSession.id == warmer_id).first()
            if not warmer:
                raise HTTPException(status_code=404, detail="Warmer session not found")
            
            return {
                "success": True,
                "data": {
                    "id": warmer.id,
                    "name": warmer.name,
                    "orchestrator_session": warmer.orchestrator_session,
                    "participant_sessions": warmer.participant_sessions,
                    "status": warmer.status,
                    "group_message_delay_min": warmer.group_message_delay_min,
                    "group_message_delay_max": warmer.group_message_delay_max,
                    "direct_message_delay_min": warmer.direct_message_delay_min,
                    "direct_message_delay_max": warmer.direct_message_delay_max,
                    "total_groups_created": warmer.total_groups_created,
                    "total_messages_sent": warmer.total_messages_sent,
                    "created_at": warmer.created_at.isoformat() if warmer.created_at else None,
                    "last_activity": warmer.stopped_at.isoformat() if hasattr(warmer, 'stopped_at') and warmer.stopped_at else None
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting warmer {warmer_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{warmer_id}/groups/check")
async def check_warmer_groups(warmer_id: int) -> Dict:
    """Check current group status for warmer"""
    try:
        from database.connection import get_db
        from warmer.models import WarmerSession
        from warmer.group_manager import GroupManager
        
        # Get warmer session
        with get_db() as db:
            warmer = db.query(WarmerSession).filter(WarmerSession.id == warmer_id).first()
            if not warmer:
                raise HTTPException(status_code=404, detail="Warmer session not found")
            
            all_sessions = warmer.all_sessions
            warmer_user_id = warmer.user_id
        
        # Check common groups
        group_manager = GroupManager()
        common_groups = await group_manager._get_common_groups(all_sessions, user_id=warmer_user_id)
        
        return {
            "success": True,
            "warmer_id": warmer_id,
            "total_sessions": len(all_sessions),
            "common_groups_count": len(common_groups),
            "groups_needed": max(0, 5 - len(common_groups)),
            "has_enough_groups": len(common_groups) >= 5,
            "common_group_ids": list(common_groups)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking warmer groups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{warmer_id}/metrics")
async def get_warmer_metrics(warmer_id: int) -> Dict:
    """Get detailed metrics for a warmer session"""
    try:
        # Get warmer status
        status = warmer_engine.get_warmer_status(warmer_id)
        
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        
        # Get additional metrics from database
        from database.connection import get_db
        from warmer.models import WarmerSession, WarmerGroup, WarmerConversation
        
        with get_db() as db:
            warmer = db.query(WarmerSession).filter(WarmerSession.id == warmer_id).first()
            if not warmer:
                raise HTTPException(status_code=404, detail="Warmer session not found")
            
            # Count active groups
            active_groups = db.query(WarmerGroup).filter(
                WarmerGroup.warmer_session_id == warmer_id,
                WarmerGroup.is_active == True
            ).count()
            
            # Get recent conversations
            recent_conversations = db.query(WarmerConversation).filter(
                WarmerConversation.warmer_session_id == warmer_id
            ).order_by(WarmerConversation.sent_at.desc()).limit(10).all()
            
            # Calculate message rate
            message_rate = 0
            if warmer.duration_minutes and warmer.duration_minutes > 0:
                message_rate = warmer.total_messages_sent / warmer.duration_minutes
            
            return {
                "warmer_id": warmer_id,
                "name": warmer.name,
                "status": warmer.status,
                "statistics": {
                    "total_messages": warmer.total_messages_sent,
                    "group_messages": warmer.total_group_messages,
                    "direct_messages": warmer.total_direct_messages,
                    "groups_created": warmer.total_groups_created,
                    "active_groups": active_groups,
                    "duration_minutes": warmer.duration_minutes,
                    "message_rate_per_minute": round(message_rate, 2)
                },
                "recent_conversations": [
                    {
                        "sender": conv.sender_session,
                        "type": conv.message_type,
                        "message": conv.message_content[:100] + "..." if len(conv.message_content) > 100 else conv.message_content,
                        "sent_at": conv.sent_at.isoformat() if conv.sent_at else None
                    }
                    for conv in recent_conversations
                ],
                "configuration": {
                    "orchestrator": warmer.orchestrator_session,
                    "participants": warmer.participant_sessions,
                    "total_sessions": len(warmer.all_sessions),
                    "group_delay": f"{warmer.group_message_delay_min}-{warmer.group_message_delay_max}s",
                    "direct_delay": f"{warmer.direct_message_delay_min}-{warmer.direct_message_delay_max}s"
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting warmer metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{warmer_id}/join-groups")
async def join_groups(warmer_id: int, request: JoinGroupsRequest) -> WarmerResponse:
    """Join groups using invite links for all sessions in the warmer"""
    try:
        # Check if warmer exists
        status = warmer_engine.get_warmer_status(warmer_id)
        
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        
        # Join groups using the group manager
        from warmer.group_manager import GroupManager
        group_manager = GroupManager()
        
        result = await group_manager.join_groups_by_links(warmer_id, request.invite_links)
        
        if result["validation_passed"]:
            return WarmerResponse(
                success=True,
                message=f"Successfully joined {len(result['joined_groups'])} groups with all sessions",
                data=result
            )
        else:
            return WarmerResponse(
                success=False,
                error=f"Only {len(result['joined_groups'])} out of {len(request.invite_links)} groups were joined by all sessions",
                data=result
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error joining groups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{warmer_id}/groups")
async def get_warmer_groups(warmer_id: int) -> Dict:
    """Get all groups associated with a warmer session"""
    try:
        from database.connection import get_db
        from warmer.models import WarmerSession, WarmerGroup
        
        with get_db() as db:
            warmer = db.query(WarmerSession).filter(WarmerSession.id == warmer_id).first()
            if not warmer:
                raise HTTPException(status_code=404, detail="Warmer session not found")
            
            groups = db.query(WarmerGroup).filter(
                WarmerGroup.warmer_session_id == warmer_id,
                WarmerGroup.is_active == True
            ).all()
            
            return {
                "success": True,
                "groups": [
                    {
                        "id": group.id,
                        "group_id": group.group_id,
                        "group_name": group.group_name,
                        "members": group.members,
                        "message_count": group.message_count,
                        "last_message_at": group.last_message_at.isoformat() if group.last_message_at else None
                    }
                    for group in groups
                ]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting warmer groups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class AddGroupsRequest(BaseModel):
    """Request model for adding groups to warmer"""
    group_links: List[str] = Field(..., min_items=1, max_items=20)


@router.post("/{warmer_id}/groups/add")
async def add_groups_to_warmer(warmer_id: int, request: AddGroupsRequest) -> Dict:
    """Add groups to warmer session and persist them"""
    try:
        from database.connection import get_db
        from warmer.models import WarmerSession, WarmerGroup
        from warmer.group_manager import GroupManager
        
        with get_db() as db:
            warmer = db.query(WarmerSession).filter(WarmerSession.id == warmer_id).first()
            if not warmer:
                raise HTTPException(status_code=404, detail="Warmer session not found")
            
            # Join groups using the group manager
            group_manager = GroupManager()
            result = await group_manager.join_groups_by_links(warmer_id, request.group_links)
            
            # Save joined groups to database
            added_count = 0
            for group_data in result.get("joined_groups", []):
                # Check if group already exists
                existing = db.query(WarmerGroup).filter(
                    WarmerGroup.warmer_session_id == warmer_id,
                    WarmerGroup.group_id == group_data["group_id"]
                ).first()
                
                if not existing:
                    new_group = WarmerGroup(
                        warmer_session_id=warmer_id,
                        group_id=group_data["group_id"],
                        group_name=group_data.get("subject", "Unknown Group"),
                        members=group_data.get("members", []),
                        is_active=True
                    )
                    db.add(new_group)
                    added_count += 1
                else:
                    # Reactivate if it was deactivated
                    existing.is_active = True
                    added_count += 1
            
            db.commit()
            
            return {
                "success": True,
                "message": f"Added {added_count} groups to warmer",
                "added_count": added_count,
                "data": result
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding groups to warmer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{warmer_id}/groups/{group_id}")
async def remove_group_from_warmer(warmer_id: int, group_id: int) -> Dict:
    """Remove a group from warmer session (mark as inactive)"""
    try:
        from database.connection import get_db
        from warmer.models import WarmerGroup
        
        with get_db() as db:
            group = db.query(WarmerGroup).filter(
                WarmerGroup.id == group_id,
                WarmerGroup.warmer_session_id == warmer_id
            ).first()
            
            if not group:
                raise HTTPException(status_code=404, detail="Group not found")
            
            # Mark as inactive instead of deleting
            group.is_active = False
            db.commit()
            
            return {
                "success": True,
                "message": "Group removed from warmer"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing group from warmer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class SessionManageRequest(BaseModel):
    """Request model for managing sessions"""
    session_name: str = Field(..., min_length=1, max_length=100)


@router.post("/{warmer_id}/sessions/add")
async def add_session_to_warmer(warmer_id: int, request: SessionManageRequest) -> Dict:
    """Add a participant session to warmer"""
    try:
        from database.connection import get_db
        from warmer.models import WarmerSession
        
        with get_db() as db:
            warmer = db.query(WarmerSession).filter(WarmerSession.id == warmer_id).first()
            if not warmer:
                raise HTTPException(status_code=404, detail="Warmer session not found")
            
            # Check if warmer is active (only allow modifications when inactive or stopped)
            if warmer.status not in ["inactive", "stopped"]:
                raise HTTPException(status_code=400, detail="Cannot modify sessions while warmer is active")
            
            # Check if session already exists in warmer
            current_sessions = warmer.participant_sessions
            if request.session_name in current_sessions:
                raise HTTPException(status_code=400, detail="Session already in warmer")
            
            # Check if trying to add orchestrator
            if request.session_name == warmer.orchestrator_session:
                raise HTTPException(status_code=400, detail="Session is already the orchestrator")
            
            # Add session to participants
            current_sessions.append(request.session_name)
            warmer.participant_sessions = current_sessions
            db.commit()
            
            return {
                "success": True,
                "message": f"Successfully added {request.session_name} to warmer",
                "participant_sessions": warmer.participant_sessions
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding session to warmer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{warmer_id}/sessions/remove")
async def remove_session_from_warmer(warmer_id: int, request: SessionManageRequest) -> Dict:
    """Remove a participant session from warmer"""
    try:
        from database.connection import get_db
        from warmer.models import WarmerSession
        
        with get_db() as db:
            warmer = db.query(WarmerSession).filter(WarmerSession.id == warmer_id).first()
            if not warmer:
                raise HTTPException(status_code=404, detail="Warmer session not found")
            
            # Check if warmer is active (only allow modifications when inactive or stopped)
            if warmer.status not in ["inactive", "stopped"]:
                raise HTTPException(status_code=400, detail="Cannot modify sessions while warmer is active")
            
            # Cannot remove orchestrator
            if request.session_name == warmer.orchestrator_session:
                raise HTTPException(status_code=400, detail="Cannot remove orchestrator session")
            
            # Check if session exists in participants
            current_sessions = warmer.participant_sessions
            if request.session_name not in current_sessions:
                raise HTTPException(status_code=404, detail="Session not found in warmer")
            
            # Remove session from participants
            current_sessions.remove(request.session_name)
            warmer.participant_sessions = current_sessions
            db.commit()
            
            return {
                "success": True,
                "message": f"Successfully removed {request.session_name} from warmer",
                "participant_sessions": warmer.participant_sessions
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing session from warmer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{warmer_id}")
async def delete_warmer(warmer_id: int) -> WarmerResponse:
    """Delete a warmer session (must be stopped first)"""
    try:
        # Check if warmer is active
        status = warmer_engine.get_warmer_status(warmer_id)
        
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        
        if status["is_active"]:
            return WarmerResponse(
                success=False,
                error="Cannot delete active warmer. Stop it first."
            )
        
        # Delete from database
        from database.connection import get_db
        from warmer.models import WarmerSession
        
        with get_db() as db:
            warmer = db.query(WarmerSession).filter(WarmerSession.id == warmer_id).first()
            if not warmer:
                raise HTTPException(status_code=404, detail="Warmer session not found")
            
            db.delete(warmer)
            db.commit()
        
        return WarmerResponse(
            success=True,
            message="Warmer session deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting warmer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))