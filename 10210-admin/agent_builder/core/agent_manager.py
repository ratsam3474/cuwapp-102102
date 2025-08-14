"""
Agent Manager - Handles agent lifecycle (start, stop, pause, resume, logs)
"""
import asyncio
import logging
import os
import json
import signal
from typing import Dict, Optional, List, Any
from datetime import datetime
from enum import Enum
import subprocess
import psutil
from pathlib import Path

from agent_builder.models.agent import Agent, AgentStatus
from agent_builder.core.langchain_agent import AgentFactory, RootOrchestrator
from agent_builder.database.connection import AsyncSessionLocal

logger = logging.getLogger(__name__)

class AgentState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"

class DeployedAgent:
    """Represents a deployed agent instance"""
    def __init__(self, agent_id: str, port: int, process: subprocess.Popen = None):
        self.agent_id = agent_id
        self.port = port
        self.process = process
        self.state = AgentState.STOPPED
        self.started_at: Optional[datetime] = None
        self.paused_at: Optional[datetime] = None
        self.log_file: Path = Path(f"logs/agents/{agent_id}.log")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.orchestrator: Optional[RootOrchestrator] = None

class AgentManager:
    """Manages deployed agents lifecycle"""
    
    def __init__(self):
        self.agents: Dict[str, DeployedAgent] = {}
        self.port_pool = list(range(8201, 8300))  # Pool of available ports
        self.used_ports = set()
        
    def _get_free_port(self) -> int:
        """Get a free port from the pool"""
        for port in self.port_pool:
            if port not in self.used_ports:
                # Check if port is actually free
                try:
                    import socket
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.bind(('', port))
                        self.used_ports.add(port)
                        return port
                except:
                    continue
        raise RuntimeError("No free ports available")
    
    async def start_agent(self, agent_id: str) -> Dict[str, Any]:
        """Start an agent"""
        # Check if already running
        if agent_id in self.agents and self.agents[agent_id].state == AgentState.RUNNING:
            return {"success": False, "error": "Agent already running"}
        
        try:
            # Get agent configuration from database
            async with AsyncSessionLocal() as session:
                agent = await session.get(Agent, agent_id)
                if not agent:
                    return {"success": False, "error": "Agent not found"}
            
            # Get a free port
            port = self._get_free_port()
            
            # Create deployed agent instance
            deployed = DeployedAgent(agent_id, port)
            deployed.state = AgentState.STARTING
            self.agents[agent_id] = deployed
            
            # Create ADK orchestrator
            orchestrator = AgentFactory.create_agent(agent)
            deployed.orchestrator = orchestrator
            
            # Create agent server script
            server_script = self._create_agent_server(agent_id, port, agent)
            
            # Start the agent process
            env = os.environ.copy()
            env["AGENT_ID"] = agent_id
            env["AGENT_PORT"] = str(port)
            env["WAHA_BASE_URL"] = os.getenv("WAHA_BASE_URL", "http://localhost:4500")
            env["WAHA_API_KEY"] = os.getenv("WAHA_API_KEY", "")
            
            process = subprocess.Popen(
                ["python", server_script],
                env=env,
                stdout=open(deployed.log_file, "a"),
                stderr=subprocess.STDOUT
            )
            
            deployed.process = process
            deployed.state = AgentState.RUNNING
            deployed.started_at = datetime.now()
            
            # Update agent in database
            async with AsyncSessionLocal() as session:
                agent = await session.get(Agent, agent_id)
                agent.status = AgentStatus.ACTIVE
                agent.port = port
                agent.webhook_url = f"http://localhost:{port}/webhook"
                await session.commit()
            
            # Register webhook with WAHA
            await self._register_webhook(agent_id, port, agent.triggers, agent.whatsapp_session)
            
            logger.info(f"Started agent {agent_id} on port {port}")
            
            return {
                "success": True,
                "port": port,
                "webhook_url": f"http://localhost:{port}/webhook",
                "state": deployed.state
            }
            
        except Exception as e:
            logger.error(f"Failed to start agent {agent_id}: {str(e)}")
            if agent_id in self.agents:
                self.agents[agent_id].state = AgentState.ERROR
            return {"success": False, "error": str(e)}
    
    async def stop_agent(self, agent_id: str) -> Dict[str, Any]:
        """Stop an agent"""
        if agent_id not in self.agents:
            return {"success": False, "error": "Agent not found"}
        
        deployed = self.agents[agent_id]
        
        try:
            # Terminate the process
            if deployed.process:
                deployed.process.terminate()
                try:
                    deployed.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    deployed.process.kill()
            
            # Free the port
            self.used_ports.discard(deployed.port)
            
            # Update state
            deployed.state = AgentState.STOPPED
            
            # Update database
            async with AsyncSessionLocal() as session:
                agent = await session.get(Agent, agent_id)
                agent.status = AgentStatus.INACTIVE
                agent.port = None
                await session.commit()
            
            # Unregister webhook
            await self._unregister_webhook(agent_id)
            
            # Remove from active agents
            del self.agents[agent_id]
            
            logger.info(f"Stopped agent {agent_id}")
            
            return {"success": True, "state": AgentState.STOPPED}
            
        except Exception as e:
            logger.error(f"Failed to stop agent {agent_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def pause_agent(self, agent_id: str) -> Dict[str, Any]:
        """Pause an agent (temporarily suspend processing)"""
        if agent_id not in self.agents:
            return {"success": False, "error": "Agent not found"}
        
        deployed = self.agents[agent_id]
        
        if deployed.state != AgentState.RUNNING:
            return {"success": False, "error": f"Cannot pause agent in state: {deployed.state}"}
        
        try:
            # Send pause signal to agent process
            if deployed.process:
                # On Windows, we'll use a different approach
                if os.name == 'nt':
                    # Write pause flag file
                    pause_file = Path(f"data/agents/{agent_id}.pause")
                    pause_file.parent.mkdir(parents=True, exist_ok=True)
                    pause_file.touch()
                else:
                    # On Unix, send SIGUSR1
                    deployed.process.send_signal(signal.SIGUSR1)
            
            deployed.state = AgentState.PAUSED
            deployed.paused_at = datetime.now()
            
            logger.info(f"Paused agent {agent_id}")
            
            return {"success": True, "state": AgentState.PAUSED}
            
        except Exception as e:
            logger.error(f"Failed to pause agent {agent_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def resume_agent(self, agent_id: str) -> Dict[str, Any]:
        """Resume a paused agent"""
        if agent_id not in self.agents:
            return {"success": False, "error": "Agent not found"}
        
        deployed = self.agents[agent_id]
        
        if deployed.state != AgentState.PAUSED:
            return {"success": False, "error": f"Cannot resume agent in state: {deployed.state}"}
        
        try:
            # Send resume signal
            if deployed.process:
                if os.name == 'nt':
                    # Remove pause flag file
                    pause_file = Path(f"data/agents/{agent_id}.pause")
                    if pause_file.exists():
                        pause_file.unlink()
                else:
                    # On Unix, send SIGUSR2
                    deployed.process.send_signal(signal.SIGUSR2)
            
            deployed.state = AgentState.RUNNING
            deployed.paused_at = None
            
            logger.info(f"Resumed agent {agent_id}")
            
            return {"success": True, "state": AgentState.RUNNING}
            
        except Exception as e:
            logger.error(f"Failed to resume agent {agent_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def restart_agent(self, agent_id: str) -> Dict[str, Any]:
        """Restart an agent"""
        # Stop if running
        if agent_id in self.agents:
            await self.stop_agent(agent_id)
        
        # Start again
        return await self.start_agent(agent_id)
    
    async def get_agent_logs(self, agent_id: str, lines: int = 100) -> List[str]:
        """Get agent logs"""
        log_file = Path(f"logs/agents/{agent_id}.log")
        
        if not log_file.exists():
            return []
        
        try:
            # Read last N lines
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
                return all_lines[-lines:]
        except Exception as e:
            logger.error(f"Failed to read logs for {agent_id}: {str(e)}")
            return [f"Error reading logs: {str(e)}"]
    
    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get current agent status"""
        if agent_id not in self.agents:
            return {
                "state": AgentState.STOPPED,
                "running": False
            }
        
        deployed = self.agents[agent_id]
        
        # Check if process is still alive
        if deployed.process and deployed.process.poll() is not None:
            # Process died
            deployed.state = AgentState.ERROR
            self.used_ports.discard(deployed.port)
        
        return {
            "state": deployed.state,
            "running": deployed.state == AgentState.RUNNING,
            "port": deployed.port,
            "started_at": deployed.started_at.isoformat() if deployed.started_at else None,
            "paused_at": deployed.paused_at.isoformat() if deployed.paused_at else None
        }
    
    def _create_agent_server(self, agent_id: str, port: int, agent: Agent) -> str:
        """Create agent server script"""
        script_path = Path(f"data/agents/server_{agent_id}.py")
        script_path.parent.mkdir(parents=True, exist_ok=True)
        
        script_content = f'''"""
Agent server for {agent.name}
Auto-generated by Agent Builder
"""
import asyncio
import os
import sys
from pathlib import Path

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import logging

# Import agent components
from agent_builder.core.webhook_handler import WebhookHandler
from agent_builder.database.connection import AsyncSessionLocal
from agent_builder.models.agent import Agent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="{agent.name} Agent")

# Initialize webhook handler
webhook_handler = None

@app.on_event("startup")
async def startup():
    global webhook_handler
    webhook_handler = WebhookHandler("{agent_id}")
    await webhook_handler.initialize()
    logger.info(f"Agent {agent_id} started on port {port}")

@app.post("/webhook")
async def handle_webhook(request: Request):
    """Handle incoming WAHA webhooks"""
    try:
        data = await request.json()
        result = await webhook_handler.handle_webhook(data)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Webhook error: {{str(e)}}")
        return JSONResponse({{"error": str(e)}}, status_code=500)

@app.get("/health")
async def health():
    return {{"status": "healthy", "agent_id": "{agent_id}"}}

@app.get("/pause-check")
async def pause_check():
    """Check if agent should be paused"""
    pause_file = Path(f"data/agents/{agent_id}.pause")
    return {{"paused": pause_file.exists()}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port={port})
'''
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        return str(script_path)
    
    async def _register_webhook(self, agent_id: str, port: int, triggers: List[str], session: str = "default"):
        """Register webhook with WAHA for the agent's triggers"""
        import httpx
        
        webhook_url = f"http://localhost:{port}/webhook"
        waha_base_url = os.getenv("WAHA_BASE_URL", "http://localhost:4500")
        waha_api_key = os.getenv("WAHA_API_KEY", "")
        
        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": waha_api_key
        }
        
        # WAHA webhook configuration
        webhook_config = {
            "url": webhook_url,
            "events": triggers,  # The trigger types match WAHA event names
            "hmac": {
                "key": f"agent_{agent_id}_secret"  # Optional HMAC for security
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Register webhook with WAHA for specific session
                response = await client.post(
                    f"{waha_base_url}/api/{session}/webhook",
                    headers=headers,
                    json=webhook_config
                )
                response.raise_for_status()
                logger.info(f"Registered webhook {webhook_url} for triggers: {triggers}")
            except Exception as e:
                logger.error(f"Failed to register webhook: {str(e)}")
                raise
    
    async def _unregister_webhook(self, agent_id: str):
        """Unregister agent's webhooks from WAHA"""
        import httpx
        
        waha_base_url = os.getenv("WAHA_BASE_URL", "http://localhost:4500")
        waha_api_key = os.getenv("WAHA_API_KEY", "")
        
        headers = {
            "X-Api-Key": waha_api_key
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Get current webhooks
                response = await client.get(
                    f"{waha_base_url}/api/webhook",
                    headers=headers
                )
                response.raise_for_status()
                webhooks = response.json()
                
                # Find and remove this agent's webhook
                for webhook in webhooks:
                    if f"agent_{agent_id}" in webhook.get("hmac", {}).get("key", ""):
                        # Delete this webhook
                        await client.delete(
                            f"{waha_base_url}/api/webhook/{webhook['id']}",
                            headers=headers
                        )
                        logger.info(f"Unregistered webhook for agent {agent_id}")
                        break
            except Exception as e:
                logger.error(f"Failed to unregister webhook: {str(e)}")

# Global agent manager instance
agent_manager = AgentManager()