"""PDF text-layer extraction."""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.extraction.base import (
    InvalidDocumentError,
    NoExtractableTextError,
    RawExtraction,
)


class PdfTextExtractor:
    """Extract machine-readable text from PDF pages."""

    supported_media_types = frozenset({"application/pdf"})

    def extract(self, content: bytes) -> RawExtraction:
        try:
            reader = PdfReader(BytesIO(content), strict=False)
            if reader.is_encrypted:
                raise InvalidDocumentError("Encrypted PDFs are not supported")

            page_text = [page.extract_text() or "" for page in reader.pages]
        except PdfReadError as exc:
            raise InvalidDocumentError("PDF content could not be parsed") from exc

        pages_with_text = sum(bool(text.strip()) for text in page_text)
        if pages_with_text == 0:
            raise NoExtractableTextError("PDF contains no extractable text")

        return RawExtraction(
            text="\n\n".join(page_text),
            metadata={
                "page_count": len(reader.pages),
                "pages_with_text": pages_with_text,
            },
        )
