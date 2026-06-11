"""Protocols Support — MCP, A2A, and emerging standards.

Polaris Agent supports the following protocols out of the box:

MCP (Model Context Protocol) — Agent ↔ Tools/Data
    Spec: modelcontextprotocol.io (2025-11-25)
    Polaris acts as both MCP Server (expose tools) and MCP Client (consume tools)

A2A (Agent-to-Agent Protocol) — Agent ↔ Agent
    Spec: a2a-protocol.org (v1.0, April 2026)
    Polaris can discover, delegate to, and receive tasks from other A2A agents
"""

from protocols.a2a import A2AClient, A2AServer, AgentCard, Task, TaskState
from mcp import MCPClient
from mcp.server import PolarisMCPServer

__all__ = [
    # MCP
    "PolarisMCPServer",
    "MCPClient",
    # A2A
    "A2AServer",
    "A2AClient",
    "AgentCard",
    "Task",
    "TaskState",
]
