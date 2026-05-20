import traceback
import uuid

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    错误处理中间件
    统一处理应用中的异常并返回标准化的错误响应
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            return response
        except Exception as e:
            error_code = "INTERNAL_ERROR"
            error_message = str(e)
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            if isinstance(e, ValueError):
                error_code = "INVALID_REQUEST"
                error_message = str(e)
                status_code = status.HTTP_400_BAD_REQUEST
            elif isinstance(e, PermissionError):
                error_code = "FORBIDDEN"
                error_message = "Permission denied"
                status_code = status.HTTP_403_FORBIDDEN
            elif isinstance(e, NotImplementedError):
                error_code = "NOT_IMPLEMENTED"
                error_message = "Feature not implemented"
                status_code = status.HTTP_501_NOT_IMPLEMENTED

            error_response = {
                "error": {
                    "code": error_code,
                    "message": error_message,
                    "details": traceback.format_exc().split("\n")[-5:],
                    "request_id": request_id,
                }
            }

            return JSONResponse(status_code=status_code, content=error_response)
