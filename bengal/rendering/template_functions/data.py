"""
Data manipulation functions for templates.

Provides 8 functions for working with JSON, YAML, and nested data structures.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site

logger = get_logger(__name__)


def register(env: Environment, site: Site) -> None:
    """Register data manipulation functions with Jinja2 environment."""

    # Create closures that have access to site
    def get_data_with_site(path: str) -> Any:
        return get_data(path, site.root_path)

    env.filters.update(
        {
            "jsonify": jsonify,
            "merge": merge,
            "has_key": has_key,
            "get_nested": get_nested,
            "keys": keys_filter,
            "values": values_filter,
            "items": items_filter,
        }
    )

    env.globals.update(
        {
            "get_data": get_data_with_site,
        }
    )


def get_data(path: str, root_path: Any) -> Any:
    """
    Load data from JSON or YAML file.

    Uses bengal.utils.file_io.load_data_file internally for robust file loading
    with error handling and logging.

    Args:
        path: Relative path to data file
        root_path: Site root path

    Returns:
        Parsed data (dict, list, or primitive)

    Example:
        {% set authors = get_data('data/authors.json') %}
        {% for author in authors %}
            {{ author.name }}
        {% endfor %}
    """
    if not path:
        logger.debug("get_data_empty_path", caller="template")
        return {}

    from pathlib import Path

    from bengal.utils.file_io import load_data_file

    file_path = Path(root_path) / path

    # Use file_io utility for robust loading with error handling
    # on_error='return_empty' returns {} for missing/invalid files
    return load_data_file(file_path, on_error="return_empty", caller="template")


def jsonify(data: Any, indent: int | None = None) -> str:
    """
    Convert data to JSON string.

    Args:
        data: Data to convert (dict, list, etc.)
        indent: Indentation level (default: None for compact)

    Returns:
        JSON string

    Example:
        {{ data | jsonify }}
        {{ data | jsonify(2) }}  # Pretty-printed
    """
    try:
        return json.dumps(data, indent=indent, ensure_ascii=False)
    except (TypeError, ValueError):
        return "{}"


def merge(dict1: dict[str, Any], dict2: dict[str, Any], deep: bool = True) -> dict[str, Any]:
    """
    Merge two dictionaries.

    Delegates to bengal.config.merge.deep_merge for consistent behavior
    across the codebase.

    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)
        deep: Perform deep merge (default: True)

    Returns:
        Merged dictionary

    Example:
        {% set config = defaults | merge(custom_config) %}
    """
    from bengal.config.merge import deep_merge

    if not isinstance(dict1, dict):
        dict1 = {}
    if not isinstance(dict2, dict):
        dict2 = {}

    if not deep:
        # Shallow merge
        result = dict1.copy()
        result.update(dict2)
        return result

    # Deep merge - delegate to config utility
    return deep_merge(dict1, dict2)


def has_key(data: dict[str, Any], key: str) -> bool:
    """
    Check if dictionary has a key.

    Args:
        data: Dictionary to check
        key: Key to look for

    Returns:
        True if key exists

    Example:
        {% if data | has_key('author') %}
            {{ data.author }}
        {% endif %}
    """
    if not isinstance(data, dict):
        return False

    return key in data


def get_nested(data: dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Access nested data using dot notation.

    Args:
        data: Dictionary with nested data
        path: Dot-separated path (e.g., "user.profile.name")
        default: Default value if path not found

    Returns:
        Value at path or default

    Example:
        {{ data | get_nested('user.profile.name') }}
        {{ data | get_nested('user.email', 'no-email') }}
    """
    if not isinstance(data, dict) or not path:
        return default

    keys = path.split(".")
    current = data

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current


def keys_filter(data: dict[str, Any]) -> list[str]:
    """
    Get dictionary keys as list.

    Args:
        data: Dictionary or DotDict

    Returns:
        List of keys

    Example:
        {% for key in data | keys %}
            {{ key }}
        {% endfor %}
    """
    # Handle DotDict objects
    try:
        from bengal.utils.dotdict import DotDict

        if isinstance(data, DotDict):
            return list(data.keys())
    except (ImportError, TypeError):
        # DotDict not available or data type incompatible; fall through to regular dict handling.
        pass

    # Handle regular dicts
    if isinstance(data, dict):
        return list(data.keys())

    # Fallback: try calling keys() if it exists
    if hasattr(data, "keys"):
        try:
            return list(data.keys())
        except (AttributeError, TypeError):
            pass

    return []


def values_filter(data: dict[str, Any]) -> list[Any]:
    """
    Get dictionary values as list.

    Args:
        data: Dictionary or DotDict

    Returns:
        List of values

    Example:
        {% for value in data | values %}
            {{ value }}
        {% endfor %}
    """
    # Handle DotDict objects
    try:
        from bengal.utils.dotdict import DotDict

        if isinstance(data, DotDict):
            return list(data.values())
    except (ImportError, TypeError):
        # DotDict not available or data type incompatible; fall through to regular dict handling.
        pass

    # Handle regular dicts
    if isinstance(data, dict):
        return list(data.values())

    # Fallback: try calling values() if it exists
    if hasattr(data, "values"):
        try:
            return list(data.values())
        except (AttributeError, TypeError):
            pass

    return []


def items_filter(data: dict[str, Any]) -> list[tuple[str, Any]]:
    """
    Get dictionary items as list of (key, value) tuples.

    Args:
        data: Dictionary or DotDict

    Returns:
        List of (key, value) tuples

    Example:
        {% for key, value in data | items %}
            {{ key }}: {{ value }}
        {% endfor %}
    """
    # Handle DotDict objects (from bengal.utils.dotdict)
    # DotDict doesn't inherit from dict but has an items() method
    try:
        from bengal.utils.dotdict import DotDict

        if isinstance(data, DotDict):
            return list(data.items())
    except (ImportError, TypeError):
        # DotDict not available or data type incompatible; fall through to regular dict handling.
        pass

    # Handle regular dicts
    if isinstance(data, dict):
        return list(data.items())

    # Fallback: try calling items() if it exists
    if hasattr(data, "items"):
        try:
            return list(data.items())
        except (AttributeError, TypeError):
            pass

    return []
