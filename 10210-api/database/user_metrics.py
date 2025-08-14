"""
User Metrics Model - Tracks lifetime user statistics
"""

from sqlalchemy import Column, String, Integer, Float, DateTime
from sqlalchemy.sql import func
from database.connection import Base
from datetime import datetime


class UserMetrics(Base):
    """Lifetime metrics for each user"""
    __tablename__ = "user_metrics"
    
    user_id = Column(String(255), primary_key=True, index=True)
    
    # Campaign metrics
    total_campaigns_created = Column(Integer, default=0)
    total_campaigns_completed = Column(Integer, default=0)
    total_campaigns_failed = Column(Integer, default=0)
    
    # Message metrics
    total_messages_sent = Column(Integer, default=0)
    total_messages_delivered = Column(Integer, default=0)
    total_messages_failed = Column(Integer, default=0)
    total_messages_read = Column(Integer, default=0)
    total_messages_responded = Column(Integer, default=0)
    
    # Contact metrics
    total_contacts_imported = Column(Integer, default=0)
    total_unique_contacts = Column(Integer, default=0)
    
    # Session metrics
    total_sessions_created = Column(Integer, default=0)
    total_sessions_deleted = Column(Integer, default=0)
    
    # Warmer metrics
    total_warmer_hours = Column(Float, default=0.0)
    total_warmer_messages = Column(Integer, default=0)
    
    # Activity timestamps
    last_campaign_date = Column(DateTime)
    last_message_date = Column(DateTime)
    last_login_date = Column(DateTime)
    
    # Meta
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def get_or_create(cls, db, user_id):
        """Get existing metrics or create new one"""
        metrics = db.query(cls).filter(cls.user_id == user_id).first()
        if not metrics:
            metrics = cls(user_id=user_id)
            db.add(metrics)
            db.commit()
        return metrics
    
    def increment_campaigns(self, db, status='created'):
        """Increment campaign counters"""
        self.total_campaigns_created += 1
        if status == 'completed':
            self.total_campaigns_completed += 1
        elif status == 'failed':
            self.total_campaigns_failed += 1
        self.last_campaign_date = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.commit()
    
    def add_messages(self, db, sent=0, delivered=0, failed=0, read=0, responded=0):
        """Add to message counters"""
        self.total_messages_sent += sent
        self.total_messages_delivered += delivered
        self.total_messages_failed += failed
        self.total_messages_read += read
        self.total_messages_responded += responded
        if sent > 0:
            self.last_message_date = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.commit()
    
    def add_contacts(self, db, imported=0, unique=0):
        """Add to contact counters"""
        self.total_contacts_imported += imported
        self.total_unique_contacts += unique
        self.updated_at = datetime.utcnow()
        db.commit()
    
    def add_session(self, db, created=False, deleted=False):
        """Track session changes"""
        if created:
            self.total_sessions_created += 1
        if deleted:
            self.total_sessions_deleted += 1
        self.updated_at = datetime.utcnow()
        db.commit()
    
    def add_warmer_time(self, db, hours=0, messages=0):
        """Add warmer usage"""
        self.total_warmer_hours += hours
        self.total_warmer_messages += messages
        self.updated_at = datetime.utcnow()
        db.commit()
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "campaigns": {
                "total_created": self.total_campaigns_created,
                "total_completed": self.total_campaigns_completed,
                "total_failed": self.total_campaigns_failed
            },
            "messages": {
                "total_sent": self.total_messages_sent,
                "total_delivered": self.total_messages_delivered,
                "total_failed": self.total_messages_failed,
                "total_read": self.total_messages_read,
                "total_responded": self.total_messages_responded
            },
            "contacts": {
                "total_imported": self.total_contacts_imported,
                "total_unique": self.total_unique_contacts
            },
            "sessions": {
                "total_created": self.total_sessions_created,
                "total_deleted": self.total_sessions_deleted,
                "net_sessions": self.total_sessions_created - self.total_sessions_deleted
            },
            "warmer": {
                "total_hours": round(self.total_warmer_hours, 2),
                "total_messages": self.total_warmer_messages
            },
            "activity": {
                "last_campaign": self.last_campaign_date.isoformat() if self.last_campaign_date else None,
                "last_message": self.last_message_date.isoformat() if self.last_message_date else None,
                "last_login": self.last_login_date.isoformat() if self.last_login_date else None
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }