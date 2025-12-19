"""
JSON compatibility layer with orjson acceleration.

Provides a unified interface for JSON serialization/deserialization using
orjson (Rust-based, 3-10x faster) with automatic fallback to stdlib json
if orjson is unavailable.

Performance:
    orjson provides significant speedups for JSON operations:
    - Serialization (dumps): 3-10x faster than stdlib json
    - Deserialization (loads): 2-3x faster than stdlib json
    - Native support for datetime, dataclass, numpy, UUID

Usage:
    >>> from bengal.utils.json_compat import dumps, loads, dump, load
    >>>
    >>> # Serialize to string
    >>> data = {"key": "value", "date": datetime.now()}
    >>> json_str = dumps(data)
    >>>
    >>> # Deserialize from string
    >>> parsed = loads(json_str)
    >>>
    >>> # File operations
    >>> dump(data, path)  # Write to file
    >>> loaded = load(path)  # Read from file

API Compatibility:
    This module provides drop-in replacements for stdlib json functions:
    - dumps(obj, indent=None) -> str
    - loads(data) -> Any
    - dump(obj, path, indent=None) -> None  # Path-based, not file handle
    - load(path) -> Any  # Path-based, not file handle

Note:
    The file-based functions (dump/load) take Path objects directly rather
    than file handles, which is more convenient for Bengal's use patterns.

See Also:
    - bengal/utils/file_io.py - Uses json_compat for file operations
    - bengal/cache/cache_store.py - Uses json_compat for cache serialization
    - https://github.com/ijl/orjson - orjson documentation
"""

from __future__ import annotations

import json as stdlib_json
from pathlib import Path
from typing import Any

# Try to import orjson for Rust-accelerated JSON
try:
    import orjson

    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False
    orjson = None  # type: ignore[assignment]


def dumps(
    obj: Any,
    *,
    indent: int | None = None,
    default: Any = None,
    ensure_ascii: bool = False,
) -> str:
    """
    Serialize object to JSON string.

    Uses orjson if available (3-10x faster), falls back to stdlib json.

    Args:
        obj: Object to serialize
        indent: Indentation level (None for compact, 2 for pretty)
        default: Function to serialize non-standard types (stdlib json only)
        ensure_ascii: If True, escape non-ASCII characters (stdlib json only)

    Returns:
        JSON string

    Note:
        orjson automatically handles datetime, dataclass, UUID, and numpy types.
        For stdlib json, use default=str to handle datetime.

    Example:
        >>> dumps({"key": "value"})
        '{"key":"value"}'
        >>> dumps({"key": "value"}, indent=2)
        '{\\n  "key": "value"\\n}'
    """
    if ORJSON_AVAILABLE:
        # Build orjson options
        options = orjson.OPT_SERIALIZE_DATACLASS
        if indent is not None:
            options |= orjson.OPT_INDENT_2

        # orjson.dumps returns bytes, decode to string
        return orjson.dumps(obj, option=options).decode("utf-8")
    else:
        # Fallback to stdlib json
        return stdlib_json.dumps(
            obj, indent=indent, default=default or str, ensure_ascii=ensure_ascii
        )


def loads(data: str | bytes) -> Any:
    """
    Deserialize JSON string to object.

    Uses orjson if available (2-3x faster), falls back to stdlib json.

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
    if ORJSON_AVAILABLE:
        return orjson.loads(data)
    else:
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return stdlib_json.loads(data)


def dump(
    obj: Any,
    path: Path | str,
    *,
    indent: int | None = 2,
    default: Any = None,
) -> None:
    """
    Serialize object and write to JSON file.

    Creates parent directories if they don't exist.

    Args:
        obj: Object to serialize
        path: Path to output file
        indent: Indentation level (default: 2 for readability)
        default: Function to serialize non-standard types (stdlib json only)

    Example:
        >>> dump({"key": "value"}, Path("output.json"))
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    json_str = dumps(obj, indent=indent, default=default)
    path.write_text(json_str, encoding="utf-8")


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
    content = path.read_bytes()  # Read as bytes for orjson efficiency
    return loads(content)


# Re-export JSONDecodeError for convenience
if ORJSON_AVAILABLE:
    JSONDecodeError = orjson.JSONDecodeError
else:
    JSONDecodeError = stdlib_json.JSONDecodeError


__all__ = [
    "dumps",
    "loads",
    "dump",
    "load",
    "JSONDecodeError",
    "ORJSON_AVAILABLE",
]
