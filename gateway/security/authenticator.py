"""JWT-based bearer token authentication.

Moved from gateway.api.dependencies to provide a single source of truth for
authentication logic. Supports configurable secret and algorithm via gateway Settings.
"""

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt

from gateway.config import settings


class Authenticator:
    """JWT authenticator for bearer token validation.

    Reads the Authorization header, extracts and verifies the JWT,
    and returns the decoded payload.
    """

    def __init__(
        self,
        secret: str | None = None,
        algorithm: str | None = None,
    ):
        self.secret = secret or settings.jwt_secret
        self.algorithm = algorithm or settings.jwt_algorithm

    async def get_current_user(self, request: Request) -> Optional[dict]:
        """Extract and validate JWT from the Authorization header.

        Returns None when no token is present (allows unauthenticated access).
        Raises 401 when a token is present but invalid.
        """
        token = request.headers.get("Authorization", "").replace("Bearer ", "")

        if not token:
            return None

        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

    async def require_authentication(
        self, current_user: dict = Depends(get_current_user)
    ) -> dict:
        """FastAPI dependency — rejects requests without a valid token."""
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        return current_user


# Module-level singleton for use as FastAPI dependencies
_authenticator = Authenticator()
get_current_user = _authenticator.get_current_user
require_authentication = _authenticator.require_authentication


async def get_request_id(request: Request) -> str:
    """Extract the request_id set by RequestLoggerMiddleware."""
    return getattr(request.state, "request_id", "unknown")
