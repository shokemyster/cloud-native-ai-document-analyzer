"""Create asynchronous processing jobs.

Revision ID: 20260628_0002
Revises: 20260627_0001
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260628_0002"
down_revision: str | None = "20260627_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create durable processing-job state."""

    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("celery_task_id", sa.String(length=255), nullable=False),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_processing_jobs_attempt_count_nonnegative",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'queued', 'processing', 'completed', "
            "'enqueue_failed', 'failed')",
            name="processing_job_status",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_processing_jobs_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_processing_jobs"),
    )
    op.create_index(
        "ix_processing_jobs_document_id",
        "processing_jobs",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_processing_jobs_status_created_at",
        "processing_jobs",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove processing-job state."""

    op.drop_index(
        "ix_processing_jobs_status_created_at",
        table_name="processing_jobs",
    )
    op.drop_index(
        "ix_processing_jobs_document_id",
        table_name="processing_jobs",
    )
    op.drop_table("processing_jobs")
