"""
Shared utilities for the services package.

Consolidates common patterns used across service modules:
- Package directory resolution (get_bengal_dir)
- Immutable data structures (freeze_dict, freeze_value)
- Collection helpers (find_first)

These utilities support the snapshot-enabled architecture where
services operate on immutable data structures.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, TypeVar

T = TypeVar("T")


@lru_cache(maxsize=1)
def get_bengal_dir() -> Path:
    """
    Get the bengal package root directory (cached).

    Returns:
        Path to the bengal package directory

    Raises:
        AssertionError: If bengal module has no __file__

    Example:
        >>> bengal_dir = get_bengal_dir()
        >>> themes_dir = bengal_dir / "themes"
    """
    import bengal

    assert bengal.__file__ is not None, "bengal module has no __file__"
    return Path(bengal.__file__).parent


def get_bundled_themes_dir() -> Path:
    """
    Get the directory containing bundled themes.

    Returns:
        Path to bengal/themes/ directory
    """
    return get_bengal_dir() / "themes"


def freeze_dict(d: dict[str, Any]) -> MappingProxyType[str, Any]:
    """
    Recursively freeze a dictionary.

    Converts:
    - dict → MappingProxyType (immutable view)
    - list → tuple (immutable sequence)

    Args:
        d: Dictionary to freeze

    Returns:
        Immutable MappingProxyType view of the dictionary

    Example:
        >>> data = {"key": [1, 2, {"nested": "value"}]}
        >>> frozen = freeze_dict(data)
        >>> frozen["key"]  # Returns tuple
        (1, 2, mappingproxy({'nested': 'value'}))
    """
    result: dict[str, Any] = {}
    for k, v in d.items():
        result[k] = freeze_value(v)
    return MappingProxyType(result)


def freeze_value(item: Any) -> Any:
    """
    Freeze a single value.

    Converts:
    - dict → MappingProxyType
    - list → tuple (with nested values frozen)
    - Other values returned unchanged

    Args:
        item: Value to freeze

    Returns:
        Frozen version of the value
    """
    if isinstance(item, dict):
        return freeze_dict(item)
    elif isinstance(item, list):
        return tuple(freeze_value(i) for i in item)
    return item
