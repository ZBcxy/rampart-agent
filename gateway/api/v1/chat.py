"""Chat API endpoints with proper SSE streaming and LLM-backed completion."""

import json
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.align.align_guard import AlignGuard

router = APIRouter()

# Lazy-init the real Agent with tools
_agent = None


def _get_agent():
    global _agent
    if _agent is not None:
        return _agent

    import os
    from core.agent import Agent, AgentConfig

    config = AgentConfig(
        model=os.environ.get("LLM_MODEL", "gpt-4o"),
        provider=os.environ.get("LLM_PROVIDER", "openai"),
        api_key=os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"),
        api_base=os.environ.get("OPENAI_API_BASE"),
        max_steps=int(os.environ.get("POLARIS_MAX_STEPS", "20")),
    )

    _agent = Agent(config=config)

    # Register tools from registry
    try:
        from tools.registry import ToolRegistry
        r = ToolRegistry()
        r.register_all()
        _agent.register_tools_from_registry(r)
    except ImportError:
        pass

    return _agent


# Models
class FunctionCall(BaseModel):
    """A function/tool call from the assistant."""

    name: str = Field(..., description="Function name")
    arguments: str = Field(..., description="Function arguments as JSON string")


class ToolCall(BaseModel):
    """A tool call with ID."""

    id: str = Field(..., description="Tool call ID")
    type: str = Field("function", description="Tool call type")
    function: FunctionCall


class Message(BaseModel):
    """Chat message."""

    role: str = Field(..., description="Message role", examples=["user", "assistant", "system", "tool"])
    content: Optional[str] = Field(None, description="Message content")
    tool_calls: Optional[List[ToolCall]] = Field(None, description="Tool calls from assistant")
    tool_call_id: Optional[str] = Field(None, description="Tool call ID for tool responses")
    name: Optional[str] = Field(None, description="Optional name for the sender")


class ChatOptions(BaseModel):
    """Chat completion options."""

    agent: Optional[str] = Field("default", description="Agent name")
    autonomy_level: Optional[str] = Field("L2", description="Autonomy level (L0-L4)")
    stream: Optional[bool] = Field(False, description="Whether to stream the response")
    max_steps: Optional[int] = Field(20, description="Maximum execution steps")
    temperature: Optional[float] = Field(0.7, description="Sampling temperature")
    max_tokens: Optional[int] = Field(2000, description="Max tokens for response")
    tools: Optional[List[Dict[str, Any]]] = Field(None, description="Available tools/functions")


class ChatRequest(BaseModel):
    """Chat completion request."""

    messages: List[Message] = Field(..., description="Conversation messages")
    options: Optional[ChatOptions] = Field(default_factory=ChatOptions, description="Request options")


class ChatChoice(BaseModel):
    """A single completion choice."""

    index: int = Field(0, description="Choice index")
    message: Optional[Message] = Field(None, description="Complete message (non-streaming)")
    delta: Optional[Dict[str, Any]] = Field(None, description="Message delta (streaming)")
    finish_reason: Optional[str] = Field("stop", description="Why generation stopped")
    tool_calls_log: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Tool call log")


