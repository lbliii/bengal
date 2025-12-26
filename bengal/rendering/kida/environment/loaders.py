"""Template loaders for Kida environment.

Provides filesystem and dictionary-based template loaders.
"""

from __future__ import annotations

from pathlib import Path

from bengal.rendering.kida.environment.exceptions import TemplateNotFoundError


class FileSystemLoader:
    """Load templates from the filesystem.

    Example:
        >>> loader = FileSystemLoader("templates")
        >>> source, filename = loader.get_source("index.html")
    """

    __slots__ = ("_paths", "_encoding")

    def __init__(
        self,
        paths: str | Path | list[str | Path],
        encoding: str = "utf-8",
    ):
        if isinstance(paths, (str, Path)):
            paths = [paths]
        self._paths = [Path(p) for p in paths]
        self._encoding = encoding

    def get_source(self, name: str) -> tuple[str, str]:
        """Load template source from filesystem."""
        for base in self._paths:
            path = base / name
            if path.is_file():
                return path.read_text(self._encoding), str(path)

        raise TemplateNotFoundError(
            f"Template '{name}' not found in: {', '.join(str(p) for p in self._paths)}"
        )

    def list_templates(self) -> list[str]:
        """List all templates in search paths."""
        templates = set()
        for base in self._paths:
            if base.is_dir():
                for path in base.rglob("*.html"):
                    templates.add(str(path.relative_to(base)))
                for path in base.rglob("*.xml"):
                    templates.add(str(path.relative_to(base)))
        return sorted(templates)


class DictLoader:
    """Load templates from a dictionary.

    Useful for testing and embedded templates.

    Example:
        >>> loader = DictLoader({"index.html": "Hello, {{ name }}!"})
        >>> source, _ = loader.get_source("index.html")
    """

    __slots__ = ("_mapping",)

    def __init__(self, mapping: dict[str, str]):
        self._mapping = mapping

    def get_source(self, name: str) -> tuple[str, None]:
        if name not in self._mapping:
            raise TemplateNotFoundError(f"Template '{name}' not found")
        return self._mapping[name], None

    def list_templates(self) -> list[str]:
        return sorted(self._mapping.keys())
