from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel


class NoOptions(BaseModel):
    """Default options model when a converter needs no configuration."""
    pass


class BaseConverter(ABC):
    source_format: ClassVar[str]
    target_format: ClassVar[str]
    source_mime_types: ClassVar[list[str]]
    options_model: ClassVar[type[BaseModel]] = NoOptions
    engine: ClassVar[str]

    @property
    def conversion_type(self) -> str:
        return f"{self.source_format}-to-{self.target_format}"

    @abstractmethod
    async def convert(self, input_path: Path, output_dir: Path, options: BaseModel) -> Path:
        """Convert input file and return the path to the output file."""
        ...
