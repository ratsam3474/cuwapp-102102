"""
WebSocket endpoint for real-time campaign updates
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for campaign updates"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.campaign_subscribers: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept new WebSocket connection"""
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()
        self.active_connections[client_id].add(websocket)
        logger.info(f"WebSocket connected: {client_id}")
    
    def disconnect(self, websocket: WebSocket, client_id: str):
        """Remove WebSocket connection"""
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        
        # Remove from campaign subscribers
        for campaign_id, subscribers in list(self.campaign_subscribers.items()):
            subscribers.discard(websocket)
            if not subscribers:
                del self.campaign_subscribers[campaign_id]
        
        logger.info(f"WebSocket disconnected: {client_id}")
    
    async def subscribe_to_campaign(self, websocket: WebSocket, campaign_id: int):
        """Subscribe to campaign updates"""
        if campaign_id not in self.campaign_subscribers:
            self.campaign_subscribers[campaign_id] = set()
        self.campaign_subscribers[campaign_id].add(websocket)
        logger.info(f"Subscribed to campaign {campaign_id}")
    
    async def unsubscribe_from_campaign(self, websocket: WebSocket, campaign_id: int):
        """Unsubscribe from campaign updates"""
        if campaign_id in self.campaign_subscribers:
            self.campaign_subscribers[campaign_id].discard(websocket)
            if not self.campaign_subscribers[campaign_id]:
                del self.campaign_subscribers[campaign_id]
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific connection"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def broadcast_campaign_update(self, campaign_id: int, data: dict):
        """Broadcast update to all subscribers of a campaign"""
        if campaign_id in self.campaign_subscribers:
            message = json.dumps({
                "type": "campaign_update",
                "campaign_id": campaign_id,
                "data": data
            })
            
            dead_connections = set()
            for connection in self.campaign_subscribers[campaign_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to connection: {e}")
                    dead_connections.add(connection)
            
            # Remove dead connections
            for conn in dead_connections:
                self.campaign_subscribers[campaign_id].discard(conn)

# Global connection manager
manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    """WebSocket endpoint for real-time updates"""
    if not client_id:
        client_id = str(id(websocket))
    
    await manager.connect(websocket, client_id)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to WhatsApp Agent WebSocket",
            "client_id": client_id
        })
        
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            
            action = data.get("action")
            
            if action == "ping":
                # Respond to ping
                await websocket.send_json({"type": "pong"})
            
            elif action == "subscribe":
                # Subscribe to campaign updates
                campaign_id = data.get("campaign_id")
                if campaign_id:
                    await manager.subscribe_to_campaign(websocket, campaign_id)
                    await websocket.send_json({
                        "type": "subscribed",
                        "campaign_id": campaign_id
                    })
            
            elif action == "unsubscribe":
                # Unsubscribe from campaign updates
                campaign_id = data.get("campaign_id")
                if campaign_id:
                    await manager.unsubscribe_from_campaign(websocket, campaign_id)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "campaign_id": campaign_id
                    })
            
            elif action == "get_status":
                # Get current connection status
                await websocket.send_json({
                    "type": "status",
                    "connected_clients": len(manager.active_connections),
                    "subscribed_campaigns": list(manager.campaign_subscribers.keys())
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, client_id)

# Helper function to send updates from other parts of the application
async def notify_campaign_progress(campaign_id: int, progress_data: dict):
    """Send campaign progress update to all subscribers"""
    await manager.broadcast_campaign_update(campaign_id, progress_data)

# Example usage in message processor:
# await notify_campaign_progress(campaign_id, {
#     "processed": 50,
#     "total": 100,
#     "success": 48,
#     "failed": 2,
#     "current_message": "Processing row 51..."
# })
