"""Unit tests for the local object-storage adapter."""

import asyncio
import hashlib
from pathlib import Path

import pytest

from app.storage.base import ObjectTooLargeError, StorageError
from app.storage.local import LocalObjectStorage


class MemoryStream:
    """Small async byte stream used to exercise chunked storage."""

    def __init__(self, content: bytes) -> None:
        self._content = content
        self._position = 0

    async def read(self, size: int = -1) -> bytes:
        if self._position >= len(self._content):
            return b""

        end = len(self._content) if size < 0 else self._position + size
        chunk = self._content[self._position : end]
        self._position = end
        return chunk


class CancellingStream:
    """Stream that simulates cancellation after writing a partial object."""

    def __init__(self) -> None:
        self._read_count = 0

    async def read(self, size: int = -1) -> bytes:
        self._read_count += 1
        if self._read_count == 1:
            return b"partial"
        raise asyncio.CancelledError


@pytest.mark.asyncio
async def test_save_streams_content_and_calculates_metadata(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path)
    await storage.initialize()
    content = b"document content"

    stored = await storage.save(
        MemoryStream(content),
        key="documents/example.pdf",
        max_size_bytes=1024,
    )

    assert (tmp_path / stored.key).read_bytes() == content
    assert stored.size_bytes == len(content)
    assert stored.checksum_sha256 == hashlib.sha256(content).hexdigest()


@pytest.mark.asyncio
async def test_save_removes_partial_file_when_limit_is_exceeded(
    tmp_path: Path,
) -> None:
    storage = LocalObjectStorage(tmp_path)
    await storage.initialize()

    with pytest.raises(ObjectTooLargeError):
        await storage.save(
            MemoryStream(b"too large"),
            key="oversized.csv",
            max_size_bytes=3,
        )

    remaining_files = await asyncio.to_thread(lambda: list(tmp_path.iterdir()))
    assert remaining_files == []


@pytest.mark.asyncio
async def test_storage_key_cannot_escape_root(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path)
    await storage.initialize()

    with pytest.raises(StorageError, match="escapes"):
        await storage.save(
            MemoryStream(b"content"),
            key="../outside.pdf",
            max_size_bytes=1024,
        )


@pytest.mark.asyncio
async def test_save_removes_partial_file_when_cancelled(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path)
    await storage.initialize()

    with pytest.raises(asyncio.CancelledError):
        await storage.save(
            CancellingStream(),
            key="cancelled.pdf",
            max_size_bytes=1024,
        )

    remaining_files = await asyncio.to_thread(lambda: list(tmp_path.iterdir()))
    assert remaining_files == []
