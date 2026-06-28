"""Unit tests for upload persistence and queue publication ordering."""

from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.messaging.base import DocumentTaskPublisher, TaskPublishError
from app.models.document import Document
from app.models.processing_job import JobStatus, ProcessingJob
from app.repositories.documents import DocumentRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.services.documents import DocumentService, JobEnqueueError
from app.storage.base import AsyncReadable, ObjectStorage, StoredObject


class FakeUpload:
    filename: str | None = "report.pdf"
    content_type: str | None = "application/pdf"

    async def read(self, size: int = -1) -> bytes:
        return b"content"


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def refresh(self, instance: object) -> None:
        return None


class FakeStorage:
    def __init__(self) -> None:
        self.deleted_keys: list[str] = []

    async def initialize(self) -> None:
        return None

    async def save(
        self,
        source: AsyncReadable,
        *,
        key: str,
        max_size_bytes: int,
    ) -> StoredObject:
        return StoredObject(key=key, size_bytes=7, checksum_sha256="a" * 64)

    async def delete(self, key: str) -> None:
        self.deleted_keys.append(key)


class FakeDocumentRepository:
    async def create(self, session: object, **values: object) -> Document:
        return Document(
            id=uuid4(),
            created_at=datetime.now(UTC),
            **values,
        )


class FakeJobRepository:
    def __init__(self) -> None:
        self.job: ProcessingJob | None = None

    async def create(
        self,
        session: object,
        *,
        document_id: UUID,
    ) -> ProcessingJob:
        job_id = uuid4()
        self.job = ProcessingJob(
            id=job_id,
            document_id=document_id,
            status=JobStatus.PENDING,
            celery_task_id=str(job_id),
            attempt_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        return self.job

    async def mark_queued(self, session: object, job_id: UUID) -> bool:
        assert self.job is not None
        self.job.status = JobStatus.QUEUED
        return True

    async def mark_enqueue_failed(
        self,
        session: object,
        job_id: UUID,
        *,
        error_message: str,
    ) -> bool:
        assert self.job is not None
        self.job.status = JobStatus.ENQUEUE_FAILED
        self.job.error_message = error_message
        return True


class FakePublisher:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.published_job_id: UUID | None = None

    async def publish(self, job_id: UUID) -> None:
        self.published_job_id = job_id
        if self.fail:
            raise TaskPublishError("Redis unavailable")

    async def close(self) -> None:
        return None


def build_service(
    tmp_path: Path,
    *,
    storage: FakeStorage,
    publisher: FakePublisher,
    job_repository: FakeJobRepository,
) -> DocumentService:
    settings = Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://unused",
            "upload_directory": tmp_path,
        }
    )
    return DocumentService(
        repository=cast(DocumentRepository, FakeDocumentRepository()),
        job_repository=cast(ProcessingJobRepository, job_repository),
        publisher=cast(DocumentTaskPublisher, publisher),
        storage=cast(ObjectStorage, storage),
        settings=settings,
    )


@pytest.mark.asyncio
async def test_upload_commits_then_publishes_and_marks_queued(tmp_path: Path) -> None:
    session = FakeSession()
    storage = FakeStorage()
    publisher = FakePublisher()
    job_repository = FakeJobRepository()
    service = build_service(
        tmp_path,
        storage=storage,
        publisher=publisher,
        job_repository=job_repository,
    )

    result = await service.upload(cast(AsyncSession, session), FakeUpload())

    assert publisher.published_job_id == result.job.id
    assert result.job.status == JobStatus.QUEUED
    assert session.commits == 2
    assert storage.deleted_keys == []


@pytest.mark.asyncio
async def test_broker_failure_is_persisted_without_deleting_file(
    tmp_path: Path,
) -> None:
    session = FakeSession()
    storage = FakeStorage()
    publisher = FakePublisher(fail=True)
    job_repository = FakeJobRepository()
    service = build_service(
        tmp_path,
        storage=storage,
        publisher=publisher,
        job_repository=job_repository,
    )

    with pytest.raises(JobEnqueueError):
        await service.upload(cast(AsyncSession, session), FakeUpload())

    assert job_repository.job is not None
    assert job_repository.job.status == JobStatus.ENQUEUE_FAILED
    assert session.commits == 2
    assert storage.deleted_keys == []
