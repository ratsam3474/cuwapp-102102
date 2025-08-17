"""
WhatsApp Warmer Microservice
Runs independently on port 8001
Handles all warmer operations separately from main API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / "10210-api"))

from dotenv import load_dotenv
load_dotenv()

# Create warmer-specific app
app = FastAPI(
    title="WhatsApp Warmer Service",
    description="Dedicated service for WhatsApp warming operations",
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

# Import warmer components
from warmer.api import router as warmer_router
from database.connection import init_database

# Initialize database connection
init_database()

# Mount warmer routes
app.include_router(warmer_router)

@app.get("/")
async def root():
    return {
        "service": "WhatsApp Warmer",
        "status": "running",
        "port": 8001,
        "endpoints": [
            "/api/warmer/list",
            "/api/warmer/create",
            "/api/warmer/{id}/start",
            "/api/warmer/{id}/stop",
            "/api/warmer/{id}/status"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "warmer", "port": 8001}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)