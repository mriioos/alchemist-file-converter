import asyncio

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_mock_converter(app_client: AsyncClient):
    resp = await app_client.post(
        "/convert/mock-to-out",
        files={"file": ("test.mock", b"hello world", "application/octet-stream")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data
    assert data["conversion_type"] == "mock-to-out"
    assert data["status"] in ("pending", "processing", "completed")


@pytest.mark.asyncio
async def test_upload_wrong_mime(app_client: AsyncClient):
    resp = await app_client.post(
        "/convert/mock-to-out",
        files={"file": ("test.mock", b"hello", "text/plain")},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_unknown_conversion_type(app_client: AsyncClient):
    resp = await app_client.post(
        "/convert/nonexistent-to-nothing",
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_full_upload_poll_download(app_client: AsyncClient):
    # Upload
    resp = await app_client.post(
        "/convert/mock-to-out",
        files={"file": ("test.mock", b"hello world", "application/octet-stream")},
    )
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]

    # Poll until complete
    for _ in range(50):
        resp = await app_client.get(f"/tasks/{task_id}")
        assert resp.status_code == 200
        if resp.json()["status"] == "completed":
            break
        await asyncio.sleep(0.05)

    assert resp.json()["status"] == "completed"
    assert resp.json()["output_filename"] == "test.out"

    # Download
    resp = await app_client.get(f"/tasks/{task_id}/download")
    assert resp.status_code == 200
    assert resp.content == b"converted"
