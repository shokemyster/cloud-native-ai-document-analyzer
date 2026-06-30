"""Tests for replaceable PDF and CSV text extraction."""

from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)

from app.extraction.base import NoExtractableTextError
from app.extraction.csv import CsvTextExtractor
from app.extraction.pdf import PdfTextExtractor
from app.extraction.service import CompositeDocumentTextExtractor


def build_text_pdf(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    content = DecodedStreamObject()
    content.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode())
    page[NameObject("/Resources")] = resources
    page[NameObject("/Contents")] = writer._add_object(content)

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.mark.asyncio
async def test_csv_extraction_handles_utf8_bom_and_metadata() -> None:
    extractor = CompositeDocumentTextExtractor([CsvTextExtractor()])

    result = await extractor.extract(
        "\ufeffname,value\nalpha,42\n".encode(),
        media_type="text/csv",
        max_characters=1000,
    )

    assert result.text == "name\tvalue\nalpha\t42"
    assert result.metadata["row_count"] == 2
    assert result.was_truncated is False


@pytest.mark.asyncio
async def test_extraction_records_deterministic_truncation() -> None:
    extractor = CompositeDocumentTextExtractor([CsvTextExtractor()])

    result = await extractor.extract(
        b"column\n" + b"value\n" * 20,
        media_type="text/csv",
        max_characters=60,
    )

    assert len(result.text) == 60
    assert "document text truncated" in result.text
    assert result.was_truncated is True
    assert result.source_character_count > len(result.text)


@pytest.mark.asyncio
async def test_pdf_extraction_reads_text_layer() -> None:
    extractor = CompositeDocumentTextExtractor([PdfTextExtractor()])

    result = await extractor.extract(
        build_text_pdf("Quarterly summary"),
        media_type="application/pdf",
        max_characters=1000,
    )

    assert result.text == "Quarterly summary"
    assert result.metadata["page_count"] == 1


def test_pdf_extraction_rejects_page_without_text() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    output = BytesIO()
    writer.write(output)

    with pytest.raises(NoExtractableTextError):
        PdfTextExtractor().extract(output.getvalue())
