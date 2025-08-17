"""
API Gateway Service - runs on port 8000 (app.cuwapp.com)
Handles authentication, container provisioning, and returns user container URLs
Dashboard then makes direct calls to user containers
"""

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import os
from typing import Optional
from datetime import datetime

from dynamic_urls import url_manager
from auth.session_manager import session_manager

logger = logging.getLogger(__name__)

app = FastAPI(title="CuWhapp API Gateway")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.cuwapp.com",
        "https://dashboard.cuwapp.com", 
        "https://auth.cuwapp.com",
        "http://localhost:3000",
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root(request: Request):
    """
    Entry point from auth redirect
    Handles user container provisioning and returns config
    """
    # Check if this is an API request (has auth headers) or web request
    auth_header = request.headers.get('Authorization')
    if auth_header:
        # This is an API request with auth headers
        return await handle_api_request(request)
    
    # Get token from URL parameters for web requests
    token = request.query_params.get("token")
    
    if not token:
        # No token, serve the gateway HTML page
        gateway_html = os.path.join(static_dir, "gateway.html")
        if os.path.exists(gateway_html):
            return FileResponse(gateway_html)
        else:
            # Fallback redirect to auth
            return RedirectResponse(url="https://auth.cuwapp.com")
    
    try:
        # Validate token
        validation = session_manager.validate_session(token)
        if not validation["valid"]:
            return RedirectResponse(url="https://auth.cuwapp.com")
        
        # Get user from token
        user_id = validation["user_id"]
        email = validation["email"]
        plan_type = validation["plan_type"]
        
        # Load or create user infrastructure
        logger.info(f"Provisioning infrastructure for user {user_id} ({plan_type})")
        infrastructure = url_manager.load_or_create_user_infrastructure(user_id)
        
        # Check if container is being created (show loading)
        if infrastructure.get("status") == "creating":
            # Return HTML with loading animation
            return HTMLResponse("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Starting Your Engine...</title>
                    <style>
                        body { 
                            display: flex; 
                            justify-content: center; 
                            align-items: center; 
                            height: 100vh; 
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            font-family: Arial, sans-serif;
                        }
                        .loading-container {
                            text-align: center;
                            color: white;
                        }
                        .spinner {
                            border: 3px solid rgba(255,255,255,0.3);
                            border-radius: 50%;
                            border-top: 3px solid white;
                            width: 50px;
                            height: 50px;
                            animation: spin 1s linear infinite;
                            margin: 20px auto;
                        }
                        @keyframes spin {
                            0% { transform: rotate(0deg); }
                            100% { transform: rotate(360deg); }
                        }
                    </style>
                    <script>
                        setTimeout(() => {
                            window.location.reload();
                        }, 3000);
                    </script>
                </head>
                <body>
                    <div class="loading-container">
                        <h1>Starting Your Engine...</h1>
                        <div class="spinner"></div>
                        <p>Please wait while we prepare your workspace</p>
                    </div>
                </body>
                </html>
            """)
        
        # Container ready, return configuration as JSON embedded in HTML
        # The frontend will extract this and save to localStorage/session
        config_data = {
            "token": token,
            "userId": user_id,
            "email": email,
            "planType": plan_type,
            "infrastructure": {
                "apiUrl": infrastructure['api_url'],
                "warmerUrl": infrastructure['warmer_url'],
                "campaignUrl": infrastructure['campaign_url']
            },
            "status": infrastructure.get('status', 'active')
        }
        
        # Return HTML that saves config and redirects to dashboard
        return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Loading Dashboard...</title>
                <script>
                    // Save configuration to localStorage
                    const config = {json.dumps(config_data)};
                    
                    // Save to multiple storage keys for compatibility
                    localStorage.setItem('session_token', config.token);
                    localStorage.setItem('user_infrastructure', JSON.stringify(config.infrastructure));
                    localStorage.setItem('cuwhapp_user_cache', JSON.stringify({{
                        id: config.userId,
                        email: config.email,
                        token: config.token,
                        isLoggedIn: true,
                        lastUpdated: new Date().toISOString()
                    }}));
                    
                    // Store URLs in session storage too
                    sessionStorage.setItem('API_URL', config.infrastructure.apiUrl);
                    sessionStorage.setItem('WARMER_URL', config.infrastructure.warmerUrl);
                    sessionStorage.setItem('CAMPAIGN_URL', config.infrastructure.campaignUrl);
                    
                    // Redirect to dashboard
                    window.location.href = 'https://dashboard.cuwapp.com';
                </script>
            </head>
            <body>
                <p>Loading dashboard...</p>
            </body>
            </html>
        """)
        
    except Exception as e:
        logger.error(f"Error in gateway root: {e}")
        return RedirectResponse(url="https://auth.cuwapp.com?error=gateway_error")

@app.post("/api/gateway/refresh-infrastructure")
async def refresh_infrastructure(authorization: Optional[str] = Header(None)):
    """
    Called by dashboard to refresh/validate container URLs
    Used on page refresh or when container might have timed out
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No valid authorization")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        # Validate token
        validation = session_manager.validate_session(token)
        if not validation["valid"]:
            return JSONResponse(
                status_code=401,
                content={
                    "valid": False,
                    "redirect": "https://auth.cuwapp.com"
                }
            )
        
        user_id = validation["user_id"]
        
        # Load or refresh user infrastructure
        # This will restart container if it was stopped (free users)
        infrastructure = url_manager.load_or_create_user_infrastructure(user_id)
        
        return {
            "valid": True,
            "user_id": user_id,
            "email": validation["email"],
            "plan_type": validation["plan_type"],
            "infrastructure": {
                "apiUrl": infrastructure['api_url'],
                "warmerUrl": infrastructure['warmer_url'],
                "campaignUrl": infrastructure['campaign_url']
            },
            "status": infrastructure.get('status', 'active')
        }
        
    except Exception as e:
        logger.error(f"Error refreshing infrastructure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/gateway/status")
async def gateway_status():
    """Check gateway and infrastructure status"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "timestamp": datetime.utcnow().isoformat(),
        "capabilities": [
            "user-authentication",
            "container-provisioning", 
            "infrastructure-management"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "api-gateway"}

# Import HTMLResponse and json
from fastapi.responses import HTMLResponse
import json

async def handle_api_request(request: Request):
    """Handle API requests with auth headers"""
    auth_header = request.headers.get('Authorization', '')
    user_id = request.headers.get('X-User-Id')
    plan = request.headers.get('X-Plan', 'free')
    
    if not auth_header or not user_id:
        raise HTTPException(status_code=401, detail="Missing authentication")
    
    token = auth_header.replace('Bearer ', '')
    
    try:
        # Validate token
        validation = session_manager.validate_session(token)
        if not validation["valid"]:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Load or create user infrastructure
        infrastructure = url_manager.load_or_create_user_infrastructure(user_id)
        
        return JSONResponse({
            "api_url": infrastructure['api_url'],
            "warmer_url": infrastructure['warmer_url'],
            "campaign_url": infrastructure['campaign_url'],
            "waha_url": infrastructure.get('waha_url', 'http://localhost:3000'),
            "status": infrastructure.get('status', 'active')
        })
    except Exception as e:
        logger.error(f"Error handling API request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)