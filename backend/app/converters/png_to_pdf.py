import asyncio
from pathlib import Path

from PIL import Image
from pydantic import BaseModel

from app.converters.base import BaseConverter, NoOptions


class PngToPdfConverter(BaseConverter):
    source_format = "png"
    target_format = "pdf"
    source_mime_types = ["image/png"]
    options_model = NoOptions
    engine = "pillow"

    async def convert(self, input_path: Path, output_dir: Path, options: BaseModel) -> Path:
        output_path = output_dir / f"{input_path.stem}.pdf"

        def _convert() -> None:
            with Image.open(input_path) as img:
                rgb = img.convert("RGB")
                rgb.save(str(output_path), "PDF")

        await asyncio.to_thread(_convert)
        return output_path
