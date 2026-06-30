"""Local filesystem object-storage adapter for development."""

import asyncio
import hashlib
import os
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.storage.base import (
    AsyncReadable,
    EmptyObjectError,
    ObjectTooLargeError,
    StorageError,
    StoredObject,
)

CHUNK_SIZE_BYTES = 1024 * 1024


class LocalObjectStorage:
    """Store document bytes beneath one configured local directory."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    async def initialize(self) -> None:
        await asyncio.to_thread(self._root.mkdir, parents=True, exist_ok=True)

    async def save(
        self,
        source: AsyncReadable,
        *,
        key: str,
        max_size_bytes: int,
    ) -> StoredObject:
        destination = self._path_for(key)
        temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
        digest = hashlib.sha256()
        size_bytes = 0
        file_handle: BinaryIO | None = None

        await asyncio.to_thread(destination.parent.mkdir, parents=True, exist_ok=True)

        try:
            file_handle = await asyncio.to_thread(temporary.open, "xb")

            while chunk := await source.read(CHUNK_SIZE_BYTES):
                size_bytes += len(chunk)
                if size_bytes > max_size_bytes:
                    raise ObjectTooLargeError

                digest.update(chunk)
                await asyncio.to_thread(file_handle.write, chunk)

            if size_bytes == 0:
                raise EmptyObjectError

            await asyncio.to_thread(file_handle.flush)
            await asyncio.to_thread(os.fsync, file_handle.fileno())
            await asyncio.to_thread(file_handle.close)
            file_handle = None
            await asyncio.to_thread(os.replace, temporary, destination)
        except (EmptyObjectError, ObjectTooLargeError):
            await self._cleanup(file_handle, temporary)
            raise
        except OSError as exc:
            await self._cleanup(file_handle, temporary)
            raise StorageError("Local object storage operation failed") from exc
        except BaseException:
            await self._cleanup(file_handle, temporary)
            raise

        return StoredObject(
            key=key,
            size_bytes=size_bytes,
            checksum_sha256=digest.hexdigest(),
        )

    async def read(self, key: str) -> bytes:
        path = self._path_for(key)
        try:
            return await asyncio.to_thread(path.read_bytes)
        except OSError as exc:
            raise StorageError("Local object read failed") from exc

    async def delete(self, key: str) -> None:
        path = self._path_for(key)
        try:
            await asyncio.to_thread(path.unlink, missing_ok=True)
        except OSError as exc:
            raise StorageError("Local object deletion failed") from exc

    def _path_for(self, key: str) -> Path:
        if not key:
            raise StorageError("Storage key must not be empty")

        candidate = (self._root / key).resolve()
        if not candidate.is_relative_to(self._root):
            raise StorageError("Storage key escapes the configured root")
        return candidate

    async def _cleanup(
        self,
        file_handle: BinaryIO | None,
        temporary: Path,
    ) -> None:
        if file_handle is not None:
            await asyncio.to_thread(file_handle.close)
        await asyncio.to_thread(temporary.unlink, missing_ok=True)
