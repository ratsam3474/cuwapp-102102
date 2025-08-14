#!/usr/bin/env python3
"""
Initialize database tables
Run this script to create all necessary database tables
"""

import os
import sys
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize all database tables"""
    try:
        # Import database connection
        from database.connection import init_database as init_db_connection, Base
        
        # Import all models to register them with SQLAlchemy
        logger.info("Loading database models...")
        
        # Core models
        from database.models import Campaign, Delivery, CampaignAnalytics
        logger.info("Loaded campaign models")
        
        # User session models
        from database.user_sessions import UserWhatsAppSession, UserSessionActivity
        logger.info("Loaded user session models")
        
        # Subscription models
        from database.subscription_models import UserSubscription, Payment, WebhookEvent, UsageLog
        logger.info("Loaded subscription models")
        
        # Warmer models
        try:
            from warmer.models import WarmerSession, WarmerGroup, WarmerConversation, WarmerContact
            logger.info("Loaded warmer models")
        except ImportError:
            logger.warning("Warmer models not available")
        
        # Initialize database connection
        logger.info("Initializing database connection...")
        if not init_db_connection():
            logger.error("Failed to initialize database connection")
            return False
        
        # Get engine after initialization
        from database.connection import engine
        
        # Create all tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        
        # List all tables created
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        logger.info(f"Database initialized with {len(tables)} tables:")
        for table in tables:
            logger.info(f"  - {table}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("Starting database initialization...")
    
    if init_database():
        logger.info("✅ Database initialization completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Database initialization failed!")
        sys.exit(1)