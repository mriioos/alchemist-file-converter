import asyncio
from pathlib import Path

import pytest
import pytest_asyncio

from app.exceptions import TaskExpiredError, TaskNotFoundError, TaskNotReadyError
from app.models import TaskStatus
from app.queue import TaskQueue
from tests.conftest import FailingConverter, MockConverter


@pytest.mark.asyncio
async def test_submit_and_complete(queue: TaskQueue, tmp_path: Path):
    converter = MockConverter()
    input_file = tmp_path / "test.mock"
    input_file.write_text("hello")

    task = await queue.submit(converter, input_file, None)
    assert task.status in (TaskStatus.PENDING, TaskStatus.PROCESSING, TaskStatus.COMPLETED)

    # Wait for completion
    for _ in range(50):
        if task.status == TaskStatus.COMPLETED:
            break
        await asyncio.sleep(0.05)

    assert task.status == TaskStatus.COMPLETED
    assert task.output_filename == "test.out"
    assert task.output_path.exists()


@pytest.mark.asyncio
async def test_failing_task(queue: TaskQueue, tmp_path: Path):
    converter = FailingConverter()
    input_file = tmp_path / "test.fail"
    input_file.write_text("hello")

    task = await queue.submit(converter, input_file, None)

    for _ in range(50):
        if task.status == TaskStatus.FAILED:
            break
        await asyncio.sleep(0.05)

    assert task.status == TaskStatus.FAILED
    assert "Intentional failure" in task.error


@pytest.mark.asyncio
async def test_get_task_not_found(queue: TaskQueue):
    with pytest.raises(TaskNotFoundError):
        queue.get_task("nonexistent")


@pytest.mark.asyncio
async def test_validate_download_not_ready(queue: TaskQueue, tmp_path: Path):
    converter = MockConverter()
    # Create a converter that takes time
    input_file = tmp_path / "test.mock"
    input_file.write_text("hello")

    task = await queue.submit(converter, input_file, None)

    # Wait for completion first
    for _ in range(50):
        if task.status == TaskStatus.COMPLETED:
            break
        await asyncio.sleep(0.05)

    # Now it should be downloadable
    result = queue.validate_download(task.task_id)
    assert result.output_path.exists()


@pytest.mark.asyncio
async def test_validate_download_expired(queue: TaskQueue, tmp_path: Path):
    converter = MockConverter()
    input_file = tmp_path / "test.mock"
    input_file.write_text("hello")

    task = await queue.submit(converter, input_file, None)

    for _ in range(50):
        if task.status == TaskStatus.COMPLETED:
            break
        await asyncio.sleep(0.05)

    # Delete the output to simulate expiration
    task.output_path.unlink()
    with pytest.raises(TaskExpiredError):
        queue.validate_download(task.task_id)
