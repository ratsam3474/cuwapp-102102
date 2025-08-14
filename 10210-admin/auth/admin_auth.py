"""
Admin authentication logic
"""

from fastapi import HTTPException, Request, Response, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database.connection import get_db_dependency
from database.admin_users import AdminUser
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Admin registration secret code
ADMIN_SECRET_CODE = "10210"

# Cookie name for admin session (unique to avoid conflicts)
ADMIN_SESSION_COOKIE = "cuwhapp_admin_session"


async def create_admin_user(
    email: str,
    password: str,
    secret_code: str,
    db: Session
) -> dict:
    """Create a new admin user"""
    # Verify secret code
    if secret_code != ADMIN_SECRET_CODE:
        raise HTTPException(status_code=403, detail="Invalid admin secret code")
    
    # Check if user already exists
    existing_user = db.query(AdminUser).filter(AdminUser.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Admin user already exists")
    
    # Create new admin user
    admin_user = AdminUser(
        email=email,
        password_hash=AdminUser.hash_password(password),
        is_active=True
    )
    
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    return {
        "success": True,
        "message": "Admin user created successfully",
        "email": email
    }


async def login_admin(
    email: str,
    password: str,
    response: Response,
    db: Session
) -> dict:
    """Login admin user and set session"""
    # Find admin user
    admin_user = db.query(AdminUser).filter(AdminUser.email == email).first()
    
    if not admin_user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not admin_user.verify_password(password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check if user is active
    if not admin_user.is_active:
        raise HTTPException(status_code=403, detail="Admin account is disabled")
    
    # Generate new session token
    session_token = AdminUser.generate_admin_token()
    
    # Update user session and last login
    admin_user.admin_session_token = session_token
    admin_user.last_login = datetime.now(timezone.utc)
    db.commit()
    
    # Set session cookie (httponly for security)
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=session_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=86400  # 24 hours
    )
    
    return {
        "success": True,
        "message": "Login successful",
        "email": email
    }


async def logout_admin(
    request: Request,
    response: Response,
    db: Session
) -> dict:
    """Logout admin user"""
    # Get session token from cookie
    session_token = request.cookies.get(ADMIN_SESSION_COOKIE)
    
    if session_token:
        # Clear session token in database
        admin_user = db.query(AdminUser).filter(
            AdminUser.admin_session_token == session_token
        ).first()
        
        if admin_user:
            admin_user.admin_session_token = None
            db.commit()
    
    # Clear cookie
    response.delete_cookie(ADMIN_SESSION_COOKIE)
    
    return {
        "success": True,
        "message": "Logout successful"
    }


async def get_current_admin(
    request: Request,
    db: Session = Depends(get_db_dependency)
) -> AdminUser:
    """Get current logged in admin user"""
    # Get session token from cookie
    session_token = request.cookies.get(ADMIN_SESSION_COOKIE)
    
    if not session_token:
        return None
    
    # Find admin user by session token
    admin_user = db.query(AdminUser).filter(
        AdminUser.admin_session_token == session_token,
        AdminUser.is_active == True
    ).first()
    
    return admin_user


async def require_admin(
    request: Request,
    db: Session = Depends(get_db_dependency)
) -> AdminUser:
    """Dependency to require admin authentication"""
    admin_user = await get_current_admin(request, db)
    
    if not admin_user:
        # If it's an API call, return 401
        if request.url.path.startswith("/api/"):
            raise HTTPException(status_code=401, detail="Admin authentication required")
        # Otherwise redirect to login
        return RedirectResponse(url="/login", status_code=302)
    
    return admin_user