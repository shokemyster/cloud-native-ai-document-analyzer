"""REST endpoints for asynchronous processing-job status."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_processing_job_service, get_session
from app.schemas.processing_job import (
    ProcessingJobListResponse,
    ProcessingJobResponse,
)
from app.services.jobs import ProcessingJobNotFoundError, ProcessingJobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=ProcessingJobListResponse)
async def list_processing_jobs(
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[ProcessingJobService, Depends(get_processing_job_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProcessingJobListResponse:
    """Return processing history using bounded offset pagination."""

    jobs, total = await service.list(session, limit=limit, offset=offset)
    return ProcessingJobListResponse(
        items=[ProcessingJobResponse.model_validate(job) for job in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{job_id}", response_model=ProcessingJobResponse)
async def get_processing_job(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[ProcessingJobService, Depends(get_processing_job_service)],
) -> ProcessingJobResponse:
    """Return the durable status of one processing job."""

    try:
        job = await service.get(session, job_id)
    except ProcessingJobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processing job not found",
        ) from exc

    return ProcessingJobResponse.model_validate(job)
