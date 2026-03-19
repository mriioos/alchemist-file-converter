import asyncio
import zipfile
from pathlib import Path

from pydantic import BaseModel, Field

from app.converters.base import BaseConverter
from app.exceptions import ConversionError


class PdfToJpgOptions(BaseModel):
    dpi: int = Field(default=200, ge=72, le=600, description="DPI for rendering")
    quality: int = Field(default=85, ge=1, le=100, description="JPEG quality")


class PdfToJpgConverter(BaseConverter):
    source_format = "pdf"
    target_format = "jpg"
    source_mime_types = ["application/pdf"]
    options_model = PdfToJpgOptions
    engine = "poppler"

    async def convert(self, input_path: Path, output_dir: Path, options: BaseModel) -> Path:
        opts: PdfToJpgOptions = options  # type: ignore[assignment]

        def _convert() -> Path:
            try:
                from pdf2image import convert_from_path
            except ImportError:
                raise ConversionError("pdf2image is not installed")

            images = convert_from_path(
                str(input_path),
                dpi=opts.dpi,
                fmt="jpeg",
            )

            if not images:
                raise ConversionError("No pages found in PDF")

            if len(images) == 1:
                out = output_dir / f"{input_path.stem}.jpg"
                images[0].save(str(out), "JPEG", quality=opts.quality)
                return out

            # Multi-page: create ZIP
            zip_path = output_dir / f"{input_path.stem}_pages.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for i, img in enumerate(images, 1):
                    page_path = output_dir / f"{input_path.stem}_page_{i}.jpg"
                    img.save(str(page_path), "JPEG", quality=opts.quality)
                    zf.write(page_path, page_path.name)
                    page_path.unlink()
            return zip_path

        return await asyncio.to_thread(_convert)
