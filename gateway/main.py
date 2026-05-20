from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from gateway.api.v1 import agents, chat, health, tasks
from gateway.config import settings
from gateway.middlewares.error_handler import ErrorHandlerMiddleware
from gateway.middlewares.rate_limiter import RateLimiterMiddleware
from gateway.middlewares.request_logger import RequestLoggerMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="BeiJiXing Agent Gateway API",
        description="API gateway for BeiJiXing autonomous agent framework",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(RateLimiterMiddleware)

    app.include_router(health, prefix="/v1/health", tags=["Health"])
    app.include_router(chat, prefix="/v1/chat", tags=["Chat"])
    app.include_router(tasks, prefix="/v1/tasks", tags=["Tasks"])
    app.include_router(agents, prefix="/v1/agents", tags=["Agents"])

    return app


app = create_app()


@app.get("/", tags=["Root"])
async def root(request: Request):
    return {"message": "BeiJiXing Agent Gateway", "version": "1.0.0"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="BeiJiXing Agent Gateway",
        version="1.0.0",
        description="API gateway for BeiJiXing autonomous agent framework",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
