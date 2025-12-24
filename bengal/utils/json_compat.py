"""
JSON utilities with atomic file writes.

Provides a unified interface for JSON operations using Python's standard library
json module, with atomic writes for crash safety.

Usage:
    >>> from bengal.utils.json_compat import dumps, loads, dump, load
    >>>
    >>> # Serialize to string
    >>> data = {"key": "value"}
    >>> json_str = dumps(data)
    >>>
    >>> # Deserialize from string
    >>> parsed = loads(json_str)
    >>>
    >>> # File operations (atomic writes)
    >>> dump(data, path)  # Write to file atomically
    >>> loaded = load(path)  # Read from file

See Also:
    - bengal/utils/file_io.py - Uses json_compat for file operations
    - bengal/cache/cache_store.py - Uses json_compat for cache serialization
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bengal.utils.atomic_write import atomic_write_text

# Re-export for convenience
JSONDecodeError = json.JSONDecodeError


def dumps(
    obj: Any,
    *,
    indent: int | None = None,
) -> str:
    """
    Serialize object to JSON string.

    Args:
        obj: Object to serialize
        indent: Indentation level (None for compact, 2 for pretty)

    Returns:
        JSON string

    Example:
        >>> dumps({"key": "value"})
        '{"key": "value"}'
        >>> dumps({"key": "value"}, indent=2)
        '{\\n  "key": "value"\\n}'
    """
    return json.dumps(obj, indent=indent, ensure_ascii=False)


def loads(data: str | bytes) -> Any:
    """
    Deserialize JSON string to object.

    Args:
        data: JSON string or bytes to parse

    Returns:
        Parsed Python object

    Raises:
        json.JSONDecodeError: If JSON is invalid

    Example:
        >>> loads('{"key": "value"}')
        {'key': 'value'}
    """
    return json.loads(data)


def dump(
    obj: Any,
    path: Path | str,
    *,
    indent: int | None = 2,
) -> None:
    """
    Serialize object and write to JSON file atomically (crash-safe).

    Creates parent directories if they don't exist.
    Uses atomic write to ensure file is never partially written.

    Args:
        obj: Object to serialize
        path: Path to output file
        indent: Indentation level (default: 2 for readability)

    Example:
        >>> dump({"key": "value"}, Path("output.json"))
    """
    path = Path(path)
    json_str = dumps(obj, indent=indent)
    atomic_write_text(path, json_str)


def load(path: Path | str) -> Any:
    """
    Read and deserialize JSON file.

    Args:
        path: Path to JSON file

    Returns:
        Parsed Python object

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid

    Example:
        >>> data = load(Path("config.json"))
    """
    path = Path(path)
    content = path.read_text(encoding="utf-8")
    return loads(content)


__all__ = [
    "dumps",
    "loads",
    "dump",
    "load",
    "JSONDecodeError",
]
