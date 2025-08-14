"""
DigitalOcean Function client for WAHA orchestration
"""
import os
import json
import logging
import requests
from typing import List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)

class PlanType(Enum):
    FREE = "free"
    STARTER = "starter"
    HOBBY = "hobby"
    PRO = "pro"
    PREMIUM = "premium"
    ADMIN = "admin"

class DOWahaClient:
    """Client for DigitalOcean Function WAHA orchestration"""
    
    def __init__(self):
        # Get DO Function URL from environment or use default
        self.function_url = os.getenv(
            "DO_WAHA_FUNCTION_URL",
            "https://faas-nyc1-2ef2e6cc.doserverless.co/api/v1/web/fn-a71361db-f473-4bce-a159-0c0d9d3aa3b5/waha-manager/waha-manager"
        )
        # Docker droplet IP
        self.docker_host = os.getenv("DOCKER_DROPLET_IP", "localhost")
        
    async def create_user_instances(self, user_id: str, plan_type: PlanType) -> List[str]:
        """Create WAHA instances for a user based on plan via DO Function"""
        
        # Plan configurations
        plan_configs = {
            PlanType.FREE: {
                "instances": 0,  # Use shared instance
                "max_sessions": 1,
            },
            PlanType.STARTER: {
                "instances": 1,
                "max_sessions": 1,
            },
            PlanType.HOBBY: {
                "instances": 1,
                "max_sessions": 3,
            },
            PlanType.PRO: {
                "instances": 1,
                "max_sessions": 10,
            },
            PlanType.PREMIUM: {
                "instances": 3,
                "max_sessions": 10,  # Per instance
            },
            PlanType.ADMIN: {
                "instances": 1,
                "max_sessions": 100,
            }
        }
        
        config = plan_configs.get(plan_type, plan_configs[PlanType.FREE])
        instance_endpoints = []
        
        if plan_type == PlanType.FREE:
            # Free users use shared instance on port 4500
            logger.info(f"User {user_id} is on FREE plan, using shared instance")
            return [f"http://{self.docker_host}:4500"]
        
        # For paid plans, create dedicated instances
        num_instances = config["instances"]
        max_sessions = config["max_sessions"]
        
        for i in range(num_instances):
            try:
                # Call DO Function to create instance
                payload = {
                    "action": "create",
                    "docker_host": self.docker_host,
                    "image": "devlikeapro/waha-plus:latest",
                    "user_id": user_id,
                    "plan_type": plan_type.value,
                    "max_sessions": max_sessions
                }
                
                logger.info(f"Creating WAHA instance {i+1}/{num_instances} for user {user_id}")
                
                response = requests.post(
                    self.function_url,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("body", {}).get("success"):
                        instance = result["body"]["instance"]
                        endpoint = instance["endpoint"]
                        port = instance["port"]
                        
                        logger.info(f"Created WAHA instance on port {port} for user {user_id}")
                        instance_endpoints.append(endpoint)
                    else:
                        error = result.get("body", {}).get("error", "Unknown error")
                        logger.error(f"Failed to create instance: {error}")
                else:
                    logger.error(f"DO Function returned status {response.status_code}: {response.text}")
                    
            except Exception as e:
                logger.error(f"Error creating instance via DO Function: {e}")
        
        return instance_endpoints
    
    async def destroy_user_instances(self, user_id: str, ports: List[int]) -> bool:
        """Destroy WAHA instances for a user"""
        
        success = True
        for port in ports:
            try:
                payload = {
                    "action": "destroy",
                    "docker_host": self.docker_host,
                    "port": port
                }
                
                response = requests.post(
                    self.function_url,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    logger.info(f"Destroyed WAHA instance on port {port}")
                else:
                    logger.error(f"Failed to destroy instance on port {port}")
                    success = False
                    
            except Exception as e:
                logger.error(f"Error destroying instance: {e}")
                success = False
        
        return success
    
    async def list_instances(self) -> List[Dict[str, Any]]:
        """List all WAHA instances"""
        
        try:
            payload = {
                "action": "list",
                "docker_host": self.docker_host
            }
            
            response = requests.post(
                self.function_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("body", {}).get("success"):
                    return result["body"]["instances"]
            
            return []
            
        except Exception as e:
            logger.error(f"Error listing instances: {e}")
            return []