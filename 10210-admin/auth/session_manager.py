"""
Session Manager - Handles session creation, validation, and timeout logic
Free plan: 1-hour session timeout
Paid plans: Persistent sessions
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
import hashlib
import secrets
from database.connection import get_db
from database.subscription_models import UserSubscription, PlanType

logger = logging.getLogger(__name__)

# Session configuration
SESSION_CONFIG = {
    PlanType.FREE: {
        "timeout_minutes": 60,  # 1 hour for free plan
        "persistent": False,
        "refresh_allowed": False
    },
    PlanType.STARTER: {
        "timeout_minutes": None,  # No timeout for paid plans
        "persistent": True,
        "refresh_allowed": True
    },
    PlanType.HOBBY: {
        "timeout_minutes": None,
        "persistent": True,
        "refresh_allowed": True
    },
    PlanType.PRO: {
        "timeout_minutes": None,
        "persistent": True,
        "refresh_allowed": True
    },
    PlanType.PREMIUM: {
        "timeout_minutes": None,
        "persistent": True,
        "refresh_allowed": True
    },
    PlanType.ADMIN: {
        "timeout_minutes": None,
        "persistent": True,
        "refresh_allowed": True
    }
}

class SessionManager:
    """Manages user sessions with plan-based timeout logic"""
    
    def __init__(self, secret_key: str = None):
        """Initialize session manager with secret key"""
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.algorithm = "HS256"
        self.active_sessions = {}  # In-memory session store (use Redis in production)
        logger.info("SessionManager initialized")
    
    def create_session(self, user_id: str, user_email: str, plan_type: PlanType = PlanType.FREE) -> Dict[str, Any]:
        """Create a new session with plan-based configuration"""
        try:
            # Get session configuration for the plan
            config = SESSION_CONFIG.get(plan_type, SESSION_CONFIG[PlanType.FREE])
            
            # Generate session ID
            session_id = hashlib.sha256(f"{user_id}{datetime.utcnow().isoformat()}{secrets.token_urlsafe(16)}".encode()).hexdigest()
            
            # Calculate expiration based on plan
            created_at = datetime.utcnow()
            if config["timeout_minutes"]:
                expires_at = created_at + timedelta(minutes=config["timeout_minutes"])
                session_duration = config["timeout_minutes"]
            else:
                # Persistent session - expires in 30 days
                expires_at = created_at + timedelta(days=30)
                session_duration = 30 * 24 * 60  # Minutes
            
            # Create JWT token
            payload = {
                "session_id": session_id,
                "user_id": user_id,
                "email": user_email,
                "plan_type": plan_type.value,
                "created_at": created_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "persistent": config["persistent"],
                "iat": created_at,
                "exp": expires_at
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            # Store session in memory
            self.active_sessions[session_id] = {
                "user_id": user_id,
                "email": user_email,
                "plan_type": plan_type,
                "created_at": created_at,
                "expires_at": expires_at,
                "last_activity": created_at,
                "persistent": config["persistent"],
                "refresh_allowed": config["refresh_allowed"]
            }
            
            logger.info(f"Session created for user {user_id} ({plan_type.value} plan) - Duration: {session_duration} minutes")
            
            return {
                "success": True,
                "token": token,
                "session_id": session_id,
                "expires_at": expires_at.isoformat(),
                "session_duration_minutes": session_duration,
                "persistent": config["persistent"],
                "plan_type": plan_type.value,
                "message": f"Session created. {'Expires in 1 hour (Free plan)' if plan_type == PlanType.FREE else 'Persistent session (Paid plan)'}"
            }
            
        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_session(self, token: str) -> Dict[str, Any]:
        """Validate session token and check for timeout"""
        try:
            # Decode JWT token
            try:
                payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            except jwt.ExpiredSignatureError:
                logger.warning("Session token expired")
                return {
                    "valid": False,
                    "error": "Session expired",
                    "reason": "timeout"
                }
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid session token: {str(e)}")
                return {
                    "valid": False,
                    "error": "Invalid session token",
                    "reason": "invalid"
                }
            
            session_id = payload.get("session_id")
            user_id = payload.get("user_id")
            plan_type = PlanType(payload.get("plan_type", "free"))
            
            # Check if session exists in memory
            if session_id not in self.active_sessions:
                # Try to restore from database
                with get_db() as db:
                    user_sub = db.query(UserSubscription).filter(
                        UserSubscription.user_id == user_id
                    ).first()
                    
                    if not user_sub:
                        return {
                            "valid": False,
                            "error": "User subscription not found",
                            "reason": "no_subscription"
                        }
                    
                    # Restore session if valid
                    expires_at = datetime.fromisoformat(payload.get("expires_at"))
                    if datetime.utcnow() < expires_at:
                        self.active_sessions[session_id] = {
                            "user_id": user_id,
                            "email": payload.get("email"),
                            "plan_type": user_sub.plan_type,
                            "created_at": datetime.fromisoformat(payload.get("created_at")),
                            "expires_at": expires_at,
                            "last_activity": datetime.utcnow(),
                            "persistent": payload.get("persistent", False),
                            "refresh_allowed": SESSION_CONFIG[user_sub.plan_type]["refresh_allowed"]
                        }
                    else:
                        return {
                            "valid": False,
                            "error": "Session expired",
                            "reason": "timeout"
                        }
            
            # Get session from memory
            session = self.active_sessions[session_id]
            
            # Check for plan-based timeout
            now = datetime.utcnow()
            config = SESSION_CONFIG.get(session["plan_type"], SESSION_CONFIG[PlanType.FREE])
            
            # For free plan, check strict 1-hour timeout
            if session["plan_type"] == PlanType.FREE:
                time_since_creation = (now - session["created_at"]).total_seconds() / 60
                if time_since_creation > 60:  # 60 minutes = 1 hour
                    # Remove expired session
                    del self.active_sessions[session_id]
                    logger.info(f"Free plan session expired for user {user_id} after {time_since_creation:.1f} minutes")
                    return {
                        "valid": False,
                        "error": "Session expired after 1 hour (Free plan limit)",
                        "reason": "timeout",
                        "plan_type": "free",
                        "upgrade_message": "Upgrade to Starter plan or higher for persistent sessions"
                    }
            
            # For all plans, check absolute expiration
            if now > session["expires_at"]:
                del self.active_sessions[session_id]
                logger.info(f"Session expired for user {user_id}")
                return {
                    "valid": False,
                    "error": "Session expired",
                    "reason": "timeout"
                }
            
            # Update last activity
            session["last_activity"] = now
            
            # Calculate remaining time
            if session["plan_type"] == PlanType.FREE:
                time_remaining = 60 - (now - session["created_at"]).total_seconds() / 60
                time_remaining_str = f"{int(time_remaining)} minutes"
            else:
                time_remaining = (session["expires_at"] - now).total_seconds() / 86400
                time_remaining_str = f"{int(time_remaining)} days"
            
            return {
                "valid": True,
                "session_id": session_id,
                "user_id": user_id,
                "email": session["email"],
                "plan_type": session["plan_type"].value,
                "persistent": session["persistent"],
                "time_remaining": time_remaining_str,
                "last_activity": session["last_activity"].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Session validation error: {str(e)}")
            return {
                "valid": False,
                "error": str(e),
                "reason": "error"
            }
    
    def refresh_session(self, token: str) -> Dict[str, Any]:
        """Refresh session (only for paid plans)"""
        try:
            # Validate current session
            validation = self.validate_session(token)
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": validation["error"]
                }
            
            session_id = validation["session_id"]
            session = self.active_sessions.get(session_id)
            
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            # Check if refresh is allowed
            if not session["refresh_allowed"]:
                return {
                    "success": False,
                    "error": "Session refresh not allowed for Free plan",
                    "upgrade_message": "Upgrade to Starter plan or higher for session refresh"
                }
            
            # Create new session with same user data
            return self.create_session(
                session["user_id"],
                session["email"],
                session["plan_type"]
            )
            
        except Exception as e:
            logger.error(f"Session refresh error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def logout_session(self, token: str) -> Dict[str, Any]:
        """Logout and invalidate session"""
        try:
            # Decode token to get session ID
            try:
                payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
                session_id = payload.get("session_id")
                
                # Remove from active sessions
                if session_id in self.active_sessions:
                    user_id = self.active_sessions[session_id]["user_id"]
                    del self.active_sessions[session_id]
                    logger.info(f"User {user_id} logged out")
                    
                return {
                    "success": True,
                    "message": "Logged out successfully"
                }
                
            except jwt.InvalidTokenError:
                return {
                    "success": True,
                    "message": "Session already invalid"
                }
                
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_session_timeout_warning(self, token: str) -> Optional[Dict[str, Any]]:
        """Check if session is about to expire (for free plan warning)"""
        try:
            validation = self.validate_session(token)
            if not validation["valid"]:
                return None
            
            session_id = validation["session_id"]
            session = self.active_sessions.get(session_id)
            
            if not session or session["plan_type"] != PlanType.FREE:
                return None
            
            # Check if less than 10 minutes remaining
            now = datetime.utcnow()
            time_elapsed = (now - session["created_at"]).total_seconds() / 60
            time_remaining = 60 - time_elapsed
            
            if time_remaining <= 10 and time_remaining > 0:
                return {
                    "warning": True,
                    "minutes_remaining": int(time_remaining),
                    "message": f"Your session will expire in {int(time_remaining)} minutes (Free plan limit)",
                    "upgrade_message": "Upgrade to Starter plan or higher to keep working without interruption"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Session warning check error: {str(e)}")
            return None
    
    def get_active_sessions_count(self) -> Dict[str, int]:
        """Get count of active sessions by plan type"""
        counts = {plan.value: 0 for plan in PlanType}
        
        for session in self.active_sessions.values():
            plan_type = session["plan_type"].value
            counts[plan_type] = counts.get(plan_type, 0) + 1
        
        return counts
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions from memory"""
        try:
            now = datetime.utcnow()
            expired_sessions = []
            
            for session_id, session in self.active_sessions.items():
                # Check expiration
                if now > session["expires_at"]:
                    expired_sessions.append(session_id)
                    continue
                
                # Check free plan 1-hour timeout
                if session["plan_type"] == PlanType.FREE:
                    time_since_creation = (now - session["created_at"]).total_seconds() / 60
                    if time_since_creation > 60:
                        expired_sessions.append(session_id)
            
            # Remove expired sessions
            for session_id in expired_sessions:
                del self.active_sessions[session_id]
            
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            
            return len(expired_sessions)
            
        except Exception as e:
            logger.error(f"Session cleanup error: {str(e)}")
            return 0

# Global session manager instance
session_manager = SessionManager()