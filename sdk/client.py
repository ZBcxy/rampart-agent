"""Rampart Agent SDK Client

Provides a Python client for interacting with the Rampart Agent Gateway API.
Supports synchronous and asynchronous usage patterns.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional

import httpx


@dataclass
class Message:
    """Chat message."""

    role: str  # "user", "assistant", "system"
    content: str


@dataclass
class ChatCompletionChoice:
    """A single completion choice."""

    message: Message
    finish_reason: Optional[str] = "stop"
    tool_calls_log: List[dict] = field(default_factory=list)


@dataclass
class ChatCompletionResponse:
    """Full chat completion response."""

    id: str
    choices: List[ChatCompletionChoice]
    usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentInfo:
    """Information about a registered agent."""

    agent_id: str
    name: str
    description: str
    status: str = "ready"
    capabilities: List[str] = field(default_factory=list)


@dataclass
class TaskInfo:
    """Information about a task."""

    task_id: str
    status: str
    agent_id: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class RampartClient:
    """Synchronous client for the Rampart Agent Gateway API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """
        Initialize the client.

        Args:
            base_url: Base URL of the Rampart Gateway API
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client = httpx.Client(
            timeout=timeout,
            headers=self._build_headers(),
        )

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def chat(
        self,
        messages: List[Message],
        agent: str = "default",
        autonomy_level: str = "L2",
        stream: bool = False,
        max_steps: int = 20,
    ) -> ChatCompletionResponse:
        """
        Send a chat completion request.

        Args:
            messages: List of conversation messages
            agent: Agent name to use
            autonomy_level: Autonomy level (L0-L4)
            stream: Whether to stream the response
            max_steps: Maximum execution steps

        Returns:
            ChatCompletionResponse
        """
        body = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "options": {
                "agent": agent,
                "autonomy_level": autonomy_level,
                "stream": stream,
                "max_steps": max_steps,
            },
        }

        response = self._client.post(f"{self.base_url}/v1/chat/completions", json=body)
        response.raise_for_status()
        data = response.json()

        choices = [
            ChatCompletionChoice(
                message=Message(role=c["message"]["role"], content=c["message"]["content"]),
                finish_reason=c.get("finish_reason", "stop"),
                tool_calls_log=c.get("tool_calls_log", []),
            )
            for c in data.get("choices", [])
        ]

        return ChatCompletionResponse(
            id=data["id"],
            choices=choices,
            usage=data.get("usage", {}),
            metadata=data.get("metadata", {}),
        )

    def chat_stream(
        self,
        messages: List[Message],
        agent: str = "default",
        autonomy_level: str = "L2",
        max_steps: int = 20,
    ) -> Iterator[Dict[str, Any]]:
        """
        Stream chat completion responses.

        Args:
            messages: List of conversation messages
            agent: Agent name to use
            autonomy_level: Autonomy level
            max_steps: Maximum execution steps

        Yields:
            Dict[str, Any]: Streamed response chunks
        """
        body = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "options": {
                "agent": agent,
                "autonomy_level": autonomy_level,
                "stream": True,
                "max_steps": max_steps,
            },
        }

        with self._client.stream("POST", f"{self.base_url}/v1/chat/stream", json=body) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line and line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        yield json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

    def list_agents(self) -> List[AgentInfo]:
        """List all registered agents."""
        response = self._client.get(f"{self.base_url}/v1/agents")
        response.raise_for_status()
        data = response.json()
        return [
            AgentInfo(
                agent_id=a["agent_id"],
                name=a["name"],
                description=a.get("description", ""),
                status=a.get("status", "ready"),
                capabilities=a.get("capabilities", []),
            )
            for a in data.get("agents", [])
        ]

    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get a specific agent by ID."""
        response = self._client.get(f"{self.base_url}/v1/agents/{agent_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        a = response.json()
        return AgentInfo(
            agent_id=a["agent_id"],
            name=a["name"],
            description=a.get("description", ""),
            status=a.get("status", "ready"),
            capabilities=a.get("capabilities", []),
        )

    def create_task(self, description: str, agent_id: Optional[str] = None) -> TaskInfo:
        """Create a new task."""
        body = {"description": description}
        if agent_id:
            body["agent_id"] = agent_id
        response = self._client.post(f"{self.base_url}/v1/tasks", json=body)
        response.raise_for_status()
        data = response.json()
        return TaskInfo(
            task_id=data["task_id"],
            status=data["status"],
            agent_id=data.get("agent_id"),
            created_at=data.get("created_at"),
        )

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Get task status."""
        response = self._client.get(f"{self.base_url}/v1/tasks/{task_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        return TaskInfo(
            task_id=data["task_id"],
            status=data["status"],
            agent_id=data.get("agent_id"),
            created_at=data.get("created_at"),
            completed_at=data.get("completed_at"),
            result=data.get("result"),
        )

    def wait_for_task(self, task_id: str, poll_interval: float = 1.0, timeout: float = 300.0) -> TaskInfo:
        """
        Wait for a task to complete.

        Args:
            task_id: Task ID to wait for
            poll_interval: Seconds between status checks
            timeout: Maximum wait time in seconds

        Returns:
            TaskInfo with final status

        Raises:
            TimeoutError: If task doesn't complete within timeout
        """
        start = time.time()
        while time.time() - start < timeout:
            task = self.get_task(task_id)
            if task is None:
                raise ValueError(f"Task {task_id} not found")
            if task.status in ("completed", "failed", "cancelled"):
                return task
            time.sleep(poll_interval)
        raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")

    def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        response = self._client.get(f"{self.base_url}/v1/health")
        response.raise_for_status()
        return response.json()

    def close(self):
        """Close the client connection."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class AsyncRampartClient:
    """Asynchronous client for the Rampart Agent Gateway API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(timeout=self.timeout, headers=headers)
        return self._client

    async def chat(
        self,
        messages: List[Message],
        agent: str = "default",
        autonomy_level: str = "L2",
        stream: bool = False,
        max_steps: int = 20,
    ) -> ChatCompletionResponse:
        """Send an async chat completion request."""
        client = await self._get_client()
        body = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "options": {
                "agent": agent,
                "autonomy_level": autonomy_level,
                "stream": stream,
                "max_steps": max_steps,
            },
        }
        response = await client.post(f"{self.base_url}/v1/chat/completions", json=body)
        response.raise_for_status()
        data = response.json()

        choices = [
            ChatCompletionChoice(
                message=Message(role=c["message"]["role"], content=c["message"]["content"]),
                finish_reason=c.get("finish_reason", "stop"),
                tool_calls_log=c.get("tool_calls_log", []),
            )
            for c in data.get("choices", [])
        ]

        return ChatCompletionResponse(
            id=data["id"],
            choices=choices,
            usage=data.get("usage", {}),
            metadata=data.get("metadata", {}),
        )

    async def chat_stream(
        self,
        messages: List[Message],
        agent: str = "default",
        autonomy_level: str = "L2",
        max_steps: int = 20,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream async chat completion responses."""
        client = await self._get_client()
        body = {
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "options": {
                "agent": agent,
                "autonomy_level": autonomy_level,
                "stream": True,
                "max_steps": max_steps,
            },
        }
        async with client.stream("POST", f"{self.base_url}/v1/chat/stream", json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line and line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        yield json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

    async def list_agents(self) -> List[AgentInfo]:
        """List all registered agents."""
        client = await self._get_client()
        response = await client.get(f"{self.base_url}/v1/agents")
        response.raise_for_status()
        data = response.json()
        return [
            AgentInfo(
                agent_id=a["agent_id"],
                name=a["name"],
                description=a.get("description", ""),
                status=a.get("status", "ready"),
                capabilities=a.get("capabilities", []),
            )
            for a in data.get("agents", [])
        ]

    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get a specific agent by ID."""
        client = await self._get_client()
        response = await client.get(f"{self.base_url}/v1/agents/{agent_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        a = response.json()
        return AgentInfo(
            agent_id=a["agent_id"],
            name=a["name"],
            description=a.get("description", ""),
            status=a.get("status", "ready"),
            capabilities=a.get("capabilities", []),
        )

    async def create_task(self, description: str, agent_id: Optional[str] = None) -> TaskInfo:
        """Create a new task."""
        client = await self._get_client()
        body = {"description": description}
        if agent_id:
            body["agent_id"] = agent_id
        response = await client.post(f"{self.base_url}/v1/tasks", json=body)
        response.raise_for_status()
        data = response.json()
        return TaskInfo(
            task_id=data["task_id"],
            status=data["status"],
            agent_id=data.get("agent_id"),
            created_at=data.get("created_at"),
        )

    async def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Get task status."""
        client = await self._get_client()
        response = await client.get(f"{self.base_url}/v1/tasks/{task_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        return TaskInfo(
            task_id=data["task_id"],
            status=data["status"],
            agent_id=data.get("agent_id"),
            created_at=data.get("created_at"),
            completed_at=data.get("completed_at"),
            result=data.get("result"),
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        client = await self._get_client()
        response = await client.get(f"{self.base_url}/v1/health")
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the async client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
