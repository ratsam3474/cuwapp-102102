"""
User-specific Analytics Module
Provides analytics filtered by user_id
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session
from database.models import Campaign
from database.subscription_models import UserSubscription
from database.user_sessions import UserWhatsAppSession, UserSessionActivity
from warmer.models import WarmerSession, WarmerContact
import logging

logger = logging.getLogger(__name__)


class UserAnalytics:
    """Handles user-specific analytics"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_overview(self, user_id: str) -> Dict:
        """Get overview statistics for a specific user"""
        try:
            # Get user subscription
            subscription = self.db.query(UserSubscription).filter(
                UserSubscription.user_id == user_id
            ).first()
            
            if not subscription:
                return {
                    "error": "User subscription not found",
                    "user_id": user_id
                }
            
            # Get user's sessions
            sessions = self.db.query(UserWhatsAppSession).filter(
                UserWhatsAppSession.user_id == user_id
            ).all()
            
            # Get user's campaigns
            campaigns = self.db.query(Campaign).filter(
                Campaign.user_id == user_id
            ).all()
            
            # Calculate campaign statistics
            active_campaigns = [c for c in campaigns if c.status in ['running', 'scheduled', 'queued']]
            completed_campaigns = [c for c in campaigns if c.status == 'completed']
            
            # Get contacts count
            contacts_count = self.db.query(WarmerContact).filter(
                WarmerContact.user_id == user_id
            ).count()
            
            # Calculate messages sent
            total_messages_sent = sum(s.messages_sent for s in sessions)
            
            # Get recent activity
            recent_activity = self.db.query(UserSessionActivity).filter(
                UserSessionActivity.user_id == user_id
            ).order_by(UserSessionActivity.created_at.desc()).limit(5).all()
            
            return {
                "user_id": user_id,
                "subscription": {
                    "plan": subscription.plan_type.value,
                    "status": subscription.status.value,
                    "messages_limit": subscription.max_messages_per_month,
                    "messages_used": subscription.messages_sent_this_month,
                    "messages_remaining": max(0, subscription.max_messages_per_month - subscription.messages_sent_this_month),
                    "sessions_limit": subscription.max_sessions,
                    "sessions_used": subscription.current_sessions
                },
                "sessions": {
                    "total": len(sessions),
                    "active": len([s for s in sessions if s.status == 'active']),
                    "primary": next((s.session_name for s in sessions if s.is_primary), None)
                },
                "campaigns": {
                    "total": len(campaigns),
                    "active": len(active_campaigns),
                    "completed": len(completed_campaigns),
                    "success_rate": self._calculate_success_rate(campaigns)
                },
                "contacts": {
                    "total": contacts_count,
                    "imported_today": self._get_contacts_imported_today(user_id)
                },
                "messages": {
                    "total_sent": total_messages_sent,
                    "sent_today": self._get_messages_sent_today(user_id),
                    "sent_this_month": subscription.messages_sent_this_month
                },
                "recent_activity": [
                    {
                        "type": activity.activity_type,
                        "timestamp": activity.created_at.isoformat(),
                        "data": activity.get_data()
                    } for activity in recent_activity
                ]
            }
        except Exception as e:
            logger.error(f"Error getting user overview: {e}")
            return {"error": str(e)}
    
    def get_user_campaign_analytics(self, user_id: str, period: str = "month") -> Dict:
        """Get campaign analytics for a specific user"""
        try:
            # Define time period
            if period == "day":
                start_date = datetime.now(timezone.utc) - timedelta(days=1)
            elif period == "week":
                start_date = datetime.now(timezone.utc) - timedelta(weeks=1)
            elif period == "year":
                start_date = datetime.now(timezone.utc) - timedelta(days=365)
            else:  # month
                start_date = datetime.now(timezone.utc) - timedelta(days=30)
            
            # Get campaigns in period
            campaigns = self.db.query(Campaign).filter(
                and_(
                    Campaign.user_id == user_id,
                    Campaign.created_at >= start_date
                )
            ).all()
            
            # Group by status
            campaigns_by_status = {}
            for campaign in campaigns:
                status = campaign.status
                if status not in campaigns_by_status:
                    campaigns_by_status[status] = 0
                campaigns_by_status[status] += 1
            
            # Calculate daily distribution
            daily_distribution = self._calculate_daily_distribution(campaigns, start_date)
            
            # Get top performing campaigns
            top_campaigns = sorted(
                campaigns,
                key=lambda c: c.messages_sent if hasattr(c, 'messages_sent') else 0,
                reverse=True
            )[:5]
            
            return {
                "user_id": user_id,
                "period": period,
                "total_campaigns": len(campaigns),
                "campaigns_by_status": campaigns_by_status,
                "daily_distribution": daily_distribution,
                "top_campaigns": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "status": c.status,
                        "messages_sent": getattr(c, 'messages_sent', 0),
                        "created_at": c.created_at.isoformat() if c.created_at else None
                    } for c in top_campaigns
                ],
                "average_messages_per_campaign": self._calculate_average_messages(campaigns)
            }
        except Exception as e:
            logger.error(f"Error getting campaign analytics: {e}")
            return {"error": str(e)}
    
    def get_user_session_analytics(self, user_id: str) -> Dict:
        """Get session analytics for a specific user"""
        try:
            sessions = self.db.query(UserWhatsAppSession).filter(
                UserWhatsAppSession.user_id == user_id
            ).all()
            
            # Get activity for each session
            session_analytics = []
            for session in sessions:
                activity_count = self.db.query(UserSessionActivity).filter(
                    and_(
                        UserSessionActivity.user_id == user_id,
                        UserSessionActivity.session_name == session.session_name
                    )
                ).count()
                
                session_analytics.append({
                    "session_name": session.session_name,
                    "phone_number": session.phone_number,
                    "status": session.status,
                    "is_primary": session.is_primary,
                    "messages_sent": session.messages_sent,
                    "campaigns_run": session.campaigns_run,
                    "contacts_imported": session.contacts_imported,
                    "activity_count": activity_count,
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                    "last_active": session.last_active.isoformat() if session.last_active else None
                })
            
            return {
                "user_id": user_id,
                "total_sessions": len(sessions),
                "active_sessions": len([s for s in sessions if s.status == 'active']),
                "sessions": session_analytics
            }
        except Exception as e:
            logger.error(f"Error getting session analytics: {e}")
            return {"error": str(e)}
    
    def _calculate_success_rate(self, campaigns: List) -> float:
        """Calculate campaign success rate"""
        if not campaigns:
            return 0.0
        
        completed = [c for c in campaigns if c.status == 'completed']
        if not completed:
            return 0.0
        
        # Consider a campaign successful if it sent at least 80% of planned messages
        successful = 0
        for campaign in completed:
            if hasattr(campaign, 'messages_sent') and hasattr(campaign, 'total_contacts'):
                if campaign.total_contacts > 0:
                    rate = campaign.messages_sent / campaign.total_contacts
                    if rate >= 0.8:
                        successful += 1
        
        return round((successful / len(completed)) * 100, 2) if completed else 0.0
    
    def _get_contacts_imported_today(self, user_id: str) -> int:
        """Get number of contacts imported today"""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        return self.db.query(WarmerContact).filter(
            and_(
                WarmerContact.user_id == user_id,
                WarmerContact.created_at >= today_start
            )
        ).count()
    
    def _get_messages_sent_today(self, user_id: str) -> int:
        """Get number of messages sent today"""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        activities = self.db.query(UserSessionActivity).filter(
            and_(
                UserSessionActivity.user_id == user_id,
                UserSessionActivity.activity_type == 'send_message',
                UserSessionActivity.created_at >= today_start
            )
        ).all()
        
        return len(activities)
    
    def _calculate_daily_distribution(self, campaigns: List, start_date: datetime) -> List[Dict]:
        """Calculate daily distribution of campaigns"""
        distribution = {}
        
        for campaign in campaigns:
            if campaign.created_at:
                date_key = campaign.created_at.date().isoformat()
                if date_key not in distribution:
                    distribution[date_key] = 0
                distribution[date_key] += 1
        
        # Fill in missing dates
        current_date = start_date.date()
        end_date = datetime.now(timezone.utc).date()
        
        result = []
        while current_date <= end_date:
            date_key = current_date.isoformat()
            result.append({
                "date": date_key,
                "count": distribution.get(date_key, 0)
            })
            current_date += timedelta(days=1)
        
        return result
    
    def _calculate_average_messages(self, campaigns: List) -> float:
        """Calculate average messages per campaign"""
        if not campaigns:
            return 0.0
        
        total_messages = sum(
            getattr(c, 'messages_sent', 0) for c in campaigns
        )
        
        return round(total_messages / len(campaigns), 2) if campaigns else 0.0