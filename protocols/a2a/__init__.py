"""A2A (Agent-to-Agent) Protocol Implementation — Google Standard v1.0

A2A enables Polaris agents to discover, communicate with, and delegate tasks
to other A2A-compliant agents across different frameworks and vendors.

Spec: https://a2a-protocol.org
GitHub: https://github.com/a2aproject

Architecture:
    A2A = Agent ↔ Agent (complementary to MCP = Agent ↔ Tools)
    MCP answers "What can this agent access?"
    A2A answers "Which agent should handle this task?"

Key components:
    - Agent Cards: Self-describing JSON metadata at /.well-known/agent-card.json
    - Task Lifecycle: submitted → working → completed/failed/canceled
    - Transport: JSON-RPC 2.0 over HTTPS + SSE for streaming
    - Security: API keys, OAuth 2.0, OpenID Connect, mTLS, JWS signing
"""

from protocols.a2a.server import A2AServer
from protocols.a2a.client import A2AClient
from protocols.a2a.types import (
    AgentCard,
    AgentCapabilities,
    Task,
    TaskState,
    Message,
    Part,
    TextPart,
    FilePart,
    DataPart,
    Artifact,
)

__all__ = [
    "A2AServer",
    "A2AClient",
    "AgentCard",
    "AgentCapabilities",
    "Task",
    "TaskState",
    "Message",
    "Part",
    "TextPart",
    "FilePart",
    "DataPart",
    "Artifact",
]
