import asyncio
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.converters.base import BaseConverter, NoOptions
from app.models import TaskStatus
from app.queue import TaskQueue


class MockConverter(BaseConverter):
    source_format = "mock"
    target_format = "out"
    source_mime_types = ["application/octet-stream"]
    options_model = NoOptions
    engine = "mock"

    async def convert(self, input_path: Path, output_dir: Path, options) -> Path:
        output_path = output_dir / f"{input_path.stem}.out"
        output_path.write_text("converted")
        return output_path


class FailingConverter(BaseConverter):
    source_format = "fail"
    target_format = "out"
    source_mime_types = ["application/octet-stream"]
    options_model = NoOptions
    engine = "mock"

    async def convert(self, input_path: Path, output_dir: Path, options) -> Path:
        raise RuntimeError("Intentional failure")


@pytest.fixture
def mock_converter():
    return MockConverter()


@pytest.fixture
def failing_converter():
    return FailingConverter()


@pytest.fixture
def tmp_work_dir(tmp_path):
    original = settings.WORK_DIR
    settings.WORK_DIR = tmp_path
    yield tmp_path
    settings.WORK_DIR = original


@pytest_asyncio.fixture
async def queue():
    q = TaskQueue()
    q.init_semaphores({"mock"})
    yield q
    await q.stop()


@pytest_asyncio.fixture
async def app_client(tmp_work_dir):
    """Create a test client with mock converter registered."""
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from fastapi import Request

    from app.exceptions import (
        FileTooLargeError,
        TaskExpiredError,
        TaskNotFoundError,
        TaskNotReadyError,
        UnsupportedMimeTypeError,
    )
    from app.queue import task_queue
    from app.registry import registry
    from app.routes.convert import register_routes
    from app.routes.tasks import router as tasks_router

    # Build a fresh app for testing
    test_app = FastAPI()

    # Register exception handlers
    @test_app.exception_handler(UnsupportedMimeTypeError)
    async def mime_handler(request: Request, exc: UnsupportedMimeTypeError):
        return JSONResponse(status_code=415, content={"detail": f"Expected {', '.join(exc.expected)}, got {exc.got}"})

    @test_app.exception_handler(FileTooLargeError)
    async def size_handler(request: Request, exc: FileTooLargeError):
        return JSONResponse(status_code=413, content={"detail": "File exceeds 50MB limit"})

    @test_app.exception_handler(TaskNotFoundError)
    async def not_found_handler(request: Request, exc: TaskNotFoundError):
        return JSONResponse(status_code=404, content={"detail": "Task not found"})

    @test_app.exception_handler(TaskNotReadyError)
    async def not_ready_handler(request: Request, exc: TaskNotReadyError):
        return JSONResponse(status_code=409, content={"detail": "Task still processing"})

    @test_app.exception_handler(TaskExpiredError)
    async def expired_handler(request: Request, exc: TaskExpiredError):
        return JSONResponse(status_code=410, content={"detail": "File expired. Re-upload to convert again."})

    test_app.include_router(tasks_router)

    # Clear previous state
    registry._converters.clear()

    # Register mock converters
    registry.register(MockConverter())
    registry.register(FailingConverter())

    # Init queue semaphores
    task_queue._tasks.clear()
    task_queue.init_semaphores({"mock"})

    # Generate conversion routes on the test app
    register_routes(test_app)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
