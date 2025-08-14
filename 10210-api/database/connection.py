"""
Database connection and session management
"""

import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_DIR = "data"
DATABASE_FILE = "wagent.db"
DATABASE_PATH = os.path.join(DATABASE_DIR, DATABASE_FILE)
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# SQLAlchemy setup
engine = None
SessionLocal = None
Base = declarative_base()

def init_database():
    """Initialize database connection and create tables"""
    global engine, SessionLocal
    
    try:
        # Create data directory if it doesn't exist
        os.makedirs(DATABASE_DIR, exist_ok=True)
        
        # Create SQLite engine
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},  # SQLite specific
            echo=False  # Set to True for SQL debugging
        )
        
        # Create session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Import all models to ensure they're registered
        from . import models
        from . import user_sessions
        from . import subscription_models
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info(f"Database initialized successfully at {DATABASE_PATH}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        return False

def get_session() -> Session:
    """Get database session"""
    if SessionLocal is None:
        init_database()
    return SessionLocal()

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Database session context manager"""
    db = get_session()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database transaction error: {str(e)}")
        raise
    finally:
        db.close()

def get_db_dependency() -> Generator[Session, None, None]:
    """FastAPI dependency for database session"""
    db = get_session()
    try:
        yield db
    finally:
        db.close()

def test_connection() -> bool:
    """Test database connection"""
    try:
        with get_db() as db:
            result = db.execute(text("SELECT 1")).fetchone()
            return result[0] == 1
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False

def create_backup(backup_path: str = None) -> str:
    """Create database backup"""
    import shutil
    from datetime import datetime
    
    if backup_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(DATABASE_DIR, "backups", f"wagent_backup_{timestamp}.db")
    
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    shutil.copy2(DATABASE_PATH, backup_path)
    
    logger.info(f"Database backup created: {backup_path}")
    return backup_path

def get_database_info() -> dict:
    """Get database information and statistics"""
    try:
        with get_db() as db:
            # Get table counts
            campaigns_count = db.execute(text("SELECT COUNT(*) FROM campaigns")).scalar()
            deliveries_count = db.execute(text("SELECT COUNT(*) FROM deliveries")).scalar()
            analytics_count = db.execute(text("SELECT COUNT(*) FROM campaign_analytics")).scalar()
            
            # Get database size
            db_size = os.path.getsize(DATABASE_PATH) if os.path.exists(DATABASE_PATH) else 0
            
            return {
                "database_path": DATABASE_PATH,
                "database_size_bytes": db_size,
                "database_size_mb": round(db_size / (1024 * 1024), 2),
                "tables": {
                    "campaigns": campaigns_count,
                    "deliveries": deliveries_count,
                    "campaign_analytics": analytics_count
                }
            }
    except Exception as e:
        logger.error(f"Failed to get database info: {str(e)}")
        return {"error": str(e)}
