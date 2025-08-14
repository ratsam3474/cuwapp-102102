"""
Webhook handler for routing WAHA events to appropriate sub-agents
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from agent_builder.database.connection import AsyncSessionLocal
from agent_builder.models.agent import Agent
from agent_builder.core.langchain_agent import AgentFactory

logger = logging.getLogger(__name__)

class WebhookHandler:
    """Handles incoming WAHA webhooks and routes to agents"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.agent: Optional[Agent] = None
        self.orchestrator = None
        self.pause_check_enabled = True
        
    async def initialize(self):
        """Initialize the webhook handler"""
        # Load agent configuration
        async with AsyncSessionLocal() as session:
            self.agent = await session.get(Agent, self.agent_id)
            if not self.agent:
                raise ValueError(f"Agent {self.agent_id} not found")
        
        # Create orchestrator
        self.orchestrator = AgentFactory.create_agent(self.agent)
        logger.info(f"Initialized webhook handler for agent {self.agent_id}")
    
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming webhook"""
        try:
            # Check if paused (Windows compatibility)
            if self.pause_check_enabled:
                from pathlib import Path
                pause_file = Path(f"data/agents/{self.agent_id}.pause")
                if pause_file.exists():
                    logger.info(f"Agent {self.agent_id} is paused, skipping webhook")
                    return {"status": "paused", "message": "Agent is paused"}
            
            # Extract event type from webhook
            event_type = webhook_data.get("event")
            if not event_type:
                return {"error": "No event type in webhook"}
            
            # Log the webhook
            logger.info(f"Received webhook: {event_type} for agent {self.agent_id}")
            
            # Check if this agent handles this trigger
            if event_type not in [t.value for t in self.agent.triggers]:
                return {
                    "status": "ignored",
                    "message": f"Agent does not handle {event_type} events"
                }
            
            # Prepare input for orchestrator
            input_data = {
                "trigger_type": event_type,
                "webhook_data": webhook_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Execute the orchestrator
            result = await self.orchestrator.run_async(input_data)
            
            # Log result
            logger.info(f"Agent {self.agent_id} processed {event_type}: {result.get('success')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Webhook handler error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "agent_id": self.agent_id
            }
    
    async def update_session_context(self, context: Dict[str, Any]):
        """Update the orchestrator's session context"""
        if self.orchestrator:
            self.orchestrator.update_session_data(context)