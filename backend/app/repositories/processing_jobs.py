"""Persistence and atomic transitions for processing jobs."""

from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.processing_job import JobStatus, ProcessingJob

MAX_ERROR_MESSAGE_LENGTH = 1000


class ProcessingJobRepository:
    """Create, query, and atomically transition processing jobs."""

    async def create(
        self,
        session: AsyncSession,
        *,
        document_id: UUID,
    ) -> ProcessingJob:
        job_id = uuid4()
        job = ProcessingJob(
            id=job_id,
            document_id=document_id,
            status=JobStatus.PENDING,
            celery_task_id=str(job_id),
        )
        session.add(job)
        await session.flush()
        return job

    async def get(
        self,
        session: AsyncSession,
        job_id: UUID,
    ) -> ProcessingJob | None:
        return await session.get(ProcessingJob, job_id)

    async def list(
        self,
        session: AsyncSession,
        *,
        limit: int,
        offset: int,
    ) -> list[ProcessingJob]:
        statement = (
            select(ProcessingJob)
            .order_by(ProcessingJob.created_at.desc(), ProcessingJob.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.scalars(statement)
        return list(result.all())

    async def count(self, session: AsyncSession) -> int:
        statement = select(func.count()).select_from(ProcessingJob)
        result = await session.scalar(statement)
        return int(result or 0)

    async def mark_queued(self, session: AsyncSession, job_id: UUID) -> bool:
        statement = (
            update(ProcessingJob)
            .where(
                ProcessingJob.id == job_id,
                ProcessingJob.status == JobStatus.PENDING,
            )
            .values(status=JobStatus.QUEUED, error_message=None)
            .returning(ProcessingJob.id)
        )
        result = await session.scalar(statement)
        return result is not None

    async def mark_enqueue_failed(
        self,
        session: AsyncSession,
        job_id: UUID,
        *,
        error_message: str,
    ) -> bool:
        statement = (
            update(ProcessingJob)
            .where(
                ProcessingJob.id == job_id,
                ProcessingJob.status == JobStatus.PENDING,
            )
            .values(
                status=JobStatus.ENQUEUE_FAILED,
                error_message=error_message[:MAX_ERROR_MESSAGE_LENGTH],
            )
            .returning(ProcessingJob.id)
        )
        result = await session.scalar(statement)
        return result is not None

    async def claim(
        self,
        session: AsyncSession,
        job_id: UUID,
    ) -> ProcessingJob | None:
        statement = (
            update(ProcessingJob)
            .where(
                ProcessingJob.id == job_id,
                ProcessingJob.status.in_((JobStatus.PENDING, JobStatus.QUEUED)),
            )
            .values(
                status=JobStatus.PROCESSING,
                attempt_count=ProcessingJob.attempt_count + 1,
                started_at=func.now(),
                error_message=None,
            )
            .returning(ProcessingJob)
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def mark_completed(self, session: AsyncSession, job_id: UUID) -> bool:
        statement = (
            update(ProcessingJob)
            .where(
                ProcessingJob.id == job_id,
                ProcessingJob.status == JobStatus.PROCESSING,
            )
            .values(
                status=JobStatus.COMPLETED,
                completed_at=func.now(),
                error_message=None,
            )
            .returning(ProcessingJob.id)
        )
        result = await session.scalar(statement)
        return result is not None

    async def mark_failed(
        self,
        session: AsyncSession,
        job_id: UUID,
        *,
        error_message: str,
    ) -> bool:
        statement = (
            update(ProcessingJob)
            .where(
                ProcessingJob.id == job_id,
                ProcessingJob.status == JobStatus.PROCESSING,
            )
            .values(
                status=JobStatus.FAILED,
                completed_at=func.now(),
                error_message=error_message[:MAX_ERROR_MESSAGE_LENGTH],
            )
            .returning(ProcessingJob.id)
        )
        result = await session.scalar(statement)
        return result is not None
