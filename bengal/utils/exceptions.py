"""
Base exception hierarchy for Bengal.

All Bengal-specific exceptions should extend from BengalError or one of its
subclasses to provide consistent error context and formatting.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class BengalError(Exception):
    """
    Base exception for all Bengal errors.

    Provides consistent context support including file paths, line numbers,
    suggestions, and original error chaining.

    Example:
        raise BengalError(
            "Invalid configuration",
            file_path=config_path,
            line_number=12,
            suggestion="Check the configuration documentation"
        )
    """

    def __init__(
        self,
        message: str,
        *,
        file_path: Path | str | None = None,
        line_number: int | None = None,
        suggestion: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize Bengal error.

        Args:
            message: Human-readable error message
            file_path: Path to file where error occurred (Path or str)
            line_number: Line number where error occurred
            suggestion: Helpful suggestion for fixing the error
            original_error: Original exception that caused this error (for chaining)
        """
        self.message = message
        self.file_path = Path(file_path) if isinstance(file_path, str) else file_path
        self.line_number = line_number
        self.suggestion = suggestion
        self.original_error = original_error
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with context."""
        parts = [self.message]
        if self.file_path:
            parts.append(f"File: {self.file_path}")
        if self.line_number:
            parts.append(f"Line: {self.line_number}")
        if self.suggestion:
            parts.append(f"Tip: {self.suggestion}")
        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the error
        """
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "file_path": str(self.file_path) if self.file_path else None,
            "line_number": self.line_number,
            "suggestion": self.suggestion,
        }


class BengalConfigError(BengalError):
    """Configuration-related errors."""

    pass


class BengalContentError(BengalError):
    """Content-related errors."""

    pass


class BengalRenderingError(BengalError):
    """Rendering-related errors."""

    pass


class BengalDiscoveryError(BengalError):
    """Content discovery errors."""

    pass


class BengalCacheError(BengalError):
    """Cache-related errors."""

    pass


