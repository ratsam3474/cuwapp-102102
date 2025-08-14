"""
Tool wrappers to convert WAHA endpoints and other tools to LangChain-compatible format
"""
from typing import Dict, List, Optional, Any, Type
import httpx
import os
import json
from functools import wraps

from langchain.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field, create_model
from langchain.callbacks.manager import CallbackManagerForToolRun
import asyncio

# Get WAHA configuration
WAHA_BASE_URL = os.getenv("WAHA_BASE_URL", "http://localhost:4500")
WAHA_API_KEY = os.getenv("WAHA_API_KEY", "")

class WahaToolWrapper:
    """Wrapper to convert WAHA API endpoints to LangChain-compatible tools"""
    
    # Tool definitions mapped by ID
    TOOL_DEFINITIONS = {
        "send_text": {
            "endpoint": "/api/sendText",
            "method": "POST",
            "description": "Send a text message to a WhatsApp chat",
            "params": ["chatId", "text", "session"]
        },
        "send_image": {
            "endpoint": "/api/sendImage", 
            "method": "POST",
            "description": "Send an image with optional caption",
            "params": ["chatId", "file", "caption", "session"]
        },
        "send_file": {
            "endpoint": "/api/sendFile",
            "method": "POST", 
            "description": "Send a file or document",
            "params": ["chatId", "file", "session"]
        },
        "send_location": {
            "endpoint": "/api/sendLocation",
            "method": "POST",
            "description": "Send a location",
            "params": ["chatId", "latitude", "longitude", "session"]
        },
        "send_contact": {
            "endpoint": "/api/sendContactVcard",
            "method": "POST",
            "description": "Send a contact card",
            "params": ["chatId", "contactVcard", "session"]
        },
        "send_poll": {
            "endpoint": "/api/sendPoll",
            "method": "POST",
            "description": "Send a poll with options",
            "params": ["chatId", "name", "options", "session"]
        },
        "get_contacts": {
            "endpoint": "/api/contacts/all",
            "method": "GET",
            "description": "Get all contacts",
            "params": ["session"]
        },
        "check_number_exists": {
            "endpoint": "/api/contacts/check-exists",
            "method": "POST",
            "description": "Check if a phone number has WhatsApp",
            "params": ["phone", "session"]
        },
        "get_groups": {
            "endpoint": "/api/{session}/groups",
            "method": "GET",
            "description": "Get all groups",
            "params": ["session"]
        },
        "create_group": {
            "endpoint": "/api/{session}/groups",
            "method": "POST",
            "description": "Create a new group",
            "params": ["name", "participants", "session"]
        },
        "send_seen": {
            "endpoint": "/api/sendSeen",
            "method": "POST",
            "description": "Mark messages as read",
            "params": ["chatId", "session"]
        },
        "start_typing": {
            "endpoint": "/api/startTyping",
            "method": "POST",
            "description": "Show typing indicator",
            "params": ["chatId", "session"]
        },
        "stop_typing": {
            "endpoint": "/api/stopTyping",
            "method": "POST",
            "description": "Hide typing indicator",
            "params": ["chatId", "session"]
        },
        "react_message": {
            "endpoint": "/api/reaction",
            "method": "POST",
            "description": "Add reaction to a message",
            "params": ["messageId", "reaction", "session"]
        }
    }
    
    @classmethod
    def create_tool(cls, tool_id: str) -> Optional[BaseTool]:
        """Create a LangChain-compatible tool from WAHA endpoint"""
        if tool_id not in cls.TOOL_DEFINITIONS:
            return None
        
        definition = cls.TOOL_DEFINITIONS[tool_id]
        
        # Create dynamic input model based on parameters
        fields = {}
        for param in definition["params"]:
            if param == "session":
                fields[param] = (str, Field(default="default", description="WhatsApp session"))
            elif param == "options":
                fields[param] = (List[str], Field(..., description="List of poll options"))
            elif param == "participants":
                fields[param] = (List[str], Field(..., description="List of participant phone numbers"))
            elif param == "file":
                fields[param] = (Dict[str, Any], Field(..., description="File data or URL"))
            elif param in ["latitude", "longitude"]:
                fields[param] = (float, Field(..., description=f"Location {param}"))
            else:
                fields[param] = (str, Field(..., description=f"The {param}"))
        
        InputModel = create_model(f"{tool_id}_input", **fields)
        
        async def waha_tool_impl(
            **kwargs
        ) -> Dict[str, Any]:
            """Execute WAHA API call"""
            # Build URL
            endpoint = definition["endpoint"]
            session = kwargs.get("session", "default")
            
            # Replace session placeholder in URL if needed
            if "{session}" in endpoint:
                url = f"{WAHA_BASE_URL}{endpoint.format(session=session)}"
                # Remove session from body params
                body_params = {k: v for k, v in kwargs.items() if k != "session"}
            else:
                url = f"{WAHA_BASE_URL}{endpoint}"
                body_params = kwargs
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "X-Api-Key": WAHA_API_KEY
            }
            
            async with httpx.AsyncClient() as client:
                try:
                    if definition["method"] == "GET":
                        response = await client.get(url, headers=headers, params=body_params)
                    else:
                        response = await client.request(
                            method=definition["method"],
                            url=url,
                            headers=headers,
                            json=body_params
                        )
                    
                    response.raise_for_status()
                    
                    return {
                        "success": True,
                        "data": response.json() if response.text else None,
                        "status_code": response.status_code
                    }
                except httpx.HTTPError as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "status_code": getattr(e.response, "status_code", None)
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e)
                    }
        
        # Create sync wrapper
        def waha_tool(**kwargs) -> str:
            """Sync wrapper for async tool"""
            result = asyncio.run(waha_tool_impl(**kwargs))
            return json.dumps(result)
        
        # Create LangChain tool
        return StructuredTool(
            name=f"waha_{tool_id}",
            description=definition["description"],
            func=waha_tool,
            args_schema=InputModel
        )
    
    @classmethod
    def get_all_tools(cls) -> List[Dict[str, Any]]:
        """Get all available WAHA tools with metadata"""
        tools = []
        for tool_id, definition in cls.TOOL_DEFINITIONS.items():
            tools.append({
                "id": tool_id,
                "name": f"waha_{tool_id}",
                "description": definition["description"],
                "category": "waha",
                "params": definition["params"]
            })
        return tools

