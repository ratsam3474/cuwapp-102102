"""
WAHA Orchestrator Service
Manages dynamic WAHA instances inside Docker container
"""

import asyncio
import docker
import json
import logging
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
import redis
from database.subscription_models import PlanType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WAHA Orchestrator", version="1.0.0")

class WAHARequest(BaseModel):
    user_id: str
    plan_type: str
    action: str  # create, destroy, get_url

class WAHAResponse(BaseModel):
    success: bool
    instance_urls: List[str] = []
    message: str = ""

class WAHAOrchestrator:
    def __init__(self):
        self.docker_client = None
        self.redis_client = None
        self.user_instances: Dict[str, List[str]] = {}
        self.port_manager = PortManager()
        
    async def initialize(self):
        """Initialize Docker and Redis connections"""
        try:
            # Wait for Docker daemon to be ready
            await asyncio.sleep(5)
            
            # Initialize Docker client
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized")
            
            # Initialize Redis for state management
            redis_host = os.getenv('REDIS_HOST', 'redis')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            
            self.redis_client = redis.Redis(
                host=redis_host, 
                port=redis_port, 
                decode_responses=True
            )
            logger.info("Redis client initialized")
            
            # Load existing state
            await self.load_state()
            
            # Create shared free instance
            await self.ensure_free_instance()
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise
    
    async def load_state(self):
        """Load instance state from Redis"""
        try:
            state_data = self.redis_client.get("waha:user_instances")
            if state_data:
                self.user_instances = json.loads(state_data)
                logger.info(f"Loaded state for {len(self.user_instances)} users")
        except Exception as e:
            logger.warning(f"Failed to load state: {e}")
    
    async def save_state(self):
        """Save instance state to Redis"""
        try:
            self.redis_client.set("waha:user_instances", json.dumps(self.user_instances))
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def get_instance_port(self, user_id: str, plan_type: PlanType) -> int:
        """Get port for WAHA instance"""
        if plan_type == PlanType.FREE:
            return 4500  # Shared instance
        elif plan_type == PlanType.ADMIN:
            return 9000  # Admin instance
        else:
            # Generate unique port for paid users
            user_hash = abs(hash(user_id)) % 4498
            return 4501 + user_hash
    
    def get_instance_name(self, user_id: str, plan_type: PlanType, instance_index: int = 0) -> str:
        """Generate instance name"""
        if plan_type == PlanType.FREE:
            return "cuwhapp-waha-shared-free"
        elif plan_type == PlanType.ADMIN:
            return "cuwhapp-waha-admin"
        else:
            if instance_index == 0:
                return f"cuwhapp-waha-{user_id[:8]}"
            return f"cuwhapp-waha-{user_id[:8]}-{instance_index}"
    
    async def ensure_free_instance(self):
        """Ensure the shared free instance exists"""
        instance_name = "cuwhapp-waha-shared-free"
        
        try:
            container = self.docker_client.containers.get(instance_name)
            if container.status == 'running':
                logger.info("Free shared instance already running")
                return
            else:
                container.remove()
        except docker.errors.NotFound:
            pass
        
        # Create shared free instance
        await self.create_instance(
            instance_name=instance_name,
            port=4500,
            plan_type=PlanType.FREE,
            max_sessions=1000,  # Support up to 1000 free users
            cpu_limit="4.0",
            memory_limit="3800m"
        )
        
        logger.info("Created shared free WAHA instance")
    
    async def ensure_waha_image(self):
        """Ensure WAHA Plus image is available"""
        try:
            # Check if image exists locally
            self.docker_client.images.get("devlikeapro/waha-plus:latest")
            logger.info("WAHA Plus image already available locally")
        except docker.errors.ImageNotFound:
            logger.info("WAHA Plus image not found locally, pulling...")
            try:
                # Login and pull image
                import subprocess
                docker_username = os.getenv('WAHA_DOCKER_USERNAME', 'devlikeapro')
                docker_password = os.getenv('WAHA_DOCKER_PASSWORD')
                
                subprocess.run([
                    "docker", "login", "-u", docker_username, 
                    "-p", docker_password
                ], check=True)
                
                self.docker_client.images.pull("devlikeapro/waha-plus:latest")
                logger.info("WAHA Plus image pulled successfully")
                
                # Logout for security
                subprocess.run(["docker", "logout"], check=True)
                
            except Exception as e:
                logger.error(f"Failed to pull WAHA Plus image: {e}")
                raise

    async def create_instance(
        self, 
        instance_name: str, 
        port: int,
        plan_type: PlanType,
        max_sessions: int,
        cpu_limit: str,
        memory_limit: str,
        user_id: str = "shared"
    ) -> str:
        """Create a WAHA instance"""
        
        # Ensure WAHA image is available
        await self.ensure_waha_image()
        
        # Environment variables
        environment = {
            "WAHA_PRINT_QR": "false",
            "WAHA_LOG_LEVEL": "info",
            "WAHA_API_KEY": os.getenv('WAHA_API_KEY', 'waha_secure_key'),
            "WAHA_API_KEY_HEADER": "X-API-Key",
            "WAHA_SESSION_STORE_ENABLED": "true",
            "WAHA_SESSION_STORE_PATH": "/app/sessions",
            "WAHA_WEBHOOK_URL": f"http://cuwhapp-main:8000/api/waha/webhook",
            "WAHA_WEBHOOK_EVENTS": "message,session.status",
            "WAHA_FILES_MIMETYPES": "audio,image,video,document",
            "WAHA_FILES_LIFETIME": "180",
            "WAHA_MAX_SESSIONS": str(max_sessions),
            "WAHA_PLAN_TYPE": plan_type.value,
            "WAHA_PORT": str(port)
        }
        
        # Volume mounts
        volumes = {
            f"waha_sessions_{instance_name}": {"bind": "/app/sessions", "mode": "rw"},
            f"waha_files_{instance_name}": {"bind": "/app/files", "mode": "rw"}
        }
        
        try:
            container = self.docker_client.containers.run(
                image="devlikeapro/waha-plus:latest",
                name=instance_name,
                ports={f"3000/tcp": port},
                environment=environment,
                volumes=volumes,
                network_mode="container:cuwhapp-main",  # Share network with main app
                restart_policy={"Name": "unless-stopped"},
                detach=True,
                # Resource limits
                mem_limit=memory_limit,
                cpus=cpu_limit,
                labels={
                    "cuwhapp.service": "waha",
                    "cuwhapp.user_id": user_id,
                    "cuwhapp.plan_type": plan_type.value,
                    "cuwhapp.port": str(port)
                }
            )
            
            logger.info(f"Created WAHA instance {instance_name} on port {port}")
            return instance_name
            
        except Exception as e:
            logger.error(f"Failed to create WAHA instance {instance_name}: {e}")
            raise
    
    async def create_user_instances(self, user_id: str, plan_type: PlanType) -> List[str]:
        """Create WAHA instances for a user based on plan"""
        
        # Plan configurations
        plan_configs = {
            PlanType.FREE: {
                "instances": 0,  # Use shared instance
                "max_sessions": 1,
                "cpu_limit": "0.1",  # Minimal since it's shared
                "memory_limit": "100m"
            },
            PlanType.STARTER: {
                "instances": 1,
                "max_sessions": 1,
                "cpu_limit": "0.4",
                "memory_limit": "400m"
            },
            PlanType.HOBBY: {
                "instances": 1,
                "max_sessions": 3,
                "cpu_limit": "1.2",
                "memory_limit": "1200m"
            },
            PlanType.PRO: {
                "instances": 1,
                "max_sessions": 10,
                "cpu_limit": "4.0",
                "memory_limit": "3800m"
            },
            PlanType.PREMIUM: {
                "instances": 3,
                "max_sessions": 10,  # Per instance
                "cpu_limit": "4.0",
                "memory_limit": "3800m"
            },
            PlanType.ADMIN: {
                "instances": 1,
                "max_sessions": 100,
                "cpu_limit": "8.0",
                "memory_limit": "8000m"
            }
        }
        
        config = plan_configs.get(plan_type, plan_configs[PlanType.FREE])
        instance_names = []
        
        if plan_type == PlanType.FREE:
            # Free users use shared instance
            instance_names = ["cuwhapp-waha-shared-free"]
        else:
            # Create dedicated instances
            for i in range(config["instances"]):
                port = self.get_instance_port(user_id, plan_type) + i
                instance_name = self.get_instance_name(user_id, plan_type, i)
                
                try:
                    await self.create_instance(
                        instance_name=instance_name,
                        port=port,
                        plan_type=plan_type,
                        max_sessions=config["max_sessions"],
                        cpu_limit=config["cpu_limit"],
                        memory_limit=config["memory_limit"],
                        user_id=user_id
                    )
                    instance_names.append(instance_name)
                    
                except Exception as e:
                    logger.error(f"Failed to create instance {instance_name}: {e}")
        
        # Update user mapping
        self.user_instances[user_id] = instance_names
        await self.save_state()
        
        return instance_names
    
    async def get_user_instance_urls(self, user_id: str) -> List[str]:
        """Get URLs for user's WAHA instances"""
        if user_id not in self.user_instances:
            return []
        
        urls = []
        for instance_name in self.user_instances[user_id]:
            try:
                container = self.docker_client.containers.get(instance_name)
                port_info = container.attrs['NetworkSettings']['Ports']
                
                if '3000/tcp' in port_info and port_info['3000/tcp']:
                    port = port_info['3000/tcp'][0]['HostPort']
                    urls.append(f"http://localhost:{port}")
                else:
                    urls.append(f"http://{instance_name}:3000")
                    
            except Exception as e:
                logger.error(f"Failed to get URL for {instance_name}: {e}")
        
        return urls
    
    async def destroy_user_instances(self, user_id: str) -> bool:
        """Destroy all instances for a user"""
        if user_id not in self.user_instances:
            return True
        
        try:
            for instance_name in self.user_instances[user_id]:
                if instance_name.startswith("cuwhapp-waha-shared"):
                    continue  # Don't destroy shared instances
                
                try:
                    container = self.docker_client.containers.get(instance_name)
                    container.stop(timeout=10)
                    container.remove()
                    logger.info(f"Destroyed instance {instance_name}")
                except docker.errors.NotFound:
                    pass
                except Exception as e:
                    logger.error(f"Failed to destroy {instance_name}: {e}")
            
            # Remove from mapping
            del self.user_instances[user_id]
            await self.save_state()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to destroy instances for user {user_id}: {e}")
            return False
    
    async def get_stats(self) -> Dict:
        """Get orchestrator statistics"""
        containers = self.docker_client.containers.list(
            all=True, 
            filters={"label": "cuwhapp.service=waha"}
        )
        
        stats = {
            "total_instances": len(containers),
            "running_instances": len([c for c in containers if c.status == 'running']),
            "total_users": len(self.user_instances),
            "instances_by_plan": {},
            "port_usage": {}
        }
        
        for container in containers:
            labels = container.labels
            plan_type = labels.get('cuwhapp.plan_type', 'unknown')
            port = labels.get('cuwhapp.port', 'unknown')
            
            if plan_type not in stats["instances_by_plan"]:
                stats["instances_by_plan"][plan_type] = 0
            stats["instances_by_plan"][plan_type] += 1
            
            stats["port_usage"][port] = container.name
        
        return stats

