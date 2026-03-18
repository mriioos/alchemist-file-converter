"""Integration tests for LibreOffice-based converters.

Skipped when LibreOffice is not on PATH.
"""
import zipfile
from io import BytesIO

import pytest

from tests.integration.conftest import skip_no_libreoffice, upload_and_download

pytestmark = skip_no_libreoffice


# ── To-PDF conversions ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_docx_to_pdf(integration_client):
    data = await upload_and_download(
        integration_client,
        "docx-to-pdf",
        "sample.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert data[:5] == b"%PDF-", "Output should be a valid PDF"


@pytest.mark.asyncio
async def test_pptx_to_pdf(integration_client):
    data = await upload_and_download(
        integration_client,
        "pptx-to-pdf",
        "sample.pptx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
    assert data[:5] == b"%PDF-", "Output should be a valid PDF"


@pytest.mark.asyncio
async def test_xlsx_to_pdf(integration_client):
    data = await upload_and_download(
        integration_client,
        "xlsx-to-pdf",
        "sample.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert data[:5] == b"%PDF-", "Output should be a valid PDF"


@pytest.mark.asyncio
async def test_html_to_pdf(integration_client):
    data = await upload_and_download(
        integration_client,
        "html-to-pdf",
        "sample.html",
        "text/html",
    )
    assert data[:5] == b"%PDF-", "Output should be a valid PDF"


# ── From-PDF conversions ────────────────────────────────────────────


def _is_valid_ooxml_zip(data: bytes, expected_content_type_fragment: str) -> bool:
    """Check that data is a ZIP with [Content_Types].xml containing the expected type."""
    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            if "[Content_Types].xml" not in zf.namelist():
                return False
            ct = zf.read("[Content_Types].xml").decode("utf-8", errors="replace")
            return expected_content_type_fragment in ct
    except zipfile.BadZipFile:
        return False


@pytest.mark.asyncio
async def test_pdf_to_docx(integration_client):
    data = await upload_and_download(
        integration_client, "pdf-to-docx", "sample.pdf", "application/pdf"
    )
    # DOCX is a ZIP; first bytes should be PK (ZIP magic)
    assert data[:2] == b"PK", "Output should be a ZIP (DOCX)"
    assert _is_valid_ooxml_zip(data, "wordprocessingml"), \
        "DOCX should contain wordprocessingml content type"


@pytest.mark.asyncio
async def test_pdf_to_pptx(integration_client):
    data = await upload_and_download(
        integration_client, "pdf-to-pptx", "sample.pdf", "application/pdf"
    )
    assert data[:2] == b"PK", "Output should be a ZIP (PPTX)"
    assert _is_valid_ooxml_zip(data, "presentationml"), \
        "PPTX should contain presentationml content type"


@pytest.mark.asyncio
async def test_pdf_to_xlsx(integration_client):
    data = await upload_and_download(
        integration_client, "pdf-to-xlsx", "sample.pdf", "application/pdf"
    )
    assert data[:2] == b"PK", "Output should be a ZIP (XLSX)"
    assert _is_valid_ooxml_zip(data, "spreadsheetml"), \
        "XLSX should contain spreadsheetml content type"