class UsageInfo(BaseModel):
    """Token usage information."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResponse(BaseModel):
    """Chat completion response."""

    id: str = Field(..., description="Response ID")
    object: str = Field("chat.completion", description="Object type")
    created: int = Field(..., description="Unix timestamp")
    model: str = Field("polaris-agent", description="Model used")
    choices: List[ChatChoice]
    usage: UsageInfo = Field(default_factory=UsageInfo, description="Token usage")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


@router.post(
    "/completions",
    status_code=status.HTTP_200_OK,
    response_model=ChatResponse,
    summary="Create chat completion",
    description="Generate an agent response for the given conversation",
)
async def create_chat_completion(request: Request, body: ChatRequest):
    """Create a chat completion with plan-based execution."""
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"

    # Validate input
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    if body.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="last message must be from user")

    # Check alignment guard on user input
    user_content = body.messages[-1].content or ""
    guard_result = align_guard.check_input(user_content)
    if not guard_result.allowed:
        return ChatResponse(
            id=chat_id,
            created=int(__import__("time").time()),
            choices=[
                ChatChoice(
                    index=0,
                    message=Message(
                        role="assistant",
                        content=f"I cannot process this request due to safety policy: "
                        f"{'; '.join(v.message for v in guard_result.violations)}",
                    ),
                    finish_reason="content_filter",
                )
            ],
            metadata={"filtered": True, "violations": len(guard_result.violations)},
        )

    # Check policy
    options = body.options or ChatOptions()
    autonomy_level = AutonomyLevel[f"{options.autonomy_level}_level".upper().replace("L", "L")] if options.autonomy_level else None
    if autonomy_level:
        policy_engine.set_autonomy_level(autonomy_level)

    policy_decision = policy_engine.check_operation("chat_request")
    if not policy_decision.allowed:
        raise HTTPException(status_code=403, detail=policy_decision.reason)

    # Use the real Agent
    agent = _get_agent()
    goal = user_content
    context = {
        "history": [{"role": m.role, "content": m.content or ""} for m in body.messages[:-1]],
        "available_tools": options.tools or [],
    }

    try:
        result = await agent.run(goal, context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    response_content = result.summary

    # Check output through alignment guard
    guard_output = AlignGuard(enabled=True).check_output(response_content)
    if not guard_output.allowed:
        response_content += "\n\n[Note: Some content filtered by safety policy.]"

    return ChatResponse(
        id=chat_id,
        created=int(__import__("time").time()),
        choices=[
            ChatChoice(
                index=0,
                message=Message(role="assistant", content=response_content),
                finish_reason="stop" if result.success else "error",
                tool_calls_log=result.tool_calls,
            )
        ],
        usage=UsageInfo(
            prompt_tokens=len(user_content) // 4,
            completion_tokens=len(response_content) // 4,
            total_tokens=len(user_content) // 4 + len(response_content) // 4,
        ),
        metadata={
            "plan_id": result.plan_id,
            "steps": len(result.steps),
            "total_time": result.total_time,
        },
    )


@router.post(
    "/stream",
    status_code=status.HTTP_200_OK,
    summary="Stream chat completion",
    description="Stream the agent's response using Server-Sent Events (SSE)",
)
async def stream_chat(request: Request, body: ChatRequest):
    """Stream a chat completion using SSE protocol."""
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"

    # Validate
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    options = body.options or ChatOptions()

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events for the chat stream."""
        import time as time_module

        # Start event
        yield _sse_event(
            {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": int(time_module.time()),
                "model": "polaris-agent",
                "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}],
            }
        )

        try:
            user_content = body.messages[-1].content or ""
            agent = _get_agent()

            async for event in agent.run_stream(user_content):
                if event["type"] == "blocked":
                    yield _sse_event({
                        "id": chat_id, "object": "chat.completion.chunk", "created": int(time_module.time()),
                        "model": "polaris-agent",
                        "choices": [{"index": 0, "delta": {"content": f"⚠️ {event['reason']}"}, "finish_reason": "content_filter"}],
                    })
                    yield _sse_done()
                    return

                content = ""
                if event["type"] == "status":
                    content = f"🔄 {event['status']}...\n"
                elif event["type"] == "plan":
                    content = f"📋 Plan: {event.get('content', '')[:200]}\n"
                elif event["type"] == "step":
                    content = f"\n[{event['phase'].upper()}] {event.get('thought', '')[:200]}\n"
                    for tr in event.get("tool_results", []):
                        content += f"  {'✓' if tr.get('error') is None else '✗'} {tr['tool']}\n"
                elif event["type"] == "complete":
                    content = f"\n✨ {event.get('summary', 'Done')}\n"

                if content:
                    yield _sse_event({
                        "id": chat_id, "object": "chat.completion.chunk", "created": int(time_module.time()),
                        "model": "polaris-agent",
                        "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
                    })

        except Exception as e:
            yield _sse_event({
                "id": chat_id, "object": "chat.completion.chunk", "created": int(time_module.time()),
                "model": "polaris-agent",
                "choices": [{"index": 0, "delta": {"content": f"\n❌ Error: {e}"}, "finish_reason": "error"}],
            })

        finally:
            yield _sse_done()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream",
        },
    )


# SSE helpers


def _sse_event(data: Dict[str, Any]) -> str:
    """Format a dict as an SSE event string."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _sse_done() -> str:
    """SSE stream termination marker."""
    return "data: [DONE]\n\n"


