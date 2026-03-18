from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskInfo:
    """Internal mutable task state (not a Pydantic model — avoids copy overhead)."""

    __slots__ = (
        "task_id",
        "conversion_type",
        "status",
        "created_at",
        "input_path",
        "output_path",
        "output_filename",
        "error",
    )

    def __init__(
        self,
        task_id: str,
        conversion_type: str,
        input_path: Path,
    ):
        self.task_id = task_id
        self.conversion_type = conversion_type
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now(UTC)
        self.input_path = input_path
        self.output_path: Optional[Path] = None
        self.output_filename: Optional[str] = None
        self.error: Optional[str] = None


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    conversion_type: str
    created_at: datetime
    output_filename: Optional[str] = None
    error: Optional[str] = None
