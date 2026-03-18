import asyncio
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.config import settings
from app.converters.base import BaseConverter
from app.exceptions import ConversionError

PDFA_DEF_PS = """
[{
  /Title (converted)
  /Author (File Converter)
} /DOCINFO pdfmark
[{
  /Type /Catalog
  /MarkInfo << /Marked true >>
  /OutputIntents [
    <<
      /Type /OutputIntent
      /S /GTS_PDFA1
      /DestOutputProfile currentdevice /OutputAttributes get /OutputConditionIdentifier get
      /OutputCondition (sRGB)
      /Info (sRGB IEC61966-2.1)
      /RegistryName (http://www.color.org)
    >>
  ]
} /PUT pdfmark
"""


class PdfToPdfaOptions(BaseModel):
    pdfa_version: Literal["1b", "2b", "3b"] = Field(
        default="2b", description="PDF/A version"
    )


class PdfToPdfaConverter(BaseConverter):
    source_format = "pdf"
    target_format = "pdfa"
    source_mime_types = ["application/pdf"]
    options_model = PdfToPdfaOptions
    engine = "ghostscript"

    async def convert(self, input_path: Path, output_dir: Path, options: BaseModel) -> Path:
        opts: PdfToPdfaOptions = options  # type: ignore[assignment]
        output_path = output_dir / f"{input_path.stem}_pdfa.pdf"

        version_map = {"1b": "1", "2b": "2", "3b": "3"}
        pdfa_level = version_map[opts.pdfa_version]

        # Write PostScript definitions file
        ps_path = output_dir / "PDFA_def.ps"
        ps_path.write_text(PDFA_DEF_PS)

        proc = await asyncio.create_subprocess_exec(
            "gs",
            "-dPDFA=" + pdfa_level,
            "-dBATCH",
            "-dNOPAUSE",
            "-dNOOUTERSAVE",
            "-sColorConversionStrategy=UseDeviceIndependentColor",
            "-sDEVICE=pdfwrite",
            "-dPDFACompatibilityPolicy=1",
            f"-sOutputFile={output_path}",
            str(ps_path),
            str(input_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=settings.GHOSTSCRIPT_TIMEOUT
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise ConversionError("Conversion timed out")

        if proc.returncode != 0:
            raise ConversionError(f"Ghostscript failed: {stderr.decode()}")

        if not output_path.exists():
            raise ConversionError("Ghostscript did not produce output file")
        return output_path
