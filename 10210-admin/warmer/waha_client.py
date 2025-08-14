"""
WAHA Client for Main Application
Interface to communicate with WAHA Orchestrator
"""

import aiohttp
import asyncio
import logging
from typing import List, Optional
from database.subscription_models import PlanType
import os

logger = logging.getLogger(__name__)

class WAHAClient:
    """Client to communicate with WAHA Orchestrator"""
    
    def __init__(self):
        self.orchestrator_url = os.getenv('WAHA_ORCHESTRATOR_URL', 'http://waha-orchestrator:8002')
        self.session = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def create_user_instance(self, user_id: str, plan_type: PlanType) -> List[str]:
        """Create WAHA instance(s) for user"""
        session = await self.get_session()
        
        try:
            payload = {
                "user_id": user_id,
                "plan_type": plan_type.value,
                "action": "create"
            }
            
            async with session.post(f"{self.orchestrator_url}/waha/manage", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('instance_urls', [])
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to create WAHA instance: {error_text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error creating WAHA instance: {e}")
            return []
    
    async def get_user_instance_urls(self, user_id: str) -> List[str]:
        """Get URLs for user's WAHA instances"""
        session = await self.get_session()
        
        try:
            payload = {
                "user_id": user_id,
                "plan_type": "free",  # Not used for get_url action
                "action": "get_url"
            }
            
            async with session.post(f"{self.orchestrator_url}/waha/manage", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('instance_urls', [])
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting WAHA instance URLs: {e}")
            return []
    
    async def destroy_user_instances(self, user_id: str) -> bool:
        """Destroy user's WAHA instances"""
        session = await self.get_session()
        
        try:
            payload = {
                "user_id": user_id,
                "plan_type": "free",  # Not used for destroy action
                "action": "destroy"
            }
            
            async with session.post(f"{self.orchestrator_url}/waha/manage", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('success', False)
                else:
                    return False
                    
        except Exception as e:
            logger.error(f"Error destroying WAHA instances: {e}")
            return False
    
    async def get_waha_stats(self) -> dict:
        """Get WAHA orchestrator statistics"""
        session = await self.get_session()
        
        try:
            async with session.get(f"{self.orchestrator_url}/waha/stats") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}
                    
        except Exception as e:
            logger.error(f"Error getting WAHA stats: {e}")
            return {}
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()

# Global WAHA client
waha_client = WAHAClient()