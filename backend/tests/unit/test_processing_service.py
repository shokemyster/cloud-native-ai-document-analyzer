"""Tests for idempotent AI document-processing orchestration."""

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.base import (
    AnalysisContext,
    AnalysisOutput,
    AnalyzerError,
    AnalyzerResult,
    DocumentAnalyzer,
)
from app.extraction.base import DocumentTextExtractor, ExtractedDocument
from app.models.document import Document
from app.models.document_analysis import (
    AnalysisStatus,
    DocumentAnalysis,
)
from app.models.processing_job import JobStatus, ProcessingJob
from app.repositories.document_analyses import DocumentAnalysisRepository
from app.repositories.documents import DocumentRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.services.processing import DocumentProcessingService
from app.storage.base import ObjectStorage


class RecordingSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.attributes_expired = False

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1
        self.attributes_expired = True


class RollbackSensitiveJob:
    """Simulate ORM attributes that cannot be read after rollback."""

    def __init__(
        self,
        session: RecordingSession,
        *,
        job_id: UUID,
        document_id: UUID,
    ) -> None:
        self._session = session
        self._job_id = job_id
        self._document_id = document_id

    @property
    def id(self) -> UUID:
        self._assert_not_expired()
        return self._job_id

    @property
    def document_id(self) -> UUID:
        self._assert_not_expired()
        return self._document_id

    def _assert_not_expired(self) -> None:
        if self._session.attributes_expired:
            raise RuntimeError("expired ORM job attribute was accessed")


class RollbackSensitiveAnalysis:
    """Simulate an analysis identity expired by rollback."""

    def __init__(self, session: RecordingSession, analysis_id: UUID) -> None:
        self._session = session
        self._analysis_id = analysis_id

    @property
    def id(self) -> UUID:
        if self._session.attributes_expired:
            raise RuntimeError("expired ORM analysis attribute was accessed")
        return self._analysis_id


class FakeDocumentRepository:
    def __init__(self, document: Document) -> None:
        self.document = document

    async def get(self, session: object, document_id: object) -> Document:
        return self.document


class ClaimOnceJobRepository:
    def __init__(self, job: ProcessingJob) -> None:
        self.job = job
        self.claimed = False
        self.completed = False
        self.failure_code: str | None = None
        self.status = JobStatus.QUEUED

    async def claim(self, session: object, job_id: object) -> ProcessingJob | None:
        if self.claimed:
            return None
        self.claimed = True
        self.status = JobStatus.PROCESSING
        return self.job

    async def mark_completed(self, session: object, job_id: object) -> bool:
        self.completed = True
        self.status = JobStatus.COMPLETED
        return True

    async def mark_failed(
        self,
        session: object,
        job_id: object,
        *,
        error_message: str,
    ) -> bool:
        self.failure_code = error_message
        self.status = JobStatus.FAILED
        return True


class RecordingAnalysisRepository:
    def __init__(
        self,
        document_id: UUID,
        job_id: UUID,
        *,
        analysis: object | None = None,
    ) -> None:
        self.analysis = analysis or DocumentAnalysis(
            id=uuid4(),
            document_id=document_id,
            job_id=job_id,
            status=AnalysisStatus.PROCESSING,
            provider="openai",
            model_name="configured-model",
            created_at=datetime.now(UTC),
        )
        self.completed_values: dict[str, object] | None = None
        self.failure_code: str | None = None
        self.status = AnalysisStatus.PROCESSING

    async def start(self, session: object, **values: object) -> DocumentAnalysis:
        return cast(DocumentAnalysis, self.analysis)

    async def mark_completed(
        self,
        session: object,
        analysis_id: object,
        **values: object,
    ) -> bool:
        self.completed_values = values
        self.status = AnalysisStatus.COMPLETED
        return True

    async def mark_failed(
        self,
        session: object,
        analysis_id: object,
        *,
        error_code: str,
    ) -> bool:
        self.failure_code = error_code
        self.status = AnalysisStatus.FAILED
        return True


class FakeStorage:
    async def read(self, key: str) -> bytes:
        return uuid4().bytes


class FakeExtractor:
    def __init__(self) -> None:
        self.result = ExtractedDocument(
            text=uuid4().hex,
            source_character_count=40,
            was_truncated=False,
            metadata={"row_count": 2},
        )

    async def extract(
        self,
        content: bytes,
        *,
        media_type: str,
        max_characters: int,
    ) -> ExtractedDocument:
        return self.result


