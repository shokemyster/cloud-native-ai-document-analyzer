"""Parser selection, text normalization, and input bounding."""

import asyncio
from collections.abc import Iterable

from app.extraction.base import (
    ContentTextExtractor,
    ExtractedDocument,
    NoExtractableTextError,
    UnsupportedDocumentFormatError,
)

TRUNCATION_MARKER = "\n\n[... document text truncated ...]\n\n"


class CompositeDocumentTextExtractor:
    """Select a parser and prepare bounded text for an analyzer."""

    def __init__(self, extractors: Iterable[ContentTextExtractor]) -> None:
        self._extractors: dict[str, ContentTextExtractor] = {}
        for extractor in extractors:
            for media_type in extractor.supported_media_types:
                if media_type in self._extractors:
                    raise ValueError(f"Duplicate extractor for {media_type}")
                self._extractors[media_type] = extractor

    async def extract(
        self,
        content: bytes,
        *,
        media_type: str,
        max_characters: int,
    ) -> ExtractedDocument:
        extractor = self._extractors.get(media_type)
        if extractor is None:
            raise UnsupportedDocumentFormatError(
                "No text extractor supports this media type"
            )

        raw = await asyncio.to_thread(extractor.extract, content)
        normalized = self._normalize(raw.text)
        if not normalized:
            raise NoExtractableTextError("Document contains no extractable text")

        source_character_count = len(normalized)
        bounded, was_truncated = self._truncate(normalized, max_characters)
        return ExtractedDocument(
            text=bounded,
            source_character_count=source_character_count,
            was_truncated=was_truncated,
            metadata={"media_type": media_type, **raw.metadata},
        )

    @staticmethod
    def _normalize(text: str) -> str:
        lines: list[str] = []
        previous_was_blank = False

        for raw_line in text.splitlines():
            line = "\t".join(
                " ".join(segment.split()) for segment in raw_line.split("\t")
            )
            if line:
                lines.append(line)
                previous_was_blank = False
            elif lines and not previous_was_blank:
                lines.append("")
                previous_was_blank = True

        return "\n".join(lines).strip()

    @staticmethod
    def _truncate(text: str, max_characters: int) -> tuple[str, bool]:
        if len(text) <= max_characters:
            return text, False

        if max_characters <= len(TRUNCATION_MARKER):
            return text[:max_characters], True

        available = max_characters - len(TRUNCATION_MARKER)
        head_length = available * 3 // 4
        tail_length = available - head_length
        return (
            text[:head_length] + TRUNCATION_MARKER + text[-tail_length:],
            True,
        )
