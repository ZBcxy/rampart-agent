"""Multi-Agent Coordinator

Orchestrates multiple specialized agents working together through a shared
blackboard. Implements role-based task delegation, consensus building, and
collaborative problem-solving patterns.
"""

import asyncio
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

from multi_agent.blackboard import Blackboard, BlackboardEntry, EntryStatus


class AgentRole(Enum):
    """Predefined agent roles for task assignment."""

    COORDINATOR = "coordinator"
    ANALYST = "analyst"
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    SAFETY_CHECKER = "safety_checker"
    SYNTHESIZER = "synthesizer"
    CUSTOM = "custom"


@dataclass
class AgentCapability:
    """Description of what an agent can do."""

    name: str
    description: str
    input_keys: List[str] = field(default_factory=list)  # Keys this agent reads from blackboard
    output_keys: List[str] = field(default_factory=list)  # Keys this agent writes to blackboard
    confidence_threshold: float = 0.3


@dataclass
class AgentRegistration:
    """Registration info for an agent in the coordinator."""

    agent_id: str
    name: str
    role: AgentRole
    capabilities: List[AgentCapability] = field(default_factory=list)
    status: str = "ready"  # ready, busy, error, offline
    last_active: datetime = field(default_factory=datetime.now)
    tasks_completed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskStatus(Enum):
    """Status of a coordinated task."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    AWAITING_CONSENSUS = "awaiting_consensus"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """A task to be executed by one or more agents."""

    task_id: str
    description: str
    assigned_roles: List[AgentRole]
    input_data: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    assigned_agents: List[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    required_consensus: int = 1  # Minimum agents that must agree
    metadata: Dict[str, Any] = field(default_factory=dict)

    def elapsed_time(self) -> float:
        """Seconds since task creation."""
        end = self.completed_at or datetime.now()
        return (end - self.created_at).total_seconds()


class Coordinator:
    """Multi-agent coordinator that delegates tasks and builds consensus.

    The coordinator:
    1. Receives a complex task
    2. Decomposes it into sub-tasks
    3. Assigns sub-tasks to specialized agents based on roles/capabilities
    4. Collects results on the blackboard
    5. Builds consensus when multiple agents contribute
    6. Synthesizes a final response
    """

    def __init__(self, blackboard: Optional[Blackboard] = None):
        """
        Initialize the coordinator.

        Args:
            blackboard: Shared blackboard. Creates a new one if not provided.
        """
        self.blackboard = blackboard or Blackboard(name="coordinator")
        self.agents: Dict[str, AgentRegistration] = {}
        self.tasks: Dict[str, Task] = {}
        self._agent_callbacks: Dict[str, Callable] = {}  # agent_id -> async handler
        self._lock = threading.RLock()
        self._task_counter = 0
        self._agent_counter = 0

    def register_agent(
        self,
        name: str,
        role: AgentRole,
        capabilities: Optional[List[AgentCapability]] = None,
        callback: Optional[Callable[..., Coroutine]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Register an agent with the coordinator.

        Args:
            name: Human-readable name
            role: The agent's role
            capabilities: What the agent can do
            callback: Async function to call when assigning tasks
            metadata: Additional agent metadata

        Returns:
            agent_id
        """
        with self._lock:
            agent_id = f"agent_{self._agent_counter}"
            self._agent_counter += 1

            registration = AgentRegistration(
                agent_id=agent_id,
                name=name,
                role=role,
                capabilities=capabilities or [],
                metadata=metadata or {},
            )

            self.agents[agent_id] = registration

            if callback:
                self._agent_callbacks[agent_id] = callback

            return agent_id

    def unregister_agent(self, agent_id: str) -> bool:
        """Remove an agent from the coordinator."""
        with self._lock:
            if agent_id in self.agents:
                del self.agents[agent_id]
                self._agent_callbacks.pop(agent_id, None)
                return True
            return False

    def create_task(
        self,
        description: str,
        assigned_roles: List[AgentRole],
        input_data: Optional[Dict[str, Any]] = None,
        required_consensus: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new coordinated task.

        Args:
            description: Task description
            assigned_roles: Roles needed to complete the task
            input_data: Input data for the task
            required_consensus: Minimum agents that must agree
            metadata: Additional metadata

        Returns:
            task_id
        """
        with self._lock:
            task_id = f"task_{self._task_counter}"
            self._task_counter += 1

            task = Task(
                task_id=task_id,
                description=description,
                assigned_roles=assigned_roles,
                input_data=input_data or {},
                required_consensus=max(1, required_consensus),
                metadata=metadata or {},
            )

            self.tasks[task_id] = task
            return task_id

    def assign_task(self, task_id: str) -> Dict[str, str]:
        """
        Assign a task to available agents matching the required roles.

        Args:
            task_id: ID of the task to assign

        Returns:
            Mapping of role -> agent_id for each assignment
        """
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            assignments = {}
            for role in task.assigned_roles:
                candidates = [
                    (aid, agent)
                    for aid, agent in self.agents.items()
                    if agent.role == role and agent.status == "ready"
                ]
                if candidates:
                    # Pick the agent with fewest tasks
                    candidates.sort(key=lambda x: x[1].tasks_completed)
                    agent_id = candidates[0][0]
                    self.agents[agent_id].status = "busy"
                    assignments[role.value] = agent_id
                    task.assigned_agents.append(agent_id)

            task.status = TaskStatus.ASSIGNED
            return assignments

    async def execute_task(self, task_id: str) -> Dict[str, Any]:
        """
        Execute a task by dispatching to assigned agents.

        Args:
            task_id: Task to execute

        Returns:
            Aggregated results from all agents
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if not task.assigned_agents:
            self.assign_task(task_id)

        task.status = TaskStatus.IN_PROGRESS

        # Dispatch to agents in parallel
        agent_tasks = []
        for agent_id in task.assigned_agents:
            if agent_id in self._agent_callbacks:
                cb = self._agent_callbacks[agent_id]
                agent_tasks.append(cb(task, self.blackboard))

        if agent_tasks:
            results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        else:
            results = []

        # Collect and aggregate results
        task_result = self._aggregate_results(task, results)
        task.result = task_result
        task.completed_at = datetime.now()
        task.status = TaskStatus.COMPLETED

        # Release agents
        for agent_id in task.assigned_agents:
            if agent_id in self.agents:
                self.agents[agent_id].status = "ready"
                self.agents[agent_id].tasks_completed += 1
                self.agents[agent_id].last_active = datetime.now()

        return task_result

    def _aggregate_results(self, task: Task, agent_results: List[Any]) -> Dict[str, Any]:
        """
        Aggregate results from multiple agents.

        Also reads relevant entries from the blackboard.

        Args:
            task: The executed task
            agent_results: Results from each agent callback

        Returns:
            Aggregated result dict
        """
        successful = [r for r in agent_results if not isinstance(r, Exception)]
        errors = [str(r) for r in agent_results if isinstance(r, Exception)]

        # Read blackboard for any published results
        blackboard_entries = self.blackboard.query(
            key_prefix=f"task/{task.task_id}",
            min_confidence=0.3,
            status=EntryStatus.ACCEPTED,
        )

        blackboard_data = {}
        for entry in blackboard_entries:
            blackboard_data[entry.key] = {
                "value": entry.value,
                "author": entry.author,
                "confidence": entry.confidence,
            }

        return {
            "task_id": task.task_id,
            "status": "completed" if not errors else "partial",
            "agent_results": successful,
            "errors": errors,
            "blackboard_findings": blackboard_data,
            "consensus": self._build_consensus(task.task_id),
            "elapsed_time": task.elapsed_time(),
        }

    def _build_consensus(self, task_id: str) -> Dict[str, Any]:
        """
        Build consensus from multiple agent contributions on the blackboard.

        Args:
            task_id: Task to build consensus for

        Returns:
            Consensus result dict
        """
        entries = self.blackboard.query(
            key_prefix=f"task/{task_id}",
            status=EntryStatus.PROPOSED,
        )

        if not entries:
            return {"consensus_reached": False, "reason": "No proposals found"}

        # Group by key
        by_key: Dict[str, List[BlackboardEntry]] = {}
        for entry in entries:
            by_key.setdefault(entry.key, []).append(entry)

        consensus = {}
        for key, key_entries in by_key.items():
            if len(key_entries) >= 1:
                # For now: pick the highest confidence entry
                best = max(key_entries, key=lambda e: e.confidence)
                consensus[key] = {
                    "value": best.value,
                    "confidence": best.confidence,
                    "agreeing_agents": len(key_entries),
                    "total_proposals": len(key_entries),
                }
                # Mark accepted
                self.blackboard.update(best.entry_id, status=EntryStatus.ACCEPTED)

        return {
            "consensus_reached": len(consensus) > 0,
            "findings": consensus,
            "total_proposals": len(entries),
            "unique_findings": len(consensus),
        }

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task."""
        task = self.tasks.get(task_id)
        if not task:
            return None

        return {
            "task_id": task.task_id,
            "description": task.description,
            "status": task.status.value,
            "assigned_agents": task.assigned_agents,
            "elapsed_time": task.elapsed_time(),
            "has_result": task.result is not None,
        }

    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of an agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            return None
        return {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "role": agent.role.value,
            "status": agent.status,
            "tasks_completed": agent.tasks_completed,
            "capabilities": [
                {"name": c.name, "description": c.description} for c in agent.capabilities
            ],
        }

    def list_agents_by_role(self, role: AgentRole) -> List[AgentRegistration]:
        """List all agents with a specific role."""
        return [agent for agent in self.agents.values() if agent.role == role]

    def get_coordination_summary(self) -> Dict[str, Any]:
        """Get a summary of the coordinator's state."""
        role_counts: Dict[str, int] = {}
        status_counts: Dict[str, int] = {}
        for agent in self.agents.values():
            role_counts[agent.role.value] = role_counts.get(agent.role.value, 0) + 1
            status_counts[agent.status] = status_counts.get(agent.status, 0) + 1

        task_status_counts: Dict[str, int] = {}
        for task in self.tasks.values():
            task_status_counts[task.status.value] = task_status_counts.get(task.status.value, 0) + 1

        return {
            "total_agents": len(self.agents),
            "agents_by_role": role_counts,
            "agents_by_status": status_counts,
            "total_tasks": len(self.tasks),
            "tasks_by_status": task_status_counts,
            "blackboard_stats": self.blackboard.get_statistics(),
        }
