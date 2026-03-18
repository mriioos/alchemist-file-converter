"""Integration tests for Pillow-based converters (JPG→PDF, PNG→PDF).

No system dependencies required — Pillow is a Python package.
"""
import pytest

from tests.integration.conftest import upload_and_download


@pytest.mark.asyncio
async def test_jpg_to_pdf(integration_client):
    data = await upload_and_download(
        integration_client, "jpg-to-pdf", "sample.jpg", "image/jpeg"
    )
    assert data[:5] == b"%PDF-", "Output should be a valid PDF"


@pytest.mark.asyncio
async def test_png_to_pdf(integration_client):
    data = await upload_and_download(
        integration_client, "png-to-pdf", "sample.png", "image/png"
    )
    assert data[:5] == b"%PDF-", "Output should be a valid PDF"
