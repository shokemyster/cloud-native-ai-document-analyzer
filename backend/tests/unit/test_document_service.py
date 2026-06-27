"""Unit tests for document workflow validation."""

from pathlib import Path
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.repositories.documents import DocumentRepository
from app.services.documents import (
    DocumentService,
    DocumentTooLargeError,
    UnsupportedDocumentTypeError,
)
from app.storage.base import ObjectTooLargeError, StoredObject


class FakeUpload:
    """Upload stream with configurable request metadata."""

    def __init__(self, *, filename: str, content_type: str) -> None:
        self.filename: str | None = filename
        self.content_type: str | None = content_type

    async def read(self, size: int = -1) -> bytes:
        return b"content"


class RecordingStorage:
    """Storage fake that records whether persistence was attempted."""

    def __init__(self, *, too_large: bool = False) -> None:
        self.save_called = False
        self._too_large = too_large

    async def initialize(self) -> None:
        return None

    async def save(
        self,
        source: FakeUpload,
        *,
        key: str,
        max_size_bytes: int,
    ) -> StoredObject:
        self.save_called = True
        if self._too_large:
            raise ObjectTooLargeError
        return StoredObject(key=key, size_bytes=7, checksum_sha256="a" * 64)

    async def delete(self, key: str) -> None:
        return None


def build_settings(tmp_path: Path) -> Settings:
    return Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://unused",
            "upload_directory": tmp_path,
        }
    )


@pytest.mark.asyncio
async def test_unsupported_extension_is_rejected_before_storage(
    tmp_path: Path,
) -> None:
    storage = RecordingStorage()
    service = DocumentService(
        repository=DocumentRepository(),
        storage=storage,
        settings=build_settings(tmp_path),
    )

    with pytest.raises(UnsupportedDocumentTypeError):
        await service.upload(
            cast(AsyncSession, object()),
            FakeUpload(filename="notes.txt", content_type="text/plain"),
        )

    assert storage.save_called is False


@pytest.mark.asyncio
async def test_storage_size_error_becomes_service_error(tmp_path: Path) -> None:
    service = DocumentService(
        repository=DocumentRepository(),
        storage=RecordingStorage(too_large=True),
        settings=build_settings(tmp_path),
    )

    with pytest.raises(DocumentTooLargeError):
        await service.upload(
            cast(AsyncSession, object()),
            FakeUpload(filename="report.pdf", content_type="application/pdf"),
        )
