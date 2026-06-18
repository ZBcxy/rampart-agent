"""A2A Protocol Types — Google A2A v1.0 Spec

https://a2a-protocol.org/specification/
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class TaskState(str, Enum):
    """A2A Task lifecycle states."""
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    REJECTED = "rejected"


class PartType(str, Enum):
    TEXT = "text"
    FILE = "file"
    DATA = "data"


@dataclass
class TextPart:
    """Text content part of a message or artifact."""
    type: str = "text"
    text: str = ""


@dataclass
class FilePart:
    """File content part (inline bytes or URI)."""
    type: str = "file"
    file_uri: Optional[str] = None
    mime_type: Optional[str] = None
    data: Optional[str] = None  # Base64-encoded bytes


@dataclass
class DataPart:
    """Structured data content part."""
    type: str = "data"
    data: Dict[str, Any] = field(default_factory=dict)
    mime_type: str = "application/json"


Part = Union[TextPart, FilePart, DataPart]


@dataclass
class Message:
    """A single turn of communication between agents."""
    message_id: str = field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:8]}")
    role: str = "user"  # user | agent
    parts: List[Dict[str, Any]] = field(default_factory=list)
    task_id: Optional[str] = None
    context_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def text_message(cls, text: str, role: str = "user", task_id: str | None = None) -> "Message":
        return cls(role=role, parts=[{"type": "text", "text": text}], task_id=task_id)


@dataclass
class Artifact:
    """Tangible output from a task."""
    artifact_id: str = field(default_factory=lambda: f"art-{uuid.uuid4().hex[:8]}")
    name: Optional[str] = None
    description: Optional[str] = None
    parts: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Stateful unit of work in A2A."""
    id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:12]}")
    session_id: Optional[str] = None
    state: TaskState = TaskState.SUBMITTED
    messages: List[Message] = field(default_factory=list)
    artifacts: List[Artifact] = field(default_factory=list)
    context_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def update_state(self, state: TaskState):
        self.state = state
        self.updated_at = datetime.now().isoformat()

    def add_message(self, message: Message):
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()

    def add_artifact(self, artifact: Artifact):
        self.artifacts.append(artifact)
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sessionId": self.session_id,
            "state": self.state.value,
            "messages": [
                {
                    "messageId": m.message_id,
                    "role": m.role,
                    "parts": m.parts,
                    "taskId": m.task_id,
                    "contextId": m.context_id,
                    "metadata": m.metadata,
                }
                for m in self.messages
            ],
            "artifacts": [
                {
                    "artifactId": a.artifact_id,
                    "name": a.name,
                    "description": a.description,
                    "parts": a.parts,
                    "metadata": a.metadata,
                }
                for a in self.artifacts
            ],
            "metadata": self.metadata,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


@dataclass
class AgentCapabilities:
    """What an A2A agent can do."""
    streaming: bool = True
    push_notifications: bool = False
    state_transition_history: bool = False
    extensions: List[str] = field(default_factory=list)


@dataclass
class AgentSkill:
    """A specific skill an agent exposes."""
    id: str
    name: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    input_modes: List[str] = field(default_factory=lambda: ["text"])
    output_modes: List[str] = field(default_factory=lambda: ["text"])


@dataclass
class AgentCard:
    """Self-describing metadata for A2A agent discovery.

    Published at: GET /.well-known/agent-card.json
    """
    name: str = "Polaris Agent"
    description: str = "Navigate Complexity with AI — Autonomous Agent Framework"
    url: str = ""  # Base URL of the agent
    version: str = "1.1.0"
    provider: Optional[Dict[str, str]] = None  # {name, url, organization}
    capabilities: AgentCapabilities = field(default_factory=AgentCapabilities)
    skills: List[AgentSkill] = field(default_factory=list)
    default_input_modes: List[str] = field(default_factory=lambda: ["text"])
    default_output_modes: List[str] = field(default_factory=lambda: ["text"])
    authentication: Optional[Dict[str, Any]] = None
    documentation_url: Optional[str] = None
    icon_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "provider": self.provider,
            "capabilities": {
                "streaming": self.capabilities.streaming,
                "pushNotifications": self.capabilities.push_notifications,
                "stateTransitionHistory": self.capabilities.state_transition_history,
                "extensions": self.capabilities.extensions,
            },
            "skills": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "tags": s.tags,
                    "examples": s.examples,
                    "inputModes": s.input_modes,
                    "outputModes": s.output_modes,
                }
                for s in self.skills
            ],
            "defaultInputModes": self.default_input_modes,
            "defaultOutputModes": self.default_output_modes,
            "authentication": self.authentication,
            "documentationUrl": self.documentation_url,
            "iconUrl": self.icon_url,
        }
