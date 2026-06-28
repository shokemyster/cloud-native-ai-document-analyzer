"""Celery task adapters for document processing."""

import asyncio
from uuid import UUID

from app.config.settings import get_settings
from app.database.session import Database
from app.messaging.base import DOCUMENT_PROCESSING_TASK_NAME
from app.repositories.documents import DocumentRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.services.processing import DocumentProcessingService
from app.worker.celery_app import celery_app


@celery_app.task(name=DOCUMENT_PROCESSING_TASK_NAME)  # type: ignore[untyped-decorator]
def process_document(job_id: str) -> None:
    """Run one async processing workflow from a Celery worker process."""

    asyncio.run(_process_document(UUID(job_id)))


async def _process_document(job_id: UUID) -> None:
    settings = get_settings()
    database = Database(settings)
    service = DocumentProcessingService(
        document_repository=DocumentRepository(),
        job_repository=ProcessingJobRepository(),
    )

    try:
        async with database.session() as session:
            await service.process(session, job_id)
    finally:
        await database.dispose()
