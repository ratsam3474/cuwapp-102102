from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Union
from datetime import datetime
import json
import base64
import os
import logging
from waha_functions import WAHAClient
from utils.orphan_cleanup import orphan_cleaner

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NEW PHASE 2 IMPORTS
try:
    from jobs.manager import CampaignManager
    from jobs.models import CampaignCreate, CampaignUpdate, MessageSample, MessageMode
    from database.connection import init_database, get_database_info
    from utils.templates import MessageTemplateEngine
    from jobs.scheduler import campaign_scheduler
    from api_extensions import router as file_router
    PHASE_2_ENABLED = True
    
    # Try to import warmer module
    try:
        from warmer.api import router as warmer_router
        WARMER_ENABLED = True
    except ImportError:
        logger.warning("WhatsApp Warmer module not available")
        WARMER_ENABLED = False
        warmer_router = None
    
    # Try to import email module
    try:
        from email_service.api import router as email_router
        EMAIL_ENABLED = True
        logger.info("Email module loaded successfully")
    except ImportError as e:
        logger.warning(f"Email module not available: {e}")
        EMAIL_ENABLED = False
        email_router = None
    
    # Try to import analytics module
    try:
        from analytics.api import router as analytics_router
        ANALYTICS_ENABLED = True
        logger.info("Analytics module loaded successfully")
    except ImportError as e:
        logger.warning(f"Analytics module not available: {e}")
        ANALYTICS_ENABLED = False
        analytics_router = None
    
    # Try to import payments module
    try:
        from payments.api import router as payments_router
        from payments.direct_payments_api import router as direct_payments_router
        PAYMENTS_ENABLED = True
        logger.info("Payments module loaded successfully")
    except ImportError as e:
        logger.warning(f"Payments module not available: {e}")
        PAYMENTS_ENABLED = False
        payments_router = None
        direct_payments_router = None
    
    # Try to import users module
    try:
        from api.users import router as users_router
        USERS_ENABLED = True
        logger.info("Users module loaded successfully")
    except ImportError as e:
        logger.warning(f"Users module not available: {e}")
        USERS_ENABLED = False
        users_router = None
        
except ImportError as e:
    logger.warning(f"Phase 2 components not available: {str(e)}")
    PHASE_2_ENABLED = False
    WARMER_ENABLED = False
    ANALYTICS_ENABLED = False

