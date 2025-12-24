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
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Both are dicts: recursively merge
            result[key] = deep_merge(result[key], value)
        else:
            # Override wins: lists, primitives, or type mismatch
            result[key] = value

    return result


def _merge_into(target: dict[str, Any], source: dict[str, Any]) -> None:
    """
    Merge source dictionary into target dictionary in place.

    This is an internal helper that mutates the target dictionary directly,
    avoiding the overhead of creating new dictionaries at each step. Used by
    :func:`batch_deep_merge` for efficient multi-config merging.

    Args:
        target: Target dictionary to merge into (**mutated in place**).
        source: Source dictionary to merge from (not mutated).

    Warning:
        This function mutates the target dictionary. Only use when you own
        the target dictionary and don't need to preserve its original state.

    Example:
        >>> target = {"site": {"title": "Base"}}
        >>> source = {"site": {"baseurl": "/"}, "build": {"parallel": True}}
        >>> _merge_into(target, source)
        >>> target
        {'site': {'title': 'Base', 'baseurl': '/'}, 'build': {'parallel': True}}
    """
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            # Both are dicts: recursively merge in place
            # Note: target[key] is already owned by target, so safe to mutate
            _merge_into(target[key], value)
        elif isinstance(value, dict):
            # Source value is a dict not in target: copy to avoid mutating source
            target[key] = _deep_copy_dict(value)
        else:
            # Override wins: lists, primitives, or type mismatch
            # Lists and primitives are safe to assign (immutable or we don't mutate)
            target[key] = value


def _deep_copy_dict(d: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively copy a dictionary.

    Optimized for config dicts: only copies nested dicts, leaves
    primitives and lists as-is (they're not mutated by merge).

    Args:
        d: Dictionary to copy.

    Returns:
        Deep copy of the dictionary.
    """
    result: dict[str, Any] = {}
    for key, value in d.items():
        if isinstance(value, dict):
            result[key] = _deep_copy_dict(value)
        else:
            result[key] = value
    return result


def batch_deep_merge(configs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Merge multiple configuration dictionaries in a single pass.

    This is an optimized alternative to calling :func:`deep_merge` repeatedly.
    Instead of O(F × K × D) complexity from cumulative merging, this achieves
    O(K × D) by merging all configs into a single result dictionary in place.

    Complexity:
        - Sequential deep_merge: O(F × K × D) where F = files, K = keys, D = depth
        - batch_deep_merge: O(K × D) - single pass through all keys

    For 12 config files with 130 keys at depth 3:
        - Sequential: ~4,680 operations
        - Batch: ~390 operations (12× reduction)

    Args:
        configs: List of configuration dictionaries to merge, in precedence order
            (later configs override earlier ones).

    Returns:
        New merged dictionary containing all keys from all configs.

    Example:
        >>> configs = [
        ...     {"site": {"title": "Base"}},
        ...     {"site": {"baseurl": "/"}},
        ...     {"build": {"parallel": True}},
        ... ]
        >>> result = batch_deep_merge(configs)
        >>> result
        {'site': {'title': 'Base', 'baseurl': '/'}, 'build': {'parallel': True}}

    Note:
        The input dictionaries are not mutated. A new result dictionary is
        created and populated using in-place merge operations.

    See Also:
        - :func:`deep_merge`: For merging exactly two dictionaries.
    """
    if not configs:
        return {}

    # Start with empty dict and merge all configs in place
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
