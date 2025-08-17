"""
Celery tasks for WhatsApp Warmer
Handles warmer operations, group management, and conversation orchestration
"""

import logging
from celery import shared_task
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio
import random

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_warmer_message(self, warmer_id: int, message_type: str = "group"):
    """
    Send a single warmer message (group or direct)
    """
    try:
        from warmer.warmer_engine import warmer_engine
        
        logger.info(f"Sending {message_type} message for warmer {warmer_id}")
        
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if message_type == "group":
                result = loop.run_until_complete(
                    warmer_engine._send_group_message_task(warmer_id)
                )
            else:
                result = loop.run_until_complete(
                    warmer_engine._send_direct_message_task(warmer_id)
                )
            
            return {"success": True, "warmer_id": warmer_id, "type": message_type}
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error sending warmer message: {str(e)}")
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

@shared_task
def start_warmer_session(warmer_id: int, user_id: str):
    """
    Start a warmer session
    Sets up contacts, groups, and begins conversation flow
    """
    try:
        from warmer.warmer_engine import warmer_engine
        from database.connection import get_db
        from warmer.models import WarmerSession
        
        logger.info(f"Starting warmer session {warmer_id} for user {user_id}")
        
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Start the warmer
            result = loop.run_until_complete(
                warmer_engine.start_warming(warmer_id)
            )
            
            if result["success"]:
                # Schedule periodic messages
                schedule_warmer_messages.delay(warmer_id)
                
                logger.info(f"Warmer {warmer_id} started successfully")
                return result
            else:
                logger.error(f"Failed to start warmer: {result}")
                return result
                
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error starting warmer session: {str(e)}")
        return {"success": False, "error": str(e)}

@shared_task
def stop_warmer_session(warmer_id: int):
    """
    Stop a warmer session
    """
    try:
        from warmer.warmer_engine import warmer_engine
        
        logger.info(f"Stopping warmer session {warmer_id}")
        
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                warmer_engine.stop_warming(warmer_id)
            )
            
            logger.info(f"Warmer {warmer_id} stopped")
            return result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error stopping warmer session: {str(e)}")
        return {"success": False, "error": str(e)}

@shared_task
def schedule_warmer_messages(warmer_id: int):
    """
    Schedule messages for a warmer session
    Creates a series of delayed tasks for natural conversation flow
    """
    try:
        from database.connection import get_db
        from warmer.models import WarmerSession
        
        with get_db() as db:
            warmer = db.query(WarmerSession).filter(
                WarmerSession.id == warmer_id
            ).first()
            
            if not warmer or warmer.status != "warming":
                logger.info(f"Warmer {warmer_id} not active, stopping message scheduling")
                return {"success": False, "reason": "Warmer not active"}
            
            # Schedule messages for the next hour
            for i in range(20):  # 20 messages in an hour
                # Random delay between 2-5 minutes
                delay_minutes = random.randint(2, 5)
                delay_seconds = delay_minutes * 60 + random.randint(0, 30)
                
                # 70% group messages, 30% direct messages
                message_type = "group" if random.random() < 0.7 else "direct"
                
                # Schedule the message
                send_warmer_message.apply_async(
                    args=[warmer_id, message_type],
                    countdown=delay_seconds + (i * 180)  # Spread over time
                )
            
            # Schedule next batch in 1 hour
            schedule_warmer_messages.apply_async(
                args=[warmer_id],
                countdown=3600  # 1 hour
            )
            
            logger.info(f"Scheduled 20 messages for warmer {warmer_id}")
            return {"success": True, "scheduled": 20}
            
    except Exception as e:
        logger.error(f"Error scheduling warmer messages: {str(e)}")
        return {"success": False, "error": str(e)}

