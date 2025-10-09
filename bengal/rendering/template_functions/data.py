"""
Data manipulation functions for templates.

Provides 8 functions for working with JSON, YAML, and nested data structures.
"""

import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from jinja2 import Environment
    from bengal.core.site import Site

logger = get_logger(__name__)


def register(env: 'Environment', site: 'Site') -> None:
    """Register data manipulation functions with Jinja2 environment."""
    
    # Create closures that have access to site
    def get_data_with_site(path: str) -> Any:
        return get_data(path, site.root_path)
    
    env.filters.update({
        'jsonify': jsonify,
        'merge': merge,
        'has_key': has_key,
        'get_nested': get_nested,
        'keys': keys_filter,
        'values': values_filter,
        'items': items_filter,
    })
    
    env.globals.update({
        'get_data': get_data_with_site,
    })


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
    return load_data_file(file_path, on_error='return_empty', caller='template')


def jsonify(data: Any, indent: Optional[int] = None) -> str:
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
        return '{}'


def merge(dict1: Dict[str, Any], dict2: Dict[str, Any], deep: bool = True) -> Dict[str, Any]:
    """
    Merge two dictionaries.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)
        deep: Perform deep merge (default: True)
    
    Returns:
        Merged dictionary
    
    Example:
        {% set config = defaults | merge(custom_config) %}
    """
    if not isinstance(dict1, dict):
        dict1 = {}
    if not isinstance(dict2, dict):
        dict2 = {}
    
    if not deep:
        # Shallow merge
        result = dict1.copy()
        result.update(dict2)
        return result
    
    # Deep merge
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge(result[key], value, deep=True)
        else:
            result[key] = value
    
    return result


def has_key(data: Dict[str, Any], key: str) -> bool:
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


def get_nested(data: Dict[str, Any], path: str, default: Any = None) -> Any:
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
    
    keys = path.split('.')
    current = data
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current


def keys_filter(data: Dict[str, Any]) -> List[str]:
    """
    Get dictionary keys as list.
    
    Args:
        data: Dictionary
    
    Returns:
        List of keys
    
    Example:
        {% for key in data | keys %}
            {{ key }}
        {% endfor %}
    """
    if not isinstance(data, dict):
        return []
    
    return list(data.keys())


def values_filter(data: Dict[str, Any]) -> List[Any]:
    """
    Get dictionary values as list.
    
    Args:
        data: Dictionary
    
    Returns:
        List of values
    
    Example:
        {% for value in data | values %}
            {{ value }}
        {% endfor %}
    """
    if not isinstance(data, dict):
        return []
    
    return list(data.values())


def items_filter(data: Dict[str, Any]) -> List[tuple]:
    """
    Get dictionary items as list of (key, value) tuples.
    
    Args:
        data: Dictionary
    
    Returns:
        List of (key, value) tuples
    
    Example:
        {% for key, value in data | items %}
            {{ key }}: {{ value }}
        {% endfor %}
    """
    if not isinstance(data, dict):
        return []
    
    return list(data.items())

