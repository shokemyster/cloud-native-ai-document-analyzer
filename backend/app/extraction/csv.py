"""CSV text extraction using the Python standard library."""

import csv
from io import StringIO

from app.extraction.base import (
    InvalidDocumentError,
    NoExtractableTextError,
    RawExtraction,
)


class CsvTextExtractor:
    """Normalize UTF-8 CSV rows into analyzer-friendly text."""

    supported_media_types = frozenset(
        {
            "application/csv",
            "application/vnd.ms-excel",
            "text/csv",
        }
    )

    def extract(self, content: bytes) -> RawExtraction:
        try:
            decoded = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise InvalidDocumentError("CSV must use UTF-8 encoding") from exc

        rows: list[str] = []
        max_column_count = 0

        try:
            reader = csv.reader(StringIO(decoded, newline=""))
            for row in reader:
                normalized_cells = [" ".join(cell.split()) for cell in row]
                max_column_count = max(max_column_count, len(normalized_cells))
                rows.append("\t".join(normalized_cells))
        except csv.Error as exc:
            raise InvalidDocumentError("CSV content could not be parsed") from exc

        text = "\n".join(rows)
        if not text.strip():
            raise NoExtractableTextError("CSV contains no extractable text")

        return RawExtraction(
            text=text,
            metadata={
                "row_count": len(rows),
                "max_column_count": max_column_count,
            },
        )
