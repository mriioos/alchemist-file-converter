import asyncio
import shutil
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.queue import task_queue
from app.registry import ConverterRegistry, registry
from app.routes.convert import register_routes

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _has_binary(name: str) -> bool:
    return shutil.which(name) is not None


has_libreoffice = _has_binary("libreoffice") or _has_binary("soffice")
has_poppler = _has_binary("pdftoppm")
has_ghostscript = _has_binary("gs") or _has_binary("gswin64c") or _has_binary("gswin32c")

skip_no_libreoffice = pytest.mark.skipif(
    not has_libreoffice, reason="LibreOffice not found on PATH"
)
skip_no_poppler = pytest.mark.skipif(
    not has_poppler, reason="Poppler (pdftoppm) not found on PATH"
)
skip_no_ghostscript = pytest.mark.skipif(
    not has_ghostscript, reason="Ghostscript not found on PATH"
)


@pytest_asyncio.fixture
async def integration_client(tmp_path):
    """Full app client with real converters discovered from the registry."""
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    from app.exceptions import (
        FileTooLargeError,
        TaskExpiredError,
        TaskNotFoundError,
        TaskNotReadyError,
        UnsupportedMimeTypeError,
    )
    from app.routes.tasks import router as tasks_router

    original_work_dir = settings.WORK_DIR
    settings.WORK_DIR = tmp_path

    test_app = FastAPI()

    @test_app.exception_handler(UnsupportedMimeTypeError)
    async def _(request: Request, exc: UnsupportedMimeTypeError):
        return JSONResponse(status_code=415, content={"detail": str(exc)})

    @test_app.exception_handler(FileTooLargeError)
    async def _(request: Request, exc: FileTooLargeError):
        return JSONResponse(status_code=413, content={"detail": "File too large"})

    @test_app.exception_handler(TaskNotFoundError)
    async def _(request: Request, exc: TaskNotFoundError):
        return JSONResponse(status_code=404, content={"detail": "Task not found"})

    @test_app.exception_handler(TaskNotReadyError)
    async def _(request: Request, exc: TaskNotReadyError):
        return JSONResponse(status_code=409, content={"detail": "Task still processing"})

    @test_app.exception_handler(TaskExpiredError)
    async def _(request: Request, exc: TaskExpiredError):
        return JSONResponse(status_code=410, content={"detail": "File expired"})

    test_app.include_router(tasks_router)

    # Discover real converters
    registry._converters.clear()
    registry.discover()

    engines = {c.engine for c in registry.all().values()}
    task_queue._tasks.clear()
    task_queue.init_semaphores(engines)

    register_routes(test_app)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    settings.WORK_DIR = original_work_dir


async def upload_and_download(
    client: AsyncClient,
    conversion_type: str,
    fixture_name: str,
    mime_type: str,
    params: dict | None = None,
    timeout_seconds: float = 30.0,
) -> bytes:
    """Upload a fixture, poll until complete, download and return the bytes."""
    fixture_path = FIXTURES / fixture_name
    assert fixture_path.exists(), f"Fixture missing: {fixture_path}"

    content = fixture_path.read_bytes()
    resp = await client.post(
        f"/convert/{conversion_type}",
        files={"file": (fixture_name, content, mime_type)},
        params=params or {},
    )
    assert resp.status_code == 200, f"Upload failed ({resp.status_code}): {resp.text}"
    task_id = resp.json()["task_id"]

    # Poll for completion
    elapsed = 0.0
    interval = 0.2
    while elapsed < timeout_seconds:
        resp = await client.get(f"/tasks/{task_id}")
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] == "completed":
            break
        if data["status"] == "failed":
            raise AssertionError(f"Conversion failed: {data.get('error')}")
        await asyncio.sleep(interval)
        elapsed += interval
    else:
        raise AssertionError(f"Conversion timed out after {timeout_seconds}s")

    # Download
    resp = await client.get(f"/tasks/{task_id}/download")
    assert resp.status_code == 200, f"Download failed ({resp.status_code}): {resp.text}"
    assert len(resp.content) > 0, "Downloaded file is empty"
    return resp.content
