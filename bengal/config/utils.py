"""
Shared configuration utilities to reduce code duplication.

This module provides common utility functions used across the config package
to avoid repeating the same logic in multiple files.

Key Functions:
    coerce_bool: Convert various types to boolean with sensible defaults.
    unwrap_config: Extract raw dict from Config/ConfigSection objects.
    get_config_value: Get value from nested or flat config structure.
    get_default_config: Get a deep copy of DEFAULTS.

Example:
    >>> from bengal.config.utils import coerce_bool, get_config_value
    >>> coerce_bool("yes")
    True
    >>> coerce_bool("invalid", default=False)
    False

See Also:
- :mod:`bengal.config.defaults`: Default configuration values.
- :mod:`bengal.config.merge`: Deep merge utilities.

"""

from __future__ import annotations

from typing import Any

# =============================================================================
# Boolean Coercion
# =============================================================================

# Recognized truthy string values (case-insensitive)
TRUTHY_STRINGS = frozenset({"true", "yes", "1", "on"})

# Recognized falsy string values (case-insensitive)
FALSY_STRINGS = frozenset({"false", "no", "0", "off"})


def coerce_bool(value: Any, default: bool | None = None) -> bool | None:
    """
    Coerce a value to boolean with sensible defaults.

    Handles multiple input types with predictable conversion:
    - ``None``: Returns the default value.
    - ``bool``: Returns as-is.
    - ``int``: Returns ``bool(value)`` (0 → False, non-zero → True).
    - ``str``: Checks against TRUTHY_STRINGS and FALSY_STRINGS.

    For unrecognized string values, returns the default.

    Args:
        value: Value to coerce (bool, int, str, or None).
        default: Value to return for None or unrecognized strings.

    Returns:
        Coerced boolean value, or default if conversion not possible.

    Example:
        >>> coerce_bool(True)
        True
        >>> coerce_bool("yes")
        True
        >>> coerce_bool("FALSE")
        False
        >>> coerce_bool(1)
        True
        >>> coerce_bool(0)
        False
        >>> coerce_bool(None, default=True)
        True
        >>> coerce_bool("invalid", default=False)
        False
        >>> coerce_bool("maybe")  # Unrecognized
        None

    """
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return bool(value)

    if isinstance(value, str):
        lower = value.lower().strip()
        if lower in TRUTHY_STRINGS:
            return True
        if lower in FALSY_STRINGS:
            return False
        # Unrecognized string - return default
        return default

    # Unknown type - return default
    return default


# =============================================================================
# Config Object Unwrapping
# =============================================================================


def unwrap_config(config: Any) -> dict[str, Any]:
    """
    Extract raw dictionary from Config, ConfigSection, or pass-through dict.

    Bengal's config system has multiple accessor types:
    - ``Config``: Has ``.raw`` property returning underlying dict.
    - ``ConfigSection``: Has ``._data`` attribute with section dict.
    - Plain ``dict``: Returned as-is.

    This function provides a uniform way to get the raw dict regardless
    of which accessor type is passed.

    Args:
        config: A Config object, ConfigSection, dict, or any type.

    Returns:
        The underlying dictionary. Returns empty dict for unrecognized types.

    Example:
        >>> from bengal.config.accessor import Config
        >>> cfg = Config({"title": "Test"})
        >>> unwrap_config(cfg)
        {'title': 'Test'}
        >>> unwrap_config({"title": "Test"})
        {'title': 'Test'}

    """
    if hasattr(config, "raw"):
        return config.raw
    if hasattr(config, "_data"):
        return config._data
    if isinstance(config, dict):
        return config
    return {}


# =============================================================================
# Nested/Flat Config Value Access
# =============================================================================


def get_config_value(
    config: dict[str, Any] | Any,
    key: str,
    sections: tuple[str, ...] = ("site", "build"),
    default: Any = None,
) -> Any:
    """
    Get config value checking both flat and nested paths.

    Bengal configs can be in two forms:
    - Flat: ``{"title": "Site", "parallel": True}``
    - Nested: ``{"site": {"title": "Site"}, "build": {"parallel": True}}``

    This function checks the flat path first, then searches through
    the specified sections for nested access.

    Args:
        config: Config dict or Config object.
        key: Key to look up (e.g., ``"title"``, ``"parallel"``).
        sections: Sections to check for nested access. Defaults to
            ``("site", "build")``.
        default: Value to return if key is not found.

    Returns:
        Config value from first matching location, or default if not found.

    Example:
        >>> # Flat config
        >>> get_config_value({"title": "My Site"}, "title")
        'My Site'

        >>> # Nested config
        >>> get_config_value({"site": {"title": "My Site"}}, "title")
        'My Site'

        >>> # With custom sections
        >>> get_config_value(
        ...     {"dev": {"port": 8080}},
        ...     "port",
        ...     sections=("dev",)
        ... )
        8080

    """
    config = unwrap_config(config)

    # Check flat path first (most common after config loading)
    if key in config:
        return config[key]

    # Check nested paths in specified sections
    for section in sections:
        section_dict = config.get(section)
        if isinstance(section_dict, dict) and key in section_dict:
            return section_dict[key]

    return default


# =============================================================================
# Default Config
# =============================================================================


def get_default_config() -> dict[str, Any]:
    """
    Get a deep copy of DEFAULTS for config initialization.

    Returns a deep copy of DEFAULTS to avoid mutation. This ensures
    consistency across all config loading modes (single-file, directory).

    This function should be used instead of inline ``deep_merge({}, DEFAULTS)``
    patterns throughout the config package.

    Returns:
        Default configuration dictionary with all settings from DEFAULTS.

    Example:
        >>> defaults = get_default_config()
        >>> defaults["site"]["title"]
        'Bengal Site'
        >>> # Mutations don't affect DEFAULTS
        >>> defaults["site"]["title"] = "Custom"
        >>> from bengal.config.defaults import DEFAULTS
        >>> DEFAULTS["site"]["title"]
        'Bengal Site'

    """
    from bengal.config.defaults import DEFAULTS
    from bengal.config.merge import deep_merge

    return deep_merge({}, DEFAULTS)


__all__ = [
    "FALSY_STRINGS",
    "TRUTHY_STRINGS",
    "coerce_bool",
    "get_config_value",
    "get_default_config",
    "unwrap_config",
]
