"""
General Celery tasks for system maintenance and monitoring
"""

import logging
from celery import shared_task
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

@shared_task
def cleanup_old_sessions():
    """
    Clean up old inactive sessions
    Runs hourly via Celery Beat
    """
    try:
        from database.connection import get_db
        from database.user_sessions import UserWhatsAppSession
        from waha_functions import WAHAClient
        
        waha = WAHAClient()
        cleanup_count = 0
        
        with get_db() as db:
            # Find sessions that have been inactive for more than 7 days
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            old_sessions = db.query(UserWhatsAppSession).filter(
                UserWhatsAppSession.last_activity < cutoff_date,
                UserWhatsAppSession.status.in_(["stopped", "failed", "logged_out"])
            ).all()
            
            for session in old_sessions:
                try:
                    # Delete from WAHA
                    if session.waha_session_name:
                        waha.delete_session(session.waha_session_name)
                    
                    # Delete from database
                    db.delete(session)
                    cleanup_count += 1
                    
                    logger.info(f"Cleaned up old session: {session.session_name}")
                    
                except Exception as e:
                    logger.error(f"Error cleaning up session {session.session_name}: {e}")
            
            db.commit()
        
        logger.info(f"Cleaned up {cleanup_count} old sessions")
        return {"success": True, "cleaned": cleanup_count}
        
    except Exception as e:
        logger.error(f"Error cleaning up old sessions: {str(e)}")
        return {"success": False, "error": str(e)}

@shared_task
def update_usage_metrics():
    """
    Update user usage metrics
    Runs every 15 minutes via Celery Beat
    """
    try:
        from database.connection import get_db
        from database.subscription_models import UserSubscription
        from database.user_metrics import UserMetrics
        from database.models import Campaign, Delivery
        from warmer.models import WarmerSession
        
        with get_db() as db:
            # Get all users with subscriptions
            users = db.query(UserSubscription).all()
            
            for user_sub in users:
                user_id = user_sub.user_id
                
                # Get or create metrics record
                metrics = db.query(UserMetrics).filter(
                    UserMetrics.user_id == user_id
                ).first()
                
                if not metrics:
                    metrics = UserMetrics(user_id=user_id)
                    db.add(metrics)
                
                # Update campaign metrics
                campaigns = db.query(Campaign).filter(
                    Campaign.user_id == user_id
                ).all()
                
                metrics.total_campaigns_created = len(campaigns)
                
                # Count messages
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
                        
                        if hasattr(delivery, 'read_at') and delivery.read_at:
                            total_read += 1
                        if hasattr(delivery, 'response_received') and delivery.response_received:
                            total_responded += 1
                
                metrics.total_messages_sent = total_sent
                metrics.total_messages_delivered = total_delivered
                metrics.total_messages_failed = total_failed
                metrics.total_messages_read = total_read
                metrics.total_messages_responded = total_responded
                
                # Update warmer metrics
                warmers = db.query(WarmerSession).filter(
                    WarmerSession.user_id == user_id
                ).all()
                
                metrics.total_warmers_created = len(warmers)
                metrics.total_warmer_messages = sum(w.total_messages_sent for w in warmers)
                metrics.total_warmer_hours = sum(w.total_duration_minutes or 0 for w in warmers) / 60
                
                # Update session counts
                from database.user_sessions import UserWhatsAppSession
                
                sessions = db.query(UserWhatsAppSession).filter(
                    UserWhatsAppSession.user_id == user_id
                ).all()
                
                metrics.total_sessions_created = len(sessions)
                metrics.active_sessions = len([s for s in sessions if s.status == "active"])
                
                # Update timestamp
                metrics.last_updated = datetime.utcnow()
            
            db.commit()
            
        logger.info(f"Updated metrics for {len(users)} users")
        return {"success": True, "users_updated": len(users)}
        
    except Exception as e:
        logger.error(f"Error updating usage metrics: {str(e)}")
        return {"success": False, "error": str(e)}

