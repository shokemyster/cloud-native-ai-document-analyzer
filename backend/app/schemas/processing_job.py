"""Processing-job API response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.processing_job import JobStatus


class ProcessingJobResponse(BaseModel):
    """Public status for an asynchronous document-processing job."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    document_id: UUID
    status: JobStatus
    attempt_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class ProcessingJobListResponse(BaseModel):
    """Paginated processing-job collection."""

    items: list[ProcessingJobResponse]
    total: int
    limit: int
    offset: int
