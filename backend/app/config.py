from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "FC_"}

    WORK_DIR: Path = Path("/tmp/conversions")
    TASK_TTL_SECONDS: int = 900  # 15 minutes
    MAX_UPLOAD_BYTES: int = 100 * 1024 * 1024  # 100 MB
    CLEANUP_INTERVAL_SECONDS: int = 60

    ENGINE_CONCURRENCY: dict[str, int] = {
        "libreoffice": 1,
        "pillow": 4,
        "poppler": 4,
        "ghostscript": 2,
    }

    LIBREOFFICE_TIMEOUT: int = 120
    GHOSTSCRIPT_TIMEOUT: int = 120

    # When the backend runs behind a reverse proxy at a path prefix (e.g. /api),
    # set this so FastAPI generates correct URLs in OpenAPI / Swagger docs.
    # Leave empty for direct access (dev, standalone).
    ROOT_PATH: str = ""


settings = Settings()
