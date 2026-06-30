"""Text-extraction contracts and domain errors."""

from dataclasses import dataclass
from typing import Protocol

type MetadataValue = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class RawExtraction:
    """Text and metadata returned by one format-specific parser."""

    text: str
    metadata: dict[str, MetadataValue]


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    """Normalized and size-bounded text prepared for analysis."""

    text: str
    source_character_count: int
    was_truncated: bool
    metadata: dict[str, MetadataValue]


class ExtractionError(Exception):
    """Base exception for expected document-extraction failures."""


class UnsupportedDocumentFormatError(ExtractionError):
    """Raised when no parser supports a document media type."""


class InvalidDocumentError(ExtractionError):
    """Raised when document bytes cannot be parsed safely."""


class NoExtractableTextError(ExtractionError):
    """Raised when a document contains no machine-readable text."""


class ContentTextExtractor(Protocol):
    """Synchronous parser for one or more document media types."""

    supported_media_types: frozenset[str]

    def extract(self, content: bytes) -> RawExtraction: ...


class DocumentTextExtractor(Protocol):
    """Asynchronous facade selecting and bounding format-specific parsing."""

    async def extract(
        self,
        content: bytes,
        *,
        media_type: str,
        max_characters: int,
    ) -> ExtractedDocument: ...
