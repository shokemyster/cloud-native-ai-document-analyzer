"""Storage interfaces shared by application services and adapters."""

from dataclasses import dataclass
from typing import Protocol


class AsyncReadable(Protocol):
    """Minimal asynchronous byte-stream contract."""

    async def read(self, size: int = -1) -> bytes: ...


@dataclass(frozen=True, slots=True)
class StoredObject:
    """Metadata calculated while persisting a file."""

    key: str
    size_bytes: int
    checksum_sha256: str


class StorageError(Exception):
    """Base exception for object-storage failures."""


class EmptyObjectError(StorageError):
    """Raised when an uploaded stream contains no bytes."""


class ObjectTooLargeError(StorageError):
    """Raised when a stream exceeds its configured maximum size."""


class ObjectStorage(Protocol):
    """Asynchronous storage contract for document bytes."""

    async def initialize(self) -> None: ...

    async def save(
        self,
        source: AsyncReadable,
        *,
        key: str,
        max_size_bytes: int,
    ) -> StoredObject: ...

    async def delete(self, key: str) -> None: ...
