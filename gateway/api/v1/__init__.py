from .agents import router as agents_router
from .chat import router as chat_router
from .health import router as health_router
from .tasks import router as tasks_router

__all__ = ["health", "chat", "tasks", "agents"]

health = health_router
chat = chat_router
tasks = tasks_router
agents = agents_router
