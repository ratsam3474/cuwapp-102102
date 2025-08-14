"""
Tool Models and Registry
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum

class ToolCategory(str, Enum):
    WAHA = "waha"
    MCP = "mcp"
    CUSTOM = "custom"
    BUILTIN = "builtin"

class ToolParameter(BaseModel):
    name: str
    type: str  # string, number, boolean, object, array
    description: str
    required: bool = False
    default: Optional[Any] = None

class ToolDefinition(BaseModel):
    id: str  # Unique identifier
    name: str  # Display name
    category: ToolCategory
    description: str
    
    # For WAHA tools
    endpoint: Optional[str] = None  # API endpoint path
    method: Optional[str] = None  # HTTP method
    
    # Parameters
    parameters: List[ToolParameter] = Field(default_factory=list)
    
    # Examples and metadata
    example: Optional[Dict] = None
    tags: List[str] = Field(default_factory=list)
    
    # For custom tools
    function_code: Optional[str] = None  # Python code for custom functions
    
    # For MCP tools
    mcp_server: Optional[str] = None
    mcp_method: Optional[str] = None

# WAHA Tools based on OpenAPI spec
WAHA_TOOLS = [
    # Messaging Tools
    ToolDefinition(
        id="send_text",
        name="Send Text Message",
        category=ToolCategory.WAHA,
        description="Send a text message to a chat",
        endpoint="/api/sendText",
        method="POST",
        parameters=[
            ToolParameter(name="chatId", type="string", description="Chat or phone number ID", required=True),
            ToolParameter(name="text", type="string", description="Message text to send", required=True),
            ToolParameter(name="session", type="string", description="WhatsApp session", default="default")
        ],
        tags=["messaging", "core"]
    ),
    ToolDefinition(
        id="send_image",
        name="Send Image",
        category=ToolCategory.WAHA,
        description="Send an image with optional caption",
        endpoint="/api/sendImage",
        method="POST",
        parameters=[
            ToolParameter(name="chatId", type="string", description="Chat or phone number ID", required=True),
            ToolParameter(name="file", type="object", description="Image file or URL", required=True),
            ToolParameter(name="caption", type="string", description="Optional image caption"),
            ToolParameter(name="session", type="string", description="WhatsApp session", default="default")
        ],
        tags=["messaging", "media"]
    ),
    ToolDefinition(
        id="send_file",
        name="Send File/Document",
        category=ToolCategory.WAHA,
        description="Send a file or document",
        endpoint="/api/sendFile",
        method="POST",
        parameters=[
            ToolParameter(name="chatId", type="string", description="Chat or phone number ID", required=True),
            ToolParameter(name="file", type="object", description="File data or URL", required=True),
            ToolParameter(name="session", type="string", description="WhatsApp session", default="default")
        ],
        tags=["messaging", "media"]
    ),
    
    # Group Management Tools
    ToolDefinition(
        id="create_group",
        name="Create Group",
        category=ToolCategory.WAHA,
        description="Create a new WhatsApp group",
        endpoint="/api/{session}/groups",
        method="POST",
        parameters=[
            ToolParameter(name="name", type="string", description="Group name", required=True),
            ToolParameter(name="participants", type="array", description="Initial participants", required=True)
        ],
        tags=["groups", "management"]
    ),
    ToolDefinition(
        id="add_participants",
        name="Add Group Participants",
        category=ToolCategory.WAHA,
        description="Add participants to a group",
        endpoint="/api/{session}/groups/{id}/participants/add",
        method="POST",
        parameters=[
            ToolParameter(name="groupId", type="string", description="Group ID", required=True),
            ToolParameter(name="participants", type="array", description="Participants to add", required=True)
        ],
        tags=["groups", "participants"]
    ),
    ToolDefinition(
        id="remove_participants",
        name="Remove Group Participants",
        category=ToolCategory.WAHA,
        description="Remove participants from a group",
        endpoint="/api/{session}/groups/{id}/participants/remove",
        method="POST",
        parameters=[
            ToolParameter(name="groupId", type="string", description="Group ID", required=True),
            ToolParameter(name="participants", type="array", description="Participants to remove", required=True)
        ],
        tags=["groups", "participants"]
    ),
    ToolDefinition(
        id="get_group_info",
        name="Get Group Information",
        category=ToolCategory.WAHA,
        description="Get detailed information about a group",
        endpoint="/api/{session}/groups/{id}",
        method="GET",
        parameters=[
            ToolParameter(name="groupId", type="string", description="Group ID", required=True)
        ],
        tags=["groups", "info"]
    ),
    
    # Contact Management
    ToolDefinition(
        id="check_number_exists",
        name="Check if Number Exists",
        category=ToolCategory.WAHA,
        description="Check if a phone number is registered on WhatsApp",
        endpoint="/api/contacts/check-exists",
        method="GET",
        parameters=[
            ToolParameter(name="phone", type="string", description="Phone number to check", required=True),
            ToolParameter(name="session", type="string", description="WhatsApp session", default="default")
        ],
        tags=["contacts", "validation"]
    ),
    ToolDefinition(
        id="get_contact_info",
        name="Get Contact Information",
        category=ToolCategory.WAHA,
        description="Get contact details including profile picture and about",
        endpoint="/api/contacts",
        method="GET",
        parameters=[
            ToolParameter(name="contactId", type="string", description="Contact ID", required=True),
            ToolParameter(name="session", type="string", description="WhatsApp session", default="default")
        ],
        tags=["contacts", "info"]
    ),
    
    # Chat Management
    ToolDefinition(
        id="get_messages",
        name="Get Chat Messages",
        category=ToolCategory.WAHA,
        description="Retrieve messages from a chat",
        endpoint="/api/{session}/chats/{chatId}/messages",
        method="GET",
        parameters=[
            ToolParameter(name="chatId", type="string", description="Chat ID", required=True),
            ToolParameter(name="limit", type="number", description="Number of messages", default=50),
            ToolParameter(name="offset", type="number", description="Skip messages", default=0)
        ],
        tags=["chats", "messages"]
    ),
    
    # Status/Presence
    ToolDefinition(
        id="send_seen",
        name="Mark Messages as Read",
        category=ToolCategory.WAHA,
        description="Mark messages as read/seen",
        endpoint="/api/sendSeen",
        method="POST",
        parameters=[
            ToolParameter(name="chatId", type="string", description="Chat ID", required=True),
            ToolParameter(name="messageId", type="string", description="Message ID to mark as read", required=True),
            ToolParameter(name="session", type="string", description="WhatsApp session", default="default")
        ],
        tags=["messaging", "status"]
    ),
    
    # Add more WAHA tools here...
    # Total: 126 tools from all endpoints
]

# Built-in ADK Tools
BUILTIN_TOOLS = [
    ToolDefinition(
        id="google_search",
        name="Google Search",
        category=ToolCategory.BUILTIN,
        description="Search the web using Google",
        parameters=[
            ToolParameter(name="query", type="string", description="Search query", required=True),
            ToolParameter(name="num_results", type="number", description="Number of results", default=5)
        ],
        tags=["search", "web"]
    ),
    ToolDefinition(
        id="code_execution",
        name="Code Execution",
        category=ToolCategory.BUILTIN,
        description="Execute Python code in a sandboxed environment",
        parameters=[
            ToolParameter(name="code", type="string", description="Python code to execute", required=True)
        ],
        tags=["code", "computation"]
    ),
    ToolDefinition(
        id="vertex_search",
        name="Vertex AI Search",
        category=ToolCategory.BUILTIN,
        description="Search through indexed documents using Vertex AI",
        parameters=[
            ToolParameter(name="query", type="string", description="Search query", required=True),
            ToolParameter(name="data_store", type="string", description="Data store ID", required=True)
        ],
        tags=["search", "ai"]
    ),
]

class ToolRegistry:
    """Registry for all available tools"""
    
    _waha_tools: Dict[str, ToolDefinition] = {}
    _builtin_tools: Dict[str, ToolDefinition] = {}
    _custom_tools: Dict[str, ToolDefinition] = {}
    _mcp_tools: Dict[str, ToolDefinition] = {}
    
    @classmethod
    def initialize(cls):
        """Initialize the tool registry with all available tools"""
        # Load WAHA tools
        for tool in WAHA_TOOLS:
            cls._waha_tools[tool.id] = tool
            
        # Load built-in tools
        for tool in BUILTIN_TOOLS:
            cls._builtin_tools[tool.id] = tool
    
    @classmethod
    def get_all_tools(cls) -> Dict[str, List[ToolDefinition]]:
        """Get all tools organized by category"""
        return {
            "waha": list(cls._waha_tools.values()),
            "builtin": list(cls._builtin_tools.values()),
            "custom": list(cls._custom_tools.values()),
            "mcp": list(cls._mcp_tools.values())
        }
    
    @classmethod
    def get_tool(cls, tool_id: str, category: ToolCategory) -> Optional[ToolDefinition]:
        """Get a specific tool by ID and category"""
        registry_map = {
            ToolCategory.WAHA: cls._waha_tools,
            ToolCategory.BUILTIN: cls._builtin_tools,
            ToolCategory.CUSTOM: cls._custom_tools,
            ToolCategory.MCP: cls._mcp_tools
        }
        return registry_map[category].get(tool_id)
    
    @classmethod
    def add_custom_tool(cls, tool: ToolDefinition):
        """Add a custom tool to the registry"""
        cls._custom_tools[tool.id] = tool
    
    @classmethod
    def add_mcp_tool(cls, tool: ToolDefinition):
        """Add an MCP tool to the registry"""
        cls._mcp_tools[tool.id] = tool