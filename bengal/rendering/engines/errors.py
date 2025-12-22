"""
Standardized exception types for template engines.

This module defines the error hierarchy for template-related failures. All
engines MUST use these types for consistent error handling and reporting.

Exception Hierarchy:
    BengalRenderingError (base)
    ├── TemplateNotFoundError  - Template file doesn't exist
    └── TemplateRenderError    - Rendering failed (see bengal.rendering.errors)

    TemplateError (dataclass)  - Validation result, not an exception

Usage:
    >>> from bengal.rendering.engines.errors import TemplateNotFoundError
    >>>
    >>> # Raise when template lookup fails
    >>> if not template_path.exists():
    ...     raise TemplateNotFoundError("page.html", search_paths)

    >>> # Return TemplateError from validate()
    >>> errors = [TemplateError("bad.html", "syntax error", line=5)]

Error Handling Guidelines:
    - render_template() MUST raise TemplateNotFoundError if template missing
    - render_template() MUST raise TemplateRenderError if rendering fails
    - validate() MUST NOT raise; return list of TemplateError instead
    - template_exists() MUST NOT raise; return False instead

Related Modules:
    - bengal.rendering.errors: TemplateRenderError with rich context
    - bengal.errors: Base BengalRenderingError class
    - bengal.rendering.engines.protocol: Protocol defining error contracts
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bengal.errors import BengalRenderingError


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
    original_exception: Exception | None = None  # Original exception for type checking

    def __str__(self) -> str:
        loc = f":{self.line}" if self.line else ""
        return f"{self.template}{loc}: {self.message}"


class TemplateNotFoundError(BengalRenderingError):
    """
    Raised when a template cannot be found.

    MUST be raised by render_template() when template doesn't exist.

    Extends BengalRenderingError for consistent error handling.
    """

    def __init__(
        self,
        name: str,
        search_paths: list[Path],
        *,
        suggestion: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        self.name = name
        self.search_paths = search_paths
        paths_str = "\n  ".join(str(p) for p in search_paths)
        message = f"Template not found: '{name}'\nSearched in:\n  {paths_str}"

        # Generate suggestion if not provided
        if suggestion is None:
            suggestion = "Check template name and search paths. Ensure template exists in one of the search directories."

        super().__init__(
            message=message,
            suggestion=suggestion,
            original_error=original_error,
        )


# TemplateRenderError moved to bengal.rendering.errors
# Import from there instead:
#   from bengal.rendering.errors import TemplateRenderError
