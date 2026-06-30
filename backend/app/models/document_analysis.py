"""Persisted structured document-analysis results."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AnalysisStatus(StrEnum):
    """Persisted lifecycle states for one analysis attempt."""

    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentAnalysis(Base):
    """Structured AI result and non-sensitive processing metadata."""

    __tablename__ = "document_analyses"
    __table_args__ = (
        Index(
            "ix_document_analyses_document_created_at",
            "document_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    document_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(
            AnalysisStatus,
            name="document_analysis_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda values: [item.value for item in values],
            length=32,
        ),
        nullable=False,
        default=AnalysisStatus.PROCESSING,
        server_default=AnalysisStatus.PROCESSING.value,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_output: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    status_metadata: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
