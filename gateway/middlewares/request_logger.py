import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    记录所有请求的基本信息
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        logger.info(
            f"Request received: {request.method} {request.url.path} "
            f"from {request.client.host}:{request.client.port}"
        )

        response = await call_next(request)

        process_time = (time.time() - start_time) * 1000
        logger.info(
            f"Request completed: {request.method} {request.url.path} "
            f"status={response.status_code} duration={process_time:.2f}ms"
        )

        return response
