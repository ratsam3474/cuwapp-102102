"""
Session Middleware - Automatically validates sessions and enforces timeouts
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
import logging
from .session_manager import session_manager

logger = logging.getLogger(__name__)

class SessionMiddleware(BaseHTTPMiddleware):
    """Middleware to validate sessions and enforce plan-based timeouts"""
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        # Paths that don't require authentication
        self.exclude_paths = exclude_paths or [
            "/",
            "/health",
            "/api/auth/login",
            "/api/auth/magic-link",
            "/api/auth/verify-magic-link",
            "/api/auth/newsletter/subscribe",
            "/api/auth/waitlist/join",
            "/api/payments/webhook",
            "/docs",
            "/openapi.json",
            "/swagger.yaml",
            "/static",
            "/favicon.ico"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Process each request to validate session"""
        
        # Skip validation for excluded paths
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)
        
        # Skip validation for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        
        # Check if this is a protected endpoint
        if path.startswith("/api/"):
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Authentication required",
                        "error": "no_session",
                        "message": "Please login to continue"
                    }
                )
            
            # Extract and validate token
            token = auth_header.replace("Bearer ", "")
            validation = session_manager.validate_session(token)
            
            if not validation["valid"]:
                # Handle free plan timeout specially
                if validation.get("plan_type") == "free" and validation.get("reason") == "timeout":
                    return JSONResponse(
                        status_code=401,
                        content={
                            "detail": "Session expired",
                            "error": "session_timeout",
                            "reason": "free_plan_limit",
                            "message": "Your session has expired after 1 hour (Free plan limit)",
                            "upgrade_message": "Upgrade to Starter plan or higher for persistent sessions",
                            "plan_type": "free",
                            "expired": True
                        }
                    )
                
                # Handle other session errors
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": validation.get("error", "Invalid session"),
                        "error": "invalid_session",
                        "reason": validation.get("reason", "unknown")
                    }
                )
            
            # Add user info to request state for use in endpoints
            request.state.user_id = validation["user_id"]
            request.state.email = validation["email"]
            request.state.plan_type = validation["plan_type"]
            request.state.session_id = validation["session_id"]
            
            # Check for session timeout warning (free plan)
            warning = session_manager.check_session_timeout_warning(token)
            
            # Process the request
            response = await call_next(request)
            
            # Add warning header if session is about to expire
            if warning:
                response.headers["X-Session-Warning"] = f"{warning['minutes_remaining']} minutes remaining"
                response.headers["X-Session-Upgrade-Message"] = warning.get("upgrade_message", "")
            
            return response
        
        # For non-API routes, continue without validation
        return await call_next(request)

def get_current_user(request: Request) -> Optional[dict]:
    """Helper function to get current user from request state"""
    if hasattr(request.state, "user_id"):
        return {
            "user_id": request.state.user_id,
            "email": request.state.email,
            "plan_type": request.state.plan_type,
            "session_id": request.state.session_id
        }
    return None