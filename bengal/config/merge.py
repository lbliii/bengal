"""
Deep merge utilities for config system.

Provides deterministic deep merging of configuration dictionaries
with clear override semantics.
"""

from __future__ import annotations

from typing import Any


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge override dict into base dict.

    Override semantics:
    - Dicts: recursively merge
    - Lists: replace entirely (override wins)
    - Primitives: replace (override wins)

    Args:
        base: Base configuration dictionary
        override: Override configuration dictionary

    Returns:
        Merged dictionary (new dict, does not mutate inputs)

    Examples:
        >>> base = {"site": {"title": "Base"}, "build": {"parallel": True}}
        >>> override = {"site": {"baseurl": "https://example.com"}}
        >>> result = deep_merge(base, override)
        >>> result
        {
            "site": {"title": "Base", "baseurl": "https://example.com"},
            "build": {"parallel": True}
        }
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Both are dicts: recursively merge
            result[key] = deep_merge(result[key], value)
        else:
            # Override wins: lists, primitives, or type mismatch
            result[key] = value

    return result


def set_nested_key(config: dict[str, Any], key_path: str, value: Any) -> None:
    """
    Set a nested key in config dictionary using dot notation.

    Creates intermediate dicts as needed.

    Args:
        config: Configuration dictionary to modify (mutates in place)
        key_path: Dot-separated path (e.g., "site.theme.name")
        value: Value to set

    Examples:
        >>> config = {}
        >>> set_nested_key(config, "site.theme.name", "default")
        >>> config
        {"site": {"theme": {"name": "default"}}}
    """
    keys = key_path.split(".")
    current = config

    # Navigate to parent
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        elif not isinstance(current[key], dict):
            # Can't traverse non-dict, skip
            return
        current = current[key]

    # Set final key
    final_key = keys[-1]
    current[final_key] = value


def get_nested_key(config: dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Get a nested key from config dictionary using dot notation.

    Args:
        config: Configuration dictionary
        key_path: Dot-separated path (e.g., "site.theme.name")
        default: Default value if key not found

    Returns:
        Value at key_path, or default if not found

    Examples:
        >>> config = {"site": {"theme": {"name": "default"}}}
        >>> get_nested_key(config, "site.theme.name")
        "default"
        >>> get_nested_key(config, "site.missing", "fallback")
        "fallback"
    """
    keys = key_path.split(".")
    current = config

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current
