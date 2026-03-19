import importlib
import logging
import pkgutil
from typing import Optional

from app.converters.base import BaseConverter

logger = logging.getLogger(__name__)


class ConverterRegistry:
    def __init__(self) -> None:
        self._converters: dict[str, BaseConverter] = {}

    def register(self, converter: BaseConverter) -> None:
        key = converter.conversion_type
        if key in self._converters:
            logger.warning("Duplicate converter for %s — skipping", key)
            return
        self._converters[key] = converter
        logger.info("Registered converter: %s (engine=%s)", key, converter.engine)

    def get(self, conversion_type: str) -> Optional[BaseConverter]:
        return self._converters.get(conversion_type)

    def all(self) -> dict[str, BaseConverter]:
        return dict(self._converters)

    def discover(self) -> None:
        """Auto-discover all BaseConverter subclasses in app.converters."""
        import app.converters as converters_pkg

        for importer, modname, ispkg in pkgutil.iter_modules(converters_pkg.__path__):
            if modname == "base":
                continue
            module = importlib.import_module(f"app.converters.{modname}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseConverter)
                    and attr is not BaseConverter
                ):
                    self.register(attr())


registry = ConverterRegistry()
