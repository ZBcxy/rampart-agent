"""MCP (Model Context Protocol) Integration

Implements both MCP Server and Client for interoperability with
the broader agent ecosystem, including Claude Code.

MCP Protocol version: 2024-11-05

Usage:
    # As a server (expose Rampart tools to other agents)
    from mcp import RampartMCPServer
    server = RampartMCPServer(tool_registry)
    server.run_stdio()

    # As a client (use external MCP tools in Rampart)
    from mcp import MCPClient
    client = MCPClient()
    tools = await client.list_tools()
    result = await client.call_tool("tool_name", {"arg": "value"})
"""

from mcp.client import MCPClient
from mcp.server import RampartMCPServer
from mcp.protocol import (
    JSONRPCRequest,
    JSONRPCResponse,
    ToolDefinition,
    ToolCallRequest,
    ToolCallResult,
    create_request,
    create_response,
    create_error,
    parse_message,
    serialize_message,
)

__all__ = [
    "RampartMCPServer",
    "MCPClient",
    "JSONRPCRequest",
    "JSONRPCResponse",
    "ToolDefinition",
    "ToolCallRequest",
    "ToolCallResult",
    "create_request",
    "create_response",
    "create_error",
    "parse_message",
    "serialize_message",
]
