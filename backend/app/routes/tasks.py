from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.models import TaskResponse
from app.queue import task_queue

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    return task_queue.get_task_response(task_id)


@router.get("/{task_id}/download")
async def download_task(task_id: str) -> FileResponse:
    task = task_queue.validate_download(task_id)
    return FileResponse(
        path=str(task.output_path),
        filename=task.output_filename,
        media_type="application/octet-stream",
    )
