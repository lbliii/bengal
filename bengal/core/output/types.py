"""Output tracking types for build coordination.

This module defines the core types used to track output files written during
a build. The typed output records enable reliable hot reload decisions in
the dev server, eliminating error-prone snapshot diffing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal

# Extensions mapped to output types
_EXTENSION_MAP: dict[str, str] = {
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".js": "js",
    ".mjs": "js",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".svg": "image",
    ".webp": "image",
    ".ico": "image",
    ".woff": "font",
    ".woff2": "font",
    ".ttf": "font",
    ".otf": "font",
    ".eot": "font",
    ".json": "json",
    ".xml": "xml",
    ".webmanifest": "manifest",
}


class OutputType(Enum):
    """Classification of output files.

    Used to determine reload strategy in the dev server:
    - CSS-only changes trigger CSS hot reload (no page refresh)
    - Other changes trigger full page reload
    """

    HTML = "html"
    CSS = "css"
    JS = "js"
    IMAGE = "image"
    FONT = "font"
    ASSET = "asset"
    JSON = "json"
    MANIFEST = "manifest"
    XML = "xml"


@dataclass(frozen=True, slots=True)
class OutputRecord:
    """Immutable record of a written output file.

    Attributes:
        path: Relative path to output file (relative to output directory)
        output_type: Classification of the output file
        phase: Build phase that produced this output (render, asset, postprocess)

    Example:
        >>> record = OutputRecord(Path("posts/hello.html"), OutputType.HTML, "render")
        >>> record.output_type == OutputType.HTML
        True
    """

    path: Path
    output_type: OutputType
    phase: Literal["render", "asset", "postprocess"]

    @classmethod
    def from_path(
        cls,
        path: Path,
        phase: Literal["render", "asset", "postprocess"] = "render",
    ) -> OutputRecord:
        """Create an OutputRecord, auto-detecting output type from extension.

        Args:
            path: Path to the output file (absolute or relative)
            phase: Build phase that produced this output

        Returns:
            OutputRecord with auto-detected output type

        Example:
            >>> OutputRecord.from_path(Path("style.css"), phase="asset")
            OutputRecord(path=PosixPath('style.css'), output_type=<OutputType.CSS: 'css'>, phase='asset')
        """
        suffix = path.suffix.lower()
        type_name = _EXTENSION_MAP.get(suffix, "asset")
        output_type = OutputType(type_name)
        return cls(path=path, output_type=output_type, phase=phase)

    def __str__(self) -> str:
        """Return string representation for debugging."""
        return f"{self.output_type.value}:{self.path}"
