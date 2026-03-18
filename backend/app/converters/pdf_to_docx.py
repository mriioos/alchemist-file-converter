import asyncio
from pathlib import Path

from pydantic import BaseModel

from app.config import settings
from app.converters.base import BaseConverter, NoOptions
from app.exceptions import ConversionError


class PdfToDocxConverter(BaseConverter):
    source_format = "pdf"
    target_format = "docx"
    source_mime_types = ["application/pdf"]
    options_model = NoOptions
    engine = "libreoffice"

    async def convert(self, input_path: Path, output_dir: Path, options: BaseModel) -> Path:
        proc = await asyncio.create_subprocess_exec(
            "libreoffice",
            "--headless",
            "--infilter=impress_pdf_import",
            "--convert-to",
            "docx",
            "--outdir",
            str(output_dir),
            str(input_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=settings.LIBREOFFICE_TIMEOUT
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise ConversionError("Conversion timed out")

        if proc.returncode != 0:
            raise ConversionError(f"LibreOffice failed: {stderr.decode()}")

        output_path = output_dir / f"{input_path.stem}.docx"
        if not output_path.exists():
            raise ConversionError("LibreOffice did not produce output file")
        return output_path
