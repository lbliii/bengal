"""
JSON utilities using orjson for Rust-accelerated serialization.

Provides a unified interface for JSON operations using orjson, which offers
3-10x faster serialization and 2-3x faster deserialization than stdlib json.

Performance:
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

See Also:
    - bengal/utils/file_io.py - Uses json_compat for file operations
    - bengal/cache/cache_store.py - Uses json_compat for cache serialization
    - https://github.com/ijl/orjson - orjson documentation
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import orjson

# Re-export for convenience
JSONDecodeError = orjson.JSONDecodeError


def dumps(
    obj: Any,
    *,
    indent: int | None = None,
) -> str:
    """
    Serialize object to JSON string using orjson.

    Args:
        obj: Object to serialize
        indent: Indentation level (None for compact, 2 for pretty)

    Returns:
        JSON string

    Note:
        orjson automatically handles datetime, dataclass, UUID, and numpy types.

    Example:
        >>> dumps({"key": "value"})
        '{"key":"value"}'
        >>> dumps({"key": "value"}, indent=2)
        '{\\n  "key": "value"\\n}'
    """
    options = orjson.OPT_SERIALIZE_DATACLASS
    if indent is not None:
        options |= orjson.OPT_INDENT_2

    # orjson.dumps returns bytes, decode to string
    return orjson.dumps(obj, option=options).decode("utf-8")


def loads(data: str | bytes) -> Any:
    """
    Deserialize JSON string to object using orjson.

    Args:
        data: JSON string or bytes to parse

    Returns:
        Parsed Python object

    Raises:
        orjson.JSONDecodeError: If JSON is invalid

    Example:
        >>> loads('{"key": "value"}')
        {'key': 'value'}
    """
    return orjson.loads(data)


def dump(
    obj: Any,
    path: Path | str,
    *,
    indent: int | None = 2,
) -> None:
    """
    Serialize object and write to JSON file.

    Creates parent directories if they don't exist.

    Args:
        obj: Object to serialize
        path: Path to output file
        indent: Indentation level (default: 2 for readability)

    Example:
        >>> dump({"key": "value"}, Path("output.json"))
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    json_str = dumps(obj, indent=indent)
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
        orjson.JSONDecodeError: If JSON is invalid

    Example:
        >>> data = load(Path("config.json"))
    """
    path = Path(path)
    content = path.read_bytes()  # Read as bytes for orjson efficiency
    return loads(content)


__all__ = [
    "dumps",
    "loads",
    "dump",
    "load",
    "JSONDecodeError",
]