class PortManager:
    def __init__(self):
        self.allocated_ports = set()
        self.port_range = (4501, 8999)  # For paid users
    
    def allocate_port(self, user_id: str) -> int:
        """Allocate a unique port for user"""
        user_hash = abs(hash(user_id)) % (self.port_range[1] - self.port_range[0])
        port = self.port_range[0] + user_hash
        
        # Ensure uniqueness
        while port in self.allocated_ports:
            port += 1
            if port > self.port_range[1]:
                port = self.port_range[0]
        
        self.allocated_ports.add(port)
        return port
    
    def free_port(self, port: int):
        """Free an allocated port"""
        self.allocated_ports.discard(port)

# Global orchestrator instance
orchestrator = WAHAOrchestrator()

@app.on_event("startup")
async def startup():
    """Initialize orchestrator on startup"""
    await orchestrator.initialize()

@app.post("/waha/manage", response_model=WAHAResponse)
async def manage_waha_instance(request: WAHARequest):
    """Manage WAHA instances"""
    try:
        plan_type = PlanType(request.plan_type.lower())
        
        if request.action == "create":
            instance_names = await orchestrator.create_user_instances(
                request.user_id, plan_type
            )
            urls = await orchestrator.get_user_instance_urls(request.user_id)
            
            return WAHAResponse(
                success=True,
                instance_urls=urls,
                message=f"Created {len(instance_names)} instances for {plan_type.value} plan"
            )
        
        elif request.action == "get_url":
            urls = await orchestrator.get_user_instance_urls(request.user_id)
            return WAHAResponse(
                success=True,
                instance_urls=urls,
                message="Retrieved instance URLs"
            )
        
        elif request.action == "destroy":
            success = await orchestrator.destroy_user_instances(request.user_id)
            return WAHAResponse(
                success=success,
                message="Destroyed user instances" if success else "Failed to destroy instances"
            )
        
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
    
    except Exception as e:
        logger.error(f"Failed to manage WAHA instance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/waha/stats")
async def get_waha_stats():
    """Get WAHA orchestrator statistics"""
    return await orchestrator.get_stats()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "waha-orchestrator"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)