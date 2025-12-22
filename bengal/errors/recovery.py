"""
Error recovery utilities for standardized error handling patterns.

This module provides utilities for executing operations with graceful
error recovery, allowing builds to continue when possible while collecting
errors for reporting.

Key Functions
=============

**with_error_recovery()**
    Execute an operation with optional recovery callback. In strict mode,
    re-raises immediately; in production mode, attempts recovery.

**error_recovery_context()**
    Context manager that suppresses exceptions in production mode.
    Useful for try/except patterns across multiple operations.

**recover_file_processing()**
    Specialized recovery for file processing loops. Logs errors,
    collects them in BuildStats, and continues processing.

Design Philosophy
=================

Bengal uses two modes for error handling:

- **Strict Mode** (``--strict`` flag): Fail fast on any error.
  Useful for CI/CD pipelines where errors should halt the build.

- **Production Mode** (default): Recover from errors when possible.
  Log warnings, skip problematic items, and continue building.
  Report all errors at the end.

Usage
=====

Basic error recovery::

    from bengal.errors import with_error_recovery

    result = with_error_recovery(
        lambda: process_file(path),
        on_error=lambda e: None,  # Return None on error
        strict_mode=strict_mode,
        logger=logger,
    )

Context manager for multiple operations::

    from bengal.errors import error_recovery_context

    with error_recovery_context("processing files", strict_mode=False, logger=logger):
        for file in files:
            process_file(file)  # Errors logged but don't stop loop

File processing with BuildStats::

    from bengal.errors import recover_file_processing

    for file_path in files:
        result = recover_file_processing(
            file_path,
            lambda: process_file(file_path),
            strict_mode=strict_mode,
            logger=logger,
            build_stats=stats,
        )

See Also
========

- ``bengal/orchestration/render.py`` - Recovery in page rendering
- ``bengal/orchestration/asset.py`` - Recovery in asset processing
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from bengal.utils.logger import Logger

T = TypeVar("T")


def with_error_recovery(
    operation: Callable[[], T],
    *,
    on_error: Callable[[Exception], T] | None = None,
    error_types: tuple[type[Exception], ...] = (Exception,),
    strict_mode: bool = False,
    logger: Logger | None = None,
) -> T:
    """
    Execute operation with error recovery.

    In strict mode, re-raises exceptions immediately. In production mode,
    attempts recovery via on_error callback or continues with warning.

    Args:
        operation: Function to execute
        on_error: Recovery function (returns fallback value)
        error_types: Exception types to catch
        strict_mode: If True, re-raise instead of recovering
        logger: Logger instance for warnings

    Returns:
        Result of operation or recovery function

    Raises:
        Exception: If strict_mode=True or no recovery function provided

    Example:
        >>> from bengal.errors import with_error_recovery
        >>>
        >>> def process_file(path):
        ...     # File processing logic
        ...     pass
        >>>
        >>> result = with_error_recovery(
        ...     lambda: process_file(path),
        ...     on_error=lambda e: logger.warning(f"Skipped {path}: {e}"),
        ...     strict_mode=strict_mode,
        ...     logger=logger,
        ... )
    """
    try:
        return operation()
    except error_types as e:
        if strict_mode:
            raise

        if logger:
            operation_name = getattr(operation, "__name__", "operation")
            logger.warning(
                "error_recovery",
                operation=operation_name,
                error=str(e),
                error_type=type(e).__name__,
                action="recovering",
            )

        if on_error:
            return on_error(e)

        # No recovery function, re-raise
        raise


@contextmanager
def error_recovery_context(
    operation_name: str,
    *,
    strict_mode: bool = False,
    logger: Logger | None = None,
):
    """
    Context manager for error recovery.

    Suppresses exceptions in production mode, allowing execution to continue.
    In strict mode, exceptions are re-raised immediately.

    Args:
        operation_name: Name of operation for logging
        strict_mode: If True, re-raise instead of suppressing
        logger: Logger instance for warnings

    Example:
        >>> from bengal.errors import error_recovery_context
        >>>
        >>> with error_recovery_context("processing files", strict_mode=strict_mode, logger=logger):
        ...     for file in files:
        ...         process_file(file)  # Errors logged but don't stop loop
    """
    try:
        yield
    except Exception as e:
        if strict_mode:
            raise

        if logger:
            logger.warning(
                "error_recovery_context",
                operation=operation_name,
                error=str(e),
                error_type=type(e).__name__,
                action="continuing",
            )

        # Continue execution (don't re-raise)


def recover_file_processing[T](
    file_path: Any,
    operation: Callable[[], T],
    *,
    strict_mode: bool = False,
    logger: Logger | None = None,
    build_stats: Any | None = None,
) -> T | None:
    """
    Execute file processing operation with recovery.

    Convenience function for file processing loops that need to continue
    on errors while collecting them for reporting.

    Args:
        file_path: Path to file being processed (for error context)
        operation: Function to execute
        strict_mode: If True, re-raise instead of recovering
        logger: Logger instance for warnings
        build_stats: BuildStats instance for error collection (optional)

    Returns:
        Result of operation or None if error occurred and recovered

    Example:
        >>> from bengal.errors import recover_file_processing
        >>>
        >>> for file_path in files:
        ...     result = recover_file_processing(
        ...         file_path,
        ...         lambda: process_file(file_path),
        ...         strict_mode=strict_mode,
        ...         logger=logger,
        ...         build_stats=stats,
        ...     )
        ...     if result:
        ...         processed.append(result)
    """
    try:
        return operation()
    except Exception as e:
        if strict_mode:
            raise

        if logger:
            logger.warning(
                "file_processing_error",
                file_path=str(file_path),
                error=str(e),
                error_type=type(e).__name__,
                action="skipping_file",
            )

        # Collect error in build stats if available
        if build_stats:
            from bengal.errors.context import ErrorContext, enrich_error
            from bengal.errors.exceptions import BengalDiscoveryError

            context = ErrorContext(
                file_path=file_path if hasattr(file_path, "__fspath__") else None,
                operation="processing file",
                suggestion="Check file encoding, format, and permissions",
                original_error=e,
            )
            # Enrich error for better context
            enrich_error(e, context, BengalDiscoveryError)
            if hasattr(build_stats, "add_warning"):
                build_stats.add_warning(
                    str(file_path),
                    f"Error processing file: {e}",
                    warning_type="processing",
                )

        return None
