"""Integration tests for Poppler-based converters (PDF→JPG).

Skipped when pdftoppm (Poppler) is not on PATH.
"""
import zipfile
from io import BytesIO

import pytest

from tests.integration.conftest import skip_no_poppler, upload_and_download

pytestmark = skip_no_poppler

# JPEG magic bytes: FF D8 FF
JPEG_MAGIC = b"\xff\xd8\xff"


@pytest.mark.asyncio
async def test_pdf_to_jpg_single_page(integration_client):
    data = await upload_and_download(
        integration_client, "pdf-to-jpg", "sample.pdf", "application/pdf"
    )
    # Single-page PDF → single JPG (not a ZIP)
    assert data[:3] == JPEG_MAGIC, "Output should be a valid JPEG"


@pytest.mark.asyncio
async def test_pdf_to_jpg_custom_dpi(integration_client):
    data = await upload_and_download(
        integration_client,
        "pdf-to-jpg",
        "sample.pdf",
        "application/pdf",
        params={"dpi": 72, "quality": 50},
    )
    assert data[:3] == JPEG_MAGIC, "Output should be a valid JPEG"


@pytest.mark.asyncio
async def test_pdf_to_jpg_high_quality(integration_client):
    data = await upload_and_download(
        integration_client,
        "pdf-to-jpg",
        "sample.pdf",
        "application/pdf",
        params={"dpi": 300, "quality": 100},
    )
    assert data[:3] == JPEG_MAGIC, "Output should be a valid JPEG"
