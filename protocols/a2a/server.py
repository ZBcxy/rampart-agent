"""A2A Server — Expose Rampart as an A2A-compliant agent.

Publishes Agent Card at /.well-known/agent-card.json and handles
A2A JSON-RPC task lifecycle via HTTP + SSE.
"""

import json
import uuid
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from protocols.a2a.types import (
    AgentCard,
    AgentSkill,
    Artifact,
    Message,
    Task,
    TaskState,
)


class A2AServer:
    """A2A protocol server for Rampart Agent.

    Usage:
        server = A2AServer(
            agent_card=AgentCard(...),
            task_handler=my_handler,
        )
        # Mount on FastAPI app
        app.mount("/a2a", server.create_app())
    """

    def __init__(
        self,
        agent_card: AgentCard,
        task_handler: Optional[Callable[[Task], Any]] = None,
        tool_registry=None,
    ):
        self.agent_card = agent_card
        self.task_handler = task_handler
        self.tool_registry = tool_registry
        self._tasks: Dict[str, Task] = {}

        # Register skills from tool registry
        if tool_registry and not agent_card.skills:
            for tool_name in tool_registry.list_all():
                tool = tool_registry.get(tool_name)
                if tool:
                    agent_card.skills.append(
                        AgentSkill(
                            id=tool_name,
                            name=tool_name,
                            description=tool.description,
                            tags=tool.tags,
                        )
                    )

    def create_app(self) -> FastAPI:
        """Create a FastAPI app with A2A endpoints."""
        app = FastAPI(title=f"{self.agent_card.name} - A2A Server")

        @app.get("/.well-known/agent-card.json")
        async def agent_card_endpoint():
            """Agent discovery endpoint."""
            return JSONResponse(self.agent_card.to_dict())

        @app.post("/")
        async def a2a_jsonrpc(request: Request):
            """Main A2A JSON-RPC endpoint."""
            body = await request.json()
            method = body.get("method", "")
            params = body.get("params", {})
            request_id = body.get("id", "")

            try:
                if method == "tasks/send":
                    return self._handle_send(request_id, params)
                elif method == "tasks/sendSubscribe":
                    return await self._handle_send_subscribe(request_id, params, request)
                elif method == "tasks/get":
                    return self._handle_get(request_id, params)
                elif method == "tasks/cancel":
                    return self._handle_cancel(request_id, params)
                elif method == "tasks/list":
                    return self._handle_list(request_id, params)
                else:
                    return self._error(request_id, -32601, f"Method not found: {method}")
            except Exception as e:
                return self._error(request_id, -32603, str(e))

        @app.get("/tasks/{task_id}/stream")
        async def task_stream(task_id: str, request: Request):
            """SSE stream for task progress updates."""
            task = self._tasks.get(task_id)
            if not task:
                raise HTTPException(404, "Task not found")

            async def event_generator():
                for msg in task.messages:
                    yield f"data: {json.dumps({'type': 'message', 'message': msg_to_dict(msg)})}\n\n"

                if task.state in (TaskState.COMPLETED, TaskState.FAILED):
                    yield f"data: {json.dumps({'type': 'state', 'state': task.state.value})}\n\n"
                    yield "data: [DONE]\n\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream")

        @app.get("/health")
        async def health():
            return {
                "status": "ok",
                "agent": self.agent_card.name,
                "tasks_active": sum(1 for t in self._tasks.values() if t.state == TaskState.WORKING),
                "tasks_total": len(self._tasks),
            }

        return app

    def _handle_send(self, request_id: str, params: Dict) -> JSONResponse:
        """Handle tasks/send — non-streaming task creation."""
        message_data = params.get("message", {})
        task_id = params.get("id", f"task-{uuid.uuid4().hex[:12]}")

        task = Task(
            id=task_id,
            session_id=params.get("sessionId"),
            state=TaskState.WORKING,
            context_id=params.get("contextId"),
            metadata=params.get("metadata", {}),
        )

        # Add the user message
        msg = Message(
            role="user",
            parts=message_data.get("parts", []),
            task_id=task_id,
            context_id=task.context_id,
        )
        task.add_message(msg)
        self._tasks[task_id] = task

        # Execute handler
        if self.task_handler:
            try:
                result = self.task_handler(task)
                task.update_state(TaskState.COMPLETED)
                # Add result as artifact
                art = Artifact(
                    name="result",
                    parts=[{"type": "text", "text": str(result)}],
                )
                task.add_artifact(art)
                # Add response message
                resp_msg = Message.text_message(
                    str(result), role="agent", task_id=task_id
                )
                task.add_message(resp_msg)
            except Exception as e:
                task.update_state(TaskState.FAILED)
                resp_msg = Message.text_message(
                    f"Error: {str(e)}", role="agent", task_id=task_id
                )
                task.add_message(resp_msg)
        else:
            # Auto-complete if no handler
            task.update_state(TaskState.COMPLETED)
            resp_msg = Message.text_message(
                "Task received and acknowledged.",
                role="agent",
                task_id=task_id,
            )
            task.add_message(resp_msg)

        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"task": task.to_dict()},
            }
        )

    async def _handle_send_subscribe(self, request_id: str, params: Dict, request: Request) -> StreamingResponse:
        """Handle tasks/sendSubscribe — streaming task execution."""
        message_data = params.get("message", {})
        task_id = params.get("id", f"task-{uuid.uuid4().hex[:12]}")

        task = Task(
            id=task_id,
            session_id=params.get("sessionId"),
            state=TaskState.WORKING,
            context_id=params.get("contextId"),
            metadata=params.get("metadata", {}),
        )
        self._tasks[task_id] = task

        async def event_generator():
            # Send initial working state
            yield f"data: {json.dumps({'jsonrpc': '2.0', 'id': request_id, 'result': {'task': task.to_dict()}})}\n\n"

            # Execute handler with streaming
            if self.task_handler:
                try:
                    result = self.task_handler(task)
                    task.update_state(TaskState.COMPLETED)

                    art = Artifact(name="result", parts=[{"type": "text", "text": str(result)}])
                    task.add_artifact(art)
                    resp_msg = Message.text_message(str(result), role="agent", task_id=task_id)
                    task.add_message(resp_msg)

                    yield f"data: {json.dumps({'type': 'artifact', 'artifact': {'artifactId': art.artifact_id, 'name': art.name, 'parts': art.parts}})}\n\n"
                    yield f"data: {json.dumps({'type': 'state', 'state': 'completed'})}\n\n"
                except Exception as e:
                    task.update_state(TaskState.FAILED)
                    yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            else:
                task.update_state(TaskState.COMPLETED)
                yield f"data: {json.dumps({'type': 'state', 'state': 'completed'})}\n\n"

            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    def _handle_get(self, request_id: str, params: Dict) -> JSONResponse:
        """Handle tasks/get — retrieve task status."""
        task_id = params.get("id", "")
        task = self._tasks.get(task_id)
        if not task:
            return self._error(request_id, -32000, f"Task not found: {task_id}")

        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"task": task.to_dict()},
            }
        )

    def _handle_cancel(self, request_id: str, params: Dict) -> JSONResponse:
        """Handle tasks/cancel."""
        task_id = params.get("id", "")
        task = self._tasks.get(task_id)
        if not task:
            return self._error(request_id, -32000, f"Task not found: {task_id}")

        task.update_state(TaskState.CANCELED)
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"task": task.to_dict()},
            }
        )

    def _handle_list(self, request_id: str, params: Dict) -> JSONResponse:
        """Handle tasks/list."""
        limit = params.get("limit", 50)
        tasks = list(self._tasks.values())[:limit]
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tasks": [t.to_dict() for t in tasks]},
            }
        )

    def _error(self, request_id: str, code: int, message: str) -> JSONResponse:
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": code, "message": message},
            },
            status_code=400 if code == -32601 else 500,
        )


def msg_to_dict(msg: Message) -> Dict[str, Any]:
    return {
        "messageId": msg.message_id,
        "role": msg.role,
        "parts": msg.parts,
        "taskId": msg.task_id,
    }
