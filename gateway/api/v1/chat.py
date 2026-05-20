import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from core.planner import Planner

router = APIRouter()


class Message(BaseModel):
    role: str = Field(..., description="消息角色", example="user")
    content: str = Field(..., description="消息内容", example="分析销售数据")


class ChatOptions(BaseModel):
    agent: Optional[str] = Field("default", description="Agent名称")
    autonomy_level: Optional[str] = Field("L2", description="自主等级")
    stream: Optional[bool] = Field(False, description="是否流式响应")
    max_steps: Optional[int] = Field(20, description="最大步骤数")


class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., description="消息列表")
    options: Optional[ChatOptions] = Field(ChatOptions(), description="选项")


class ChatChoice(BaseModel):
    message: Message
    finish_reason: Optional[str] = Field("stop", description="结束原因")
    tool_calls_log: Optional[List[dict]] = Field([], description="工具调用日志")


class ChatResponse(BaseModel):
    id: str = Field(..., description="响应ID")
    choices: List[ChatChoice]
    usage: Dict[str, int] = Field(..., description="使用统计")
    metadata: Dict[str, Any] = Field(..., description="元数据")


@router.post("/completions", status_code=status.HTTP_200_OK, response_model=ChatResponse)
async def create_chat_completion(request: Request, body: ChatRequest):
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

    if not body.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    if body.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="last message must be from user")

    planner = Planner()
    goal = body.messages[-1].content
    context = {"history": [m.dict() for m in body.messages[:-1]]}

    plan = planner.generate_plan(goal, context)

    response_message = Message(
        role="assistant", content=f"已生成执行计划，置信度: {plan.confidence:.2f}\n\n计划内容: {plan.root.content}"
    )

    return ChatResponse(
        id=chat_id,
        choices=[{"message": response_message, "finish_reason": "stop", "tool_calls_log": []}],
        usage={"total_tokens": 1234},
        metadata={"plan_confidence": plan.confidence, "plan_id": plan.id},
    )


@router.post("/stream", status_code=status.HTTP_200_OK)
async def stream_chat(request: Request, body: ChatRequest):
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

    if not body.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    yield {
        "id": chat_id,
        "choices": [{"delta": {"role": "assistant", "content": "思考中..."}, "finish_reason": None}],
        "usage": {"total_tokens": 0},
        "metadata": {"status": "thinking"},
    }

    yield {
        "id": chat_id,
        "choices": [{"delta": {"role": "assistant", "content": "生成计划完成"}, "finish_reason": "stop"}],
        "usage": {"total_tokens": 500},
        "metadata": {"status": "completed"},
    }
