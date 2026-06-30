"""Persistence and lifecycle transitions for document analyses."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_analysis import AnalysisStatus, DocumentAnalysis

MAX_ERROR_CODE_LENGTH = 100


class DocumentAnalysisRepository:
    """Create, update, and query structured document analyses."""

    async def start(
        self,
        session: AsyncSession,
        *,
        document_id: UUID,
        job_id: UUID,
        provider: str,
        model_name: str,
    ) -> DocumentAnalysis:
        existing = await self.get_by_job(session, job_id)
        if existing is not None:
            existing.status = AnalysisStatus.PROCESSING
            existing.provider = provider
            existing.model_name = model_name
            existing.summary = None
            existing.structured_output = None
            existing.status_metadata = {}
            existing.error_code = None
            existing.completed_at = None
            await session.flush()
            return existing

        analysis = DocumentAnalysis(
            document_id=document_id,
            job_id=job_id,
            status=AnalysisStatus.PROCESSING,
            provider=provider,
            model_name=model_name,
        )
        session.add(analysis)
        await session.flush()
        return analysis

    async def get_by_job(
        self,
        session: AsyncSession,
        job_id: UUID,
    ) -> DocumentAnalysis | None:
        statement = select(DocumentAnalysis).where(DocumentAnalysis.job_id == job_id)
        result = await session.scalars(statement)
        return result.one_or_none()

    async def get_latest_for_document(
        self,
        session: AsyncSession,
        document_id: UUID,
    ) -> DocumentAnalysis | None:
        statement = (
            select(DocumentAnalysis)
            .where(DocumentAnalysis.document_id == document_id)
            .order_by(DocumentAnalysis.created_at.desc(), DocumentAnalysis.id.desc())
            .limit(1)
        )
        result = await session.scalars(statement)
        return result.one_or_none()

    async def mark_completed(
        self,
        session: AsyncSession,
        analysis_id: UUID,
        *,
        summary: str,
        structured_output: dict[str, object],
        status_metadata: dict[str, object],
        provider: str,
        model_name: str,
    ) -> bool:
        statement = (
            update(DocumentAnalysis)
            .where(
                DocumentAnalysis.id == analysis_id,
                DocumentAnalysis.status == AnalysisStatus.PROCESSING,
            )
            .values(
                status=AnalysisStatus.COMPLETED,
                summary=summary,
                structured_output=structured_output,
                status_metadata=status_metadata,
                provider=provider,
                model_name=model_name,
                error_code=None,
                completed_at=func.now(),
            )
            .returning(DocumentAnalysis.id)
        )
        result = await session.scalar(statement)
        return result is not None

    async def mark_failed(
        self,
        session: AsyncSession,
        analysis_id: UUID,
        *,
        error_code: str,
    ) -> bool:
        statement = (
            update(DocumentAnalysis)
            .where(
                DocumentAnalysis.id == analysis_id,
                DocumentAnalysis.status == AnalysisStatus.PROCESSING,
            )
            .values(
                status=AnalysisStatus.FAILED,
                error_code=error_code[:MAX_ERROR_CODE_LENGTH],
                completed_at=func.now(),
            )
            .returning(DocumentAnalysis.id)
        )
        result = await session.scalar(statement)
        return result is not None
