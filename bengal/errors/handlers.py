"""
Context-aware error handlers to enrich exception displays.

This module provides intelligent help for common Python errors by analyzing
error messages and suggesting fixes. Handlers are best-effort and must never
raise exceptions themselves.

Supported Error Types
=====================

**ImportError**
- ``cannot import name 'X' from 'module'``: Shows available exports and
  suggests close matches using fuzzy matching.
- ``No module named 'X'``: Suggests checking virtualenv and dependencies.

**AttributeError**
- ``module 'X' has no attribute 'Y'``: Shows available module attributes
  and suggests close matches.
- ``'dict' object has no attribute 'X'``: Suggests using ``dict.get()``
  or bracket access instead.

**TypeError**
- Argument/type mismatches: Suggests checking function signatures
  and parameter types.

Usage
=====

Get context-aware help for any exception::

from bengal.errors.handlers import get_context_aware_help

    try:
    from bengal.core import NonExistent
except ImportError as e:
    help_info = get_context_aware_help(e)
    if help_info:
        print(help_info.title)
        for line in help_info.lines:
            print(f"  {line}")

Integration with Traceback Renderers
====================================

The ``ContextAwareHelp`` dataclass is designed for integration with
Bengal's traceback renderers (see ``bengal/errors/traceback/``).
The compact and minimal renderers automatically call these handlers.

See Also
========

- ``bengal/errors/traceback/renderer.py`` - Uses these handlers
- ``bengal/errors/suggestions.py`` - Domain-specific suggestions

"""

from __future__ import annotations

from dataclasses import dataclass

from bengal.errors.utils import extract_between, find_close_matches, safe_list_module_exports
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ContextAwareHelp:
    """
    Container for context-aware error help information.

    Used by traceback renderers to display helpful information
    alongside error messages.

    Attributes:
        title: Short title describing the error type
            (e.g., "ImportError: cannot import name").
        lines: List of help lines to display, including suggestions,
            available options, and hints.

    Example:
            >>> help_info = ContextAwareHelp(
            ...     title="ImportError: cannot import name",
            ...     lines=[
            ...         "Did you mean:",
            ...         "  • Page",
            ...         "  • Site",
            ...         "Available in bengal.core: Page, Site, Section ...",
            ...     ],
            ... )

    """

    title: str
    lines: list[str]


def get_context_aware_help(error: BaseException) -> ContextAwareHelp | None:
    """
    Get context-aware help for an exception.

    Analyzes the error message and type to provide helpful suggestions.
    This function is best-effort and will never raise an exception.

    Args:
        error: Any exception to analyze.

    Returns:
        ContextAwareHelp with title and suggestion lines, or None
        if no specific help is available for this error.

    Example:
            >>> try:
            ...     from bengal.core import NonExistent
            ... except ImportError as e:
            ...     help_info = get_context_aware_help(e)
            ...     if help_info:
            ...         print(help_info.title)

    """
    try:
        if isinstance(error, ImportError):
            return _handle_import_error(error)
        if isinstance(error, AttributeError):
            return _handle_attribute_error(error)
        if isinstance(error, TypeError):
            return _handle_type_error(error)
    except Exception as e:
        logger.debug(
            "error_handler_context_help_failed",
            error_type=type(error).__name__,
            handler_error=str(e),
            handler_error_type=type(e).__name__,
            action="returning_none",
        )
        return None
    return None


def _handle_import_error(error: ImportError) -> ContextAwareHelp | None:
    # Common messages:
    #   cannot import name 'X' from 'pkg.mod' (/path/...)
    #   No module named 'pkg'
    msg = str(error)

    if "cannot import name" in msg and " from " in msg:
        missing = extract_between(msg, "name '", "'") or extract_between(msg, 'name "', '"')
        module = extract_between(msg, " from '", "'") or extract_between(msg, ' from "', '"')
        if module:
            exports = safe_list_module_exports(module)
            suggestions = find_close_matches(missing, exports) if missing else []
            lines: list[str] = []
            if suggestions:
                lines.append("Did you mean:")
                lines.extend([f"  • {s}" for s in suggestions])
            # Show a short sample of available exports to guide users
            if exports:
                preview = ", ".join(sorted(exports)[:8])
                lines.append(f"Available in {module}: {preview}{' …' if len(exports) > 8 else ''}")
            title = "ImportError: cannot import name"
            return ContextAwareHelp(title=title, lines=lines)

    if "No module named" in msg:
        # Suggest installing or checking environment
        missing_mod = extract_between(msg, "No module named '", "'") or extract_between(
            msg, 'No module named "', '"'
        )
        title = "ImportError: module not found"
        lines = [
            f"Missing module: {missing_mod}" if missing_mod else "Missing module",
            "Check virtualenv and dependencies (pip/uv/poetry)",
        ]
        return ContextAwareHelp(title=title, lines=lines)

    return None


def _handle_attribute_error(error: AttributeError) -> ContextAwareHelp | None:
    # Common messages:
    #   module 'json' has no attribute 'Dump'
    #   'dict' object has no attribute 'x'
    msg = str(error)

    # Module attribute case
    if "module '" in msg and "' has no attribute '" in msg:
        module = extract_between(msg, "module '", "'")
        attr = extract_between(msg, "attribute '", "'")
        exports = safe_list_module_exports(module) if module else []
        suggestions = find_close_matches(attr, exports) if attr else []
        lines: list[str] = []
        if suggestions:
            lines.append("Did you mean:")
            lines.extend([f"  • {s}" for s in suggestions])
        if exports:
            preview = ", ".join(sorted(exports)[:8])
            lines.append(f"Available in {module}: {preview}{' …' if len(exports) > 8 else ''}")
        title = "AttributeError: unknown module attribute"
        return ContextAwareHelp(title=title, lines=lines)

    # Dict object attribute case
    if "'dict' object has no attribute" in msg:
        attr = extract_between(msg, "has no attribute '", "'")
        title = "AttributeError: dict attribute access"
        if attr:
            lines = [
                "Use dict.get('<key>') or bracket access instead of attribute access",
                f"Try: mapping.get('{attr}') or mapping.get('{attr}', default)",
            ]
        else:
            lines = [
                "Use dict.get('<key>') or bracket access instead of attribute access",
            ]
        return ContextAwareHelp(title=title, lines=lines)

    return None


def _handle_type_error(error: TypeError) -> ContextAwareHelp | None:
    msg = str(error)
    title = "TypeError: argument/type mismatch"
    lines = [
        "Check function signature and parameter order",
        "Validate types of inputs (e.g., str vs int, list vs dict)",
    ]
    if "positional arguments" in msg or "keyword arguments" in msg:
        lines.append("Verify number of positional/keyword arguments")
    if "expected" in msg and "got" in msg:
        lines.append("Ensure provided value matches expected type")
    return ContextAwareHelp(title=title, lines=lines)



# Note: String utilities (extract_between, find_close_matches, safe_list_module_exports)
# have been moved to bengal.errors.utils for reuse across the errors package.
