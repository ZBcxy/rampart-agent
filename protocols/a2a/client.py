"""A2A Client — Discover and delegate tasks to remote A2A agents.

Allows Polaris to find and use other A2A-compliant agents across the web.
"""

import json
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from protocols.a2a.types import AgentCard, Message, Task, TaskState


class A2AClient:
    """Client for discovering and communicating with A2A agents.

    Usage:
        client = A2AClient()
        card = await client.discover_agent("https://agent.example.com")
        task = await client.send_task(card, "Analyze this data")
        result = await client.get_task_result(task.id)
    """

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout
        self._http: Optional[httpx.AsyncClient] = None
        self._known_agents: Dict[str, AgentCard] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self.timeout)
        return self._http

    async def discover_agent(self, base_url: str) -> AgentCard:
        """Discover an A2A agent by fetching its Agent Card.

        Args:
            base_url: The agent's base URL (e.g., "https://agent.example.com")

        Returns:
            AgentCard with the agent's capabilities and skills
        """
        client = await self._get_client()
        card_url = f"{base_url.rstrip('/')}/.well-known/agent-card.json"

        resp = await client.get(card_url)
        resp.raise_for_status()
        data = resp.json()

        card = AgentCard(
            name=data["name"],
            description=data.get("description", ""),
            url=data.get("url", base_url),
            version=data.get("version", "1.0.0"),
        )

        self._known_agents[base_url] = card
        return card

    async def send_task(
        self,
        agent_url: str,
        message: str,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> Task:
        """Send a task to an A2A agent.

        Args:
            agent_url: The agent's URL
            message: Task description in natural language
            task_id: Optional task ID (auto-generated if not provided)
            metadata: Optional metadata
            stream: Whether to use streaming (tasks/sendSubscribe)

        Returns:
            Task with the agent's response
        """
        client = await self._get_client()
        task_id = task_id or f"task-{uuid.uuid4().hex[:12]}"

        body = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tasks/sendSubscribe" if stream else "tasks/send",
            "params": {
                "id": task_id,
                "message": {
                    "messageId": f"msg-{uuid.uuid4().hex[:8]}",
                    "role": "user",
                    "parts": [{"type": "text", "text": message}],
                },
                "metadata": metadata or {},
            },
        }

        endpoint = f"{agent_url.rstrip('/')}/"
        resp = await client.post(endpoint, json=body)
        resp.raise_for_status()
        data = resp.json()

        result = data.get("result", {})
        task_data = result.get("task", {})

        # Build Task object
        task = Task(
            id=task_data.get("id", task_id),
            state=TaskState(task_data.get("state", "completed")),
            metadata=task_data.get("metadata", {}),
            created_at=task_data.get("createdAt", ""),
            updated_at=task_data.get("updatedAt", ""),
        )

        # Parse messages
        for msg_data in task_data.get("messages", []):
            task.messages.append(
                Message(
                    message_id=msg_data.get("messageId", ""),
                    role=msg_data.get("role", "user"),
                    parts=msg_data.get("parts", []),
                )
            )

        return task

    async def send_task_stream(
        self,
        agent_url: str,
        message: str,
        task_id: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Send a task and stream the response via SSE.

        Yields events: {'type': 'state', 'state': 'working'}, {'type': 'artifact', ...}, etc.
        """
        client = await self._get_client()
        task_id = task_id or f"task-{uuid.uuid4().hex[:12]}"

        body = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tasks/sendSubscribe",
            "params": {
                "id": task_id,
                "message": {
                    "messageId": f"msg-{uuid.uuid4().hex[:8]}",
                    "role": "user",
                    "parts": [{"type": "text", "text": message}],
                },
            },
        }

        endpoint = f"{agent_url.rstrip('/')}/"
        async with client.stream("POST", endpoint, json=body) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line and line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        yield json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

    async def get_task(self, agent_url: str, task_id: str) -> Optional[Task]:
        """Get the current state of a task."""
        client = await self._get_client()

        body = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tasks/get",
            "params": {"id": task_id},
        }

        endpoint = f"{agent_url.rstrip('/')}/"
        resp = await client.post(endpoint, json=body)
        resp.raise_for_status()
        data = resp.json()

        task_data = data.get("result", {}).get("task", {})
        if not task_data:
            return None

        return Task(
            id=task_data.get("id", task_id),
            state=TaskState(task_data.get("state", "working")),
            metadata=task_data.get("metadata", {}),
        )

    async def cancel_task(self, agent_url: str, task_id: str) -> bool:
        """Cancel a running task."""
        client = await self._get_client()

        body = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tasks/cancel",
            "params": {"id": task_id},
        }

        endpoint = f"{agent_url.rstrip('/')}/"
        resp = await client.post(endpoint, json=body)
        resp.raise_for_status()
        data = resp.json()

        task_data = data.get("result", {}).get("task", {})
        return task_data.get("state") == "canceled"

    async def list_agents(self) -> List[AgentCard]:
        """List all discovered agents."""
        return list(self._known_agents.values())

    async def close(self):
        """Close the HTTP client."""
        if self._http:
            await self._http.aclose()
            self._http = None
