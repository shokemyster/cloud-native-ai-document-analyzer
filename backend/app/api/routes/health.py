"""Kubernetes-compatible process and dependency health endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_redis, get_session
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """Report whether the API process can serve requests."""

    return HealthResponse()


@router.get(
    "/ready",
    response_model=HealthResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Required dependency unavailable"
        }
    },
)
async def readiness(
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> HealthResponse:
    """Report whether required API dependencies are available."""

    try:
        await session.execute(text("SELECT 1"))
        await redis.ping()
    except (RedisError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Required dependency unavailable",
        ) from exc

    return HealthResponse()
