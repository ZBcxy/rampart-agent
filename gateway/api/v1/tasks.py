import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from core.executor import DAGExecutor
from core.planner import Planner

router = APIRouter()


class TaskStatus(BaseModel):
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    progress: float = Field(0.0, description="进度")
    result: Optional[Dict[str, Any]] = Field(None, description="任务结果")
    error: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


task_store = {}


class TaskCreateRequest(BaseModel):
    goal: str = Field(..., description="任务目标")
    context: Optional[Dict[str, Any]] = Field({}, description="上下文信息")
    options: Optional[Dict[str, Any]] = Field({}, description="选项")


class TaskUpdateRequest(BaseModel):
    status: Optional[str] = Field(None, description="任务状态")
    context: Optional[Dict[str, Any]] = Field(None, description="更新上下文")


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_task(request: TaskCreateRequest):
    task_id = f"task-{uuid.uuid4().hex[:8]}"

    planner = Planner()
    plan = planner.generate_plan(request.goal, request.context)

    task = TaskStatus(
        task_id=task_id,
        status="created",
        progress=0.0,
        result={"plan_id": plan.id, "plan_confidence": plan.confidence},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    task_store[task_id] = task

    return task


@router.get("/{task_id}", status_code=status.HTTP_200_OK)
async def get_task(task_id: str):
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")

    return task_store[task_id]


@router.get("/", status_code=status.HTTP_200_OK)
async def list_tasks(limit: int = 10, offset: int = 0):
    tasks = list(task_store.values())[offset:offset + limit]
    return {
        "data": tasks,
        "pagination": {
            "page": offset // limit + 1,
            "size": limit,
            "total": len(task_store),
            "pages": (len(task_store) + limit - 1) // limit,
        },
    }


@router.put("/{task_id}", status_code=status.HTTP_200_OK)
async def update_task(task_id: str, request: TaskUpdateRequest):
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")

    task = task_store[task_id]

    if request.status:
        task.status = request.status
    if request.context:
        task.result = {"context": request.context}

    task.updated_at = datetime.now()

    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str):
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")

    del task_store[task_id]
    return None


@router.post("/{task_id}/execute", status_code=status.HTTP_200_OK)
async def execute_task(task_id: str):
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")

    task = task_store[task_id]
    task.status = "running"
    task.progress = 25.0
    task.updated_at = datetime.now()

    dag = {
        "nodes": [
            {"id": "node1", "type": "action", "content": "初始化"},
            {"id": "node2", "type": "action", "content": "执行"},
            {"id": "node3", "type": "action", "content": "完成"},
        ],
        "edges": [{"from": "node1", "to": "node2"}, {"from": "node2", "to": "node3"}],
    }

    executor = DAGExecutor()
    results = await executor.execute_dag(dag, {})

    task.status = "completed"
    task.progress = 100.0
    task.result = {"execution_results": [r.dict() for r in results], "completed_steps": len(results)}
    task.updated_at = datetime.now()

    return task
