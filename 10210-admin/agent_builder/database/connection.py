"""
Database connection and initialization for Agent Builder
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator

from agent_builder.models.agent import Base

# Database configuration
DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATABASE_DIR, exist_ok=True)

DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(DATABASE_DIR, 'agent_builder.db')}"
SYNC_DATABASE_URL = f"sqlite:///{os.path.join(DATABASE_DIR, 'agent_builder.db')}"

# Async engine for FastAPI
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Sync engine for migrations
sync_engine = create_engine(SYNC_DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

async def init_db():
    """Initialize database tables"""
    # For SQLite, we need to use sync engine for table creation
    Base.metadata.create_all(bind=sync_engine)
    print("Agent Builder database initialized")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def get_sync_db() -> Session:
    """Get synchronous database session"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()