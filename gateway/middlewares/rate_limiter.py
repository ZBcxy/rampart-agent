import time
from collections import defaultdict

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from gateway.config import settings

rate_limit_store = defaultdict(lambda: {"count": 0, "reset_time": 0})


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    限流中间件
    限制用户和系统级别的请求频率
    """

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host

        now = time.time()
        client_data = rate_limit_store[client_ip]

        if now >= client_data["reset_time"]:
            client_data["count"] = 0
            client_data["reset_time"] = now + 60

        if client_data["count"] >= settings.rate_limit_user:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests",
                        "details": [{"field": "rate_limit", "message": "User rate limit exceeded"}],
                        "request_id": getattr(request.state, "request_id", "unknown"),
                    }
                },
            )

        client_data["count"] += 1

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(settings.rate_limit_user - client_data["count"])
        response.headers["X-RateLimit-Reset"] = str(int(client_data["reset_time"]))

        return response
