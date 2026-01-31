"""
Config access utilities.

Provides helpers for accessing nested configuration values with
consistent fallback behavior. Handles both Config objects and
plain dictionaries.

Functions:
    get_site_value: Get value from site config section with flat fallback
    get_config_section: Get config section as dict with empty fallback

"""

from __future__ import annotations

from typing import Any


def get_site_value(config: Any, key: str, default: Any = None) -> Any:
    """
    Get value from site config section with flat fallback.

    Bengal config can have values in nested `[site]` section or at the
    root level (flat). This helper checks both locations consistently.

    Priority:
        1. config.site.<key> (Config object attribute access)
        2. config["site"][key] (nested dict access)
        3. config[key] (flat/root level access)
        4. default

    Args:
        config: Configuration object or dictionary
        key: Key to look up (e.g., "title", "baseurl", "author")
        default: Default value if key not found anywhere

    Returns:
        Configuration value or default

    Example:
        >>> get_site_value(config, "title", "My Site")
        'Bengal Documentation'
        >>> get_site_value(config, "baseurl", "")
        '/docs'
    """
    # Try Config object attribute access (config.site.key)
    site_attr = getattr(config, "site", None)
    if site_attr is not None:
        # Check for attribute on site section
        value = getattr(site_attr, key, None)
        if value is not None:
            return value
        # Check for get method (ConfigSection)
        if hasattr(site_attr, "get"):
            value = site_attr.get(key)
            if value is not None:
                return value

    # Try nested dict access (config["site"][key])
    if hasattr(config, "get"):
        site_section = config.get("site", {})
        if isinstance(site_section, dict) and key in site_section:
            return site_section[key]

        # Try flat/root level access (config[key])
        value = config.get(key)
        if value is not None:
            return value

    return default


def get_config_section(config: Any, section: str) -> dict[str, Any]:
    """
    Get a config section as a dictionary.

    Safely extracts a configuration section (e.g., "build", "assets", "i18n")
    and returns it as a dict. Returns empty dict if section doesn't exist.

    Handles both Config objects and plain dictionaries.

    Args:
        config: Configuration object or dictionary
        section: Section name (e.g., "build", "assets", "i18n", "menu")

    Returns:
        Config section as dict (empty dict if not found)

    Example:
        >>> build_cfg = get_config_section(config, "build")
        >>> build_cfg.get("parallel", True)
        True
    """
    # Try Config object attribute access
    section_attr = getattr(config, section, None)
    if section_attr is not None:
        # Check for _data attribute (ConfigSection internal dict)
        data_attr = getattr(section_attr, "_data", None)
        if data_attr is not None and isinstance(data_attr, dict):
            return dict(data_attr)
        # Check if it's already a dict
        if isinstance(section_attr, dict):
            return dict(section_attr)
        # Try to convert via dict()
        try:
            return dict(section_attr)
        except (TypeError, ValueError):
            pass

    # Try dict access
    if hasattr(config, "get"):
        value = config.get(section)
        if isinstance(value, dict):
            return dict(value)

    return {}
