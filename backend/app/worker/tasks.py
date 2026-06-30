"""Celery task adapters for document processing."""

import asyncio
from uuid import UUID

from app.analysis.openai import OpenAIDocumentAnalyzer
from app.config.settings import get_settings
from app.database.session import Database
from app.extraction.csv import CsvTextExtractor
from app.extraction.pdf import PdfTextExtractor
from app.extraction.service import CompositeDocumentTextExtractor
from app.messaging.base import DOCUMENT_PROCESSING_TASK_NAME
from app.repositories.document_analyses import DocumentAnalysisRepository
from app.repositories.documents import DocumentRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.services.processing import DocumentProcessingService
from app.storage.local import LocalObjectStorage
from app.worker.celery_app import celery_app


@celery_app.task(name=DOCUMENT_PROCESSING_TASK_NAME)  # type: ignore[untyped-decorator]
def process_document(job_id: str) -> None:
    """Run one async processing workflow from a Celery worker process."""

    asyncio.run(_process_document(UUID(job_id)))


async def _process_document(job_id: UUID) -> None:
    settings = get_settings()
    database = Database(settings)
    storage = LocalObjectStorage(settings.upload_directory)
    extractor = CompositeDocumentTextExtractor([PdfTextExtractor(), CsvTextExtractor()])
    analyzer = OpenAIDocumentAnalyzer(
        api_key=(
            settings.openai_api_key.get_secret_value()
            if settings.openai_api_key
            else None
        ),
        instructions=(
            settings.openai_analysis_instructions.get_secret_value()
            if settings.openai_analysis_instructions
            else None
        ),
        model=settings.ai_model,
        max_output_tokens=settings.ai_max_output_tokens,
        timeout_seconds=settings.openai_timeout_seconds,
        max_retries=settings.openai_max_retries,
    )
    service = DocumentProcessingService(
        analysis_repository=DocumentAnalysisRepository(),
        analyzer=analyzer,
        document_repository=DocumentRepository(),
        extractor=extractor,
        job_repository=ProcessingJobRepository(),
        max_input_characters=settings.ai_max_input_characters,
        storage=storage,
    )

    try:
        await storage.initialize()
        async with database.session() as session:
            await service.process(session, job_id)
    finally:
        await analyzer.close()
        await database.dispose()
