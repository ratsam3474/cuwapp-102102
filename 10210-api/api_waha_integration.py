#!/usr/bin/env python3
"""
API Integration for WAHA Multi-Instance Support
Add this to your main.py or create as a blueprint
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import logging
from waha_session_manager import waha_session_manager
from waha_pool_manager import waha_pool
from free_session_manager import free_session_manager

logger = logging.getLogger(__name__)

# Create router for WAHA endpoints
waha_router = APIRouter(prefix="/api/waha", tags=["WAHA Multi-Instance"])

@waha_router.post("/sessions/create")
async def create_session(
    user_id: str,
    session_name: str,
    config: Optional[dict] = None
):
    """Create a new WhatsApp session with automatic instance assignment"""
    try:
        result = waha_session_manager.create_session(user_id, session_name, config)
        return {
            "success": True,
            "session_name": session_name,
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@waha_router.post("/messages/send-text")
async def send_text_message(
    user_id: str,
    session_name: str,
    chat_id: str,
    text: str
):
    """Send text message using the correct WAHA instance"""
    try:
        result = waha_session_manager.send_text(user_id, session_name, chat_id, text)
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@waha_router.get("/sessions/{session_name}")
async def get_session_info(
    user_id: str,
    session_name: str
):
    """Get session info from the correct WAHA instance"""
    try:
        result = waha_session_manager.get_session_info(user_id, session_name)
        return {
            "success": True,
            "session": result
        }
    except Exception as e:
        logger.error(f"Failed to get session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@waha_router.delete("/sessions/{session_name}")
async def delete_session(
    user_id: str,
    session_name: str
):
    """Delete session from WAHA and database"""
    try:
        waha_session_manager.delete_session(user_id, session_name)
        return {
            "success": True,
            "message": f"Session {session_name} deleted"
        }
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@waha_router.get("/pool/status")
async def get_pool_status():
    """Get status of all WAHA instances in the pool"""
    try:
        return waha_pool.get_pool_status()
    except Exception as e:
        logger.error(f"Failed to get pool status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@waha_router.get("/free-users/stats")
async def get_free_user_stats():
    """Get statistics about free user sessions"""
    try:
        return free_session_manager.get_stats()
    except Exception as e:
        logger.error(f"Failed to get free user stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@waha_router.post("/free-users/cleanup")
async def trigger_free_user_cleanup():
    """Manually trigger cleanup of inactive free user sessions"""
    try:
        free_session_manager.cleanup_inactive_sessions()
        return {
            "success": True,
            "message": "Cleanup triggered"
        }
    except Exception as e:
        logger.error(f"Failed to trigger cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Function to integrate with your existing main.py
def setup_waha_multi_instance(app):
    """
    Add this to your main.py:
    
    from api_waha_integration import setup_waha_multi_instance
    setup_waha_multi_instance(app)
    """
    
    # Include the router
    app.include_router(waha_router)
    
    # Start the free user cleanup task
    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting WAHA multi-instance support...")
        free_session_manager.start()
        logger.info("Free user session manager started")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Stopping WAHA multi-instance support...")
        free_session_manager.stop()
        logger.info("Free user session manager stopped")
    
    logger.info("WAHA multi-instance support configured")