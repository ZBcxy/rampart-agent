from datetime import datetime

from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    services: dict


@router.get("/", status_code=status.HTTP_200_OK, response_model=HealthResponse)
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": "1.1.0",
        "services": {"gateway": "running", "planner": "running", "executor": "running", "memory": "running"},
    }
