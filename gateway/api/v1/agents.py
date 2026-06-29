"""Agent management API — backed by the real multi-agent Coordinator + Blackboard."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from multi_agent.blackboard import Blackboard
from multi_agent.coordinator import AgentCapability, AgentRole, Coordinator

router = APIRouter()

# ── Lazy coordinator singleton ──────────────────────────────────────────────
_coordinator: Optional[Coordinator] = None


def _get_coordinator() -> Coordinator:
    """Return a module-level Coordinator singleton."""
    global _coordinator
    if _coordinator is not None:
        return _coordinator
    _coordinator = Coordinator(blackboard=Blackboard(name="rampart-gateway"))
    return _coordinator


# ── Request / Response models ──────────────────────────────────────────────


class AgentConfigRequest(BaseModel):
    """Request body for creating or updating an agent."""

    name: str = Field(..., description="Agent display name")
    description: str = Field("", description="Agent description")
    autonomy_level: str = Field("L2", description="Autonomy level (L0-L4)")
    tools: List[str] = Field(default_factory=list, description="Available tool names")
    role: str = Field("custom", description="Agent role: analyst, researcher, coder, reviewer, safety_checker, synthesizer, coordinator, custom")
    model: str = Field("gpt-4o", description="LLM model")
    max_steps: int = Field(20, description="Maximum execution steps")
    capabilities: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Agent capabilities")


class AgentResponse(BaseModel):
    """Response body for an agent."""

    agent_id: str = Field(..., description="Unique agent ID")
    name: str = Field(..., description="Agent display name")
    role: str = Field(..., description="Agent role")
    status: str = Field("ready", description="Current status: ready, busy, error, offline")
    tasks_completed: int = Field(0, description="Tasks completed")
    config: AgentConfigRequest = Field(..., description="Agent configuration")
    created_at: datetime = Field(default_factory=datetime.now)
    last_active: Optional[datetime] = Field(None)


# ── Helpers ────────────────────────────────────────────────────────────────


def _parse_role(raw: str) -> AgentRole:
    """Convert a string to an AgentRole enum, defaulting to CUSTOM on mismatch."""
    try:
        return AgentRole(raw.lower())
    except ValueError:
        return AgentRole.CUSTOM


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.get("/", status_code=status.HTTP_200_OK)
async def list_agents(
    limit: int = 10,
    offset: int = 0,
    role: Optional[str] = None,
):
    """List registered agents, optionally filtered by role."""
    coord = _get_coordinator()

    if role:
        parsed_role = _parse_role(role)
        agents = coord.list_agents_by_role(parsed_role)
    else:
        agents = list(coord.agents.values())

    agents_slice = agents[offset : offset + limit]
    return {
        "data": [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "role": a.role.value,
                "status": a.status,
                "tasks_completed": a.tasks_completed,
                "last_active": a.last_active.isoformat() if a.last_active else None,
                "capabilities": [{"name": c.name, "description": c.description} for c in a.capabilities],
            }
            for a in agents_slice
        ],
        "pagination": {
            "page": offset // limit + 1 if limit else 1,
            "size": limit,
            "total": len(agents),
            "pages": max(1, (len(agents) + limit - 1) // limit) if limit else 1,
        },
    }


@router.get("/{agent_id}", status_code=status.HTTP_200_OK)
async def get_agent(agent_id: str):
    """Get a single agent by ID."""
    coord = _get_coordinator()
    info = coord.get_agent_status(agent_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return info


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_agent(body: AgentConfigRequest):
    """Register a new agent with the coordinator."""
    coord = _get_coordinator()

    role = _parse_role(body.role)
    capabilities = [
        AgentCapability(
            name=c.get("name", f"cap-{i}"),
            description=c.get("description", ""),
            input_keys=c.get("input_keys", []),
            output_keys=c.get("output_keys", []),
        )
        for i, c in enumerate(body.capabilities or [])
    ]

    agent_id = coord.register_agent(
        name=body.name,
        role=role,
        capabilities=capabilities if capabilities else None,
        metadata={
            "model": body.model,
            "max_steps": body.max_steps,
            "autonomy_level": body.autonomy_level,
            "tools": body.tools,
        },
    )

    info = coord.get_agent_status(agent_id)
    return info or {"agent_id": agent_id, "name": body.name, "role": role.value, "status": "ready"}


@router.put("/{agent_id}", status_code=status.HTTP_200_OK)
async def update_agent(agent_id: str, body: AgentConfigRequest):
    """Update an existing agent. Unregisters then re-registers."""
    coord = _get_coordinator()

    if agent_id not in coord.agents:
        raise HTTPException(status_code=404, detail="Agent not found")

    role = _parse_role(body.role)
    capabilities = [
        AgentCapability(
            name=c.get("name", f"cap-{i}"),
            description=c.get("description", ""),
            input_keys=c.get("input_keys", []),
            output_keys=c.get("output_keys", []),
        )
        for i, c in enumerate(body.capabilities or [])
    ]

    # Re-register: unregister old, register new, then swap the key
    coord.unregister_agent(agent_id)

    # Register with the desired agent_id by hacking counter (Coordinator doesn't
    # expose set-agent-id, so we unregister old + register fresh, then rename)
    new_id = coord.register_agent(
        name=body.name,
        role=role,
        capabilities=capabilities if capabilities else None,
        metadata={
            "model": body.model,
            "max_steps": body.max_steps,
            "autonomy_level": body.autonomy_level,
            "tools": body.tools,
        },
    )

    # Swap the key so the external agent_id stays the same
    if new_id != agent_id:
        coord.agents[agent_id] = coord.agents.pop(new_id)
        coord.agents[agent_id].agent_id = agent_id
        # Update callbacks
        cb = coord._agent_callbacks.pop(new_id, None)
        if cb:
            coord._agent_callbacks[agent_id] = cb

    info = coord.get_agent_status(agent_id)
    return info


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str):
    """Unregister an agent."""
    coord = _get_coordinator()
    if not coord.unregister_agent(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    return None


@router.post("/{agent_id}/invoke", status_code=status.HTTP_200_OK)
async def invoke_agent(
    agent_id: str,
    goal: str,
    context: Optional[Dict[str, Any]] = None,
):
    """Invoke a registered agent to perform a task.

    Creates a coordinated task, assigns it to the agent, and executes it.
    """
    coord = _get_coordinator()

    if agent_id not in coord.agents:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = coord.agents[agent_id]
    agent.status = "busy"

    try:
        task_id = coord.create_task(
            description=goal,
            assigned_roles=[agent.role],
            input_data=context or {},
        )
        coord.assign_task(task_id)
        result = await coord.execute_task(task_id)
    finally:
        agent.status = "ready"
        agent.last_active = datetime.now()

    return {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "task_id": task_id,
        "status": "completed",
        "goal": goal,
        "result": result,
    }
