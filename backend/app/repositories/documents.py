"""SQLAlchemy repository for document metadata."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


class DocumentRepository:
    """Persist and query document metadata."""

    async def create(
        self,
        session: AsyncSession,
        *,
        original_filename: str,
        media_type: str,
        size_bytes: int,
        checksum_sha256: str,
        storage_key: str,
    ) -> Document:
        document = Document(
            original_filename=original_filename,
            media_type=media_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            storage_key=storage_key,
        )
        session.add(document)
        await session.flush()
        return document

    async def get(self, session: AsyncSession, document_id: UUID) -> Document | None:
        return await session.get(Document, document_id)

    async def list(
        self,
        session: AsyncSession,
        *,
        limit: int,
        offset: int,
    ) -> list[Document]:
        statement = (
            select(Document)
            .order_by(Document.created_at.desc(), Document.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.scalars(statement)
        return list(result.all())

    async def count(self, session: AsyncSession) -> int:
        statement = select(func.count()).select_from(Document)
        result = await session.scalar(statement)
        return int(result or 0)
