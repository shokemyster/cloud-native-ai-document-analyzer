"""Document-analysis query use cases."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_analysis import DocumentAnalysis
from app.repositories.document_analyses import DocumentAnalysisRepository
from app.repositories.documents import DocumentRepository


class AnalysisDocumentNotFoundError(Exception):
    """Raised when the source document does not exist."""


class DocumentAnalysisNotFoundError(Exception):
    """Raised when a document has no analysis attempt yet."""


class DocumentAnalysisService:
    """Retrieve persisted analysis state without provider dependencies."""

    def __init__(
        self,
        *,
        analysis_repository: DocumentAnalysisRepository,
        document_repository: DocumentRepository,
    ) -> None:
        self._analysis_repository = analysis_repository
        self._document_repository = document_repository

    async def get_latest(
        self,
        session: AsyncSession,
        document_id: UUID,
    ) -> DocumentAnalysis:
        document = await self._document_repository.get(session, document_id)
        if document is None:
            raise AnalysisDocumentNotFoundError

        analysis = await self._analysis_repository.get_latest_for_document(
            session,
            document_id,
        )
        if analysis is None:
            raise DocumentAnalysisNotFoundError
        return analysis
