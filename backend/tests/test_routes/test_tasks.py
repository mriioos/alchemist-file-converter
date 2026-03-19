import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_unknown_task(app_client: AsyncClient):
    resp = await app_client.get("/tasks/nonexistent-id")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Task not found"


@pytest.mark.asyncio
async def test_download_unknown_task(app_client: AsyncClient):
    resp = await app_client.get("/tasks/nonexistent-id/download")
    assert resp.status_code == 404
