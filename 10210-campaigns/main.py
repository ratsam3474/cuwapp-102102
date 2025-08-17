"""
WhatsApp Campaigns Microservice
Runs independently on port 8002
Handles campaign creation, scheduling, and delivery
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / "10210-api"))

from dotenv import load_dotenv
load_dotenv()

# Create campaigns-specific app
app = FastAPI(
    title="WhatsApp Campaigns Service",
    description="Dedicated service for WhatsApp campaign management",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import campaign components
from jobs.manager import CampaignManager
from jobs.models import CampaignCreate, CampaignUpdate
from jobs.scheduler import campaign_scheduler
from database.connection import init_database

# Initialize
init_database()
campaign_manager = CampaignManager()

@app.get("/")
async def root():
    return {
        "service": "WhatsApp Campaigns",
        "status": "running",
        "port": 8002,
        "endpoints": [
            "/api/campaigns/list",
            "/api/campaigns/create",
            "/api/campaigns/{id}/start",
            "/api/campaigns/{id}/pause",
            "/api/campaigns/{id}/status"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "campaigns", "port": 8002}

# Campaign endpoints
@app.post("/api/campaigns/create")
async def create_campaign(campaign_data: CampaignCreate):
    """Create new campaign"""
    try:
        result = campaign_manager.create_campaign(campaign_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/campaigns/list")
async def list_campaigns(user_id: str = None):
    """List all campaigns"""
    try:
        campaigns = campaign_manager.list_campaigns(user_id=user_id)
        return campaigns
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/campaigns/{campaign_id}/start")
async def start_campaign(campaign_id: int):
    """Start campaign execution"""
    try:
        result = campaign_manager.start_campaign(campaign_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/campaigns/{campaign_id}/pause")
async def pause_campaign(campaign_id: int):
    """Pause campaign execution"""
    try:
        result = campaign_manager.pause_campaign(campaign_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/campaigns/{campaign_id}/status")
async def get_campaign_status(campaign_id: int):
    """Get campaign status and metrics"""
    try:
        status = campaign_manager.get_campaign_status(campaign_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)