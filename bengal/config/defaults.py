"""
Single source of truth for all Bengal configuration defaults.

All config access should use these defaults via get_default() or
specialized helpers like get_max_workers().

This module avoids importing heavy dependencies to stay fast at import time.
"""

from __future__ import annotations

import os
from typing import Any

# =============================================================================
# Worker Configuration
# =============================================================================

# Auto-detect optimal worker count based on CPU cores
# Leave 1 core for OS/UI, minimum 4 workers
_CPU_COUNT = os.cpu_count() or 4
DEFAULT_MAX_WORKERS = max(4, _CPU_COUNT - 1)


def get_max_workers(config_value: int | None = None) -> int:
    """
    Resolve max_workers with auto-detection.

    Args:
        config_value: User-configured value from site.config.get("max_workers")
                     - None or 0 = auto-detect based on CPU count
                     - Positive int = use that value

    Returns:
        Resolved worker count (always >= 1)

    Example:
        >>> get_max_workers(None)  # Auto-detect
        11  # On a 12-core machine
        >>> get_max_workers(0)     # Also auto-detect
        11
        >>> get_max_workers(8)     # Use specified
        8
    """
    if config_value is None or config_value == 0:
        return DEFAULT_MAX_WORKERS
    return max(1, config_value)


# =============================================================================
# Default Values
# =============================================================================

DEFAULTS: dict[str, Any] = {
    # -------------------------------------------------------------------------
    # Site Metadata
    # -------------------------------------------------------------------------
    "title": "Bengal Site",
    "baseurl": "",
    "description": "",
    "author": "",
    "language": "en",
    # -------------------------------------------------------------------------
    # Build Settings
    # -------------------------------------------------------------------------
    "output_dir": "public",
    "content_dir": "content",
    "assets_dir": "assets",
    "templates_dir": "templates",
    "parallel": True,
    "incremental": True,
    "max_workers": None,  # None = auto-detect via get_max_workers()
    "pretty_urls": True,
    "minify_html": True,
    "strict_mode": False,
    "debug": False,
    "validate_build": True,
    "validate_links": True,
    "transform_links": True,
    "cache_templates": True,
    "fast_writes": False,
    "fast_mode": False,
    "stable_section_references": True,
    "min_page_size": 1000,
    # -------------------------------------------------------------------------
    # Static Files
    # -------------------------------------------------------------------------
    # Files in static/ are copied verbatim to output root without processing.
    # Static HTML can link to /assets/css/style.css to use Bengal's theme.
    "static": {
        "enabled": True,  # Enable static folder support
        "dir": "static",  # Source directory (relative to site root)
    },
    # -------------------------------------------------------------------------
    # HTML Output
    # -------------------------------------------------------------------------
    "html_output": {
        "mode": "minify",  # minify | pretty | raw
        "remove_comments": True,
        "collapse_blank_lines": True,
    },
    # -------------------------------------------------------------------------
    # Assets
    # -------------------------------------------------------------------------
    "assets": {
        "minify": True,
        "optimize": True,
        "fingerprint": True,
        "pipeline": False,
    },
    # -------------------------------------------------------------------------
    # Theme
    # -------------------------------------------------------------------------
    "theme": {
        "name": "default",
        "default_appearance": "system",  # light | dark | system
        "default_palette": "",
        "features": [],
        "show_reading_time": True,
        "show_author": True,
        "show_prev_next": True,
        "show_children_default": True,
        "show_excerpts_default": True,
        "max_tags_display": 10,
        "popular_tags_count": 20,
    },
    # -------------------------------------------------------------------------
    # Content Processing
    # -------------------------------------------------------------------------
    "content": {
        "default_type": "doc",
        "excerpt_length": 200,
        "summary_length": 160,
        "reading_speed": 200,  # words per minute
        "related_count": 5,
        "related_threshold": 0.25,
        "toc_depth": 4,
        "toc_min_headings": 2,
        "toc_style": "nested",  # nested | flat
        "sort_pages_by": "weight",  # weight | date | title | modified
        "sort_order": "asc",  # asc | desc
    },
    # -------------------------------------------------------------------------
    # Search
    # -------------------------------------------------------------------------
    "search": {
        "enabled": True,
        "lunr": {
            "prebuilt": True,
            "min_query_length": 2,
            "max_results": 50,
            "preload": "smart",  # immediate | smart | lazy
        },
        "ui": {
            "modal": True,
            "recent_searches": 5,
            "placeholder": "Search documentation...",
        },
        "analytics": {
            "enabled": False,
            "event_endpoint": None,
        },
    },
    # -------------------------------------------------------------------------
    # Pagination
    # -------------------------------------------------------------------------
    "pagination": {
        "per_page": 10,
    },
    # -------------------------------------------------------------------------
    # Health Check
    # -------------------------------------------------------------------------
    "health_check": {
        "enabled": True,
        "verbose": False,
        "strict_mode": False,
        "orphan_threshold": 5,
        "super_hub_threshold": 50,
    },
    # -------------------------------------------------------------------------
    # Features (Output Generation)
    # -------------------------------------------------------------------------
    "features": {
        "rss": True,
        "sitemap": True,
        "search": True,
        "json": True,
        "llm_txt": True,
        "syntax_highlighting": True,
    },
    # -------------------------------------------------------------------------
    # Graph
    # -------------------------------------------------------------------------
    "graph": {
        "enabled": True,
        "path": "/graph/",
    },
    # -------------------------------------------------------------------------
    # i18n
    # -------------------------------------------------------------------------
    "i18n": {
        "strategy": None,
        "default_language": "en",
        "default_in_subdir": False,
    },
    # -------------------------------------------------------------------------
    # Output Formats
    # -------------------------------------------------------------------------
    "output_formats": {
        "enabled": True,
        "per_page": ["json"],
        "site_wide": ["index_json"],
        "options": {
            "excerpt_length": 200,
            "json_indent": None,
            "llm_separator_width": 80,
            "include_full_content_in_index": False,
            "exclude_sections": [],
            "exclude_patterns": ["404.html", "search.html"],
        },
    },
    # -------------------------------------------------------------------------
    # Markdown
    # -------------------------------------------------------------------------
    "markdown": {
        "parser": "mistune",
        "toc_depth": "2-4",
    },
}


