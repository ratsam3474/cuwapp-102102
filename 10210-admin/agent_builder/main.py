"""
WhatsApp Agent Builder Service
Runs on port 8100 - Separate from main WhatsApp Agent application
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from contextlib import asynccontextmanager
import os
import sys

# Add parent directory to path for shared imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_builder.database.connection import init_db
from agent_builder.api import agents, tools, triggers
from agent_builder.core.agent_manager import agent_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    print("Starting Agent Builder Service on port 8100")
    # Initialize database
    await init_db()
    
    # Initialize agent manager
    # Agent manager is already initialized as singleton
    
    yield
    
    print("Shutting down Agent Builder Service")

# Create FastAPI app
app = FastAPI(
    title="WhatsApp Agent Builder",
    description="Build and manage WhatsApp agents powered by Google ADK",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.cuwapp.com",  # Main WhatsApp Agent app
        "http://localhost:8100",  # Agent Builder UI
        "http://localhost:3000",  # Development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="agent_builder/static"), name="static")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Agent Builder",
        "port": 8100,
        "version": "1.0.0"
    }

# Root endpoint - serve the UI
@app.get("/")
async def root():
    return FileResponse("agent_builder/static/index.html")

# Include API routers
app.include_router(agents.router)
app.include_router(tools.router)
app.include_router(triggers.router)

@app.get("/api/triggers")
async def list_triggers():
    """List all available webhook triggers"""
    return {
        "triggers": [
            {"id": "message", "name": "New Message", "category": "message"},
            {"id": "message.any", "name": "Any Message Activity", "category": "message"},
            {"id": "group.v2.join", "name": "User Joined Group", "category": "group"},
            # ... all 28 triggers
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "agent_builder.main:app",
        host="0.0.0.0",
        port=8100,
        reload=True,
        log_level="info"
    )