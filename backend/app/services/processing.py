"""Background document-processing and AI-analysis workflow."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.base import AnalysisContext, AnalyzerError, DocumentAnalyzer
from app.extraction.base import DocumentTextExtractor, ExtractionError
from app.repositories.document_analyses import DocumentAnalysisRepository
from app.repositories.documents import DocumentRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.storage.base import ObjectStorage, StorageError

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    """Claim, analyze, and complete one idempotent processing job."""

    def __init__(
        self,
        *,
        analysis_repository: DocumentAnalysisRepository,
        analyzer: DocumentAnalyzer,
        document_repository: DocumentRepository,
        extractor: DocumentTextExtractor,
        job_repository: ProcessingJobRepository,
        max_input_characters: int,
        storage: ObjectStorage,
    ) -> None:
        self._analysis_repository = analysis_repository
        self._analyzer = analyzer
        self._document_repository = document_repository
        self._extractor = extractor
        self._job_repository = job_repository
        self._max_input_characters = max_input_characters
        self._storage = storage

    async def process(self, session: AsyncSession, job_id: UUID) -> bool:
        job = await self._job_repository.claim(session, job_id)
        if job is None:
            logger.info(
                "Processing job was already claimed or is terminal",
                extra={"job_id": str(job_id)},
            )
            await session.rollback()
            return False

        claimed_job_id = job.id
        document_id = job.document_id
        await session.commit()
        analysis_id: UUID | None = None

        try:
            analysis = await self._analysis_repository.start(
                session,
                document_id=document_id,
                job_id=claimed_job_id,
                provider=self._analyzer.provider,
                model_name=self._analyzer.model_name,
            )
            analysis_id = analysis.id
            await session.commit()

            document = await self._document_repository.get(session, document_id)
            if document is None:
                raise RuntimeError("Processing job document does not exist")

            stored_document_id = document.id
            storage_key = document.storage_key
            media_type = document.media_type
            original_filename = document.original_filename

            content = await self._storage.read(storage_key)
            extracted = await self._extractor.extract(
                content,
                media_type=media_type,
                max_characters=self._max_input_characters,
            )
            analyzer_result = await self._analyzer.analyze(
                extracted.text,
                context=AnalysisContext(
                    filename=original_filename,
                    media_type=media_type,
                ),
            )

            status_metadata: dict[str, object] = {
                "source_character_count": extracted.source_character_count,
                "analyzed_character_count": len(extracted.text),
                "was_truncated": extracted.was_truncated,
                "extraction": extracted.metadata,
                "input_tokens": analyzer_result.input_tokens,
                "output_tokens": analyzer_result.output_tokens,
            }
            analysis_completed = await self._analysis_repository.mark_completed(
                session,
                analysis_id,
                summary=analyzer_result.output.summary,
                structured_output=analyzer_result.output.model_dump(mode="json"),
                status_metadata=status_metadata,
                provider=analyzer_result.provider,
                model_name=analyzer_result.model_name,
            )
            job_completed = await self._job_repository.mark_completed(
                session,
                claimed_job_id,
            )
            if not analysis_completed or not job_completed:
                raise RuntimeError("Processing completion transition failed")
            await session.commit()

            logger.info(
                "Document analysis completed",
                extra={
                    "analysis_id": str(analysis_id),
                    "document_id": str(stored_document_id),
                    "job_id": str(claimed_job_id),
                    "model_name": analyzer_result.model_name,
                },
            )
        except Exception as exc:
            await session.rollback()
            await self._record_failure(
                session,
                job_id=claimed_job_id,
                document_id=document_id,
                analysis_id=analysis_id,
                error=exc,
            )
            raise

        return True

    async def _record_failure(
        self,
        session: AsyncSession,
        *,
        job_id: UUID,
        document_id: UUID,
        analysis_id: UUID | None,
        error: Exception,
    ) -> None:
        error_code = self._error_code(error)
        logger.error(
            "Document analysis failed",
            extra={
                "document_id": str(document_id),
                "error_code": error_code,
                "job_id": str(job_id),
            },
        )
        try:
            if analysis_id is not None:
                await self._analysis_repository.mark_failed(
                    session,
                    analysis_id,
                    error_code=error_code,
                )
            await self._job_repository.mark_failed(
                session,
                job_id,
                error_message=error_code,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            logger.error(
                "Failed to persist analysis failure state",
                extra={
                    "document_id": str(document_id),
                    "job_id": str(job_id),
                },
            )

    @staticmethod
    def _error_code(error: Exception) -> str:
        if isinstance(error, StorageError):
            return "storage_read_failed"
        if isinstance(error, ExtractionError):
            return "text_extraction_failed"
        if isinstance(error, AnalyzerError):
            return "ai_analysis_failed"
        return "processing_failed"
