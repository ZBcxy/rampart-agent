"""MCP Protocol Types and Message Definitions

Implements the Model Context Protocol (MCP) spec version 2024-11-05.
"""

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# JSON-RPC 2.0 base types
class JSONRPCVersion(str, Enum):
    V2 = "2.0"


@dataclass
class JSONRPCRequest:
    """Base JSON-RPC request."""
    jsonrpc: str = "2.0"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    method: str = ""
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JSONRPCResponse:
    """Base JSON-RPC response."""
    jsonrpc: str = "2.0"
    id: str = ""
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


# MCP-specific types
@dataclass
class ToolDefinition:
    """MCP tool definition schema."""
    name: str
    description: str = ""
    inputSchema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCallRequest:
    """Request to call a tool."""
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCallResult:
    """Result of a tool call."""
    content: List[Dict[str, Any]] = field(default_factory=list)
    isError: bool = False


@dataclass
class ResourceDefinition:
    """MCP resource definition."""
    uri: str
    name: str
    description: str = ""
    mimeType: str = "text/plain"


@dataclass
class PromptDefinition:
    """MCP prompt template definition."""
    name: str
    description: str = ""
    arguments: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ServerCapabilities:
    """MCP server capabilities."""
    tools: Dict[str, Any] = field(default_factory=lambda: {"listChanged": False})
    resources: Dict[str, Any] = field(default_factory=lambda: {"subscribe": False, "listChanged": False})
    prompts: Dict[str, Any] = field(default_factory=lambda: {"listChanged": False})


@dataclass
class ImplementationInfo:
    """Server/client implementation metadata."""
    name: str = "Rampart-Agent"
    version: str = "1.0.0"


# Renamed to avoid conflicts
MCPToolDef = ToolDefinition
MCPToolCallReq = ToolCallRequest
MCPToolCallResult = ToolCallResult


class MCPMethod(str, Enum):
    """MCP protocol methods."""
    # Lifecycle
    INITIALIZE = "initialize"
    INITIALIZED = "notifications/initialized"
    PING = "ping"

    # Tools
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"

    # Resources
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"

    # Prompts
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"


def create_request(method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a JSON-RPC request."""
    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": method,
        "params": params or {},
    }


def create_response(request_id: str, result: Any) -> Dict[str, Any]:
    """Create a JSON-RPC success response."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }


def create_error(request_id: str, code: int, message: str, data: Any = None) -> Dict[str, Any]:
    """Create a JSON-RPC error response."""
    error = {
        "code": code,
        "message": message,
    }
    if data is not None:
        error["data"] = data
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": error,
    }


def parse_message(message: str) -> Dict[str, Any]:
    """Parse a JSON-RPC message from a string."""
    return json.loads(message)


def serialize_message(message: Dict[str, Any]) -> str:
    """Serialize a JSON-RPC message to a string."""
    return json.dumps(message, ensure_ascii=False)
