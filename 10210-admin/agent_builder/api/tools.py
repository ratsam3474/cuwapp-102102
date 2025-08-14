"""
Tools API - List available tools for agents
"""
from fastapi import APIRouter
from typing import List, Dict, Any

from agent_builder.core.tool_wrappers import WahaToolWrapper, BuiltinToolWrapper
from agent_builder.models.tools import WAHA_TOOLS, ToolCategory

router = APIRouter(prefix="/api/tools", tags=["tools"])

@router.get("/")
async def list_all_tools():
    """List all available tools grouped by category"""
    tools = {
        "waha": WahaToolWrapper.get_all_tools(),
        "builtin": BuiltinToolWrapper.get_all_tools(),
        "mcp": [],  # TODO: Implement MCP tool discovery
        "custom": []  # Custom tools are user-defined
    }
    return tools

@router.get("/waha")
async def list_waha_tools():
    """List all WAHA tools with details"""
    # Return extended tool definitions from models
    tools = []
    for tool in WAHA_TOOLS:
        tools.append({
            "id": tool.id,
            "name": tool.name,
            "description": tool.description,
            "endpoint": tool.endpoint,
            "method": tool.method,
            "parameters": [
                {
                    "name": param.name,
                    "type": param.type,
                    "description": param.description,
                    "required": param.required,
                    "default": param.default
                }
                for param in tool.parameters
            ],
            "tags": tool.tags
        })
    return tools

@router.get("/builtin")
async def list_builtin_tools():
    """List ADK built-in tools"""
    return BuiltinToolWrapper.get_all_tools()

@router.get("/categories")
async def list_tool_categories():
    """List all tool categories with descriptions"""
    return [
        {
            "id": ToolCategory.WAHA,
            "name": "WAHA Tools",
            "description": "WhatsApp API tools for messaging, groups, contacts",
            "icon": "📡"
        },
        {
            "id": ToolCategory.BUILTIN,
            "name": "Built-in Tools",
            "description": "ADK built-in tools like Google Search, Code Execution",
            "icon": "🛠️"
        },
        {
            "id": ToolCategory.MCP,
            "name": "MCP Tools",
            "description": "Model Context Protocol tools from external servers",
            "icon": "🔧"
        },
        {
            "id": ToolCategory.CUSTOM,
            "name": "Custom Tools",
            "description": "Custom Python functions you define",
            "icon": "⚡"
        }
    ]