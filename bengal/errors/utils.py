"""
Shared utilities for error handling.

This module provides common utilities used across the error handling package,
reducing code duplication and ensuring consistent behavior for:

- **Signature Generation**: Unique signatures for error pattern grouping
- **Attribute Extraction**: Extract common attributes from exceptions
- **Message Formatting**: Human-readable error message extraction
- **Serialization**: Convert dataclasses and complex types to dicts
- **String Utilities**: Substring extraction, fuzzy matching
- **Singleton Pattern**: Thread-safe singleton management

Usage
=====

Generate error signature for grouping::

    from bengal.errors.utils import generate_error_signature

    signature = generate_error_signature(error, normalize_paths=True)

Extract attributes from any exception::

    from bengal.errors.utils import extract_error_attributes

    attrs = extract_error_attributes(error)
    print(attrs["file_path"], attrs["line_number"])

Use thread-safe singleton::

    from bengal.errors.utils import ThreadSafeSingleton

    _session = ThreadSafeSingleton(lambda: ErrorSession())
    session = _session.get()
    _session.reset()

See Also
========

- ``bengal/errors/aggregation.py`` - Uses signature generation
- ``bengal/errors/session.py`` - Uses signature generation, singleton
- ``bengal/errors/context.py`` - Uses attribute extraction

"""

from __future__ import annotations

import contextlib
import re
from collections.abc import Callable, Iterable
from dataclasses import fields, is_dataclass
from datetime import datetime
from difflib import get_close_matches
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, TypeVar

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


# =============================================================================
# Error Signature Generation
# =============================================================================


def generate_error_signature(
    error: Exception,
    *,
    context: dict[str, Any] | None = None,
    include_code: bool = True,
    normalize_paths: bool = True,
    normalize_lines: bool = True,
    max_message_length: int = 100,
    separator: str = "::",
) -> str:
    """
    Generate a unique signature for error pattern grouping.

    Creates a consistent signature from an error that can be used to group
    similar errors together. The signature includes the error type and a
    normalized version of the message.

    Args:
        error: Exception to generate signature for.
        context: Optional context dict with keys like "template_name", "operation".
        include_code: Whether to include Bengal error code in signature.
        normalize_paths: Replace file paths with ``<file>`` placeholder.
        normalize_lines: Replace line numbers with ``<N>`` placeholder.
        max_message_length: Truncate message to this length.
        separator: Separator between signature parts (default "::").

    Returns:
        Signature string suitable for use as dict key or pattern identifier.

    Example:
        >>> sig = generate_error_signature(error, normalize_paths=True)
        >>> # Returns: "R001::BengalRenderingError::Template not found: <file>"

    """
    parts: list[str] = []

    # Add error code if available and requested
    if include_code and hasattr(error, "code") and error.code:
        parts.append(str(error.code))

    # Add error type
    parts.append(type(error).__name__)

    # Add context info if available (template_name, operation)
    if context:
        if "template_name" in context:
            parts.append(f"template:{context['template_name']}")
        if "operation" in context:
            parts.append(f"op:{context['operation']}")

    # Normalize error message
    message = str(error)

    if normalize_paths:
        # Remove file paths (Unix and Windows style)
        message = re.sub(r"[/\\][^\s:]+\.(md|html|yaml|yml|py|toml|json)", "<file>", message)

    if normalize_lines:
        # Replace line numbers
        message = re.sub(r"line \d+", "line <N>", message)
        message = re.sub(r":\d+(?::\d+)?", ":<N>", message)

    # Truncate long messages
    if len(message) > max_message_length:
        message = message[:max_message_length]

    parts.append(message)

    return separator.join(parts)


# =============================================================================
# Error Attribute Extraction
# =============================================================================


