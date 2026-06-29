"""Integration tests for MCP protocol implementation."""

import json
import os

import pytest
from mcp.protocol import (
    MCPMethod,
    create_request,
    create_response,
    create_error,
    parse_message,
    serialize_message,
)
from mcp.server import RampartMCPServer


@pytest.fixture
def server():
    """Create a test MCP server with mock tools."""
    server = RampartMCPServer(name="test-server")

    # Register mock tools directly
    server.register_tool(
        "echo",
        lambda text: {"echo": text},
        description="Echo back the input",
        input_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to echo"}
            },
            "required": ["text"],
        },
    )

    server.register_tool(
        "add",
        lambda a, b: {"result": int(a) + int(b)},
        description="Add two numbers",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"},
            },
            "required": ["a", "b"],
        },
    )

    return server


class TestMCPProtocol:
    def test_create_request(self):
        req = create_request("tools/list")
        assert req["jsonrpc"] == "2.0"
        assert "id" in req
        assert req["method"] == "tools/list"

    def test_create_response(self):
        resp = create_response("req-1", {"tools": []})
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == "req-1"
        assert resp["result"] == {"tools": []}

    def test_create_error(self):
        resp = create_error("req-1", -32601, "Method not found")
        assert resp["jsonrpc"] == "2.0"
        assert resp["error"]["code"] == -32601
        assert resp["error"]["message"] == "Method not found"

    def test_serialize_deserialize(self):
        original = create_request("ping")
        serialized = serialize_message(original)
        parsed = parse_message(serialized)
        assert parsed["method"] == "ping"
        assert parsed["jsonrpc"] == "2.0"


class TestMCPServer:
    def test_initialize(self, server):
        req = create_request(MCPMethod.INITIALIZE, {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "test-client", "version": "1.0"},
        })
        resp = server.handle_request(req)
        assert "error" not in resp
        assert resp["result"]["protocolVersion"] == "2024-11-05"
        assert resp["result"]["serverInfo"]["name"] == "test-server"

    def test_ping(self, server):
        req = create_request(MCPMethod.PING)
        resp = server.handle_request(req)
        assert "error" not in resp
        assert resp["result"] == {}

    def test_tools_list(self, server):
        req = create_request(MCPMethod.TOOLS_LIST)
        resp = server.handle_request(req)
        assert "error" not in resp
        tools = resp["result"]["tools"]
        assert len(tools) == 2
        tool_names = [t["name"] for t in tools]
        assert "echo" in tool_names
        assert "add" in tool_names

    def test_tools_call_echo(self, server):
        req = create_request(MCPMethod.TOOLS_CALL, {
            "name": "echo",
            "arguments": {"text": "hello mcp"},
        })
        resp = server.handle_request(req)
        assert "error" not in resp
        content = resp["result"]["content"]
        assert len(content) > 0
        assert "hello mcp" in content[0]["text"]

    def test_tools_call_add(self, server):
        req = create_request(MCPMethod.TOOLS_CALL, {
            "name": "add",
            "arguments": {"a": 5, "b": 3},
        })
        resp = server.handle_request(req)
        assert "error" not in resp
        content = resp["result"]["content"]
        assert "8" in content[0]["text"]

    def test_unknown_tool(self, server):
        req = create_request(MCPMethod.TOOLS_CALL, {
            "name": "nonexistent_tool",
            "arguments": {},
        })
        resp = server.handle_request(req)
        assert "error" in resp
        assert "Tool not found" in resp["error"]["message"]

    def test_unknown_method(self, server):
        req = create_request("nonexistent/method")
        resp = server.handle_request(req)
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    def test_resources_list(self, server):
        req = create_request(MCPMethod.RESOURCES_LIST)
        resp = server.handle_request(req)
        assert "error" not in resp
        # Resources now include tool manifest
        resources = resp["result"]["resources"]
        assert len(resources) >= 1
        assert any(r["name"] == "Tool Manifest" for r in resources)

    def test_prompts_list(self, server):
        req = create_request(MCPMethod.PROMPTS_LIST)
        resp = server.handle_request(req)
        assert "error" not in resp
        # Prompts now include analyze and summarize templates
        prompts = resp["result"]["prompts"]
        assert len(prompts) >= 2
        assert any(p["name"] == "analyze" for p in prompts)
        assert any(p["name"] == "summarize" for p in prompts)


class TestMCPServerWithRegistry:
    def test_with_tool_registry(self):
        from tools.registry import ToolRegistry

        registry = ToolRegistry()
        registry.register_all()

        server = RampartMCPServer(tool_registry=registry)

        req = create_request(MCPMethod.TOOLS_LIST)
        resp = server.handle_request(req)
        assert "error" not in resp
        tools = resp["result"]["tools"]
        assert len(tools) >= 26
