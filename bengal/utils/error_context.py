"""
Error context helpers for enriching exceptions with standardized context.

Provides utilities for capturing and propagating error context including
file paths, line numbers, operations, and suggestions.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.utils.exceptions import BengalError


@dataclass
class ErrorContext:
    """
    Standardized error context for enriching exceptions.

    Captures all available context about where and why an error occurred.
    """

    file_path: Path | None = None
    line_number: int | None = None
    column: int | None = None
    operation: str | None = None  # e.g., "parsing frontmatter", "rendering template"
    suggestion: str | None = None
    original_error: Exception | None = None


def enrich_error(
    error: Exception,
    context: ErrorContext,
    error_class: type[BengalError] | None = None,
) -> BengalError:
    """
    Enrich exception with standardized context.

    If error is already a BengalError, adds missing context fields.
    Otherwise, wraps error in a new BengalError instance.

    Args:
        error: Exception to enrich
        context: Error context to add
        error_class: Class to use for wrapping (defaults to BengalError)

    Returns:
        Enriched BengalError instance

    Example:
        >>> from bengal.utils.exceptions import BengalError
        >>> from bengal.utils.error_context import ErrorContext, enrich_error
        >>>
        >>> try:
        ...     parse_file(path)
        ... except Exception as e:
        ...     context = ErrorContext(file_path=path, operation="parsing file")
        ...     enriched = enrich_error(e, context)
        ...     raise enriched
    """
    from bengal.utils.exceptions import BengalError as BaseBengalError

    # Use provided error class or default to BengalError
    if error_class is None:
        error_class = BaseBengalError

    # If already a BengalError, enrich with missing context
    if isinstance(error, BaseBengalError):
        # Add missing context fields (don't overwrite existing)
        if context.file_path and not error.file_path:
            error.file_path = context.file_path
        if context.line_number and not error.line_number:
            error.line_number = context.line_number
        if context.suggestion and not error.suggestion:
            error.suggestion = context.suggestion
        if context.original_error and not error.original_error:
            error.original_error = context.original_error
        return error

    # Create new error with context
    return error_class(
        message=str(error) or type(error).__name__,
        file_path=context.file_path,
        line_number=context.line_number,
        suggestion=context.suggestion,
        original_error=context.original_error or error,
    )


# Note: error_context_manager was removed - use error_recovery_context from
# bengal.utils.error_recovery instead, or manually use enrich_error in try/except blocks


def get_context_from_exception(error: Exception) -> ErrorContext:
    """
    Extract error context from an exception if available.

    Attempts to extract file_path, line_number, and other context
    from various exception types.

    Args:
        error: Exception to extract context from

    Returns:
        ErrorContext with any available information
    """
    context = ErrorContext()

    # Try to extract from BengalError
    if hasattr(error, "file_path"):
        context.file_path = getattr(error, "file_path", None)
    if hasattr(error, "line_number"):
        context.line_number = getattr(error, "line_number", None)
    if hasattr(error, "suggestion"):
        context.suggestion = getattr(error, "suggestion", None)
    if hasattr(error, "original_error"):
        context.original_error = getattr(error, "original_error", None)

    # Try to extract from common exception types
    if hasattr(error, "filename"):
        # FileNotFoundError, OSError, etc.
        filename = getattr(error, "filename", None)
        if filename:
            with contextlib.suppress(TypeError, ValueError):
                context.file_path = Path(filename)

    if hasattr(error, "lineno"):
        # SyntaxError, TemplateSyntaxError, etc.
        context.line_number = getattr(error, "lineno", None)

    return context
