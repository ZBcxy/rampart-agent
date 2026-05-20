from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt

from gateway.config import settings


async def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


async def get_current_user(request: Request) -> Optional[dict]:
    token = request.headers.get("Authorization", "").replace("Bearer ", "")

    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")


async def require_authentication(current_user: dict = Depends(get_current_user)) -> dict:
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return current_user
