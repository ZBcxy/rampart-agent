"""MCP Client - Connect Polaris to external MCP servers.

Allows Polaris to discover and use tools from MCP-compatible servers,
including Claude Code's built-in tools, filesystem servers, web search servers, etc.

Usage:
    client = MCPClient()
    await client.connect_stdio("python", ["-m", "some_mcp_server"])
    tools = await client.list_tools()
    result = await client.call_tool("tool_name", {"arg": "value"})
    await client.disconnect()
"""

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from mcp.protocol import (
    MCPMethod,
    create_request,
    parse_message,
)


@dataclass
class MCPTool:
    """A tool discovered from an MCP server."""
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    server_name: str = ""


@dataclass
class ServerConnection:
    """Connection to an MCP server."""
    name: str
    transport: str  # "stdio" or "http"
    process: Optional[subprocess.Popen] = None
    url: Optional[str] = None
    reader: Optional[asyncio.StreamReader] = None
    writer: Optional[asyncio.StreamWriter] = None
    _request_counter: int = 0
    _pending: Dict[str, asyncio.Future] = field(default_factory=dict)

    @property
    def next_id(self) -> str:
        self._request_counter += 1
        return f"mcp_req_{self._request_counter}"


class MCPClient:
    """Client for connecting to and using MCP servers.

    Supports multiple concurrent server connections, tool discovery,
    and execution.

    Usage:
        # Connect to a stdio MCP server
        client = MCPClient()
        await client.connect_stdio("filesystem", "npx", ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"])
        tools = await client.list_tools()
        result = await client.call_tool("read_file", {"path": "/tmp/data.txt"})

        # Connect to an HTTP MCP server
        await client.connect_http("web-search", "http://localhost:9000/mcp")
    """

    def __init__(self):
        self._connections: Dict[str, ServerConnection] = {}
        self._tools: Dict[str, Tuple[MCPTool, str]] = {}  # tool_name -> (tool, server_name)

    async def connect_stdio(self, server_name: str, command: str, args: List[str] = None, env: Dict[str, str] = None) -> ServerConnection:
        """
        Connect to an MCP server via stdio subprocess.

        Args:
            server_name: Name to identify this server
            command: Command to run (e.g., "python", "npx", "node")
            args: Command arguments
            env: Environment variables

        Returns:
            ServerConnection
        """
        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        process = subprocess.Popen(
            [command] + (args or []),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=full_env,
            bufsize=1,
        )

        conn = ServerConnection(
            name=server_name,
            transport="stdio",
            process=process,
        )
        self._connections[server_name] = conn

        # Initialize
        await self._send_stdio(conn, MCPMethod.INITIALIZE, {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "Polaris-Agent", "version": "1.0.0"},
            "capabilities": {},
        })

        # Discover tools
        await self._discover_tools(server_name)

        return conn

    async def connect_http(self, server_name: str, url: str) -> ServerConnection:
        """
        Connect to an MCP server over HTTP.

        Args:
            server_name: Name to identify this server
            url: HTTP endpoint URL for the MCP server

        Returns:
            ServerConnection
        """
        conn = ServerConnection(
            name=server_name,
            transport="http",
            url=url,
        )
        self._connections[server_name] = conn

        # Initialize over HTTP
        await self._send_http(conn, MCPMethod.INITIALIZE, {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "Polaris-Agent", "version": "1.0.0"},
            "capabilities": {},
        })

        # Discover tools
        await self._discover_tools(server_name)

        return conn

    async def _discover_tools(self, server_name: str):
        """Discover and register tools from a server."""
        conn = self._connections.get(server_name)
        if not conn:
            return

        response = await self._send_and_receive(conn, MCPMethod.TOOLS_LIST, {})
        tools = response.get("result", {}).get("tools", [])

        for tool_data in tools:
            tool = MCPTool(
                name=tool_data["name"],
                description=tool_data.get("description", ""),
                input_schema=tool_data.get("inputSchema", {}),
                server_name=server_name,
            )
            # Prefix tool name to avoid conflicts
            qualified_name = f"{server_name}/{tool.name}"
            self._tools[qualified_name] = (tool, server_name)
            self._tools[tool.name] = (tool, server_name)  # Also bare name

    async def list_tools(self, server_name: str = None) -> List[MCPTool]:
        """List tools from all connected servers or a specific one."""
        tools = []
        for name, (tool, srv) in self._tools.items():
            if server_name is None or srv == server_name:
                # Avoid duplicates (both qualified and bare names)
                if "/" in name:
                    tools.append(tool)
        return tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None, server_name: str = None) -> Any:
        """
        Call a tool on an MCP server.

        Args:
            tool_name: Tool name (can be bare or "server/tool_name")
            arguments: Tool arguments
            server_name: Server to use (if tool_name is bare and ambiguous)

        Returns:
            Tool execution result
        """
        arguments = arguments or {}

        # Resolve tool
        if "/" in tool_name:
            server_name, actual_tool = tool_name.split("/", 1)
        else:
            tool_entry = self._tools.get(tool_name)
            if not tool_entry:
                raise ValueError(f"Tool not found: {tool_name}")
            if not server_name:
                server_name = tool_entry[1]
            actual_tool = tool_name

        conn = self._connections.get(server_name)
        if not conn:
            raise ValueError(f"Server not connected: {server_name}")

        response = await self._send_and_receive(
            conn,
            MCPMethod.TOOLS_CALL,
            {"name": actual_tool, "arguments": arguments},
        )

        result = response.get("result", {})
        content = result.get("content", [])

        # Extract text content
        texts = []
        for item in content:
            if item.get("type") == "text":
                texts.append(item.get("text", ""))

        is_error = result.get("isError", False)
        return {
            "success": not is_error,
            "result": texts[0] if len(texts) == 1 else "\n".join(texts),
            "is_error": is_error,
            "raw": result,
        }

    async def _send_and_receive(self, conn: ServerConnection, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a request and wait for the response."""
        if conn.transport == "stdio":
            return await self._send_stdio(conn, method, params)
        elif conn.transport == "http":
            return await self._send_http(conn, method, params)
        else:
            raise ValueError(f"Unknown transport: {conn.transport}")

    async def _send_stdio(self, conn: ServerConnection, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a request via stdio to a subprocess."""
        if not conn.process or not conn.process.stdin:
            raise RuntimeError("Stdio connection not established")

        request = create_request(method, params or {})
        conn.process.stdin.write(json.dumps(request) + "\n")
        conn.process.stdin.flush()

        # Read response
        line = conn.process.stdout.readline()
        if not line:
            raise RuntimeError("No response from server")

        return parse_message(line.strip())

    async def _send_http(self, conn: ServerConnection, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a request via HTTP."""
        if not conn.url:
            raise RuntimeError("HTTP URL not configured")

        import httpx

        request = create_request(method, params or {})
        async with httpx.AsyncClient() as client:
            resp = await client.post(conn.url, json=request, timeout=30.0)
            resp.raise_for_status()
            return resp.json()

    def get_tools_as_openai_functions(self) -> List[Dict[str, Any]]:
        """Get all MCP tools as OpenAI function calling format."""
        functions = []
        for name, (tool, _) in self._tools.items():
            if "/" not in name:
                continue  # Skip bare names to avoid duplicates
            functions.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            })
        return functions

    def get_tools_as_anthropic_format(self) -> List[Dict[str, Any]]:
        """Get all MCP tools as Anthropic tool format."""
        tools = []
        for name, (tool, _) in self._tools.items():
            if "/" not in name:
                continue
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            })
        return tools

    async def disconnect(self, server_name: str = None):
        """Disconnect from servers."""
        names = [server_name] if server_name else list(self._connections.keys())
        for name in names:
            conn = self._connections.pop(name, None)
            if conn and conn.process:
                conn.process.terminate()
                try:
                    conn.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    conn.process.kill()

            # Clean up tools from this server
            self._tools = {
                k: v for k, v in self._tools.items()
                if v[1] != name
            }

    async def list_servers(self) -> List[Dict[str, Any]]:
        """List connected servers."""
        return [
            {"name": conn.name, "transport": conn.transport, "alive": conn.process.poll() is None if conn.process else True}
            for conn in self._connections.values()
        ]

    async def ping(self, server_name: str) -> bool:
        """Ping a server to check connectivity."""
        conn = self._connections.get(server_name)
        if not conn:
            return False
        try:
            await self._send_and_receive(conn, MCPMethod.PING, {})
            return True
        except Exception:
            return False
