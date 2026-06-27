"""Document API response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    """Public metadata returned for an uploaded document."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    original_filename: str
    media_type: str
    size_bytes: int
    checksum_sha256: str
    created_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated document collection."""

    items: list[DocumentResponse]
    total: int
    limit: int
    offset: int
