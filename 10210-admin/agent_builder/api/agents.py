"""
Agent CRUD and lifecycle API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid

from agent_builder.database.connection import get_db
from agent_builder.models.agent import (
    Agent, AgentCreate, AgentResponse, AgentUpdate, AgentStatus
)
from agent_builder.core.agent_manager import agent_manager

router = APIRouter(prefix="/api/agents", tags=["agents"])

@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    session: AsyncSession = Depends(get_db),
    status: Optional[AgentStatus] = None
):
    """List all agents with optional status filter"""
    query = select(Agent)
    if status:
        query = query.where(Agent.status == status)
    
    result = await session.execute(query)
    agents = result.scalars().all()
    
    # Convert to response model
    return [AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        status=agent.status,
        triggers=agent.triggers,
        trigger_instructions=agent.trigger_instructions or {},
        additional_instructions=agent.additional_instructions,
        tools={
            "waha_tools": agent.waha_tools or [],
            "builtin_tools": agent.builtin_tools or [],
            "mcp_tools": agent.mcp_tools or [],
            "custom_tools": agent.custom_tools or []
        },
        model=agent.model,
        temperature=float(agent.temperature),
        port=agent.port,
        webhook_url=agent.webhook_url,
        created_at=agent.created_at,
        updated_at=agent.updated_at
    ) for agent in agents]

@router.post("/", response_model=AgentResponse)
async def create_agent(
    agent_data: AgentCreate,
    session: AsyncSession = Depends(get_db)
):
    """Create a new agent"""
    # Create agent instance
    agent = Agent(
        id=str(uuid.uuid4()),
        name=agent_data.name,
        description=agent_data.description,
        status=AgentStatus.DRAFT,
        triggers=agent_data.triggers,
        trigger_instructions=agent_data.trigger_instructions,
        additional_instructions=agent_data.additional_instructions,
        waha_tools=agent_data.tools.waha_tools,
        builtin_tools=agent_data.tools.builtin_tools,
        mcp_tools=agent_data.tools.mcp_tools,
        custom_tools=agent_data.tools.custom_tools,
        knowledge_base=agent_data.knowledge_base,
        model=agent_data.model,
        temperature=str(agent_data.temperature),
        max_tokens=agent_data.max_tokens,
        whatsapp_session=agent_data.whatsapp_session
    )
    
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        status=agent.status,
        triggers=agent.triggers,
        trigger_instructions=agent.trigger_instructions or {},
        additional_instructions=agent.additional_instructions,
        tools={
            "waha_tools": agent.waha_tools or [],
            "builtin_tools": agent.builtin_tools or [],
            "mcp_tools": agent.mcp_tools or [],
            "custom_tools": agent.custom_tools or []
        },
        model=agent.model,
        temperature=float(agent.temperature),
        port=agent.port,
        webhook_url=agent.webhook_url,
        created_at=agent.created_at,
        updated_at=agent.updated_at
    )

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_db)
):
    """Get a specific agent"""
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        status=agent.status,
        triggers=agent.triggers,
        trigger_instructions=agent.trigger_instructions or {},
        additional_instructions=agent.additional_instructions,
        tools={
            "waha_tools": agent.waha_tools or [],
            "builtin_tools": agent.builtin_tools or [],
            "mcp_tools": agent.mcp_tools or [],
            "custom_tools": agent.custom_tools or []
        },
        model=agent.model,
        temperature=float(agent.temperature),
        port=agent.port,
        webhook_url=agent.webhook_url,
        created_at=agent.created_at,
        updated_at=agent.updated_at
    )

@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_update: AgentUpdate,
    session: AsyncSession = Depends(get_db)
):
    """Update an agent"""
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update fields if provided
    if agent_update.name is not None:
        agent.name = agent_update.name
    if agent_update.description is not None:
        agent.description = agent_update.description
    if agent_update.triggers is not None:
        agent.triggers = agent_update.triggers
    if agent_update.trigger_instructions is not None:
        agent.trigger_instructions = agent_update.trigger_instructions
    if agent_update.additional_instructions is not None:
        agent.additional_instructions = agent_update.additional_instructions
    if agent_update.tools is not None:
        agent.waha_tools = agent_update.tools.waha_tools
        agent.builtin_tools = agent_update.tools.builtin_tools
        agent.mcp_tools = agent_update.tools.mcp_tools
        agent.custom_tools = agent_update.tools.custom_tools
    if agent_update.model is not None:
        agent.model = agent_update.model
    if agent_update.temperature is not None:
        agent.temperature = str(agent_update.temperature)
    if agent_update.max_tokens is not None:
        agent.max_tokens = agent_update.max_tokens
    
    await session.commit()
    await session.refresh(agent)
    
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        status=agent.status,
        triggers=agent.triggers,
        trigger_instructions=agent.trigger_instructions or {},
        additional_instructions=agent.additional_instructions,
        tools={
            "waha_tools": agent.waha_tools or [],
            "builtin_tools": agent.builtin_tools or [],
            "mcp_tools": agent.mcp_tools or [],
            "custom_tools": agent.custom_tools or []
        },
        model=agent.model,
        temperature=float(agent.temperature),
        port=agent.port,
        webhook_url=agent.webhook_url,
        created_at=agent.created_at,
        updated_at=agent.updated_at
    )

@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_db)
):
    """Delete an agent"""
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Stop agent if running
    if agent.status == AgentStatus.ACTIVE:
        await agent_manager.stop_agent(agent_id)
    
    await session.delete(agent)
    await session.commit()
    
    return {"success": True, "message": "Agent deleted"}

# Lifecycle endpoints
@router.post("/{agent_id}/start")
async def start_agent(agent_id: str):
    """Start an agent"""
    result = await agent_manager.start_agent(agent_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.post("/{agent_id}/stop")
async def stop_agent(agent_id: str):
    """Stop an agent"""
    result = await agent_manager.stop_agent(agent_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.post("/{agent_id}/pause")
async def pause_agent(agent_id: str):
    """Pause an agent"""
    result = await agent_manager.pause_agent(agent_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.post("/{agent_id}/resume")
async def resume_agent(agent_id: str):
    """Resume a paused agent"""
    result = await agent_manager.resume_agent(agent_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.post("/{agent_id}/restart")
async def restart_agent(agent_id: str):
    """Restart an agent"""
    result = await agent_manager.restart_agent(agent_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.get("/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """Get agent runtime status"""
    return await agent_manager.get_agent_status(agent_id)

@router.get("/{agent_id}/logs")
async def get_agent_logs(
    agent_id: str,
    lines: int = Query(100, description="Number of log lines to return")
):
    """Get agent logs"""
    logs = await agent_manager.get_agent_logs(agent_id, lines)
    return {"logs": logs}