"""Background document-processing workflow."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.documents import DocumentRepository
from app.repositories.processing_jobs import ProcessingJobRepository

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    """Claim and execute one idempotent document-processing job."""

    def __init__(
        self,
        *,
        document_repository: DocumentRepository,
        job_repository: ProcessingJobRepository,
    ) -> None:
        self._document_repository = document_repository
        self._job_repository = job_repository

    async def process(self, session: AsyncSession, job_id: UUID) -> bool:
        job = await self._job_repository.claim(session, job_id)
        if job is None:
            logger.info(
                "Processing job was already claimed or is terminal",
                extra={"job_id": str(job_id)},
            )
            await session.rollback()
            return False

        await session.commit()

        try:
            document = await self._document_repository.get(session, job.document_id)
            if document is None:
                raise RuntimeError("Processing job document does not exist")

            logger.info(
                "Document processed",
                extra={
                    "document_id": str(document.id),
                    "job_id": str(job.id),
                    "media_type": document.media_type,
                },
            )

            completed = await self._job_repository.mark_completed(session, job.id)
            if not completed:
                raise RuntimeError("Processing job could not be completed")
            await session.commit()
        except Exception as exc:
            await session.rollback()
            await self._record_failure(session, job.id, exc)
            raise

        return True

    async def _record_failure(
        self,
        session: AsyncSession,
        job_id: UUID,
        error: Exception,
    ) -> None:
        logger.exception(
            "Document processing failed",
            extra={"job_id": str(job_id)},
        )
        try:
            await self._job_repository.mark_failed(
                session,
                job_id,
                error_message=type(error).__name__,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception(
                "Failed to persist processing failure",
                extra={"job_id": str(job_id)},
            )
