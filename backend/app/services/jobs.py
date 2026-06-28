"""Processing-job query use cases."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.processing_job import ProcessingJob
from app.repositories.processing_jobs import ProcessingJobRepository


class ProcessingJobNotFoundError(Exception):
    """Raised when requested job state does not exist."""


class ProcessingJobService:
    """Expose processing-job status independently of Celery internals."""

    def __init__(self, repository: ProcessingJobRepository) -> None:
        self._repository = repository

    async def get(
        self,
        session: AsyncSession,
        job_id: UUID,
    ) -> ProcessingJob:
        job = await self._repository.get(session, job_id)
        if job is None:
            raise ProcessingJobNotFoundError
        return job

    async def list(
        self,
        session: AsyncSession,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[ProcessingJob], int]:
        jobs = await self._repository.list(session, limit=limit, offset=offset)
        total = await self._repository.count(session)
        return jobs, total
