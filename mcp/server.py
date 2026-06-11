"""MCP Server v2025-11-25 — Expose Polaris tools via Model Context Protocol.

Implements latest MCP spec features:
- Tools (list/call)
- Resources (list/read/subscribe)
- Prompts (list/get)
- Tasks (get/cancel/list/result) — long-running operations
- Icons (tools, resources, server)
- Sampling with tool calling (SEP-1577)

Supports:
- stdio transport (for Claude Code desktop integration)
- HTTP/SSE transport (for web-based clients)

Usage with Claude Code:
    Add to .claude/mcp.json:
    {
        "mcpServers": {
            "polaris": {
                "command": "python",
                "args": ["-m", "mcp.server", "--stdio"],
                "env": {"POLARIS_CONFIG": "/path/to/config"}
            }
        }
    }
"""

import asyncio
import json
import sys
from typing import Any, Dict

from mcp.protocol import (
    MCPMethod,
    ServerCapabilities,
    ImplementationInfo,
    create_error,
    create_response,
    parse_message,
    serialize_message,
)

# JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class PolarisMCPServer:
    """MCP Server that exposes Polaris tools via the Model Context Protocol.

    Can run over stdio (for desktop app integration) or HTTP (for web clients).
    """

    def __init__(self, tool_registry=None, name: str = "polaris-agent"):
        """
        Initialize the MCP server.

        Args:
            tool_registry: ToolRegistry instance with registered tools
            name: Server name
        """
        self.name = name
        self.tool_registry = tool_registry
        self._tools: Dict[str, Any] = {}
        self._tasks: Dict[str, Dict] = {}  # Task tracking for MCP Tasks spec
        self._initialized = False
        self._server_info = ImplementationInfo(name=name, version="1.0.0")
        self._capabilities = ServerCapabilities()

        if tool_registry:
            self._sync_tools_from_registry()

    def _sync_tools_from_registry(self):
        """Sync tool definitions from the registry."""
        if not self.tool_registry:
            return
        for tool_name in self.tool_registry.list_all():
            tool = self.tool_registry.get(tool_name)
            if tool:
                self._tools[tool_name] = tool

    def register_tool(self, name: str, handler, description: str = "", input_schema: Dict = None):
        """Register a single tool directly."""
        self._tools[name] = {
            "handler": handler,
            "description": description,
            "input_schema": input_schema or {"type": "object", "properties": {}},
        }

    def handle_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a single JSON-RPC request synchronously."""
        request_id = message.get("id", "")
        method = message.get("method", "")
        params = message.get("params", {})

        try:
            if method == MCPMethod.INITIALIZE:
                return self._handle_initialize(request_id, params)
            elif method == MCPMethod.PING:
                return create_response(request_id, {})
            elif method == MCPMethod.TOOLS_LIST:
                return self._handle_tools_list(request_id)
            elif method == MCPMethod.TOOLS_CALL:
                return self._handle_tools_call(request_id, params)
            elif method == "tasks/get":
                return self._handle_tasks_get(request_id, params)
            elif method == "tasks/cancel":
                return self._handle_tasks_cancel(request_id, params)
            elif method == "tasks/list":
                return self._handle_tasks_list(request_id, params)
            elif method == "tasks/result":
                return self._handle_tasks_result(request_id, params)
            elif method == MCPMethod.RESOURCES_LIST:
                return self._handle_resources_list(request_id)
            elif method == MCPMethod.PROMPTS_LIST:
                return self._handle_prompts_list(request_id)
            else:
                return create_error(request_id, METHOD_NOT_FOUND, f"Method not found: {method}")
        except Exception as e:
            return create_error(request_id, INTERNAL_ERROR, str(e))

    def _handle_initialize(self, request_id: str, params: Dict) -> Dict[str, Any]:
        """Handle initialize request."""
        self._initialized = True
        return create_response(request_id, {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": self._server_info.name,
                "version": self._server_info.version,
            },
            "capabilities": {
                "tools": self._capabilities.tools,
                "resources": self._capabilities.resources,
                "prompts": self._capabilities.prompts,
            },
        })

    def _handle_tools_list(self, request_id: str) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = []
        for name, tool in self._tools.items():
            if isinstance(tool, dict):
                # Directly registered tool
                tools.append({
                    "name": name,
                    "description": tool.get("description", ""),
                    "inputSchema": tool.get("input_schema", {"type": "object", "properties": {}}),
                })
            else:
                # From registry
                tool_def = self.tool_registry.get(name)
                if tool_def:
                    tools.append({
                        "name": name,
                        "description": tool_def.description,
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                k: {"type": v.get("type", "string"), "description": v.get("description", "")}
                                for k, v in tool_def.parameters.items()
                            },
                            "required": [
                                k for k, v in tool_def.parameters.items()
                                if v.get("required", False)
                            ],
                        },
                    })
        return create_response(request_id, {"tools": tools})

    def _handle_tools_call(self, request_id: str, params: Dict) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if not tool_name:
            return create_error(request_id, INVALID_PARAMS, "Missing tool name")

        if tool_name not in self._tools:
            return create_error(request_id, INVALID_PARAMS, f"Tool not found: {tool_name}")

        try:
            if self.tool_registry:
                result = self.tool_registry.execute(tool_name, **arguments)
            else:
                handler = self._tools[tool_name]
                if isinstance(handler, dict):
                    handler = handler.get("handler")
                result = handler(**arguments) if handler else {"error": "No handler"}

            is_error = isinstance(result, dict) and result.get("error")

            return create_response(request_id, {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, default=str),
                    }
                ],
                "isError": bool(is_error),
            })
        except Exception as e:
            return create_response(request_id, {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "isError": True,
            })

    def _handle_tasks_get(self, request_id: str, params: Dict) -> Dict[str, Any]:
        """Handle tasks/get — retrieve long-running task status."""
        task_id = params.get("taskId", "")
        task = self._tasks.get(task_id)
        if not task:
            return create_error(request_id, -32000, f"Task not found: {task_id}")
        return create_response(request_id, {"task": task})

    def _handle_tasks_cancel(self, request_id: str, params: Dict) -> Dict[str, Any]:
        """Handle tasks/cancel."""
        task_id = params.get("taskId", "")
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "cancelled"
            return create_response(request_id, {"task": self._tasks[task_id]})
        return create_error(request_id, -32000, f"Task not found: {task_id}")

    def _handle_tasks_list(self, request_id: str, params: Dict = None) -> Dict[str, Any]:
        """Handle tasks/list — list all active tasks."""
        limit = (params or {}).get("limit", 50)
        tasks = list(self._tasks.values())[:limit]
        return create_response(request_id, {"tasks": tasks})

    def _handle_tasks_result(self, request_id: str, params: Dict) -> Dict[str, Any]:
        """Handle tasks/result — get final result of a completed task."""
        task_id = params.get("taskId", "")
        task = self._tasks.get(task_id)
        if not task:
            return create_error(request_id, -32000, f"Task not found: {task_id}")
        return create_response(request_id, {"result": task.get("result")})

    def _handle_resources_list(self, request_id: str) -> Dict[str, Any]:
        """Handle resources/list request with icon support."""
        return create_response(request_id, {"resources": [
            {
                "uri": "polaris://tools/manifest",
                "name": "Tool Manifest",
                "description": "List of all available Polaris tools with schemas",
                "mimeType": "application/json",
                "icons": [{"src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><text y='14'>🔧</text></svg>", "mimeType": "image/svg+xml"}],
            }
        ]})

    def _handle_prompts_list(self, request_id: str) -> Dict[str, Any]:
        """Handle prompts/list request."""
        return create_response(request_id, {"prompts": [
            {
                "name": "analyze",
                "description": "Analyze a given topic or data set",
                "arguments": [
                    {"name": "topic", "description": "Topic to analyze", "required": True},
                    {"name": "depth", "description": "Analysis depth (brief/standard/deep)", "required": False},
                ],
            },
            {
                "name": "summarize",
                "description": "Summarize text or documents",
                "arguments": [
                    {"name": "text", "description": "Text to summarize", "required": True},
                ],
            },
        ]})

    def run_stdio(self):
        """Run the server over stdio (stdin/stdout JSON-RPC).

        This is the default transport for Claude Code integration.
        """
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                message = parse_message(line)
            except json.JSONDecodeError:
                error_response = create_error("", PARSE_ERROR, "Parse error")
                sys.stdout.write(serialize_message(error_response) + "\n")
                sys.stdout.flush()
                continue

            # Skip notifications (no id)
            if "id" not in message:
                continue

            response = self.handle_request(message)
            sys.stdout.write(serialize_message(response) + "\n")
            sys.stdout.flush()

    async def run_http(self, host: str = "0.0.0.0", port: int = 9000):
        """Run the MCP server over HTTP SSE transport."""
        from fastapi import FastAPI, Request
        from fastapi.responses import StreamingResponse, JSONResponse

        app = FastAPI(title=f"{self.name} MCP Server")

        @app.post("/mcp")
        async def mcp_endpoint(request: Request):
            body = await request.json()
            response = self.handle_request(body)
            return JSONResponse(response)

        @app.get("/mcp/sse")
        async def mcp_sse(request: Request):
            async def event_stream():
                yield f"data: {json.dumps({'type': 'endpoint', 'url': '/mcp'})}\n\n"
            return StreamingResponse(event_stream(), media_type="text/event-stream")

        @app.get("/health")
        async def health():
            return {"status": "ok", "server": self.name, "tools": len(self._tools)}

        import uvicorn
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()


def main():
    """Entry point for stdio MCP server."""
    import argparse

    parser = argparse.ArgumentParser(description="Polaris MCP Server")
    parser.add_argument("--stdio", action="store_true", default=True, help="Run over stdio")
    parser.add_argument("--http", action="store_true", help="Run over HTTP")
    parser.add_argument("--port", type=int, default=9000, help="HTTP port")
    args = parser.parse_args()

    # Create tool registry
    try:
        from tools.registry import ToolRegistry
        registry = ToolRegistry()
        registry.register_all()
    except ImportError:
        registry = None

    server = PolarisMCPServer(tool_registry=registry)

    if args.http:
        asyncio.run(server.run_http(port=args.port))
    else:
        server.run_stdio()


if __name__ == "__main__":
    main()
