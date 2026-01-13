"""
Deep merge utilities for the configuration system.

This module provides deterministic deep merging of configuration dictionaries
with clear, predictable override semantics. It's used throughout the config
system to combine base configurations with environment-specific and
profile-specific overrides.

Override Semantics:
- **Dictionaries**: Recursively merged (keys combined, nested dicts merged).
- **Lists**: Replaced entirely (override wins).
- **Primitives**: Replaced (override wins).

Key Functions:
    deep_merge: Recursively merge two dictionaries.
    batch_deep_merge: Merge multiple dictionaries in a single pass (optimized).
    set_nested_key: Set a value at a dot-separated path.
    get_nested_key: Get a value from a dot-separated path.

Example:
    >>> base = {"site": {"title": "Base"}, "build": {"parallel": True}}
    >>> override = {"site": {"baseurl": "https://example.com"}}
    >>> result = deep_merge(base, override)
    >>> result["site"]["title"]
    'Base'
    >>> result["site"]["baseurl"]
    'https://example.com'

Note:
All functions in this module create new dictionaries rather than
mutating inputs, except where explicitly documented (e.g., ``set_nested_key``,
``_merge_into``).

See Also:
- :mod:`bengal.config.directory_loader`: Uses batch_deep_merge for config layering.
- :mod:`bengal.config.deprecation`: Uses nested key functions for migration.

"""

from __future__ import annotations

from typing import Any


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge an override dictionary into a base dictionary.
    
    Creates a new dictionary containing all keys from both inputs. When keys
    exist in both dictionaries, the override value takes precedence for
    primitives and lists, while nested dictionaries are recursively merged.
    
    Args:
        base: Base configuration dictionary (not mutated).
        override: Override configuration dictionary (not mutated).
    
    Returns:
        New merged dictionary. Neither input is mutated.
    
    Example:
            >>> base = {"site": {"title": "Base"}, "build": {"parallel": True}}
            >>> override = {"site": {"baseurl": "https://example.com"}}
            >>> result = deep_merge(base, override)
            >>> result["site"]
        {'title': 'Base', 'baseurl': 'https://example.com'}
            >>> result["build"]
        {'parallel': True}
        
    """
    # Copy base to avoid sharing nested dict references with callers
    result = _copy_dict(base)

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Both are dicts: recursively merge
            result[key] = deep_merge(result[key], value)
        else:
            # Override wins: lists, primitives, or type mismatch
            result[key] = _copy_dict(value) if isinstance(value, dict) else value

    return result


def _merge_into(target: dict[str, Any], source: dict[str, Any]) -> None:
    """Merge source into target in place. Copies source dicts to avoid mutation."""
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            _merge_into(target[key], value)
        elif isinstance(value, dict):
            target[key] = _copy_dict(value)
        else:
            target[key] = value


def _copy_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively copy dict. Leaves primitives/lists as-is (not mutated by merge)."""
    return {k: _copy_dict(v) if isinstance(v, dict) else v for k, v in d.items()}


def batch_deep_merge(configs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Merge multiple config dicts in a single pass. O(K×D) vs O(F×K×D) sequential.
    
    Args:
        configs: Dicts to merge in precedence order (later overrides earlier).
    
    Returns:
        New merged dictionary. Input dicts are not mutated.
        
    """
    result: dict[str, Any] = {}
    for config in configs:
        _merge_into(result, config)
    return result


def set_nested_key(config: dict[str, Any], key_path: str, value: Any) -> None:
    """
    Set a nested key in a configuration dictionary using dot notation.
    
    Creates intermediate dictionaries as needed to reach the target key.
    If a non-dictionary value is encountered while traversing the path,
    the operation is aborted silently.
    
    Args:
        config: Configuration dictionary to modify (**mutated in place**).
        key_path: Dot-separated path to the key (e.g., ``"site.theme.name"``).
        value: Value to set at the specified path.
    
    Warning:
        This function mutates the input dictionary.
    
    Example:
            >>> config = {}
            >>> set_nested_key(config, "site.theme.name", "default")
            >>> config
        {'site': {'theme': {'name': 'default'}}}
        
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
    Get a nested key from a configuration dictionary using dot notation.
    
    Safely traverses nested dictionaries following the dot-separated path.
    Returns the default value if any key in the path doesn't exist or
    if a non-dictionary value is encountered before reaching the target.
    
    Args:
        config: Configuration dictionary to read from.
        key_path: Dot-separated path to the key (e.g., ``"site.theme.name"``).
        default: Value to return if the key is not found.
    
    Returns:
        Value at the specified path, or ``default`` if not found.
    
    Example:
            >>> config = {"site": {"theme": {"name": "default"}}}
            >>> get_nested_key(config, "site.theme.name")
            'default'
            >>> get_nested_key(config, "site.missing", "fallback")
            'fallback'
            >>> get_nested_key(config, "nonexistent.path")  # Returns None
        
    """
    keys = key_path.split(".")
    current = config

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current