@shared_task
def check_warmer_time_limits():
    """
    Periodic task to check if any warmers have exceeded their time limits
    Runs every 5 minutes via Celery Beat
    """
    try:
        from database.connection import get_db
        from warmer.models import WarmerSession
        from database.subscription_models import UserSubscription
        
        with get_db() as db:
            # Get all active warmers
            active_warmers = db.query(WarmerSession).filter(
                WarmerSession.status == "warming"
            ).all()
            
            for warmer in active_warmers:
                if not warmer.user_id or not warmer.started_at:
                    continue
                
                # Get user subscription
                user_sub = db.query(UserSubscription).filter(
                    UserSubscription.user_id == warmer.user_id
                ).first()
                
                if not user_sub:
                    continue
                
                # Calculate current session duration
                current_duration = (datetime.utcnow() - warmer.started_at).total_seconds() / 60
                total_duration = (warmer.total_duration_minutes or 0) + current_duration
                max_duration = user_sub.warmer_duration_hours * 60
                
                # Check if exceeded
                if max_duration > 0 and total_duration >= max_duration:
                    logger.warning(f"Warmer {warmer.id} exceeded time limit ({total_duration:.1f}/{max_duration} min)")
                    
                    # Stop the warmer
                    stop_warmer_session.delay(warmer.id)
                    
                    # Update status
                    warmer.status = "stopped"
                    warmer.stopped_at = datetime.utcnow()
                    db.commit()
        
        logger.info(f"Checked {len(active_warmers)} active warmers for time limits")
        return {"success": True, "checked": len(active_warmers)}
        
    except Exception as e:
        logger.error(f"Error checking warmer time limits: {str(e)}")
        return {"success": False, "error": str(e)}

@shared_task
def join_warmer_groups(warmer_id: int, invite_links: List[str]):
    """
    Join groups for a warmer session using invite links
    """
    try:
        from warmer.group_manager import GroupManager
        
        logger.info(f"Joining {len(invite_links)} groups for warmer {warmer_id}")
        
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            group_manager = GroupManager()
            result = loop.run_until_complete(
                group_manager.join_groups_by_links(warmer_id, invite_links)
            )
            
            logger.info(f"Joined {len(result.get('joined_groups', []))} groups for warmer {warmer_id}")
            return result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error joining warmer groups: {str(e)}")
        return {"success": False, "error": str(e)}

@shared_task
def update_warmer_statistics(warmer_id: int):
    """
    Update statistics for a warmer session
    """
    try:
        from database.connection import get_db
        from warmer.models import WarmerSession, WarmerConversation
        
        with get_db() as db:
            warmer = db.query(WarmerSession).filter(
                WarmerSession.id == warmer_id
            ).first()
            
            if not warmer:
                return {"success": False, "error": "Warmer not found"}
            
            # Count messages
            total_messages = db.query(WarmerConversation).filter(
                WarmerConversation.warmer_session_id == warmer_id
            ).count()
            
            group_messages = db.query(WarmerConversation).filter(
                WarmerConversation.warmer_session_id == warmer_id,
                WarmerConversation.group_id.isnot(None)
            ).count()
            
            direct_messages = total_messages - group_messages
            
            # Update warmer statistics
            warmer.total_messages_sent = total_messages
            warmer.total_group_messages = group_messages
            warmer.total_direct_messages = direct_messages
            
            # Calculate duration if running
            if warmer.started_at and warmer.status == "warming":
                current_duration = (datetime.utcnow() - warmer.started_at).total_seconds() / 60
                warmer.duration_minutes = current_duration
            
            db.commit()
            
            logger.info(f"Updated statistics for warmer {warmer_id}: {total_messages} messages")
            
            return {
                "success": True,
                "warmer_id": warmer_id,
                "statistics": {
                    "total_messages": total_messages,
                    "group_messages": group_messages,
                    "direct_messages": direct_messages,
                    "duration_minutes": warmer.duration_minutes
                }
            }
            
    except Exception as e:
        logger.error(f"Error updating warmer statistics: {str(e)}")
        return {"success": False, "error": str(e)}