import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter()


class AgentConfig(BaseModel):
    name: str = Field(..., description="Agent名称")
    description: Optional[str] = Field("", description="Agent描述")
    autonomy_level: str = Field("L2", description="自主等级")
    tools: List[str] = Field([], description="可用工具列表")
    model: Optional[str] = Field("gpt-4", description="使用的模型")
    max_steps: int = Field(20, description="最大步骤数")


class AgentStatus(BaseModel):
    agent_id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent名称")
    status: str = Field("active", description="状态")
    config: AgentConfig = Field(..., description="配置")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_used: Optional[datetime] = Field(None, description="最后使用时间")


agent_store = {
    "agent-data-analyst": AgentStatus(
        agent_id="agent-data-analyst",
        name="DataAnalyst",
        status="active",
        config=AgentConfig(
            name="DataAnalyst",
            description="数据分析Agent，擅长处理和分析各种数据",
            autonomy_level="L3",
            tools=["sql_query", "data_visualization", "file_read", "excel_process"],
            model="gpt-4",
            max_steps=30,
        ),
        created_at=datetime.now(),
        last_used=datetime.now(),
    ),
    "agent-code-assistant": AgentStatus(
        agent_id="agent-code-assistant",
        name="CodeAssistant",
        status="active",
        config=AgentConfig(
            name="CodeAssistant",
            description="代码助手Agent，擅长编写和调试代码",
            autonomy_level="L2",
            tools=["python_runner", "code_review", "documentation"],
            model="gpt-4",
            max_steps=20,
        ),
        created_at=datetime.now(),
        last_used=datetime.now(),
    ),
}


@router.get("/", status_code=status.HTTP_200_OK)
async def list_agents(limit: int = 10, offset: int = 0):
    agents = list(agent_store.values())[offset:offset + limit]
    return {
        "data": agents,
        "pagination": {
            "page": offset // limit + 1,
            "size": limit,
            "total": len(agent_store),
            "pages": (len(agent_store) + limit - 1) // limit,
        },
    }


@router.get("/{agent_id}", status_code=status.HTTP_200_OK)
async def get_agent(agent_id: str):
    if agent_id not in agent_store:
        raise HTTPException(status_code=404, detail="Agent not found")

    return agent_store[agent_id]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_agent(request: AgentConfig):
    agent_id = f"agent-{uuid.uuid4().hex[:8]}"

    agent = AgentStatus(
        agent_id=agent_id, name=request.name, status="active", config=request, created_at=datetime.now()
    )

    agent_store[agent_id] = agent

    return agent


@router.put("/{agent_id}", status_code=status.HTTP_200_OK)
async def update_agent(agent_id: str, request: AgentConfig):
    if agent_id not in agent_store:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = agent_store[agent_id]
    agent.name = request.name
    agent.config = request
    agent.last_used = datetime.now()

    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str):
    if agent_id not in agent_store:
        raise HTTPException(status_code=404, detail="Agent not found")

    del agent_store[agent_id]
    return None


@router.post("/{agent_id}/invoke", status_code=status.HTTP_200_OK)
async def invoke_agent(agent_id: str, goal: str, context: Optional[Dict[str, Any]] = None):
    if agent_id not in agent_store:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = agent_store[agent_id]
    agent.last_used = datetime.now()

    return {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "status": "processing",
        "goal": goal,
        "context": context or {},
        "estimated_steps": min(agent.config.max_steps, 20),
    }
