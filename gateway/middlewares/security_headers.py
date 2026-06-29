"""Security headers middleware — applies CSP, HSTS, X-Frame-Options, etc."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("X-XSS-Protection", "0")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        headers.setdefault(
            "Strict-Transport-Security",
            "max-age=63072000; includeSubDomains; preload",
        )

        csp = getattr(request.app.state, "csp_directives", "default-src 'self'")
        headers.setdefault("Content-Security-Policy", csp)

        return response