class FakeAnalyzer:
    provider = "openai"
    model_name = "configured-model"

    def __init__(self, *, failure_detail: str | None = None) -> None:
        self.failure_detail = failure_detail
        self.calls = 0

    async def analyze(
        self,
        text: str,
        *,
        context: AnalysisContext,
    ) -> AnalyzerResult:
        self.calls += 1
        if self.failure_detail is not None:
            raise AnalyzerError(self.failure_detail)
        return AnalyzerResult(
            output=AnalysisOutput(
                summary="Concise summary",
                document_type="report",
                key_points=["Key point"],
            ),
            provider=self.provider,
            model_name=self.model_name,
            input_tokens=20,
            output_tokens=10,
        )

    async def close(self) -> None:
        return None


def build_service(
    *,
    analysis_repository: RecordingAnalysisRepository,
    analyzer: FakeAnalyzer,
    document: Document,
    job_repository: ClaimOnceJobRepository,
) -> DocumentProcessingService:
    return DocumentProcessingService(
        analysis_repository=cast(DocumentAnalysisRepository, analysis_repository),
        analyzer=cast(DocumentAnalyzer, analyzer),
        document_repository=cast(
            DocumentRepository,
            FakeDocumentRepository(document),
        ),
        extractor=cast(DocumentTextExtractor, FakeExtractor()),
        job_repository=cast(ProcessingJobRepository, job_repository),
        max_input_characters=1000,
        storage=cast(ObjectStorage, FakeStorage()),
    )


def build_document_and_job() -> tuple[Document, ProcessingJob]:
    document_id = uuid4()
    job_id = uuid4()
    return (
        Document(
            id=document_id,
            original_filename="fixture.pdf",
            media_type="application/pdf",
            size_bytes=10,
            checksum_sha256="a" * 64,
            storage_key="documents/fixture.pdf",
        ),
        ProcessingJob(
            id=job_id,
            document_id=document_id,
            status=JobStatus.QUEUED,
            celery_task_id=str(job_id),
        ),
    )


@pytest.mark.asyncio
async def test_processing_success_persists_analysis_and_is_idempotent() -> None:
    document, job = build_document_and_job()
    job_repository = ClaimOnceJobRepository(job)
    analysis_repository = RecordingAnalysisRepository(document.id, job.id)
    analyzer = FakeAnalyzer()
    session = RecordingSession()
    service = build_service(
        analysis_repository=analysis_repository,
        analyzer=analyzer,
        document=document,
        job_repository=job_repository,
    )

    first = await service.process(cast(AsyncSession, session), job.id)
    duplicate = await service.process(cast(AsyncSession, session), job.id)

    assert first is True
    assert duplicate is False
    assert analyzer.calls == 1
    assert job_repository.completed is True
    assert analysis_repository.completed_values is not None
    assert analysis_repository.completed_values["summary"] == "Concise summary"
    assert session.commits == 3
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_openai_rate_limit_failure_uses_captured_ids_and_marks_job_failed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    document, job = build_document_and_job()
    session = RecordingSession()
    job_id = job.id
    document_id = document.id
    job_repository = ClaimOnceJobRepository(
        cast(
            ProcessingJob,
            RollbackSensitiveJob(
                session,
                job_id=job_id,
                document_id=document_id,
            ),
        )
    )
    analysis_repository = RecordingAnalysisRepository(
        document_id,
        job_id,
        analysis=RollbackSensitiveAnalysis(session, uuid4()),
    )
    provider_detail = uuid4().hex
    service = build_service(
        analysis_repository=analysis_repository,
        analyzer=FakeAnalyzer(failure_detail=provider_detail),
        document=document,
        job_repository=job_repository,
    )

    with pytest.raises(AnalyzerError):
        await service.process(cast(AsyncSession, session), job_id)

    assert analysis_repository.failure_code == "ai_analysis_failed"
    assert job_repository.failure_code == "ai_analysis_failed"
    assert analysis_repository.status is AnalysisStatus.FAILED
    assert job_repository.status is JobStatus.FAILED
    assert provider_detail not in caplog.text
    assert session.commits == 3
    assert session.rollbacks == 1