@shared_task
def check_subscription_limits():
    """
    Check and enforce subscription limits
    """
    try:
        from database.connection import get_db
        from database.subscription_models import UserSubscription
        from database.user_sessions import UserWhatsAppSession
        from warmer.models import WarmerSession
        
        warnings = []
        
        with get_db() as db:
            subscriptions = db.query(UserSubscription).all()
            
            for sub in subscriptions:
                user_id = sub.user_id
                
                # Check session limits
                active_sessions = db.query(UserWhatsAppSession).filter(
                    UserWhatsAppSession.user_id == user_id,
                    UserWhatsAppSession.status.in_(["active", "started", "scan"])
                ).count()
                
                if active_sessions > sub.max_sessions:
                    warnings.append({
                        "user_id": user_id,
                        "type": "session_limit",
                        "limit": sub.max_sessions,
                        "current": active_sessions
                    })
                    logger.warning(f"User {user_id} exceeds session limit: {active_sessions}/{sub.max_sessions}")
                
                # Check warmer hours
                warmers = db.query(WarmerSession).filter(
                    WarmerSession.user_id == user_id,
                    WarmerSession.status == "warming"
                ).all()
                
                for warmer in warmers:
                    if warmer.started_at:
                        current_duration = (datetime.utcnow() - warmer.started_at).total_seconds() / 60
                        total_duration = (warmer.total_duration_minutes or 0) + current_duration
                        max_duration = sub.warmer_duration_hours * 60
                        
                        if max_duration > 0 and total_duration >= max_duration:
                            warnings.append({
                                "user_id": user_id,
                                "type": "warmer_hours",
                                "limit": max_duration,
                                "current": total_duration,
                                "warmer_id": warmer.id
                            })
                            logger.warning(f"User {user_id} warmer {warmer.id} exceeds time limit")
        
        logger.info(f"Checked subscription limits, found {len(warnings)} warnings")
        return {"success": True, "warnings": warnings}
        
    except Exception as e:
        logger.error(f"Error checking subscription limits: {str(e)}")
        return {"success": False, "error": str(e)}

@shared_task
def sync_waha_sessions():
    """
    Sync WAHA sessions with database
    Ensures database reflects actual WAHA state
    """
    try:
        from database.connection import get_db
        from database.user_sessions import UserWhatsAppSession
        from waha_functions import WAHAClient
        
        waha = WAHAClient()
        
        # Get all WAHA sessions
        waha_sessions = waha.get_sessions()
        waha_session_names = {s.get("name") for s in waha_sessions}
        
        with get_db() as db:
            # Get all database sessions
            db_sessions = db.query(UserWhatsAppSession).all()
            
            # Check each database session
            for session in db_sessions:
                if session.waha_session_name:
                    # Check if exists in WAHA
                    if session.waha_session_name not in waha_session_names:
                        # Session doesn't exist in WAHA but exists in DB
                        logger.warning(f"Session {session.session_name} not found in WAHA, marking as stopped")
                        session.status = "stopped"
                    else:
                        # Get WAHA session status
                        for waha_session in waha_sessions:
                            if waha_session.get("name") == session.waha_session_name:
                                waha_status = waha_session.get("status", "").lower()
                                
                                # Map WAHA status to our status
                                if waha_status == "working":
                                    session.status = "active"
                                elif waha_status == "scan":
                                    session.status = "scan"
                                elif waha_status == "stopped":
                                    session.status = "stopped"
                                elif waha_status == "failed":
                                    session.status = "failed"
                                
                                break
            
            # Check for orphaned WAHA sessions
            db_waha_names = {s.waha_session_name for s in db_sessions if s.waha_session_name}
            orphaned = waha_session_names - db_waha_names
            
            if orphaned:
                logger.warning(f"Found {len(orphaned)} orphaned WAHA sessions: {orphaned}")
                # TODO: Decide whether to delete orphaned sessions or create DB records
            
            db.commit()
        
        logger.info(f"Synced {len(db_sessions)} sessions with WAHA")
        return {"success": True, "synced": len(db_sessions), "orphaned": len(orphaned)}
        
    except Exception as e:
        logger.error(f"Error syncing WAHA sessions: {str(e)}")
        return {"success": False, "error": str(e)}

@shared_task
def send_webhook_notification(user_id: str, event_type: str, data: Dict):
    """
    Send webhook notifications to user-configured endpoints
    """
    try:
        import requests
        from database.connection import get_db
        from database.subscription_models import UserSubscription
        
        with get_db() as db:
            user_sub = db.query(UserSubscription).filter(
                UserSubscription.user_id == user_id
            ).first()
            
            if not user_sub or not user_sub.webhook_url:
                return {"success": False, "reason": "No webhook configured"}
            
            # Prepare webhook payload
            payload = {
                "user_id": user_id,
                "event": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            }
            
            # Send webhook
            response = requests.post(
                user_sub.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Webhook sent successfully to {user_sub.webhook_url}")
                return {"success": True, "status_code": response.status_code}
            else:
                logger.error(f"Webhook failed: {response.status_code} - {response.text}")
                return {"success": False, "status_code": response.status_code}
                
    except Exception as e:
        logger.error(f"Error sending webhook: {str(e)}")
        return {"success": False, "error": str(e)}