def extract_error_attributes(error: Exception) -> dict[str, Any]:
    """
    Extract common attributes from any exception.

    Provides a consistent way to get error context from both Bengal errors
    and standard Python exceptions. All values are optional and will be
    None if not present on the error.

    Args:
        error: Exception to extract attributes from.

    Returns:
        Dictionary with keys:

        - ``error_type``: Exception class name
        - ``message``: Error message string
        - ``file_path``: Path where error occurred (Path or None)
        - ``line_number``: Line number (int or None)
        - ``column``: Column number (int or None)
        - ``code``: Bengal ErrorCode (or None)
        - ``suggestion``: Fix suggestion (str or None)
        - ``build_phase``: BuildPhase enum (or None)
        - ``severity``: ErrorSeverity enum (or None)
        - ``original_error``: Wrapped exception (or None)
        - ``related_files``: List of RelatedFile (or empty list)
        - ``debug_payload``: ErrorDebugPayload (or None)

    Example:
        >>> attrs = extract_error_attributes(error)
        >>> if attrs["file_path"]:
        ...     print(f"Error in {attrs['file_path']}:{attrs['line_number']}")

    """
    result: dict[str, Any] = {
        "error_type": type(error).__name__,
        "message": str(error),
        "file_path": None,
        "line_number": None,
        "column": None,
        "code": None,
        "suggestion": None,
        "build_phase": None,
        "severity": None,
        "original_error": None,
        "related_files": [],
        "debug_payload": None,
    }

    # Bengal error attributes
    if hasattr(error, "file_path"):
        result["file_path"] = getattr(error, "file_path", None)
    if hasattr(error, "line_number"):
        result["line_number"] = getattr(error, "line_number", None)
    if hasattr(error, "column"):
        result["column"] = getattr(error, "column", None)
    if hasattr(error, "code"):
        result["code"] = getattr(error, "code", None)
    if hasattr(error, "suggestion"):
        result["suggestion"] = getattr(error, "suggestion", None)
    if hasattr(error, "build_phase"):
        result["build_phase"] = getattr(error, "build_phase", None)
    if hasattr(error, "severity"):
        result["severity"] = getattr(error, "severity", None)
    if hasattr(error, "original_error"):
        result["original_error"] = getattr(error, "original_error", None)
    if hasattr(error, "related_files"):
        result["related_files"] = getattr(error, "related_files", []) or []
    if hasattr(error, "debug_payload"):
        result["debug_payload"] = getattr(error, "debug_payload", None)

    # Standard Python exception attributes
    if hasattr(error, "filename") and result["file_path"] is None:
        filename = getattr(error, "filename", None)
        if filename:
            with contextlib.suppress(TypeError, ValueError):
                result["file_path"] = Path(filename)

    if hasattr(error, "lineno") and result["line_number"] is None:
        result["line_number"] = getattr(error, "lineno", None)

    # Kida template engine attributes (source_snippet, error code, format_compact)
    if hasattr(error, "source_snippet"):
        result["source_snippet"] = getattr(error, "source_snippet", None)
    if hasattr(error, "code") and result["code"] is None:
        # Kida ErrorCode enum — extract its string value for Bengal compatibility
        kida_code = getattr(error, "code", None)
        if kida_code is not None and hasattr(kida_code, "value"):
            result["kida_error_code"] = kida_code.value
    if hasattr(error, "format_compact"):
        result["format_compact"] = error.format_compact

    return result


# =============================================================================
# Error Message Formatting
# =============================================================================


def get_error_message(error: Any) -> str:
    """
    Extract human-readable message from any error object.

    Handles both Bengal errors (which have a ``message`` attribute) and
    standard exceptions. Special handling for template runtime errors
    with empty messages but location info.

    Args:
        error: Error object to extract message from.

    Returns:
        Human-readable error message string.

    Example:
        >>> msg = get_error_message(error)
        >>> print(f"Error: {msg}")

    """
    msg = ""

    # Prefer .message attribute if available (BengalError)
    msg = str(error.message) if hasattr(error, "message") else str(error)

    # Prefer Kida's structured format_compact() when available
    if hasattr(error, "format_compact"):
        return error.format_compact()

    # Fallback: parse Kida's empty-message TemplateRuntimeError string format
    # Format: "Runtime Error: \n  Location: template.html:37\n  ..."
    if msg.startswith("Runtime Error:") and "\n" in msg:
        lines = msg.split("\n")
        first_line = lines[0].strip()

        # If first line is just "Runtime Error:" with nothing after the colon,
        # extract location from subsequent lines for a better message
        if first_line == "Runtime Error:":
            location = ""
            source_line = ""

            for line in lines[1:]:
                stripped = line.strip()
                if stripped.startswith("Location:"):
                    location = stripped[9:].strip()
                elif stripped.startswith("Expression:"):
                    source_line = stripped[11:].strip()

            # Construct a more informative message
            if location:
                msg = f"Runtime Error in {location}"
                if source_line and source_line != "<see stack trace>":
                    msg += f": {source_line}"
            else:
                msg = "Runtime Error (no details available)"

    return msg


# =============================================================================
# Serialization Helpers
# =============================================================================


def serialize_value(value: Any) -> Any:
    """
    Serialize a single value for JSON compatibility.

    Converts common types to JSON-serializable equivalents:

    - Path → str
    - Enum → value
    - datetime → ISO format string
    - dataclass with to_dict() → dict
    - None → None
    - Other → unchanged

    Args:
        value: Value to serialize.

    Returns:
        JSON-compatible value.

    """
    if value is None:
        return None
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value) and hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, list):
        return [serialize_value(v) for v in value]
    if isinstance(value, set):
        return [serialize_value(v) for v in sorted(value, key=str)]
    if isinstance(value, dict):
        return {k: serialize_value(v) for k, v in value.items()}
    return value


