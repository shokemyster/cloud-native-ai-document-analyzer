"""Document upload and query use cases."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.messaging.base import DocumentTaskPublisher, TaskPublishError
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.repositories.documents import DocumentRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.storage.base import (
    AsyncReadable,
    EmptyObjectError,
    ObjectStorage,
    ObjectTooLargeError,
    StorageError,
)

logger = logging.getLogger(__name__)


class Upload(AsyncReadable, Protocol):
    """Upload metadata and stream required by the service."""

    filename: str | None
    content_type: str | None


class DocumentServiceError(Exception):
    """Base exception for expected document workflow failures."""


class InvalidFilenameError(DocumentServiceError):
    """Raised when an upload has no safe display filename."""


class UnsupportedDocumentTypeError(DocumentServiceError):
    """Raised when upload extension or media type is unsupported."""


class EmptyDocumentError(DocumentServiceError):
    """Raised when an uploaded document contains no bytes."""


class DocumentTooLargeError(DocumentServiceError):
    """Raised when an upload exceeds the configured size limit."""


class DocumentNotFoundError(DocumentServiceError):
    """Raised when requested document metadata does not exist."""


class JobEnqueueError(DocumentServiceError):
    """Raised after persistence when the broker rejects a new job."""

    def __init__(self, *, document_id: UUID, job_id: UUID) -> None:
        super().__init__("Processing job could not be enqueued")
        self.document_id = document_id
        self.job_id = job_id


@dataclass(frozen=True, slots=True)
class DocumentUploadResult:
    """Resources created by an accepted document upload."""

    document: Document
    job: ProcessingJob


class DocumentService:
    """Coordinate storage and metadata persistence for documents."""

    def __init__(
        self,
        *,
        repository: DocumentRepository,
        job_repository: ProcessingJobRepository,
        publisher: DocumentTaskPublisher,
        storage: ObjectStorage,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._job_repository = job_repository
        self._publisher = publisher
        self._storage = storage
        self._settings = settings

    async def upload(
        self,
        session: AsyncSession,
        upload: Upload,
    ) -> DocumentUploadResult:
        filename = self._validated_filename(upload.filename)
        extension = Path(filename).suffix.lower()
        media_type = (upload.content_type or "").partition(";")[0].lower()

        if extension not in self._settings.allowed_upload_extensions:
            raise UnsupportedDocumentTypeError
        if media_type not in self._settings.allowed_upload_media_types:
            raise UnsupportedDocumentTypeError

        storage_key = f"documents/{uuid4().hex}{extension}"

        try:
            stored_object = await self._storage.save(
                upload,
                key=storage_key,
                max_size_bytes=self._settings.max_upload_size_bytes,
            )
        except EmptyObjectError as exc:
            raise EmptyDocumentError from exc
        except ObjectTooLargeError as exc:
            raise DocumentTooLargeError from exc

        try:
            document = await self._repository.create(
                session,
                original_filename=filename,
                media_type=media_type,
                size_bytes=stored_object.size_bytes,
                checksum_sha256=stored_object.checksum_sha256,
                storage_key=stored_object.key,
            )
            job = await self._job_repository.create(
                session,
                document_id=document.id,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            try:
                await self._storage.delete(storage_key)
            except StorageError:
                logger.exception(
                    "Failed to remove stored object after database failure",
                    extra={"storage_key": storage_key},
                )
            raise

        try:
            await self._publisher.publish(job.id)
        except TaskPublishError as exc:
            await self._record_enqueue_failure(session, job, exc)
            raise JobEnqueueError(
                document_id=document.id,
                job_id=job.id,
            ) from exc

        try:
            await self._job_repository.mark_queued(session, job.id)
            await session.commit()
            await session.refresh(job)
        except Exception:
            await session.rollback()
            logger.exception(
                "Job was published but queued status could not be persisted",
                extra={"job_id": str(job.id)},
            )

        return DocumentUploadResult(document=document, job=job)

    async def get(self, session: AsyncSession, document_id: UUID) -> Document:
        document = await self._repository.get(session, document_id)
        if document is None:
            raise DocumentNotFoundError
        return document

    async def list(
        self,
        session: AsyncSession,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Document], int]:
        documents = await self._repository.list(
            session,
            limit=limit,
            offset=offset,
        )
        total = await self._repository.count(session)
        return documents, total

    @staticmethod
    def _validated_filename(filename: str | None) -> str:
        safe_filename = Path(filename or "").name.strip()
        if safe_filename in {"", ".", ".."} or len(safe_filename) > 255:
            raise InvalidFilenameError
        return safe_filename

    async def _record_enqueue_failure(
        self,
        session: AsyncSession,
        job: ProcessingJob,
        error: TaskPublishError,
    ) -> None:
        try:
            await self._job_repository.mark_enqueue_failed(
                session,
                job.id,
                error_message=str(error),
            )
            await session.commit()
            await session.refresh(job)
        except Exception:
            await session.rollback()
            logger.exception(
                "Failed to persist broker publication failure",
                extra={"job_id": str(job.id)},
            )
