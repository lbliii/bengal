"""
Standardized template engine errors.

All engines MUST use these error types for consistency.

Example:
    from bengal.rendering.engines.errors import TemplateNotFoundError

    raise TemplateNotFoundError("page.html", template_dirs)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class TemplateError:
    """
    Represents a template validation or render error.

    Returned by validate() method. Also raised during render_template().
    """

    template: str
    message: str
    line: int | None = None
    column: int | None = None
    path: Path | None = None

    def __str__(self) -> str:
        loc = f":{self.line}" if self.line else ""
        return f"{self.template}{loc}: {self.message}"


class TemplateNotFoundError(Exception):
    """
    Raised when a template cannot be found.

    MUST be raised by render_template() when template doesn't exist.
    """

    def __init__(self, name: str, search_paths: list[Path]) -> None:
        self.name = name
        self.search_paths = search_paths
        paths_str = "\n  ".join(str(p) for p in search_paths)
        super().__init__(f"Template not found: '{name}'\nSearched in:\n  {paths_str}")


class TemplateRenderError(Exception):
    """
    Raised when template rendering fails.

    MUST be raised by render_template() for runtime errors.
    """

    def __init__(self, name: str, cause: Exception) -> None:
        self.name = name
        self.cause = cause
        super().__init__(f"Error rendering '{name}': {cause}")
