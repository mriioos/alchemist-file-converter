import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup
    settings.WORK_DIR.mkdir(parents=True, exist_ok=True)
    registry.discover()
    engines = {c.engine for c in registry.all().values()}
    task_queue.init_semaphores(engines)
    register_routes(app)
    await task_queue.start_cleanup_loop()
    logger.info(
        "Started with %d converters: %s",
        len(registry.all()),
        ", ".join(sorted(registry.all().keys())),
    )
    yield
    # Shutdown
    await task_queue.stop()


app = FastAPI(title="Alchemist File Converter API", root_path=settings.ROOT_PATH, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(UnsupportedMimeTypeError)
async def mime_error_handler(request: Request, exc: UnsupportedMimeTypeError) -> JSONResponse:
    return JSONResponse(
        status_code=415,
        content={"detail": f"Expected {', '.join(exc.expected)}, got {exc.got}"},
    )


@app.exception_handler(FileTooLargeError)
async def size_error_handler(request: Request, exc: FileTooLargeError) -> JSONResponse:
    return JSONResponse(
        status_code=413,
        content={"detail": f"File exceeds {settings.MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit"},
    )


@app.exception_handler(TaskNotFoundError)
async def not_found_handler(request: Request, exc: TaskNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Task not found"})


@app.exception_handler(TaskNotReadyError)
async def not_ready_handler(request: Request, exc: TaskNotReadyError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": "Task still processing"})


@app.exception_handler(TaskExpiredError)
async def expired_handler(request: Request, exc: TaskExpiredError) -> JSONResponse:
    return JSONResponse(
        status_code=410,
        content={"detail": "File expired. Re-upload to convert again."},
    )


# Routes
app.include_router(tasks_router)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok"}


@app.get("/converters", tags=["system"])
async def list_converters() -> list[dict]:
    result = []
    for conv_type, converter in sorted(registry.all().items()):
        info: dict = {
            "conversion_type": conv_type,
            "source_format": converter.source_format,
            "target_format": converter.target_format,
            "source_mime_types": converter.source_mime_types,
            "engine": converter.engine,
        }
        schema = converter.options_model.model_json_schema()
        if schema.get("properties"):
            info["options"] = schema
        result.append(info)
    return result
