import mimetypes
import uuid
from pathlib import Path
from typing import Callable

from fastapi import Depends, FastAPI, UploadFile
from fastapi.responses import JSONResponse

from app.config import settings
from app.converters.base import BaseConverter, NoOptions
from app.exceptions import FileTooLargeError, UnsupportedMimeTypeError
from app.models import TaskResponse
from app.queue import task_queue
from app.registry import registry


def _make_endpoint(converter: BaseConverter) -> Callable:
    """Build a POST endpoint closure for a specific converter."""
    options_model = converter.options_model

    if options_model is NoOptions:
        async def endpoint(file: UploadFile) -> TaskResponse:
            return await _handle_upload(converter, file, NoOptions())
    else:
        async def endpoint(file: UploadFile, options: options_model = Depends()) -> TaskResponse:  # type: ignore[valid-type]
            return await _handle_upload(converter, file, options)

    return endpoint


async def _handle_upload(
    converter: BaseConverter,
    file: UploadFile,
    options: object,
) -> TaskResponse:
    # Validate MIME type
    mime = file.content_type or mimetypes.guess_type(file.filename or "")[0] or ""
    if mime not in converter.source_mime_types:
        raise UnsupportedMimeTypeError(converter.source_mime_types, mime)

    # Read file and check size
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise FileTooLargeError()

    # Save to work directory
    task_dir = settings.WORK_DIR / uuid.uuid4().hex
    task_dir.mkdir(parents=True, exist_ok=True)
    input_path = task_dir / (file.filename or f"input.{converter.source_format}")
    input_path.write_bytes(content)

    # Submit to queue
    task = await task_queue.submit(converter, input_path, options)
    return task_queue.get_task_response(task.task_id)


def register_routes(app: FastAPI) -> None:
    """Generate a POST route for every registered converter."""
    for conv_type, converter in registry.all().items():
        endpoint = _make_endpoint(converter)
        app.add_api_route(
            f"/convert/{conv_type}",
            endpoint,
            methods=["POST"],
            response_model=TaskResponse,
            summary=f"Convert {converter.source_format.upper()} to {converter.target_format.upper()}",
            tags=["convert"],
        )
