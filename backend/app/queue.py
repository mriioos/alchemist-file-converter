import asyncio
import logging
import shutil
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.config import settings
from app.converters.base import BaseConverter
from app.exceptions import TaskExpiredError, TaskNotFoundError, TaskNotReadyError
from app.models import TaskInfo, TaskResponse, TaskStatus

logger = logging.getLogger(__name__)


class TaskQueue:
    def __init__(self) -> None:
        self._tasks: dict[str, TaskInfo] = {}
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._cleanup_task: asyncio.Task | None = None

    def init_semaphores(self, engines: set[str]) -> None:
        for engine in engines:
            limit = settings.ENGINE_CONCURRENCY.get(engine, 1)
            self._semaphores[engine] = asyncio.Semaphore(limit)
            logger.info("Semaphore for engine %s: concurrency=%d", engine, limit)

    async def start_cleanup_loop(self) -> None:
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def submit(
        self,
        converter: BaseConverter,
        input_path: Path,
        options: object,
    ) -> TaskInfo:
        task_id = uuid.uuid4().hex
        task = TaskInfo(
            task_id=task_id,
            conversion_type=converter.conversion_type,
            input_path=input_path,
        )
        self._tasks[task_id] = task
        asyncio.create_task(self._process(task, converter, options))
        return task

    def get_task(self, task_id: str) -> TaskInfo:
        task = self._tasks.get(task_id)
        if task is None:
            raise TaskNotFoundError()
        return task

    def get_task_response(self, task_id: str) -> TaskResponse:
        task = self.get_task(task_id)
        return TaskResponse(
            task_id=task.task_id,
            status=task.status,
            conversion_type=task.conversion_type,
            created_at=task.created_at,
            output_filename=task.output_filename,
            error=task.error,
        )

    def validate_download(self, task_id: str) -> TaskInfo:
        task = self.get_task(task_id)
        if task.status in (TaskStatus.PENDING, TaskStatus.PROCESSING):
            raise TaskNotReadyError()
        if task.status == TaskStatus.FAILED:
            raise TaskNotReadyError()
        if task.output_path is None or not task.output_path.exists():
            raise TaskExpiredError()
        return task

    async def _process(
        self,
        task: TaskInfo,
        converter: BaseConverter,
        options: object,
    ) -> None:
        engine = converter.engine
        sem = self._semaphores.get(engine)
        if sem is None:
            sem = asyncio.Semaphore(1)
            self._semaphores[engine] = sem

        async with sem:
            task.status = TaskStatus.PROCESSING
            output_dir = task.input_path.parent
            try:
                result = await converter.convert(task.input_path, output_dir, options)
                task.output_path = result
                task.output_filename = result.name
                task.status = TaskStatus.COMPLETED
                logger.info("Task %s completed: %s", task.task_id, result.name)
            except Exception as exc:
                task.status = TaskStatus.FAILED
                task.error = str(exc)
                logger.error("Task %s failed: %s", task.task_id, exc)

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(settings.CLEANUP_INTERVAL_SECONDS)
            cutoff = datetime.now(UTC) - timedelta(seconds=settings.TASK_TTL_SECONDS)
            expired = [
                tid
                for tid, t in self._tasks.items()
                if t.created_at < cutoff
            ]
            for tid in expired:
                task = self._tasks.pop(tid, None)
                if task and task.input_path:
                    task_dir = task.input_path.parent
                    if task_dir.exists():
                        shutil.rmtree(task_dir, ignore_errors=True)
                logger.debug("Cleaned up task %s", tid)


task_queue = TaskQueue()
