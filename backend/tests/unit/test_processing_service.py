"""Unit tests for idempotent background processing."""

from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.processing_job import JobStatus, ProcessingJob
from app.repositories.documents import DocumentRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.services.processing import DocumentProcessingService


class RecordingSession:
    """Record service-controlled transaction boundaries."""

    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeDocumentRepository:
    def __init__(self, document: Document) -> None:
        self._document = document

    async def get(self, session: object, document_id: object) -> Document:
        return self._document


class ClaimOnceJobRepository:
    def __init__(self, job: ProcessingJob) -> None:
        self._job = job
        self._claimed = False
        self.completed = False

    async def claim(self, session: object, job_id: object) -> ProcessingJob | None:
        if self._claimed:
            return None
        self._claimed = True
        return self._job

    async def mark_completed(self, session: object, job_id: object) -> bool:
        self.completed = True
        return True

    async def mark_failed(
        self,
        session: object,
        job_id: object,
        *,
        error_message: str,
    ) -> bool:
        return True


@pytest.mark.asyncio
async def test_duplicate_delivery_does_not_process_job_twice() -> None:
    document_id = uuid4()
    job_id = uuid4()
    document = Document(
        id=document_id,
        original_filename="report.pdf",
        media_type="application/pdf",
        size_bytes=10,
        checksum_sha256="a" * 64,
        storage_key="documents/report.pdf",
    )
    job = ProcessingJob(
        id=job_id,
        document_id=document_id,
        status=JobStatus.QUEUED,
        celery_task_id=str(job_id),
    )
    job_repository = ClaimOnceJobRepository(job)
    session = RecordingSession()
    service = DocumentProcessingService(
        document_repository=cast(DocumentRepository, FakeDocumentRepository(document)),
        job_repository=cast(ProcessingJobRepository, job_repository),
    )

    first_result = await service.process(cast(AsyncSession, session), job_id)
    second_result = await service.process(cast(AsyncSession, session), job_id)

    assert first_result is True
    assert second_result is False
    assert job_repository.completed is True
    assert session.commits == 2
    assert session.rollbacks == 1