def dataclass_to_dict(
    obj: Any,
    *,
    exclude_none: bool = False,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Convert a dataclass to a dictionary with automatic type conversion.

    Recursively serializes all fields using ``serialize_value()``.

    Args:
        obj: Dataclass instance to convert.
        exclude_none: If True, omit fields with None values.
        extra_fields: Additional fields to include in output.

    Returns:
        Dictionary with serialized field values.

    Raises:
        TypeError: If obj is not a dataclass instance.

    Example:
        >>> @dataclass
        ... class Config:
        ...     path: Path
        ...     count: int
        >>> d = dataclass_to_dict(Config(Path("/tmp"), 5))
        >>> # Returns: {"path": "/tmp", "count": 5}

    """
    if not is_dataclass(obj) or isinstance(obj, type):
        raise TypeError(f"Expected dataclass instance, got {type(obj).__name__}")

    result: dict[str, Any] = {}

    for field in fields(obj):
        value = getattr(obj, field.name)
        serialized = serialize_value(value)

        if exclude_none and serialized is None:
            continue

        result[field.name] = serialized

    # Add extra fields
    if extra_fields:
        for key, value in extra_fields.items():
            result[key] = serialize_value(value)

    return result


# =============================================================================
# String Utilities
# =============================================================================


def extract_between(text: str, start: str, end: str) -> str | None:
    """
    Extract substring between two delimiters.

    Args:
        text: String to search in.
        start: Starting delimiter (not included in result).
        end: Ending delimiter (not included in result).

    Returns:
        Substring between delimiters, or None if not found.

    Example:
        >>> extract_between("error in 'module.py' at line 5", "'", "'")
        'module.py'

    """
    try:
        s = text.index(start) + len(start)
        e = text.index(end, s)
        return text[s:e]
    except ValueError:
        return None


def find_close_matches(
    name: str | None,
    candidates: Iterable[str],
    n: int = 5,
    cutoff: float = 0.6,
) -> list[str]:
    """
    Find closest string matches using fuzzy matching.

    Uses ``difflib.get_close_matches`` with configurable parameters.

    Args:
        name: String to find matches for.
        candidates: Iterable of candidate strings to match against.
        n: Maximum number of matches to return.
        cutoff: Similarity threshold (0.0 to 1.0).

    Returns:
        List of close matches, or empty list if none found.

    Example:
        >>> find_close_matches("tenmplate", ["template", "templates", "config"])
        ['template', 'templates']

    """
    if not name:
        return []
    try:
        return get_close_matches(name, list(candidates), n=n, cutoff=cutoff)
    except Exception as e:
        logger.debug(
            "utils_find_close_matches_failed",
            name=name,
            error=str(e),
            error_type=type(e).__name__,
            action="returning_empty_list",
        )
        return []


def safe_list_module_exports(module_path: str) -> list[str]:
    """
    Safely list public exports from a module.

    Attempts to import the module and extract its ``__all__`` list,
    or falls back to listing all non-private attributes.

    Args:
        module_path: Dotted module path (e.g., "bengal.core").

    Returns:
        Sorted list of export names, or empty list on any error.

    Example:
        >>> safe_list_module_exports("bengal.core")
        ['Page', 'Section', 'Site', ...]

    """
    exports: list[str] = []
    try:
        mod = __import__(module_path, fromlist=["*"])
        if hasattr(mod, "__all__") and isinstance(mod.__all__, list | tuple):
            exports = [str(x) for x in mod.__all__]
        else:
            exports = [n for n in dir(mod) if not n.startswith("_")]
    except Exception as e:
        logger.debug(
            "utils_list_exports_failed",
            module=module_path,
            error=str(e),
            error_type=type(e).__name__,
            action="returning_empty_list",
        )
        return []
    return sorted(set(exports))


# =============================================================================
# Singleton Pattern
# =============================================================================


class ThreadSafeSingleton[T]:
    """
    Thread-safe singleton container with lazy initialization.

    Provides a reusable pattern for managing singleton instances with
    thread safety and reset capability.

    Attributes:
        _instance: The singleton instance (or None if not initialized).
        _lock: Threading lock for thread safety.
        _factory: Callable that creates new instances.

    Example:
        >>> _session = ThreadSafeSingleton(lambda: ErrorSession())
        >>> session = _session.get()  # Creates instance on first call
        >>> same = _session.get()     # Returns same instance
        >>> new = _session.reset()    # Creates fresh instance

    """

    def __init__(self, factory: Callable[[], T]) -> None:
        """
        Initialize singleton container.

        Args:
            factory: Callable that creates new instances when needed.
        """
        self._instance: T | None = None
        self._lock = Lock()
        self._factory = factory

    def get(self) -> T:
        """
        Get the singleton instance, creating if necessary.

        Thread-safe with double-checked locking pattern.

        Returns:
            The singleton instance.
        """
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    self._instance = self._factory()
        return self._instance

    def reset(self) -> T:
        """
        Reset and return a fresh singleton instance.

        Creates a new instance regardless of current state.

        Returns:
            The newly created instance.
        """
        with self._lock:
            self._instance = self._factory()
            return self._instance

    def is_initialized(self) -> bool:
        """
        Check if the singleton has been initialized.

        Returns:
            True if instance exists, False otherwise.
        """
        return self._instance is not None
