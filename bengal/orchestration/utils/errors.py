"""
Error handling utilities for orchestrators.

Provides common error handling patterns used across orchestration modules,
including shutdown error detection and orchestration-specific error enrichment.

Example:
    >>> try:
    ...     process_item(item)
    ... except Exception as e:
    ...     if is_shutdown_error(e):
    ...         logger.debug("shutdown detected")
    ...         return
    ...     handle_orchestration_error(e, "assets", item)

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.errors import (
    BengalError,
    ErrorCode,
    ErrorContext,
    enrich_error,
    record_error,
)
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)


def is_shutdown_error(e: Exception) -> bool:
    """
    Check if exception is due to interpreter shutdown.

    Python's ThreadPoolExecutor can raise RuntimeError during interpreter
    shutdown. These errors should be handled gracefully (logged at debug
    level and ignored) rather than treated as failures.

    Args:
        e: Exception to check

    Returns:
        True if exception indicates interpreter shutdown

    Example:
        >>> try:
        ...     future.result()
        ... except Exception as e:
        ...     if is_shutdown_error(e):
        ...         return  # Graceful shutdown
        ...     raise
    """
    return "interpreter shutdown" in str(e)


def handle_orchestration_error(
    e: Exception,
    phase: str,
    item: Any = None,
    *,
    file_path: Path | str | None = None,
    operation: str | None = None,
    suggestion: str | None = None,
    error_code: ErrorCode | None = None,
    log_error: bool = True,
    record: bool = True,
) -> BengalError:
    """
    Handle an error during orchestration with consistent enrichment and logging.

    Consolidates the common error handling pattern across orchestrators:
    1. Creates ErrorContext with relevant information
    2. Enriches error with context
    3. Logs error with structured fields
    4. Records error in session for pattern detection

    Args:
        e: Original exception
        phase: Orchestration phase (e.g., "assets", "rendering", "postprocess")
        item: Optional item being processed when error occurred
        file_path: File path related to error (extracted from item if not provided)
        operation: Operation description (defaults to "processing {phase}")
        suggestion: Suggestion for fixing the error
        error_code: ErrorCode for categorization
        log_error: Whether to log the error
        record: Whether to record in error session

    Returns:
        Enriched BengalError

    Example:
        >>> try:
        ...     process_asset(asset)
        ... except Exception as e:
        ...     enriched = handle_orchestration_error(
        ...         e, "assets", asset,
        ...         file_path=asset.source_path,
        ...         suggestion="Check file permissions and encoding",
        ...     )
        ...     stats.add_error(enriched, category="assets")
    """
    # Extract file path from item if not provided
    if file_path is None and item is not None:
        file_path = getattr(item, "source_path", None) or getattr(item, "path", None)

    # Default operation description
    if operation is None:
        operation = f"processing {phase}"

    # Default suggestion based on phase
    if suggestion is None:
        suggestion = _get_default_suggestion(phase)

    # Default error code based on phase
    if error_code is None:
        error_code = _get_default_error_code(phase)

    # Create error context
    context = ErrorContext(
        file_path=file_path,
        operation=operation,
        suggestion=suggestion,
        original_error=e,
    )

    # Enrich error
    enriched = enrich_error(e, context, BengalError)

    # Log error
    if log_error:
        log_fields: dict[str, Any] = {
            "error": str(enriched),
            "error_type": type(e).__name__,
            "error_code": error_code.value if error_code else None,
            "suggestion": suggestion,
        }
        if file_path:
            log_fields["file_path"] = str(file_path)
        if item is not None:
            log_fields["item"] = str(item)

        logger.error(f"{phase}_error", **log_fields)

    # Record in error session
    if record:
        record_path = str(file_path) if file_path else f"{phase}:unknown"
        record_error(enriched, file_path=record_path)

    return enriched


def _get_default_suggestion(phase: str) -> str:
    """Get default error suggestion based on phase."""
    suggestions = {
        "assets": "Check file permissions, encoding, and format",
        "rendering": "Check template syntax and page frontmatter",
        "postprocess": "Check configuration and file permissions",
        "taxonomy": "Check tag template 'tag.html' exists and is valid Jinja2",
        "menu": "Check menu config for missing or misspelled page references",
        "discovery": "Check content directory structure and file formats",
    }
    return suggestions.get(phase, f"Check {phase} configuration and files")


def _get_default_error_code(phase: str) -> ErrorCode:
    """Get default error code based on phase."""
    codes = {
        "assets": ErrorCode.X003,
        "rendering": ErrorCode.R001,
        "postprocess": ErrorCode.B008,
        "taxonomy": ErrorCode.B006,
        "menu": ErrorCode.B004,
        "discovery": ErrorCode.D001,
    }
    return codes.get(phase, ErrorCode.B001)


def create_error_context_for_item(
    item: Any,
    operation: str,
    suggestion: str | None = None,
) -> dict[str, Any]:
    """
    Create error context dictionary for an item.

    Used with ErrorAggregator.add_error() for batch error tracking.

    Args:
        item: Item that caused error
        operation: Operation being performed
        suggestion: Optional suggestion for fixing

    Returns:
        Dictionary suitable for error context
    """
    context: dict[str, Any] = {"operation": operation}

    # Extract path from item
    source_path = getattr(item, "source_path", None) or getattr(item, "path", None)
    if source_path:
        context["file_path"] = str(source_path)
        context["file_name"] = source_path.name if hasattr(source_path, "name") else str(source_path)

    # Add suggestion if provided
    if suggestion:
        context["suggestion"] = suggestion

    # Add item string representation
    context["item"] = str(item)

    return context
