"""Integration tests for Ghostscript-based converters (PDF→PDF/A).

Skipped when Ghostscript (gs) is not on PATH.
"""
import pytest

from tests.integration.conftest import skip_no_ghostscript, upload_and_download

pytestmark = skip_no_ghostscript


@pytest.mark.asyncio
async def test_pdf_to_pdfa_default(integration_client):
    data = await upload_and_download(
        integration_client, "pdf-to-pdfa", "sample.pdf", "application/pdf"
    )
    assert data[:5] == b"%PDF-", "Output should be a valid PDF"


@pytest.mark.asyncio
async def test_pdf_to_pdfa_version_1b(integration_client):
    data = await upload_and_download(
        integration_client,
        "pdf-to-pdfa",
        "sample.pdf",
        "application/pdf",
        params={"pdfa_version": "1b"},
    )
    assert data[:5] == b"%PDF-", "Output should be a valid PDF"


@pytest.mark.asyncio
async def test_pdf_to_pdfa_version_3b(integration_client):
    data = await upload_and_download(
        integration_client,
        "pdf-to-pdfa",
        "sample.pdf",
        "application/pdf",
        params={"pdfa_version": "3b"},
    )
    assert data[:5] == b"%PDF-", "Output should be a valid PDF"