# Initialize FastAPI app
app = FastAPI(title="WhatsApp Agent", description="Complete WhatsApp Management Interface", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware for plan-based timeouts
try:
    from auth.middleware import SessionMiddleware
    app.add_middleware(SessionMiddleware)
    logger.info("Session middleware with plan-based timeouts enabled")
except ImportError as e:
    logger.warning(f"Session middleware not available: {e}")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve Swagger spec
from fastapi.responses import FileResponse

@app.get("/swagger.yaml")
async def get_swagger_spec():
    """Serve OpenAPI specification"""
    return FileResponse("swagger.yaml", media_type="text/yaml")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Initialize WAHA client with correct base URL
# Use environment variable or default to internal Docker service name
WAHA_BASE_URL = os.getenv("WAHA_BASE_URL", "http://localhost:4500")
waha = WAHAClient(base_url=WAHA_BASE_URL)  # Default client for backward compatibility

def get_waha_client_for_session(user_id: str, session_name: str) -> WAHAClient:
    """Get WAHA client for a specific session, using the correct WAHA instance"""
    from database.connection import get_db
    from database.user_sessions import UserWhatsAppSession
    
    with get_db() as db:
        # Look up session to get WAHA instance URL
        session = db.query(UserWhatsAppSession).filter(
            UserWhatsAppSession.user_id == user_id,
            UserWhatsAppSession.session_name == session_name
        ).first()
        
        if session and hasattr(session, 'waha_instance_url') and session.waha_instance_url:
            # Use session-specific WAHA instance
            return WAHAClient(base_url=session.waha_instance_url)
        else:
            # Fall back to default WAHA instance
            return waha

# Initialize Phase 2 components if available
if PHASE_2_ENABLED:
    campaign_manager = CampaignManager()
    template_engine = MessageTemplateEngine()
    
    # Include file processing router
    app.include_router(file_router, prefix="/api/files", tags=["files"])
    
    # Include warmer router if available
    if WARMER_ENABLED and warmer_router:
        app.include_router(warmer_router)
        logger.info("WhatsApp Warmer routes included")
    
    # Include auth router
    try:
        from auth.api import router as auth_router
        app.include_router(auth_router)
        logger.info("Auth routes included")
    except ImportError:
        logger.warning("Auth module not available")
    
    # Include email router if available  
    if EMAIL_ENABLED and email_router:
        app.include_router(email_router)
        logger.info("Email routes included")
        
        # Add direct /warmer endpoint
        @app.get("/warmer")
        async def get_warmer_list(user_id: str = Query(..., description="User ID is required")):
            """Get warmer sessions for authenticated user only"""
            try:
                from warmer.warmer_engine import warmer_engine
                # SECURITY: Filter warmers by user_id
                all_warmers = warmer_engine.get_all_warmers()
                user_warmers = [w for w in all_warmers if w.get('user_id') == user_id]
                return {
                    "success": True,
                    "message": f"Found {len(user_warmers)} warmer sessions",
                    "data": {"warmers": user_warmers}
                }
            except Exception as e:
                logger.error(f"Error listing warmers: {str(e)}")
                return {
                    "success": False,
                    "error": str(e)
                }
    
    # Include analytics router if available
    if ANALYTICS_ENABLED and analytics_router:
        app.include_router(analytics_router)
        logger.info("Analytics routes included")
    
    # Include user metrics routes
    try:
        from api.user_metrics_api import router as metrics_router
        app.include_router(metrics_router)
        logger.info("User metrics routes included")
    except ImportError as e:
        logger.warning(f"Could not load user metrics routes: {e}")
    
    # Include payments router if available
    if PAYMENTS_ENABLED and payments_router:
        app.include_router(payments_router)
        logger.info("Payments routes included")
        
        # Include direct payments router
        if direct_payments_router:
            app.include_router(direct_payments_router)
            logger.info("Direct payments routes included")
    
    if USERS_ENABLED and users_router:
        app.include_router(users_router)
        logger.info("Users routes included")
    
    # Initialize database
    init_database()
else:
    campaign_manager = None
    template_engine = None

# Pydantic models for request validation
class SessionCreate(BaseModel):
    name: str
    config: Optional[Dict] = None

class MessageSend(BaseModel):
    chatId: str
    text: str
    session: str

class FileMessage(BaseModel):
    chatId: str
    session: str
    caption: Optional[str] = ""

class LocationMessage(BaseModel):
    chatId: str
    session: str
    latitude: float
    longitude: float
    title: Optional[str] = ""

class GroupCreate(BaseModel):
    name: str
    participants: List[str]

class ContactAction(BaseModel):
    contactId: str
    session: str
    user_id: Optional[str] = None

class PhoneCheck(BaseModel):
    phone: str
    session: str

class CampaignRestart(BaseModel):
    start_row: int = 1
    stop_row: Optional[int] = None
    skip_processed: bool = False
    save_contact_before_message: bool = False

# ==================== STATIC ROUTES ====================

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve main dashboard"""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>Static files not found. Please ensure static/index.html exists.</h1>")

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page():
    """Serve analytics dashboard"""
    try:
        with open("static/analytics.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>Analytics page not found. Please ensure static/analytics.html exists.</h1>")

@app.get("/payment-success", response_class=HTMLResponse)
async def payment_success():
    """Payment success page"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment Successful - Cuwhapp</title>
        <style>
            body { font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
            .container { background: white; padding: 40px; border-radius: 10px; text-align: center; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }
            h1 { color: #28a745; margin-bottom: 20px; }
            .icon { font-size: 64px; margin-bottom: 20px; }
            a { display: inline-block; margin-top: 20px; padding: 12px 30px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; }
            a:hover { background: #218838; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">✅</div>
            <h1>Payment Successful!</h1>
            <p>Your subscription has been activated successfully.</p>
            <p>You can now access all premium features.</p>
            <a href="/">Go to Dashboard</a>
        </div>
    </body>
    </html>
    """)

@app.get("/payment-cancelled", response_class=HTMLResponse)
async def payment_cancelled():
    """Payment cancelled page"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment Cancelled - Cuwhapp</title>
        <style>
            body { font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
            .container { background: white; padding: 40px; border-radius: 10px; text-align: center; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }
            h1 { color: #dc3545; margin-bottom: 20px; }
            .icon { font-size: 64px; margin-bottom: 20px; }
            a { display: inline-block; margin-top: 20px; padding: 12px 30px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
            a:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">❌</div>
            <h1>Payment Cancelled</h1>
            <p>Your payment was cancelled.</p>
            <p>No charges were made to your account.</p>
            <a href="/">Return to Dashboard</a>
        </div>
    </body>
    </html>
    """)

# ==================== SESSION MANAGEMENT ====================

@app.get("/api/sessions")
async def get_sessions(user_id: str = Query(..., description="User ID is required")):
    """Get sessions for a specific user"""
    try:
        # SECURITY: Require user_id - never return all sessions publicly
        if not user_id:
            return {"success": False, "data": [], "error": "Authentication required"}
        
        from database.user_sessions import UserWhatsAppSession
        from database.connection import get_db
        
        with get_db() as db:
            # Get user's sessions from database
            user_sessions = db.query(UserWhatsAppSession).filter(
                UserWhatsAppSession.user_id == user_id
            ).all()
            
            # Group sessions by WAHA instance URL
            sessions_by_instance = {}
            for s in user_sessions:
                instance_url = getattr(s, 'waha_instance_url', None) or WAHA_BASE_URL
                if instance_url not in sessions_by_instance:
                    sessions_by_instance[instance_url] = []
                sessions_by_instance[instance_url].append(s)
            
            # Get sessions from each WAHA instance
            all_waha_sessions = []
            for instance_url, db_sessions in sessions_by_instance.items():
                try:
                    # Create client for this specific WAHA instance
                    instance_client = WAHAClient(base_url=instance_url)
                    instance_sessions = instance_client.get_sessions()
                    all_waha_sessions.extend(instance_sessions)
                except Exception as e:
                    logger.warning(f"Could not get sessions from {instance_url}: {e}")
            
            # Create mapping of WAHA names to display names and filter
            waha_to_display = {}
            for s in user_sessions:
                if s.waha_session_name:
                    waha_to_display[s.waha_session_name] = s.session_name
                else:
                    # Fallback for old sessions
                    waha_to_display[s.session_name] = s.session_name
            
            # Filter and map WAHA sessions to include display names
            filtered_sessions = []
            for session in all_waha_sessions:
                waha_name = session.get("name")
                if waha_name in waha_to_display:
                    # Replace the name with display name for frontend
                    session_copy = session.copy()
                    session_copy["display_name"] = waha_to_display[waha_name]
                    session_copy["name"] = waha_to_display[waha_name]  # Use display name as name
                    session_copy["waha_name"] = waha_name  # Keep actual WAHA name
                    filtered_sessions.append(session_copy)
            
            return {"success": True, "data": filtered_sessions}
    except Exception as e:
        logger.error(f"Error getting sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper function for session name mapping
def get_waha_session_name(session_name: str, user_id: Optional[str] = None) -> str:
    """Get the actual WAHA session name from display name"""
    logger.info(f"get_waha_session_name called with session_name='{session_name}', user_id='{user_id}'")
    if not user_id:
        logger.warning(f"No user_id provided, returning session_name as-is: '{session_name}'")
        return session_name
    
    from database.user_sessions import UserWhatsAppSession
    from database.connection import get_db
    
    with get_db() as db:
        # First check if this is already a WAHA session name (UUID format)
        if session_name.startswith('uuser_'):
            # This looks like a WAHA UUID, check if it exists
            user_session = db.query(UserWhatsAppSession).filter(
                UserWhatsAppSession.user_id == user_id,
                UserWhatsAppSession.waha_session_name == session_name
            ).first()
            
            if user_session:
                # Found it! Return the WAHA name (it's already a WAHA name)
                logger.info(f"Input is already a WAHA name: '{session_name}'")
                return session_name
        
        # Otherwise, treat it as a display name and look it up
        user_session = db.query(UserWhatsAppSession).filter(
            UserWhatsAppSession.user_id == user_id,
            UserWhatsAppSession.session_name == session_name
        ).first()
        
        if user_session and user_session.waha_session_name:
            logger.info(f"Found mapping: '{session_name}' -> '{user_session.waha_session_name}'")
            return user_session.waha_session_name
        else:
            logger.warning(f"No mapping found for user_id='{user_id}', session_name='{session_name}'")
    
    # Fallback: try to find by waha_session_name if session_name is actually the WAHA name
    with get_db() as db:
        user_session = db.query(UserWhatsAppSession).filter(
            UserWhatsAppSession.waha_session_name == session_name
        ).first()
        
        if user_session:
            logger.info(f"Found by WAHA name, returning: '{user_session.waha_session_name}'")
            return user_session.waha_session_name
    
    logger.warning(f"No mapping found at all, returning original: '{session_name}'")
    return session_name

@app.get("/api/sessions/names")
async def get_existing_session_names(user_id: str = Query(...)):
    """Get list of existing session names for a user"""
    try:
        from database.user_sessions import UserWhatsAppSession
        from database.connection import get_db
        
        with get_db() as db:
            sessions = db.query(UserWhatsAppSession.session_name).filter(
                UserWhatsAppSession.user_id == user_id
            ).all()
            
            return {
                "success": True,
                "session_names": [s[0] for s in sessions]
            }
    except Exception as e:
        logger.error(f"Error getting session names: {str(e)}")
        return {"success": False, "session_names": []}

@app.post("/api/sessions")
async def create_session(session_data: SessionCreate, user_id: str = Query(..., description="User ID is required")):
    """Create new session and associate with user"""
    waha_session_created = False
    waha_session_name = None
    
    try:
        # Check subscription limits
        if user_id:
            from database.user_sessions import UserWhatsAppSession
            from database.subscription_models import UserSubscription
            from database.connection import get_db
            
            with get_db() as db:
                # Get user subscription
                user_subscription = db.query(UserSubscription).filter(
                    UserSubscription.user_id == user_id
                ).first()
                
                if not user_subscription:
                    raise HTTPException(
                        status_code=403,
                        detail="No subscription found. Please subscribe to create sessions."
                    )
                
                # Count existing active sessions for this user
                existing_sessions = db.query(UserWhatsAppSession).filter(
                    UserWhatsAppSession.user_id == user_id,
                    UserWhatsAppSession.status.in_(["created", "started", "scan", "active"])
                ).count()
                
                # Check if user has reached session limit
                if existing_sessions >= user_subscription.max_sessions:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Session limit reached. Your {user_subscription.plan_type.value} plan allows {user_subscription.max_sessions} session(s). Please upgrade your plan or remove existing sessions."
                    )
                
                # Check if session name already exists for THIS USER (not globally)
                existing_name = db.query(UserWhatsAppSession).filter(
                    UserWhatsAppSession.user_id == user_id,
                    UserWhatsAppSession.session_name == session_data.name
                ).first()
                
                if existing_name:
                    # Get all existing session names for better error message
                    all_sessions = db.query(UserWhatsAppSession.session_name).filter(
                        UserWhatsAppSession.user_id == user_id
                    ).all()
                    existing_names = [s[0] for s in all_sessions]
                    raise HTTPException(
                        status_code=400,
                        detail=f"Session name '{session_data.name}' already exists for your account. Please choose a different name. Your existing sessions: {', '.join(existing_names)}"
                    )
                
                # Generate unique WAHA session name
                import uuid
                import re
                # Create a safe WAHA session name: user_id prefix + uuid
                # This ensures uniqueness and avoids naming conflicts
                waha_session_name = f"u{user_id[:8]}_{uuid.uuid4().hex[:8]}"
                
                logger.info(f"Creating WAHA session with UUID name: {waha_session_name} (display name: {session_data.name})")
                
                # Create user session record FIRST (before WAHA) but don't commit yet
                user_session = UserWhatsAppSession(
                    user_id=user_id,
                    session_name=session_data.name,  # User's chosen display name
                    waha_session_name=waha_session_name,  # Actual WAHA session name
                    display_name=session_data.name,  # Also store as display name
                    status="created",
                    is_primary=(existing_sessions == 0)  # First session is primary
                )
                
                # Add to database (but don't commit yet)
                db.add(user_session)
                
                try:
                    # Get WAHA instance URL based on user's plan
                    from waha_pool_manager import waha_pool
                    waha_instance_url = waha_pool.get_or_create_instance_for_user(user_id, waha_session_name)
                    
                    # Create WAHA client for this specific instance
                    from waha_functions import WAHAClient
                    waha_instance = WAHAClient(base_url=waha_instance_url)
                    
                    # Create session in WAHA with generated name
                    result = waha_instance.create_session(waha_session_name, session_data.config)
                    waha_session_created = True
                    
                    # Save WAHA instance URL to session record
                    user_session.waha_instance_url = waha_instance_url
                    waha_pool.save_session_assignment(user_id, waha_session_name, waha_instance_url)
                    
                    # Start the session immediately so it appears in the list
                    try:
                        waha_instance.start_session(waha_session_name)
                        logger.info(f"Started session {waha_session_name} after creation")
                        user_session.status = "started"
                    except Exception as e:
                        logger.warning(f"Could not auto-start session {waha_session_name}: {e}")
                    
                    # Update current sessions counter only after WAHA creation succeeds
                    user_subscription.current_sessions = existing_sessions + 1
                    
                    # Commit to database only after WAHA session is created successfully
                    db.commit()
                    
                    # Add the display name to the result for frontend
                    result['display_name'] = session_data.name
                    
                    logger.info(f"Session {session_data.name} created for user {user_id} ({existing_sessions + 1}/{user_subscription.max_sessions})")
                    
                    return {"success": True, "data": result}
                    
                except Exception as waha_error:
                    # If WAHA creation fails, rollback database changes
                    db.rollback()
                    logger.error(f"Failed to create WAHA session: {waha_error}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create WhatsApp session: {str(waha_error)}"
                    )
        
        return {"success": False, "error": "User ID is required"}
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # If we created a WAHA session but database failed, clean it up
        if waha_session_created and waha_session_name:
            try:
                logger.warning(f"Cleaning up orphaned WAHA session {waha_session_name}")
                # Use the instance-specific client if available
                if 'waha_instance' in locals():
                    waha_instance.delete_session(waha_session_name)
                else:
                    waha.delete_session(waha_session_name)
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up orphaned session {waha_session_name}: {cleanup_error}")
        
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_name}")
async def get_session_info(session_name: str, user_id: str = Query(..., description="User ID is required")):
    """Get session information"""
    try:
        # Get the actual WAHA session name
        actual_session_name = get_waha_session_name(session_name, user_id)
        
        # Get the correct WAHA client for this session
        waha_client = get_waha_client_for_session(user_id, session_name)
        info = waha_client.get_session_info(actual_session_name)
        # Add display name to response
        info['display_name'] = session_name
        return {"success": True, "data": info}
    except Exception as e:
        logger.error(f"Error getting session info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_name}/start")
async def start_session(session_name: str, user_id: str = Query(..., description="User ID is required")):
    """Start session"""
    try:
        actual_session_name = get_waha_session_name(session_name, user_id)
        # Get the correct WAHA client for this session
        waha_client = get_waha_client_for_session(user_id, session_name)
        result = waha_client.start_session(actual_session_name)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error starting session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_name}/stop")
async def stop_session(session_name: str, user_id: str = Query(..., description="User ID is required")):
    """Stop session"""
    try:
        actual_session_name = get_waha_session_name(session_name, user_id)
        # Get the correct WAHA client for this session
        waha_client = get_waha_client_for_session(user_id, session_name)
        result = waha_client.stop_session(actual_session_name)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error stopping session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_name}/restart")
async def restart_session(session_name: str, user_id: str = Query(..., description="User ID is required")):
    """Restart session"""
    try:
        actual_session_name = get_waha_session_name(session_name, user_id)
        result = waha.restart_session(actual_session_name)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error restarting session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_name}/logout")
async def logout_session(session_name: str, user_id: str = Query(..., description="User ID is required")):
    """Logout from WhatsApp (disconnect but keep session)"""
    try:
        actual_session_name = get_waha_session_name(session_name, user_id)
        result = waha.logout_session(actual_session_name)
        
        # Update session status in database
        from database.user_sessions import UserWhatsAppSession
        from database.connection import get_db
        
        with get_db() as db:
            user_session = db.query(UserWhatsAppSession).filter(
                UserWhatsAppSession.user_id == user_id,
                UserWhatsAppSession.session_name == session_name
            ).first()
            
            if user_session:
                user_session.status = "logged_out"
                db.commit()
        
        return {"success": True, "message": f"Logged out from WhatsApp", "data": result}
    except Exception as e:
        logger.error(f"Error logging out session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_name}/auth/request-code")
async def request_pairing_code(session_name: str, auth_data: dict, user_id: str = Query(..., description="User ID is required")):
    """Request pairing code for WhatsApp login - the code will be displayed for user to enter in WhatsApp"""
    try:
        actual_session_name = get_waha_session_name(session_name, user_id)
        phone_number = auth_data.get('phoneNumber', '')
        
        # Clean phone number - remove all non-digits and plus sign
        if phone_number:
            # Remove +, spaces, dashes, parentheses
            phone_number = ''.join(filter(str.isdigit, phone_number))
            # WAHA expects just digits, no plus sign
            # Example: 17024215458 not +17024215458
        
        logger.info(f"Requesting pairing code for session {actual_session_name} with phone {phone_number}")
        
        # Request pairing code from WAHA
        result = waha.request_pairing_code(actual_session_name, phone_number)
        
        if result:
            # Extract the pairing code from the response
            pairing_code = result.get('code', '')
            if pairing_code:
                logger.info(f"Pairing code generated successfully: {pairing_code}")
                return {
                    "success": True, 
                    "message": "Pairing code generated. Enter this code in WhatsApp on your phone.",
                    "code": pairing_code,
                    "phoneNumber": phone_number,
                    "data": result
                }
            else:
                logger.error(f"No pairing code in response: {result}")
                return {"success": False, "error": "Failed to generate pairing code - no code returned"}
        else:
            logger.error("Failed to request pairing code - no result")
            return {"success": False, "error": "Failed to request pairing code"}
    except Exception as e:
        logger.error(f"Error requesting pairing code: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_name}")
async def delete_session(session_name: str, user_id: str = Query(..., description="User ID is required")):
    """Delete session and update user's session counter"""
    try:
        # Get the actual WAHA session name
        actual_session_name = get_waha_session_name(session_name, user_id)
        
        # Delete from WAHA
        result = waha.delete_session(actual_session_name)
        
        # Update user's session counter if user_id provided
        if user_id:
            from database.user_sessions import UserWhatsAppSession
            from database.subscription_models import UserSubscription
            from database.connection import get_db
            
            with get_db() as db:
                # Delete user session record
                user_session = db.query(UserWhatsAppSession).filter(
                    UserWhatsAppSession.user_id == user_id,
                    UserWhatsAppSession.session_name == session_name
                ).first()
                
                if user_session:
                    db.delete(user_session)
                    
                    # Update subscription session counter
                    user_subscription = db.query(UserSubscription).filter(
                        UserSubscription.user_id == user_id
                    ).first()
                    
                    if user_subscription:
                        # Recount active sessions
                        active_sessions = db.query(UserWhatsAppSession).filter(
                            UserWhatsAppSession.user_id == user_id,
                            UserWhatsAppSession.status.in_(["created", "started", "scan", "active"])
                        ).count()
                        
                        user_subscription.current_sessions = active_sessions
                        logger.info(f"Session {session_name} deleted for user {user_id}. Active sessions: {active_sessions}/{user_subscription.max_sessions}")
                    
                    db.commit()
        else:
            # Try to find and delete by session name only (backward compatibility)
            from database.user_sessions import UserWhatsAppSession
            from database.connection import get_db
            
            with get_db() as db:
                user_session = db.query(UserWhatsAppSession).filter(
                    UserWhatsAppSession.session_name == session_name
                ).first()
                
                if user_session:
                    user_id = user_session.user_id
                    db.delete(user_session)
                    
                    # Update subscription counter
                    from database.subscription_models import UserSubscription
                    user_subscription = db.query(UserSubscription).filter(
                        UserSubscription.user_id == user_id
                    ).first()
                    
                    if user_subscription:
                        active_sessions = db.query(UserWhatsAppSession).filter(
                            UserWhatsAppSession.user_id == user_id,
                            UserWhatsAppSession.status.in_(["created", "started", "scan", "active"])
                        ).count()
                        user_subscription.current_sessions = active_sessions
                    
                    db.commit()
                    logger.info(f"Session {session_name} deleted (found user {user_id})")
        
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== AUTHENTICATION ====================

@app.get("/api/sessions/{session_name}/qr")
async def get_qr_code(session_name: str, user_id: str = Query(..., description="User ID is required")):
    """Get QR code image"""
    try:
        actual_session_name = get_waha_session_name(session_name, user_id)
        # Get the correct WAHA client for this session
        waha_client = get_waha_client_for_session(user_id, session_name)
        qr_image = waha_client.get_qr_code(actual_session_name)
        return Response(content=qr_image, media_type="image/png")
    except Exception as e:
        logger.error(f"Error getting QR code: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_name}/screenshot")
async def get_screenshot(session_name: str, user_id: str = Query(..., description="User ID is required")):
    """Get screenshot"""
    try:
        # Get the actual WAHA session name from display name
        actual_session_name = get_waha_session_name(session_name, user_id)
        logger.info(f"Screenshot request - Display: {session_name}, UUID: {actual_session_name}, User: {user_id}")
        screenshot = waha.get_screenshot(actual_session_name)
        return Response(content=screenshot, media_type="image/png")
    except Exception as e:
        logger.error(f"Error getting screenshot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== MESSAGING ====================

@app.post("/api/messages/text")
async def send_text_message(message: MessageSend):
    """Send text message"""
    try:
        result = waha.send_text(message.session, message.chatId, message.text)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error sending text message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/messages/file")
async def send_file_message(
    file: UploadFile = File(...),
    chatId: str = Form(...),
    session: str = Form(...),
    caption: str = Form("")
):
    """Send file message"""
    try:
        # Read file content
        file_content = await file.read()
        file_data = {
            "mimetype": file.content_type,
            "filename": file.filename,
            "data": base64.b64encode(file_content).decode('utf-8')
        }
        
        # Determine file type and send accordingly
        if file.content_type.startswith('image/'):
            result = waha.send_image(session, chatId, file_data, caption)
        elif file.content_type.startswith('video/'):
            result = waha.send_video(session, chatId, file_data, caption)
        elif file.content_type.startswith('audio/'):
            result = waha.send_voice(session, chatId, file_data)
        else:
            result = waha.send_file(session, chatId, file_data)
        
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error sending file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/messages/location")
async def send_location_message(location: LocationMessage):
    """Send location message"""
    try:
        result = waha.send_location(
            location.session, 
            location.chatId, 
            location.latitude, 
            location.longitude, 
            location.title
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error sending location: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/messages/{session}/{chat_id}/typing/start")
async def start_typing(session: str, chat_id: str):
    """Start typing indicator"""
    try:
        result = waha.start_typing(session, chat_id)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error starting typing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/messages/{session}/{chat_id}/typing/stop")
async def stop_typing(session: str, chat_id: str):
    """Stop typing indicator"""
    try:
        result = waha.stop_typing(session, chat_id)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error stopping typing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== CHATS ====================

@app.get("/api/chats/{session}")
async def get_chats(session: str):
    """Get all chats"""
    try:
        chats = waha.get_chats(session)
        return {"success": True, "data": chats}
    except Exception as e:
        logger.error(f"Error getting chats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chats/{session}/{chat_id}/messages")
async def get_chat_messages(session: str, chat_id: str, limit: int = 50):
    """Get chat messages"""
    try:
        messages = waha.get_chat_messages(session, chat_id, limit)
        return {"success": True, "data": messages}
    except Exception as e:
        logger.error(f"Error getting chat messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chats/{session}/{chat_id}/read")
async def mark_chat_as_read(session: str, chat_id: str):
    """Mark chat as read"""
    try:
        result = waha.mark_chat_as_read(session, chat_id)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error marking chat as read: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/chats/{session}/{chat_id}")
async def delete_chat(session: str, chat_id: str):
    """Delete chat"""
    try:
        result = waha.delete_chat(session, chat_id)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error deleting chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chats/{session}/{chat_id}/archive")
async def archive_chat(session: str, chat_id: str):
    """Archive chat"""
    try:
        result = waha.archive_chat(session, chat_id)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error archiving chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== CONTACTS ====================

@app.get("/api/contacts/{session}")
async def get_all_contacts(session: str, user_id: str = Query(..., description="User ID is required")):
    """Get all contacts"""
    try:
        # Get the actual WAHA session name from display name
        actual_session_name = get_waha_session_name(session, user_id)
        contacts = waha.get_all_contacts(actual_session_name)
        return {"success": True, "data": contacts}
    except Exception as e:
        logger.error(f"Error getting contacts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contacts/{session}/export")
async def export_contacts(session: str, user_id: str = Query(..., description="User ID is required")):
    """Export all contacts with same 16-column format as group exports"""
    try:
        # Get the actual WAHA session name from display name
        actual_session_name = get_waha_session_name(session, user_id)
        # Get user subscription to check limits
        from database.subscription_models import UserSubscription, PlanType
        from database.connection import get_db
        
        # Store subscription data we need before closing session
        user_plan = None
        max_contacts_export = -1
        contacts_exported_this_month = 0
        
        if user_id:
            with get_db() as db:
                user_subscription = db.query(UserSubscription).filter(
                    UserSubscription.user_id == user_id
                ).first()
                
                if user_subscription:
                    user_plan = user_subscription.plan_type
                    max_contacts_export = user_subscription.max_contacts_export
                    contacts_exported_this_month = user_subscription.contacts_exported_this_month
        
        # Get all contacts from WAHA API
        contacts = waha.get_all_contacts(actual_session_name)
        original_count = len(contacts)
        limited = False
        limit_message = ""
        
        # Apply export limits if user has subscription
        if user_plan:
            # Check if user has reached monthly limit
            remaining = max_contacts_export - contacts_exported_this_month if max_contacts_export > 0 else float('inf')
            
            if max_contacts_export > 0:  # Has a limit (not unlimited)
                if remaining <= 0:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Monthly export limit reached ({max_contacts_export} contacts). Please upgrade your plan to export more."
                    )
                
                # Limit contacts if exceeds remaining quota
                if len(contacts) > remaining:
                    limited = True
                    excluded_count = len(contacts) - int(remaining)
                    contacts = contacts[:int(remaining)]
                    limit_message = f"Export limited to {int(remaining)} contacts. {excluded_count} contacts excluded due to plan limit."
                    
                    # For free users, show upgrade prompt in the exported file
                    if user_plan == PlanType.FREE:
                        # Add a placeholder contact to show upgrade message
                        contacts.append({
                            'id': 'upgrade_prompt',
                            'number': '000000000',
                            'name': f'⚠️ UPGRADE REQUIRED: {excluded_count} more contacts available',
                            'pushname': 'Upgrade to STARTER plan or higher to export all contacts',
                            'isMyContact': False,
                            'isGroup': False
                        })
            
            # Update usage counter in a new database session
            if user_id:
                with get_db() as db:
                    user_sub = db.query(UserSubscription).filter(
                        UserSubscription.user_id == user_id
                    ).first()
                    
                    if user_sub:
                        export_count = len(contacts) - (1 if limited and user_plan == PlanType.FREE else 0)
                        user_sub.contacts_exported_this_month += export_count
                        db.commit()
                        logger.info(f"User {user_id} exported {export_count} contacts. Monthly total: {user_sub.contacts_exported_this_month}")
        
        # Import contact export handler
        from utils.contact_export_handler import ContactExportHandler
        export_handler = ContactExportHandler()
        
        # Export to all formats (JSON, Excel, CSV)
        export_result = export_handler.export_contacts(
            contacts=contacts,
            session_name=session
        )
        
        # Add limit info to response
        export_result['limited'] = limited
        export_result['original_count'] = original_count
        if limited:
            export_result['limit_message'] = limit_message
        
        return {
            "success": True,
            "data": export_result,
            "message": f"Exported {export_result['contact_count']} contacts" + (f" (Limited from {original_count})" if limited else "")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting contacts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contacts/{session}/check/{phone}")
async def check_number_exists(session: str, phone: str, user_id: str = Query(..., description="User ID is required")):
    """Check if number exists on WhatsApp"""
    try:
        # Get the actual WAHA session name from display name
        actual_session_name = get_waha_session_name(session, user_id)
        result = waha.check_number_exists(actual_session_name, phone)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error checking number: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/contacts/block")
async def block_contact(contact_action: ContactAction):
    """Block contact"""
    try:
        # Get the actual WAHA session name from display name
        actual_session_name = get_waha_session_name(contact_action.session, contact_action.user_id)
        result = waha.block_contact(actual_session_name, contact_action.contactId)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error blocking contact: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/contacts/unblock")
async def unblock_contact(contact_action: ContactAction):
    """Unblock contact"""
    try:
        # Get the actual WAHA session name from display name
        actual_session_name = get_waha_session_name(contact_action.session, contact_action.user_id)
        result = waha.unblock_contact(actual_session_name, contact_action.contactId)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error unblocking contact: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== GROUPS ====================

@app.get("/api/groups/{session}")
async def get_groups(session: str, user_id: str = Query(..., description="User ID is required"), lightweight: bool = True):
    """Get all groups - lightweight by default (no participants)"""
    try:
        # Get the actual WAHA session name from display name
        actual_session_name = get_waha_session_name(session, user_id)
        groups = waha.get_groups(actual_session_name)
        
        if lightweight:
            # Return only essential group info without participants
            lightweight_groups = []
            for group in groups:
                lightweight_groups.append({
                    "id": group.get("id"),
                    "name": group.get("name") or group.get("groupMetadata", {}).get("subject", "Unnamed Group"),
                    "isGroup": group.get("isGroup", True),
                    "timestamp": group.get("timestamp"),
                    # Don't include participants or other heavy metadata
                })
            return {"success": True, "data": lightweight_groups, "lightweight": True}
        else:
            # Return full group data (old behavior)
            return {"success": True, "data": groups, "lightweight": False}
    except Exception as e:
        logger.error(f"Error getting groups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/groups/{session}/for-campaign")
async def get_groups_for_campaign(session: str, user_id: str = Query(..., description="User ID is required")):
    """Get groups formatted for campaign source selection"""
    try:
        # Get the actual WAHA session name from display name
        actual_session_name = get_waha_session_name(session, user_id)
        groups = waha.get_groups(actual_session_name)
        
        # Format for campaign selection UI
        campaign_groups = []
        for group in groups:
            # Handle group ID - it might be a string or an object
            group_id_obj = group.get("id", "")
            if isinstance(group_id_obj, dict):
                # Extract the serialized ID from the object
                group_id = group_id_obj.get("_serialized", "") or f"{group_id_obj.get('user', '')}@{group_id_obj.get('server', '')}"
            else:
                group_id = str(group_id_obj)
            
            group_name = group.get("name") or group.get("groupMetadata", {}).get("subject", "Unnamed Group")
            
            # Get participant count if available
            participant_count = 0
            if "groupMetadata" in group and "participants" in group["groupMetadata"]:
                participant_count = len(group["groupMetadata"]["participants"])
            
            campaign_groups.append({
                "id": group_id,
                "name": group_name,
                "participantCount": participant_count,
                "display_name": f"{group_name} ({participant_count} members)" if participant_count else group_name
            })
        
        return {"success": True, "groups": campaign_groups}
    except Exception as e:
        logger.error(f"Error getting groups for campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contacts/{session}/for-campaign")
async def get_contacts_for_campaign(session: str, user_id: str = Query(..., description="User ID is required")):
    """Get contacts for campaign source selection with checkboxes"""
    try:
        # Get the actual WAHA session name from display name
        actual_session_name = get_waha_session_name(session, user_id)
        contacts = waha.get_all_contacts(actual_session_name)
        
        # Filter and format contacts
        campaign_contacts = []
        my_contacts_count = 0
        
        for contact in contacts:
            # Skip groups and @lid contacts
            if contact.get('isGroup', False) or '@g.us' in str(contact.get('id', '')):
                continue
            if '@lid' in str(contact.get('id', '')):
                continue
            
            # Get clean phone number
            phone = contact.get('number', '')
            if not phone:
                continue
                
            # Format contact for UI
            name = contact.get('name') or contact.get('pushname', '')
            is_my_contact = contact.get('isMyContact', False)
            
            if is_my_contact:
                my_contacts_count += 1
            
            campaign_contacts.append({
                "id": contact.get('id', ''),
                "number": phone,
                "name": name,
                "display_name": f"{name} (+{phone})" if name else f"+{phone}",
                "isMyContact": is_my_contact,
                "isBusiness": contact.get('isBusiness', False)
            })
        
        return {
            "success": True,
            "contacts": campaign_contacts,
            "summary": {
                "total_contacts": len(campaign_contacts),
                "my_contacts_count": my_contacts_count,
                "other_contacts_count": len(campaign_contacts) - my_contacts_count
            }
        }
    except Exception as e:
        logger.error(f"Error getting contacts for campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/groups/{session}")
async def create_group(session: str, group_data: GroupCreate, user_id: str = Query(..., description="User ID is required")):
    """Create group"""
    try:
        # Get the actual WAHA session name from display name
        actual_session_name = get_waha_session_name(session, user_id)
        result = waha.create_group(actual_session_name, group_data.name, group_data.participants)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error creating group: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/groups/{session}/{group_id}")
async def get_group_info(session: str, group_id: str, user_id: str = Query(..., description="User ID is required")):
    """Get group info"""
    try:
        # Get the actual WAHA session name from display name
        actual_session_name = get_waha_session_name(session, user_id)
        info = waha.get_group_info(actual_session_name, group_id)
        return {"success": True, "data": info}
    except Exception as e:
        logger.error(f"Error getting group info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/groups/{session}/{group_id}/leave")
async def leave_group(session: str, group_id: str, user_id: str = Query(..., description="User ID is required")):
    """Leave group"""
    try:
        # Get the actual WAHA session name from display name
        actual_session_name = get_waha_session_name(session, user_id)
        result = waha.leave_group(actual_session_name, group_id)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error leaving group: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/groups/{session}/{group_id}/export")
async def export_group_participants(session: str, group_id: str, user_id: str = Query(..., description="User ID is required")):
    """Export group participants with detailed contact information"""
    try:
        # Get the actual WAHA session name from display name
        actual_session_name = get_waha_session_name(session, user_id)
        
        # Handle URL encoding - group_id might come URL encoded
        import urllib.parse
        group_id = urllib.parse.unquote(group_id)
        
        # Get user subscription to check limits
        from database.subscription_models import UserSubscription, PlanType
        from database.connection import get_db
        
        # Store subscription data we need before closing session
        user_plan = None
        max_contacts_export = -1
        contacts_exported_this_month = 0
        
        if user_id:
            with get_db() as db:
                user_subscription = db.query(UserSubscription).filter(
                    UserSubscription.user_id == user_id
                ).first()
                
                if user_subscription:
                    user_plan = user_subscription.plan_type
                    max_contacts_export = user_subscription.max_contacts_export
                    contacts_exported_this_month = user_subscription.contacts_exported_this_month
        
        # Get group info first
        group_info = waha.get_group_info(actual_session_name, group_id)
        
        # Extract group name from the correct location in WAHA response
        if isinstance(group_info, dict):
            if 'groupMetadata' in group_info and 'subject' in group_info['groupMetadata']:
                group_name = group_info['groupMetadata']['subject']
            elif 'name' in group_info:
                group_name = group_info['name']
            else:
                group_name = 'Unknown Group'
        else:
            group_name = 'Unknown Group'
        
        # Get detailed participant information
        participants = waha.get_group_participants_details(actual_session_name, group_id)
        original_count = len(participants)
        limited = False
        limit_message = ""
        
        # Apply export limits if user has subscription
        if user_plan:
            # Check if user has reached monthly limit
            remaining = max_contacts_export - contacts_exported_this_month if max_contacts_export > 0 else float('inf')
            
            if max_contacts_export > 0:  # Has a limit (not unlimited)
                if remaining <= 0:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Monthly export limit reached ({max_contacts_export} contacts). Please upgrade your plan to export more."
                    )
                
                # Limit participants if exceeds remaining quota
                if len(participants) > remaining:
                    limited = True
                    excluded_count = len(participants) - int(remaining)
                    participants = participants[:int(remaining)]
                    limit_message = f"Export limited to {int(remaining)} participants. {excluded_count} participants excluded due to plan limit."
                    
                    # For free users, show upgrade prompt
                    if user_plan == PlanType.FREE:
                        # Add a placeholder participant to show upgrade message
                        participants.append({
                            'id': '000000000@c.us',
                            'number': '000000000',
                            'name': f'⚠️ UPGRADE REQUIRED: {excluded_count} more participants available',
                            'pushname': 'Upgrade to STARTER plan or higher to export all participants',
                            'isAdmin': False,
                            'isSuperAdmin': False
                        })
            
            # Update usage counter in a new database session
            if user_id:
                with get_db() as db:
                    user_sub = db.query(UserSubscription).filter(
                        UserSubscription.user_id == user_id
                    ).first()
                    
                    if user_sub:
                        export_count = len(participants) - (1 if limited and user_plan == PlanType.FREE else 0)
                        user_sub.contacts_exported_this_month += export_count
                        db.commit()
                        logger.info(f"User {user_id} exported {export_count} group participants. Monthly total: {user_sub.contacts_exported_this_month}")
        
        # Import export handler
        from utils.export_handler import GroupExportHandler
        export_handler = GroupExportHandler()
        
        # Export to both formats
        export_result = export_handler.export_group_participants(
            participants=participants,
            group_name=group_name,
            session_name=session
        )
        
        # Add limit info to response
        export_result['limited'] = limited
        export_result['original_count'] = original_count
        if limited:
            export_result['limit_message'] = limit_message
        
        return {
            "success": True,
            "data": export_result,
            "message": f"Exported {export_result['participant_count']} participants" + (f" (Limited from {original_count})" if limited else "")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting group participants: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== SERVER INFO ====================

@app.get("/api/server/info")
async def get_server_info():
    """Get server information"""
    try:
        version = waha.get_server_version()
        status = waha.get_server_status()
        return {
            "success": True, 
            "data": {
                "version": version,
                "status": status
            }
        }
    except Exception as e:
        logger.error(f"Error getting server info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ping")
async def ping_server():
    """Ping WAHA server"""
    try:
        result = waha.ping_server()
        return {"success": True, "data": {"message": result}}
    except Exception as e:
        logger.error(f"Error pinging server: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== PHASE 2: CAMPAIGN MANAGEMENT ====================

if PHASE_2_ENABLED:
    
    @app.get("/api/campaigns")
    async def get_campaigns(user_id: str = Query(..., description="User ID is required")):
        """Get campaigns for a specific user"""
        try:
            from database.models import Campaign
            from database.connection import get_db
            from jobs.models import CampaignResponse
            
            with get_db() as db:
                # Get user's campaigns from database directly
                campaigns = db.query(Campaign).filter(
                        Campaign.user_id == user_id
                    ).order_by(Campaign.created_at.desc()).all()
                
                # Convert to response dictionaries
                campaign_responses = []
                for campaign in campaigns:
                    try:
                        # Get phone number for the session if available
                        session_phone = None
                        if campaign.session_name and user_id:
                            from database.user_sessions import UserWhatsAppSession
                            user_session = db.query(UserWhatsAppSession).filter(
                                UserWhatsAppSession.user_id == user_id,
                                UserWhatsAppSession.session_name == campaign.session_name
                            ).first()
                            if user_session and hasattr(user_session, 'phone_number'):
                                session_phone = user_session.phone_number
                        
                        # Format session display with phone number if available
                        session_display = campaign.session_name
                        if session_phone:
                            session_display = f"{campaign.session_name} / {session_phone}"
                        
                        # Build response dict with available fields
                        response_dict = {
                            "id": campaign.id,
                            "name": campaign.name,
                            "session_name": campaign.session_name,  # Keep original for operations
                            "session_display": session_display,  # Display name with phone
                            "status": campaign.status,
                            "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
                            "user_id": campaign.user_id,
                            "file_path": campaign.file_path,
                            "message_mode": campaign.message_mode if hasattr(campaign, 'message_mode') else 'single',
                            # Campaign statistics
                            "total_rows": campaign.total_rows if hasattr(campaign, 'total_rows') else 0,
                            "processed_rows": campaign.processed_rows if hasattr(campaign, 'processed_rows') else 0,
                            "success_count": campaign.success_count if hasattr(campaign, 'success_count') else 0,
                            "error_count": campaign.error_count if hasattr(campaign, 'error_count') else 0,
                            # Legacy fields for compatibility
                            "messages_sent": campaign.success_count if hasattr(campaign, 'success_count') else 0,
                            "messages_delivered": campaign.success_count if hasattr(campaign, 'success_count') else 0,
                            "messages_failed": campaign.error_count if hasattr(campaign, 'error_count') else 0,
                            "started_at": campaign.started_at.isoformat() if hasattr(campaign, 'started_at') and campaign.started_at else None,
                            "completed_at": campaign.completed_at.isoformat() if hasattr(campaign, 'completed_at') and campaign.completed_at else None,
                        }
                        
                        # Add optional fields if they exist
                        if hasattr(campaign, 'total_recipients'):
                            response_dict["total_recipients"] = campaign.total_recipients
                        if hasattr(campaign, 'delay_seconds'):
                            response_dict["delay_seconds"] = campaign.delay_seconds
                        if hasattr(campaign, 'column_mapping'):
                            response_dict["column_mapping"] = campaign.get_column_mapping() if hasattr(campaign, 'get_column_mapping') else {}
                        if hasattr(campaign, 'message_samples'):
                            response_dict["message_samples"] = campaign.get_message_samples() if hasattr(campaign, 'get_message_samples') else []
                        
                        campaign_responses.append(response_dict)
                    except Exception as e:
                        logger.error(f"Error converting campaign {campaign.id}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        continue
                
                return {"success": True, "data": campaign_responses}
        except Exception as e:
            logger.error(f"Error getting campaigns: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ==================== TEMPLATE GENERATION ====================
    
    @app.post("/api/generate-templates")
    async def generate_similar_templates(request: dict):
        """Generate similar message templates using LiteLLM/Ollama"""
        try:
            original_template = request.get("template", "")
            count = request.get("count", 3)  # Number of variations to generate
            
            if not original_template:
                raise HTTPException(status_code=400, detail="Template is required")
            
            # Import litellm
            try:
                from litellm import completion
            except ImportError:
                raise HTTPException(status_code=500, detail="LiteLLM not available")
            
            # Get LLM configuration from environment
            # Support both Groq and Ollama
            llm_provider = os.getenv("LLM_PROVIDER", "groq").lower()  # Default to groq
            
            if llm_provider == "groq":
                # Groq configuration
                model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")  # Fastest model
                api_key = os.getenv("GROQ_API_KEY", "")
                if not api_key:
                    raise HTTPException(status_code=500, detail="GROQ_API_KEY not set in environment")
                model_string = f"groq/{model}"
            else:
                # Ollama configuration (fallback)
                model = os.getenv("OLLAMA_MODEL", "gemma3:1b")
                api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
                model_string = f"ollama/{model}"
            
            # Create prompt for generating variations
            prompt = f"""Generate {count} variations of this WhatsApp message template. 
Keep the same tone and purpose, but vary the wording and emojis.
Use placeholder {{name}} for personalization where appropriate.
Make each variation unique but maintaining the core message.

Original template:
{original_template}

Generate exactly {count} variations, one per line:"""
            
            # Generate variations using LiteLLM
            if llm_provider == "groq":
                response = completion(
                    model=model_string,
                    messages=[{"role": "user", "content": prompt}],
                    api_key=api_key,
                    temperature=0.8,
                    max_tokens=500
                )
            else:
                response = completion(
                    model=model_string,
                    messages=[{"role": "user", "content": prompt}],
                    api_base=api_base,
                    temperature=0.8,
                    max_tokens=500
                )
            
            # Parse the response
            generated_text = response.choices[0].message.content.strip()
            variations = [line.strip() for line in generated_text.split('\n') if line.strip()]
            
            # Clean up variations (remove numbering if present)
            cleaned_variations = []
            for var in variations[:count]:
                # Remove common numbering patterns like "1.", "1)", "1:"
                import re
                cleaned = re.sub(r'^[\d]+[\.\)\:]?\s*', '', var)
                if cleaned and cleaned != original_template:
                    cleaned_variations.append(cleaned)
            
            return {
                "success": True,
                "variations": cleaned_variations,
                "model_used": model_string,
                "provider": llm_provider
            }
            
        except Exception as e:
            logger.error(f"Error generating templates: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/campaigns")
    async def create_campaign(campaign_data: CampaignCreate, user_id: str = Query(..., description="User ID is required")):
        """Create new campaign"""
        try:
            # Add user_id to campaign data
            if user_id:
                campaign_data.user_id = user_id
            
            # Check if the session_name is actually a WAHA UUID
            if campaign_data.session_name and campaign_data.session_name.startswith('uuser_'):
                # It's a WAHA UUID, we need to find the display name
                from database.user_sessions import UserWhatsAppSession
                from database.connection import get_db
                
                with get_db() as db:
                    user_session = db.query(UserWhatsAppSession).filter(
                        UserWhatsAppSession.user_id == user_id,
                        UserWhatsAppSession.waha_session_name == campaign_data.session_name
                    ).first()
                    
                    if user_session:
                        # Found the session, use its display name
                        display_name = user_session.session_name
                        actual_session_name = campaign_data.session_name  # The UUID
                        
                        # Fetch phone number if not already saved and session is WORKING
                        if not user_session.phone_number:
                            try:
                                session_info = waha.get_session_info(actual_session_name)
                                if session_info.get('status') == 'WORKING' and session_info.get('me'):
                                    # Extract phone number from me.id field
                                    me_id = session_info['me'].get('id', '')
                                    if me_id.endswith('@c.us'):
                                        phone_number = me_id.replace('@c.us', '')
                                        user_session.phone_number = phone_number
                                        user_session.status = 'WORKING'
                                        db.commit()
                                        logger.info(f"Updated session {display_name} with phone number: {phone_number}")
                            except Exception as e:
                                logger.warning(f"Could not fetch phone number: {str(e)}")
                    else:
                        # UUID not found in database, use it as both
                        display_name = campaign_data.session_name
                        actual_session_name = campaign_data.session_name
            else:
                # It's a display name, convert to WAHA
                display_name = campaign_data.session_name
                actual_session_name = get_waha_session_name(campaign_data.session_name, user_id)
                
                # Fetch phone number for this session too
                if user_id:
                    from database.user_sessions import UserWhatsAppSession
                    from database.connection import get_db
                    
                    with get_db() as db:
                        user_session = db.query(UserWhatsAppSession).filter(
                            UserWhatsAppSession.user_id == user_id,
                            UserWhatsAppSession.waha_session_name == actual_session_name
                        ).first()
                        
                        if user_session and not user_session.phone_number:
                            try:
                                session_info = waha.get_session_info(actual_session_name)
                                if session_info.get('status') == 'WORKING' and session_info.get('me'):
                                    # Extract phone number from me.id field
                                    me_id = session_info['me'].get('id', '')
                                    if me_id.endswith('@c.us'):
                                        phone_number = me_id.replace('@c.us', '')
                                        user_session.phone_number = phone_number
                                        user_session.status = 'WORKING'
                                        db.commit()
                                        logger.info(f"Updated session {display_name} with phone number: {phone_number}")
                            except Exception as e:
                                logger.warning(f"Could not fetch phone number: {str(e)}")
            
            # Store both names
            campaign_data.waha_session_name = actual_session_name
            campaign_data.session_name = display_name
            
            campaign = campaign_manager.create_campaign(campaign_data)
            return {"success": True, "data": campaign.dict()}
        except Exception as e:
            logger.error(f"Error creating campaign: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/campaigns/create-with-source")
    async def create_campaign_with_source(campaign_data: dict):
        """Create campaign with flexible source (CSV, Groups, or Contacts)"""
        try:
            from jobs.campaign_sources import CampaignSourceCreate, SourceType
            from jobs.source_processor import SourceProcessor
            import asyncio
            
            # Extract start/end row if provided (for contacts and group participants)
            start_row = campaign_data.get('start_row', 1)
            end_row = campaign_data.get('end_row', None)
            
            # Get user_id if provided
            user_id = campaign_data.get('user_id')
            
            # Extract scheduling fields if provided
            scheduled_start_time = campaign_data.get('scheduled_start_time')
            is_scheduled = campaign_data.get('is_scheduled', False)
            
            # Parse scheduled_start_time if it's a string
            if scheduled_start_time and isinstance(scheduled_start_time, str):
                from datetime import datetime
                scheduled_start_time = datetime.fromisoformat(scheduled_start_time.replace('Z', '+00:00'))
            
            # Parse the campaign data with source
            source_campaign = CampaignSourceCreate(**campaign_data)
            
            # Store the display name and convert to WAHA session name
            display_name = source_campaign.session_name
            actual_session_name = get_waha_session_name(display_name, user_id)
            logger.info(f"Converting session name: '{display_name}' -> '{actual_session_name}' for user '{user_id}'")
            
            # Fetch and save phone number if session is WORKING
            if user_id:
                from database.user_sessions import UserWhatsAppSession
                from database.connection import get_db
                
                with get_db() as db:
                    user_session = db.query(UserWhatsAppSession).filter(
                        UserWhatsAppSession.user_id == user_id,
                        UserWhatsAppSession.waha_session_name == actual_session_name
                    ).first()
                    
                    if user_session and not user_session.phone_number:
                        try:
                            # Check session status first
                            session_info = waha.get_session_info(actual_session_name)
                            if session_info.get('status') == 'WORKING' and session_info.get('me'):
                                # Extract phone number from me.id field
                                me_id = session_info['me'].get('id', '')
                                if me_id.endswith('@c.us'):
                                    phone_number = me_id.replace('@c.us', '')
                                    user_session.phone_number = phone_number
                                    user_session.status = 'WORKING'
                                    db.commit()
                                    logger.info(f"Updated session {display_name} with phone number: {phone_number}")
                        except Exception as fetch_error:
                            logger.warning(f"Could not fetch phone number for session {display_name}: {str(fetch_error)}")
            
            # Process the source to get contacts
            processor = SourceProcessor()
            contacts, metadata = await processor.process_source(
                source_campaign.source,
                actual_session_name  # Use actual WAHA session name
            )
            
            # Handle different source types
            if source_campaign.source.source_type == SourceType.CSV_UPLOAD:
                # Store source info in column_mapping as JSON string
                import json
                # Handle column_mapping whether it's a string or dict
                if source_campaign.source.column_mapping:
                    if isinstance(source_campaign.source.column_mapping, str):
                        base_mapping = json.loads(source_campaign.source.column_mapping)
                    else:
                        base_mapping = source_campaign.source.column_mapping
                else:
                    base_mapping = {}
                # Store source info as a JSON string in the mapping
                base_mapping['_source_info'] = json.dumps({
                    'source_type': 'csv_upload'
                })
                column_mapping_with_source = base_mapping
                
                # Use existing CSV campaign creation
                regular_campaign = CampaignCreate(
                    name=source_campaign.name,
                    session_name=display_name,  # Keep display name for UI
                    waha_session_name=actual_session_name,  # Store WAHA session name separately
                    file_path=source_campaign.source.file_path,
                    column_mapping=column_mapping_with_source,
                    start_row=source_campaign.source.start_row,
                    end_row=source_campaign.source.end_row,
                    message_mode=source_campaign.message_mode,
                    message_samples=source_campaign.message_samples,
                    use_csv_samples=source_campaign.use_csv_samples,
                    delay_seconds=source_campaign.delay_seconds,
                    retry_attempts=source_campaign.retry_attempts,
                    max_daily_messages=source_campaign.max_daily_messages,
                    exclude_my_contacts=source_campaign.exclude_my_contacts,
                    exclude_previous_conversations=source_campaign.exclude_previous_conversations,
                    save_contact_before_message=source_campaign.save_contact_before_message,
                    user_id=user_id,  # Add user_id
                    scheduled_start_time=scheduled_start_time,  # Add scheduling
                    is_scheduled=is_scheduled
                )
                campaign = campaign_manager.create_campaign(regular_campaign)
                
            else:
                # For groups and contacts, create a temporary CSV file
                import csv
                import tempfile
                
                # Apply start/end row limiting for contacts and group participants
                # But NOT for direct group messages
                from jobs.campaign_sources import WhatsAppGroupSource, GroupDeliveryMethod
                
                if isinstance(source_campaign.source, WhatsAppGroupSource) and \
                   source_campaign.source.delivery_method == GroupDeliveryMethod.GROUP_MESSAGE:
                    # For group messages, don't apply row limiting
                    filtered_contacts = contacts
                else:
                    # Apply start/end row for individual DMs and contacts
                    if start_row > 1:
                        filtered_contacts = contacts[start_row-1:]
                    else:
                        filtered_contacts = contacts
                    
                    if end_row:
                        filtered_contacts = filtered_contacts[:end_row-start_row+1]
                
                # Create temporary CSV file with all 16 columns (same as group export)
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, 
                                                        dir='static/uploads/campaigns')
                # Use the same 16 columns as group export
                fieldnames = [
                    'phone_number', 'formatted_phone', 'country_code', 'country_name',
                    'saved_name', 'public_name', 'is_my_contact', 'is_business', 
                    'is_blocked', 'is_admin', 'is_super_admin', 'labels',
                    'last_msg_text', 'last_msg_date', 'last_msg_type', 'last_msg_status'
                ]
                csv_writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
                csv_writer.writeheader()
                
                # Add source type to each contact with all 16 columns
                source_type_label = source_campaign.source.source_type.value
                for contact in filtered_contacts:
                    csv_writer.writerow({
                        'phone_number': contact.get('phone_number', '') or contact.get('formatted_phone', ''),
                        'formatted_phone': contact.get('formatted_phone', '') or contact.get('phone_number', ''),
                        'country_code': contact.get('country_code', ''),
                        'country_name': contact.get('country_name', ''),
                        'saved_name': contact.get('saved_name', '') or contact.get('name', ''),
                        'public_name': contact.get('public_name', ''),
                        'is_my_contact': contact.get('is_my_contact', 'false'),
                        'is_business': contact.get('is_business', 'false'),
                        'is_blocked': contact.get('is_blocked', 'false'),
                        'is_admin': contact.get('is_admin', 'false'),
                        'is_super_admin': contact.get('is_super_admin', 'false'),
                        'labels': contact.get('labels', ''),
                        'last_msg_text': contact.get('last_msg_text', ''),
                        'last_msg_date': contact.get('last_msg_date', ''),
                        'last_msg_type': contact.get('last_msg_type', ''),
                        'last_msg_status': contact.get('last_msg_status', '')
                    })
                
                temp_file.close()
                
                # Create campaign with the temporary CSV and store source info as JSON string
                import json
                column_mapping_with_source = {
                    'phone': 'phone_number', 
                    'name': 'name',
                    '_source_info': json.dumps({
                        'source_type': source_campaign.source.source_type.value if hasattr(source_campaign.source.source_type, 'value') else str(source_campaign.source.source_type),
                        'delivery_method': source_campaign.source.delivery_method.value if hasattr(source_campaign.source, 'delivery_method') and hasattr(source_campaign.source.delivery_method, 'value') else None,
                        'group_ids': source_campaign.source.group_ids if hasattr(source_campaign.source, 'group_ids') else [],
                        'contact_selection': source_campaign.source.contact_selection if hasattr(source_campaign.source, 'contact_selection') else None,
                        'filter_only_my_contacts': source_campaign.source.filter_only_my_contacts if hasattr(source_campaign.source, 'filter_only_my_contacts') else False
                    })
                }
                
                regular_campaign = CampaignCreate(
                    name=source_campaign.name,
                    session_name=display_name,  # Keep display name for UI
                    waha_session_name=actual_session_name,  # Store WAHA session name separately
                    file_path=temp_file.name,
                    column_mapping=column_mapping_with_source,
                    start_row=1,  # Always 1 since we already filtered
                    message_mode=source_campaign.message_mode,
                    message_samples=source_campaign.message_samples,
                    use_csv_samples=False,
                    delay_seconds=source_campaign.delay_seconds,
                    retry_attempts=source_campaign.retry_attempts,
                    max_daily_messages=source_campaign.max_daily_messages,
                    exclude_my_contacts=source_campaign.exclude_my_contacts,
                    exclude_previous_conversations=source_campaign.exclude_previous_conversations,
                    save_contact_before_message=source_campaign.save_contact_before_message,
                    user_id=user_id,  # Add user_id
                    scheduled_start_time=scheduled_start_time,  # Add scheduling
                    is_scheduled=is_scheduled
                )
                campaign = campaign_manager.create_campaign(regular_campaign)
            
            # Add source metadata to response
            campaign_dict = campaign.dict()
            campaign_dict['source_metadata'] = metadata
            
            return {"success": True, "data": campaign_dict}
            
        except Exception as e:
            logger.error(f"Error creating campaign with source: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/campaigns/stats")
    async def get_campaign_stats():
        """Get campaign statistics"""
        try:
            stats = campaign_manager.get_campaign_stats()
            return {"success": True, "data": stats.dict()}
        except Exception as e:
            logger.error(f"Error getting campaign stats: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/campaigns/{campaign_id}")
    async def get_campaign(campaign_id: int):
        """Get campaign by ID"""
        try:
            campaign = campaign_manager.get_campaign(campaign_id)
            if not campaign:
                raise HTTPException(status_code=404, detail="Campaign not found")
            return {"success": True, "data": campaign.dict()}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting campaign {campaign_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/campaigns/{campaign_id}/start")
    async def start_campaign(campaign_id: int, user_id: str = Query(..., description="User ID is required")):
        """Start campaign"""
        try:
            # Verify campaign belongs to user
            if user_id:
                from database.models import Campaign
                from database.connection import get_db
                
                with get_db() as db:
                    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                    if not campaign:
                        raise HTTPException(status_code=404, detail="Campaign not found")
                    if campaign.user_id != user_id:
                        raise HTTPException(status_code=403, detail="Access denied")
                    
                    # DISABLED: Warmer pausing - better to keep warmers running for natural activity
                    # from jobs.scheduler import CampaignScheduler
                    # scheduler = CampaignScheduler()
                    # await scheduler._pause_warmers_for_campaign(campaign)
                    logger.info(f"Starting campaign {campaign_id} - warmers will continue running (natural activity)")
            
            success = campaign_manager.start_campaign(campaign_id)
            if not success:
                raise HTTPException(status_code=404, detail="Campaign not found")
            return {"success": True, "message": "Campaign started"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error starting campaign {campaign_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/campaigns/{campaign_id}/pause")
    async def pause_campaign(campaign_id: int, user_id: str = Query(..., description="User ID is required")):
        """Pause campaign"""
        try:
            # Verify campaign belongs to user
            if user_id:
                from database.models import Campaign
                from database.connection import get_db
                
                with get_db() as db:
                    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                    if not campaign:
                        raise HTTPException(status_code=404, detail="Campaign not found")
                    if campaign.user_id != user_id:
                        raise HTTPException(status_code=403, detail="Access denied")
            # First stop the processor if campaign is running
            from jobs.processor import message_processor
            await message_processor.stop_campaign_processing(campaign_id)
            
            # Then update campaign status to paused
            success = campaign_manager.pause_campaign(campaign_id)
            if not success:
                raise HTTPException(status_code=404, detail="Campaign not found")
            return {"success": True, "message": "Campaign paused"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error pausing campaign {campaign_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/campaigns/{campaign_id}/stop")
    async def stop_campaign(campaign_id: int, user_id: str = Query(..., description="User ID is required")):
        """Stop campaign"""
        try:
            # Verify campaign belongs to user
            if user_id:
                from database.models import Campaign
                from database.connection import get_db
                
                with get_db() as db:
                    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                    if not campaign:
                        raise HTTPException(status_code=404, detail="Campaign not found")
                    if campaign.user_id != user_id:
                        raise HTTPException(status_code=403, detail="Access denied")
            # First stop the processor if campaign is running
            from jobs.processor import message_processor
            await message_processor.stop_campaign_processing(campaign_id)
            
            # Then update campaign status
            success = campaign_manager.stop_campaign(campaign_id)
            if not success:
                raise HTTPException(status_code=404, detail="Campaign not found")
            return {"success": True, "message": "Campaign stopped"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error stopping campaign {campaign_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/campaigns/{campaign_id}/restart")
    async def restart_campaign(campaign_id: int, restart_data: CampaignRestart):
        """Restart a completed campaign with new starting row"""
        try:
            logger.info(f"Restart campaign {campaign_id} called with data: start_row={restart_data.start_row}, stop_row={restart_data.stop_row}, skip_processed={restart_data.skip_processed}")
            
            start_row = restart_data.start_row
            stop_row = restart_data.stop_row
            skip_processed = restart_data.skip_processed
            
            # Get the original campaign
            original = campaign_manager.get_campaign(campaign_id)
            if not original:
                logger.error(f"Campaign {campaign_id} not found")
                raise HTTPException(status_code=404, detail="Campaign not found")
            
            logger.info(f"Original campaign status: {original.status}")
            
            # Allow restarting campaigns that are completed, failed, or cancelled
            # Note: CampaignStatus uses lowercase values
            if original.status not in ["completed", "failed", "cancelled", "paused"]:
                logger.error(f"Campaign {campaign_id} cannot be restarted. Status: {original.status}")
                raise HTTPException(status_code=400, detail=f"Campaign cannot be restarted. Current status: {original.status}. Only completed, failed, cancelled or paused campaigns can be restarted")
            
            # Create a new campaign with same settings but different start/stop rows
            new_campaign_data = CampaignCreate(
                name=f"{original.name} (Restarted)",
                session_name=original.session_name,
                user_id=original.user_id,  # Copy user_id from original campaign
                file_path=original.file_path,
                message_mode=original.message_mode,
                message_samples=original.message_samples,
                use_csv_samples=original.use_csv_samples,
                delay_seconds=original.delay_seconds,
                retry_attempts=original.retry_attempts,
                max_daily_messages=original.max_daily_messages,
                start_row=start_row,
                end_row=stop_row,  # Add the stop row
                save_contact_before_message=restart_data.save_contact_before_message  # Use the restart option
            )
            
            # Create the new campaign
            new_campaign = campaign_manager.create_campaign(new_campaign_data)
            
            # If skip_processed is True, copy processed rows from original campaign
            if skip_processed and hasattr(campaign_manager, 'copy_processed_rows'):
                campaign_manager.copy_processed_rows(campaign_id, new_campaign.id)
            
            return {
                "success": True, 
                "message": "Campaign restarted successfully",
                "new_campaign_id": new_campaign.id
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error restarting campaign {campaign_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/api/campaigns/{campaign_id}")
    async def delete_campaign(campaign_id: int, user_id: str = Query(..., description="User ID is required")):
        """Delete campaign"""
        try:
            # Verify campaign belongs to user
            if user_id:
                from database.models import Campaign
                from database.connection import get_db
                
                with get_db() as db:
                    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                    if not campaign:
                        raise HTTPException(status_code=404, detail="Campaign not found")
                    if campaign.user_id != user_id:
                        raise HTTPException(status_code=403, detail="Access denied")
            success = campaign_manager.delete_campaign(campaign_id)
            if not success:
                raise HTTPException(status_code=404, detail="Campaign not found")
            return {"success": True, "message": "Campaign deleted"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting campaign {campaign_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/campaigns/{campaign_id}/cancel-schedule")
    async def cancel_campaign_schedule(campaign_id: int, request_data: dict):
        """Cancel a scheduled campaign"""
        try:
            user_id = request_data.get('user_id')
            
            from database.models import Campaign
            from database.connection import get_db
            
            with get_db() as db:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if not campaign:
                    raise HTTPException(status_code=404, detail="Campaign not found")
                
                # Verify campaign belongs to user if user_id provided
                if user_id and campaign.user_id != user_id:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                # Cancel the schedule
                campaign.scheduled_start_time = None
                campaign.is_scheduled = False
                campaign.status = 'created'  # Change back to created status
                
                db.commit()
                
                return {
                    "success": True,
                    "message": "Schedule cancelled successfully",
                    "campaign_id": campaign_id
                }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error cancelling campaign schedule: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/campaigns/schedule")
    async def schedule_campaign(schedule_data: dict):
        """Schedule a campaign to start at a specific time (Hobby+ plans only)"""
        try:
            campaign_id = schedule_data.get('campaign_id')
            scheduled_time = schedule_data.get('scheduled_time')
            user_id = schedule_data.get('user_id')
            
            if not campaign_id or not scheduled_time:
                raise HTTPException(status_code=400, detail="campaign_id and scheduled_time are required")
            
            # Check user subscription plan (must be Hobby or higher)
            if user_id:
                from database.subscription_models import UserSubscription, PlanType
                from database.connection import get_db
                
                with get_db() as db:
                    user_subscription = db.query(UserSubscription).filter(
                        UserSubscription.user_id == user_id
                    ).first()
                    
                    if not user_subscription:
                        raise HTTPException(
                            status_code=403,
                            detail="No subscription found. Please subscribe to use this feature."
                        )
                    
                    # Check if user has access to Schedule feature (Hobby plan or higher)
                    if user_subscription.plan_type in [PlanType.FREE, PlanType.STARTER]:
                        raise HTTPException(
                            status_code=403,
                            detail=f"Schedule Campaign is not available on {user_subscription.plan_type.value} plan. Please upgrade to Hobby plan or higher to use this feature."
                        )
            
            # Update the existing campaign with schedule information
            from database.models import Campaign
            from database.connection import get_db
            from datetime import datetime
            
            with get_db() as db:
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if not campaign:
                    raise HTTPException(status_code=404, detail="Campaign not found")
                
                # Verify campaign belongs to user if user_id provided
                if user_id and campaign.user_id != user_id:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                # Parse the scheduled time
                scheduled_datetime = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
                
                # Update campaign with scheduling info
                campaign.scheduled_start_time = scheduled_datetime
                campaign.is_scheduled = True
                campaign.status = 'scheduled'  # Update status to scheduled
                
                db.commit()
                
                return {
                    "success": True,
                    "message": f"Campaign scheduled for {scheduled_time}",
                    "campaign_id": campaign_id
                }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error scheduling campaign: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/campaigns/start-all")
    async def start_all_campaigns(request: Request, user_id: str = None):
        """Start all created campaigns sequentially (Hobby+ plans only)"""
        try:
            # Check user subscription plan (must be Hobby or higher)
            if user_id:
                from database.subscription_models import UserSubscription, PlanType
                from database.connection import get_db
                
                with get_db() as db:
                    user_subscription = db.query(UserSubscription).filter(
                        UserSubscription.user_id == user_id
                    ).first()
                    
                    if not user_subscription:
                        raise HTTPException(
                            status_code=403,
                            detail="No subscription found. Please subscribe to use this feature."
                        )
                    
                    # Check if user has access to Start All feature (Hobby plan or higher)
                    if user_subscription.plan_type in [PlanType.FREE, PlanType.STARTER]:
                        raise HTTPException(
                            status_code=403,
                            detail=f"Start All Campaigns is not available on {user_subscription.plan_type.value} plan. Please upgrade to Hobby plan or higher to use this feature."
                        )
            
            # Parse request body if present
            body = {}
            try:
                body = await request.json()
            except:
                pass
            
            skip_scheduled = body.get('skip_scheduled', False)
            
            # Get all created campaigns
            campaigns = campaign_manager.get_campaigns(status="created")
            
            # Filter out scheduled campaigns if requested
            if skip_scheduled:
                campaigns = [c for c in campaigns if not getattr(c, 'is_scheduled', False)]
            
            if not campaigns:
                return {
                    "success": True,
                    "message": "No unscheduled campaigns found to start",
                    "campaigns_queued": 0
                }
            
            # Start the first campaign
            first_campaign = campaigns[0]
            campaign_manager.start_campaign(first_campaign.id)
            
            # Mark remaining campaigns for sequential execution
            for i, campaign in enumerate(campaigns[1:], 1):
                # Update campaign metadata to indicate it's queued
                campaign_manager.update_campaign(campaign.id, {
                    "status": "queued",
                    "queue_position": i
                })
            
            return {
                "success": True,
                "message": f"Starting {len(campaigns)} campaigns sequentially",
                "campaigns_queued": len(campaigns),
                "first_campaign_id": first_campaign.id
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error starting all campaigns: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/campaigns/stop-all")
    async def stop_all_campaigns():
        """Stop all running/queued campaigns from Start All operation"""
        try:
            # Get all campaigns that are running or queued
            running_campaigns = campaign_manager.get_campaigns(status="running")
            queued_campaigns = campaign_manager.get_campaigns(status="queued")
            
            stopped_count = 0
            reset_count = 0
            cancelled_count = 0
            
            # Cancel currently running campaigns
            for campaign in running_campaigns:
                try:
                    campaign_manager.update_campaign(campaign.id, {
                        "status": "cancelled",
                        "completed_at": datetime.utcnow()
                    })
                    cancelled_count += 1
                except Exception as e:
                    logger.error(f"Failed to cancel campaign {campaign.id}: {e}")
            
            # Reset queued campaigns back to created
            for campaign in queued_campaigns:
                try:
                    campaign_manager.update_campaign(campaign.id, {
                        "status": "created",
                        "queue_position": None
                    })
                    reset_count += 1
                except Exception as e:
                    logger.error(f"Failed to reset campaign {campaign.id}: {e}")
            
            total_affected = cancelled_count + reset_count
            
            if total_affected == 0:
                return {
                    "success": True,
                    "message": "No campaigns to stop",
                    "campaigns_cancelled": 0,
                    "campaigns_reset": 0
                }
            
            return {
                "success": True,
                "message": f"Stopped {total_affected} campaigns",
                "campaigns_cancelled": cancelled_count,
                "campaigns_reset": reset_count,
                "total_affected": total_affected
            }
        except Exception as e:
            logger.error(f"Error stopping all campaigns: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/campaigns/scheduled")
    async def get_scheduled_campaigns():
        """Get all scheduled campaigns"""
        try:
            campaigns = campaign_manager.get_campaigns(is_scheduled=True)
            return {
                "success": True,
                "campaigns": [c.to_dict() for c in campaigns]
            }
        except Exception as e:
            logger.error(f"Error getting scheduled campaigns: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/campaigns/schedule-all")
    async def schedule_all_campaigns(request: Request, user_id: str = None):
        """Schedule all created campaigns to start at a specific time (Hobby+ plans only)"""
        try:
            # Check user subscription plan (must be Hobby or higher)
            if user_id:
                from database.subscription_models import UserSubscription, PlanType
                from database.connection import get_db
                
                with get_db() as db:
                    user_subscription = db.query(UserSubscription).filter(
                        UserSubscription.user_id == user_id
                    ).first()
                    
                    if not user_subscription:
                        raise HTTPException(
                            status_code=403,
                            detail="No subscription found. Please subscribe to use this feature."
                        )
                    
                    # Check if user has access to Schedule All feature (Hobby plan or higher)
                    if user_subscription.plan_type in [PlanType.FREE, PlanType.STARTER]:
                        raise HTTPException(
                            status_code=403,
                            detail=f"Schedule All Campaigns is not available on {user_subscription.plan_type.value} plan. Please upgrade to Hobby plan or higher to use this feature."
                        )
            
            body = await request.json()
            scheduled_time = body.get('scheduled_time')
            skip_scheduled = body.get('skip_scheduled', True)
            stagger_seconds = body.get('stagger_seconds', 0)  # Seconds between each campaign
            
            if not scheduled_time:
                raise HTTPException(status_code=400, detail="scheduled_time is required")
            
            # Parse scheduled time
            from datetime import datetime, timedelta
            try:
                scheduled_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
            except:
                raise HTTPException(status_code=400, detail="Invalid scheduled_time format")
            
            # Get all created campaigns
            campaigns = campaign_manager.get_campaigns(status="created")
            
            # Filter out already scheduled campaigns if requested
            if skip_scheduled:
                campaigns = [c for c in campaigns if not getattr(c, 'is_scheduled', False)]
            
            if not campaigns:
                return {
                    "success": True,
                    "message": "No campaigns found to schedule",
                    "campaigns_scheduled": 0
                }
            
            # Schedule each campaign with optional staggering
            scheduled_count = 0
            scheduled_times = []
            for i, campaign in enumerate(campaigns):
                try:
                    # Calculate staggered time for this campaign
                    campaign_scheduled_time = scheduled_dt + timedelta(seconds=i * stagger_seconds)
                    
                    campaign_manager.update_campaign(campaign.id, {
                        "scheduled_start_time": campaign_scheduled_time,
                        "is_scheduled": True,
                        "status": "scheduled"  # Set status to scheduled
                    })
                    scheduled_count += 1
                    scheduled_times.append({
                        "campaign_id": campaign.id,
                        "campaign_name": campaign.name,
                        "scheduled_time": campaign_scheduled_time.isoformat() + 'Z'
                    })
                except Exception as e:
                    logger.error(f"Failed to schedule campaign {campaign.id}: {e}")
            
            return {
                "success": True,
                "message": f"Scheduled {scheduled_count} campaigns" + (f" with {stagger_seconds}s intervals" if stagger_seconds > 0 else ""),
                "campaigns_scheduled": scheduled_count,
                "scheduled_time": scheduled_time,
                "stagger_seconds": stagger_seconds,
                "schedule_details": scheduled_times if stagger_seconds > 0 else None
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error scheduling all campaigns: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/templates/preview")
    async def preview_template(template: str = Form(...), sample_data: str = Form(...)):
        """Preview message template with sample data"""
        try:
            sample_dict = json.loads(sample_data)
            preview = template_engine.preview_message(template, sample_dict)
            return {"success": True, "data": preview}
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in sample_data")
        except Exception as e:
            logger.error(f"Error previewing template: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/database/info")
    async def get_database_info_endpoint():
        """Get database information"""
        try:
            info = get_database_info()
            return {"success": True, "data": info}
        except Exception as e:
            logger.error(f"Error getting database info: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Admin endpoints for orphaned session management
    @app.get("/api/admin/orphaned-sessions")
    async def check_orphaned_sessions():
        """Check for orphaned WAHA sessions (admin only)"""
        try:
            result = orphan_cleaner.cleanup_orphaned_sessions(auto_delete=False)
            return {
                "success": True,
                "orphaned_count": result['found'],
                "sessions": result['sessions']
            }
        except Exception as e:
            logger.error(f"Error checking orphaned sessions: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/api/admin/orphaned-sessions")
    async def cleanup_orphaned_sessions():
        """Delete orphaned WAHA sessions (admin only)"""
        try:
            result = orphan_cleaner.cleanup_orphaned_sessions(auto_delete=True)
            return {
                "success": True,
                "message": f"Cleaned up {result['deleted']} orphaned sessions",
                "found": result['found'],
                "deleted": result['deleted']
            }
        except Exception as e:
            logger.error(f"Error cleaning orphaned sessions: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/admin/orphaned-sessions/{session_name}/assign")
    async def assign_orphaned_session(session_name: str, user_id: str = Query(...)):
        """Assign an orphaned session to a user (admin only)"""
        try:
            success = orphan_cleaner.assign_orphaned_to_user(session_name, user_id)
            if success:
                return {
                    "success": True,
                    "message": f"Session {session_name} assigned to user {user_id}"
                }
            else:
                raise HTTPException(status_code=400, detail="Failed to assign session")
        except Exception as e:
            logger.error(f"Error assigning orphaned session: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/campaigns/{campaign_id}/report")
    async def get_campaign_report(campaign_id: int):
        """Get detailed campaign report with file information"""
        try:
            campaign = campaign_manager.get_campaign(campaign_id)
            if not campaign:
                raise HTTPException(status_code=404, detail="Campaign not found")
            
            # Get the raw database campaign to access all fields
            from database.connection import get_db
            from database.models import Campaign
            
            with get_db() as db:
                db_campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if not db_campaign:
                    raise HTTPException(status_code=404, detail="Campaign not found")
                
                # Extract filename from path
                filename = os.path.basename(db_campaign.file_path) if db_campaign.file_path else "Unknown"
                
                # Get actual file row count using the same FileHandler used during upload
                file_total_rows = db_campaign.total_rows  # Default to stored value
                if db_campaign.file_path and os.path.exists(db_campaign.file_path):
                    try:
                        from utils.file_handler import FileHandler
                        file_handler = FileHandler()
                        validation_result = file_handler.validate_file(db_campaign.file_path)
                        if validation_result.get("valid") and validation_result.get("file_info"):
                            file_total_rows = validation_result["file_info"]["total_rows"]
                    except Exception as e:
                        logger.warning(f"Could not get accurate row count for {db_campaign.file_path}: {e}")
                
                # Get session phone number and name
                session_phone = None
                session_phone_name = None
                try:
                    session_info = waha.get_session_info(db_campaign.session_name)
                    if session_info and session_info.get("me"):
                        session_phone = session_info["me"].get("id", "").replace("@c.us", "")
                        session_phone_name = session_info["me"].get("pushName", "")
                except Exception as e:
                    logger.warning(f"Could not get session info for {db_campaign.session_name}: {e}")
                
                # Get deliveries for this campaign
                from database.models import Delivery
                deliveries = db.query(Delivery).filter(Delivery.campaign_id == campaign_id).all()
                
                # Parse source information from column_mapping if available
                import json
                source_info = {}
                if db_campaign.column_mapping:
                    try:
                        mapping_data = json.loads(db_campaign.column_mapping) if isinstance(db_campaign.column_mapping, str) else db_campaign.column_mapping
                        # Check for _source_info key which contains JSON string
                        if '_source_info' in mapping_data:
                            source_info = json.loads(mapping_data['_source_info'])
                        elif 'source_info' in mapping_data:
                            # Backward compatibility - if source_info is directly in mapping
                            source_info = mapping_data['source_info'] if isinstance(mapping_data['source_info'], dict) else json.loads(mapping_data['source_info'])
                        elif 'source_type' in mapping_data:
                            # Fallback to basic source type if available
                            source_info = {'source_type': mapping_data.get('source_type', 'csv')}
                    except Exception as e:
                        logger.warning(f"Could not parse campaign source data: {e}")
                
                # Default to CSV if no source info found
                if not source_info:
                    source_info = {'source_type': 'csv'}
                
                # Read CSV file to get contact details if available
                contacts_preview = []
                if db_campaign.file_path and os.path.exists(db_campaign.file_path):
                    try:
                        import csv
                        with open(db_campaign.file_path, 'r', encoding='utf-8-sig') as f:
                            reader = csv.DictReader(f)
                            for idx, row in enumerate(reader):
                                if idx >= 10:  # Limit preview to first 10 rows
                                    break
                                contacts_preview.append({
                                    'phone_number': row.get('phone_number', ''),
                                    'name': row.get('name', ''),
                                    'source_type': row.get('source_type', source_info.get('source_type', 'csv'))
                                })
                    except Exception as e:
                        logger.warning(f"Could not read CSV for preview: {e}")
                
                # Process delivery records
                delivery_details = []
                for delivery in deliveries:
                    delivery_details.append({
                        'id': delivery.id,
                        'phone_number': delivery.phone_number,
                        'contact_name': delivery.recipient_name,  # Fixed: use recipient_name
                        'status': delivery.status,
                        'message_sent': delivery.final_message_content[:100] + '...' if delivery.final_message_content and len(delivery.final_message_content) > 100 else delivery.final_message_content,  # Fixed: use final_message_content
                        'error_message': delivery.error_message,
                        'created_at': delivery.created_at.isoformat() if delivery.created_at else None,
                        'delivered_at': delivery.delivered_at.isoformat() if delivery.delivered_at else None
                    })
                
                # Build detailed report
                report = {
                    "id": campaign.id,
                    "name": campaign.name,
                    "status": campaign.status,
                    "session_name": campaign.session_name,
                    "session_phone": session_phone,
                    "session_phone_name": session_phone_name,
                    "file_name": filename,
                    "file_path": db_campaign.file_path,
                    "start_row": db_campaign.start_row,
                    "end_row": db_campaign.end_row if db_campaign.end_row else db_campaign.total_rows,
                    "total_rows": campaign.total_rows,
                    "file_total_rows": file_total_rows,  # Accurate total rows in the actual file
                    "processed_rows": campaign.processed_rows,
                    "success_count": campaign.success_count,
                    "failed_count": (campaign.processed_rows or 0) - (campaign.success_count or 0),
                    "message_mode": campaign.message_mode,
                    "delay_seconds": db_campaign.delay_seconds,
                    "created_at": db_campaign.created_at.isoformat() if db_campaign.created_at else None,
                    "updated_at": db_campaign.updated_at.isoformat() if db_campaign.updated_at else None,
                    "progress_percentage": round((campaign.processed_rows or 0) / (campaign.total_rows or 1) * 100, 2),
                    "success_rate": round((campaign.success_count or 0) / (campaign.processed_rows or 1) * 100, 2) if campaign.processed_rows else 0,
                    "source_info": source_info,
                    "contacts_preview": contacts_preview,
                    "deliveries": delivery_details,
                    "total_deliveries": len(delivery_details)
                }
                
                return {"success": True, "data": report}
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting campaign report for {campaign_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

else:
    @app.get("/api/campaigns")
    async def campaigns_not_available():
        """Campaign endpoints not available"""
        raise HTTPException(
            status_code=503, 
            detail="Campaign management not available. Please install Phase 2 dependencies."
        )

# ==================== USER ANALYTICS ====================

@app.get("/api/analytics/user/{user_id}")
async def get_user_analytics(user_id: str):
    """Get comprehensive analytics for a specific user"""
    try:
        from analytics.user_analytics import UserAnalytics
        from database.connection import get_db
        
        with get_db() as db:
            analytics = UserAnalytics(db)
            overview = analytics.get_user_overview(user_id)
            
            return {"success": True, "data": overview}
    except Exception as e:
        logger.error(f"Error getting user analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/user/{user_id}/campaigns")
async def get_user_campaign_analytics(user_id: str, period: str = "month"):
    """Get campaign analytics for a specific user"""
    try:
        from analytics.user_analytics import UserAnalytics
        from database.connection import get_db
        
        with get_db() as db:
            analytics = UserAnalytics(db)
            campaign_data = analytics.get_user_campaign_analytics(user_id, period)
            
            return {"success": True, "data": campaign_data}
    except Exception as e:
        logger.error(f"Error getting campaign analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/user/{user_id}/sessions")
async def get_user_session_analytics(user_id: str):
    """Get session analytics for a specific user"""
    try:
        from analytics.user_analytics import UserAnalytics
        from database.connection import get_db
        
        with get_db() as db:
            analytics = UserAnalytics(db)
            session_data = analytics.get_user_session_analytics(user_id)
            
            return {"success": True, "data": session_data}
    except Exception as e:
        logger.error(f"Error getting session analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ERROR HANDLERS ====================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"success": False, "error": "Endpoint not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"}
    )

# ==================== WAHA SESSION MANAGEMENT ====================

# Import pool manager if available
try:
    from waha_pool_manager import waha_pool
    from waha_session_manager import waha_session_manager
    POOL_MANAGEMENT_ENABLED = True
except ImportError:
    POOL_MANAGEMENT_ENABLED = False
    waha_pool = None
    waha_session_manager = None
    logger.warning("WAHA pool management not available")

class SessionCreateRequest(BaseModel):
    user_id: str
    session_name: str

@app.post("/api/waha/sessions/start")
async def create_waha_session(request: SessionCreateRequest):
    """Create a new WAHA session with auto-scaling"""
    if not POOL_MANAGEMENT_ENABLED:
        raise HTTPException(status_code=503, detail="Pool management not available")
    
    try:
        # Get instance URL based on user plan
        instance_url = waha_pool.get_or_create_instance_for_user(
            request.user_id, 
            request.session_name
        )
        
        # Save the assignment
        waha_pool.save_session_assignment(
            request.user_id,
            request.session_name,
            instance_url
        )
        
        # Create the actual WAHA session
        waha_client = WAHAClient(base_url=instance_url)
        result = waha_client.create_session(request.session_name)
        
        return {
            "success": True,
            "session_name": request.session_name,
            "instance_url": instance_url,
            "result": result
        }
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/waha/sessions/{user_id}")
async def get_user_sessions(user_id: str):
    """Get all sessions for a user"""
    if not POOL_MANAGEMENT_ENABLED:
        raise HTTPException(status_code=503, detail="Pool management not available")
    
    try:
        sessions = waha_session_manager.get_user_sessions(user_id)
        return {"success": True, "sessions": sessions}
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== STARTUP EVENT ====================

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("WhatsApp Agent API Server starting up...")
    
    # Create static directory if it doesn't exist
    os.makedirs("static", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)
    os.makedirs("static/js", exist_ok=True)
    os.makedirs("static/uploads", exist_ok=True)
    os.makedirs("static/exports", exist_ok=True)
    
    # Start session cleanup task
    try:
        from auth.api import cleanup_sessions_task
        import asyncio
        asyncio.create_task(cleanup_sessions_task())
        logger.info("Session cleanup task started")
    except Exception as e:
        logger.warning(f"Could not start session cleanup task: {str(e)}")
    
    # Initialize Phase 2 database if available
    if PHASE_2_ENABLED:
        try:
            logger.info("Initializing Phase 2 database...")
            success = init_database()
            if success:
                logger.info("✅ Phase 2 database initialized successfully")
                
                # Start campaign scheduler
                logger.info("Starting campaign scheduler...")
                await campaign_scheduler.start()
                logger.info("✅ Campaign scheduler started")
            else:
                logger.error("❌ Phase 2 database initialization failed")
        except Exception as e:
            logger.error(f"❌ Phase 2 database initialization error: {str(e)}")
    else:
        logger.info("⚠️ Phase 2 features not available")
    
    logger.info("WhatsApp Agent API Server started successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown"""
    logger.info("WhatsApp Agent API Server shutting down...")
    
    if PHASE_2_ENABLED:
        try:
            logger.info("Stopping campaign scheduler...")
            await campaign_scheduler.stop()
            logger.info("✅ Campaign scheduler stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping scheduler: {str(e)}")
    
    logger.info("WhatsApp Agent API Server shutdown complete!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )