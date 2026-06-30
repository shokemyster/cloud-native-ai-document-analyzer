"""Document-analysis API response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.analysis.base import AnalysisOutput
from app.models.document_analysis import AnalysisStatus


class DocumentAnalysisResponse(BaseModel):
    """Latest persisted analysis state for a document."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    document_id: UUID
    job_id: UUID
    status: AnalysisStatus
    provider: str
    model_name: str
    summary: str | None
    structured_output: AnalysisOutput | None
    status_metadata: dict[str, object]
    error_code: str | None
    created_at: datetime
    completed_at: datetime | None