def get_default(key: str, nested_key: str | None = None) -> Any:
    """
    Get default value for a config key.

    Args:
        key: Top-level config key (e.g., "max_workers", "theme")
        nested_key: Optional nested key using dot notation (e.g., "lunr.prebuilt")

    Returns:
        Default value, or None if key not found

    Example:
        >>> get_default("max_workers")
        None  # Means auto-detect
        >>> get_default("content", "excerpt_length")
        200
        >>> get_default("search", "lunr.prebuilt")
        True
        >>> get_default("theme", "name")
        'default'
    """
    value = DEFAULTS.get(key)

    if nested_key is None:
        return value

    if not isinstance(value, dict):
        return None

    # Handle dot-separated nested keys
    parts = nested_key.split(".")
    for part in parts:
        if not isinstance(value, dict):
            return None
        value = value.get(part)

    return value


def get_pagination_per_page(config_value: int | None = None) -> int:
    """
    Resolve pagination per_page with default.

    Args:
        config_value: User-configured value

    Returns:
        Items per page (default: 10, minimum: 1)
    """
    if config_value is None:
        return DEFAULTS["pagination"]["per_page"]
    return max(1, config_value)


# =============================================================================
# Bool/Dict Normalization
# =============================================================================

# Keys that can be either bool or dict
BOOL_OR_DICT_KEYS = frozenset(
    {
        "health_check",
        "search",
        "graph",
        "output_formats",
    }
)


def normalize_bool_or_dict(
    value: bool | dict[str, Any] | None,
    key: str,
    default_enabled: bool = True,
) -> dict[str, Any]:
    """
    Normalize config values that can be bool or dict.

    This standardizes handling of config keys like `health_check`, `search`,
    `graph`, etc. that accept both:
    - `key: false` (bool to disable)
    - `key: { enabled: true, ... }` (dict with options)

    Args:
        value: The config value (bool, dict, or None)
        key: The config key name (for defaults lookup)
        default_enabled: Whether the feature is enabled by default

    Returns:
        Normalized dict with 'enabled' key and any other options

    Examples:
        >>> normalize_bool_or_dict(False, "health_check")
        {'enabled': False}

        >>> normalize_bool_or_dict(True, "search")
        {'enabled': True, 'lunr': {'prebuilt': True, ...}, 'ui': {...}}

        >>> normalize_bool_or_dict({'verbose': True}, "health_check")
        {'enabled': True, 'verbose': True}

        >>> normalize_bool_or_dict(None, "graph")
        {'enabled': True, 'path': '/graph/'}
    """
    # Get defaults for this key if available
    key_defaults = DEFAULTS.get(key, {})
    if not isinstance(key_defaults, dict):
        key_defaults = {"enabled": default_enabled}

    if value is None:
        # Use defaults
        result = dict(key_defaults)
        if "enabled" not in result:
            result["enabled"] = default_enabled
        return result

    if isinstance(value, bool):
        # Convert bool to dict with enabled flag
        result = dict(key_defaults)
        result["enabled"] = value
        return result

    if isinstance(value, dict):
        # Merge with defaults, user values take precedence
        result = dict(key_defaults)
        result.update(value)
        # Ensure 'enabled' exists
        if "enabled" not in result:
            result["enabled"] = default_enabled
        return result

    # Fallback for unexpected types
    return {"enabled": default_enabled}


def is_feature_enabled(
    config: dict[str, Any],
    key: str,
    default: bool = True,
) -> bool:
    """
    Check if a bool/dict config feature is enabled.

    Convenience function for quick enable/disable checks without
    needing the full normalized dict.

    Args:
        config: The site config dictionary
        key: The config key to check (e.g., "health_check", "search")
        default: Default value if key not present

    Returns:
        True if feature is enabled, False otherwise

    Examples:
        >>> is_feature_enabled({"health_check": False}, "health_check")
        False

        >>> is_feature_enabled({"search": {"enabled": True}}, "search")
        True

        >>> is_feature_enabled({}, "graph")  # Not in config
        True  # Default is True
    """
    value = config.get(key)

    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, dict):
        return value.get("enabled", default)

    return default


def get_feature_config(
    config: dict[str, Any],
    key: str,
    default_enabled: bool = True,
) -> dict[str, Any]:
    """
    Get normalized config for a bool/dict feature.

    This is the main entry point for accessing features that can be
    configured as either bool or dict.

    Args:
        config: The site config dictionary
        key: The config key (e.g., "health_check", "search", "graph")
        default_enabled: Whether the feature is enabled by default

    Returns:
        Normalized dict with 'enabled' key and feature options

    Examples:
        >>> cfg = get_feature_config({"health_check": False}, "health_check")
        >>> cfg["enabled"]
        False

        >>> cfg = get_feature_config({"search": {"ui": {"modal": False}}}, "search")
        >>> cfg["enabled"]
        True
        >>> cfg["ui"]["modal"]
        False
    """
    return normalize_bool_or_dict(
        config.get(key),
        key,
        default_enabled,
    )