class BuiltinToolWrapper:
    """Wrapper for LangChain built-in tools"""
    
    @classmethod
    def create_tool(cls, tool_name: str) -> Optional[BaseTool]:
        """Get a LangChain built-in tool"""
        # Import on demand to avoid issues if not all are installed
        if tool_name == "google_search":
            try:
                from langchain_community.tools import GoogleSearchResults
                return GoogleSearchResults()
            except ImportError:
                print(f"GoogleSearchResults not available. Install langchain-google-community")
                return None
        elif tool_name == "python_repl":
            try:
                from langchain_community.tools import PythonREPLTool
                return PythonREPLTool()
            except ImportError:
                print(f"PythonREPLTool not available")
                return None
        
        return None
    
    @classmethod
    def get_all_tools(cls) -> List[Dict[str, Any]]:
        """Get all available built-in tools"""
        return [
            {
                "id": "google_search",
                "name": "Google Search",
                "description": "Search Google for information",
                "category": "builtin"
            },
            {
                "id": "python_repl",
                "name": "Python REPL",
                "description": "Execute Python code",
                "category": "builtin"
            }
        ]

class CustomToolWrapper:
    """Wrapper for custom Python function tools"""
    
    @staticmethod
    def create_tool_from_code(code: str, tool_name: str, description: str) -> Optional[BaseTool]:
        """Create a tool from custom Python code"""
        try:
            # Create a namespace for the function
            namespace = {}
            
            # Execute the code to define the function
            exec(code, namespace)
            
            # Find the function in the namespace
            for name, obj in namespace.items():
                if callable(obj) and not name.startswith("_"):
                    # Create LangChain tool
                    return StructuredTool(
                        name=tool_name,
                        description=description,
                        func=obj
                    )
            
            return None
        except Exception as e:
            print(f"Error creating custom tool: {str(e)}")
            return None

class MCPToolWrapper:
    """Wrapper for MCP (Model Context Protocol) tools"""
    
    @staticmethod
    def create_tool(mcp_config: Dict[str, Any]) -> Optional[BaseTool]:
        """Create a tool from MCP server configuration"""
        # TODO: Implement MCP tool creation when needed
        pass