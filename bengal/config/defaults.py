"""
Single source of truth for all Bengal configuration defaults.

This module defines centralized default values for all configuration options
in Bengal. All configuration access should use these defaults via
:func:`get_default` or specialized helpers like :func:`get_max_workers`.

The ``DEFAULTS`` dictionary contains default values organized by category:
    - Site metadata (title, baseurl, description, author, language)
    - Build settings (output_dir, parallel, incremental, pretty_urls)
    - Static files configuration
    - HTML output formatting
    - Asset processing (minify, optimize, fingerprint)
    - Theme settings
    - Content processing options
    - Search configuration
    - Pagination settings
    - Health check validators and thresholds
    - Feature toggles (RSS, sitemap, search, JSON, llm_txt)
    - Graph visualization
    - Internationalization (i18n)
    - Output format options
    - Markdown parser configuration

Key Functions:
    get_default: Retrieve default value for any config key (supports nested keys).
    get_max_workers: Resolve worker count with CPU-based auto-detection.
    get_pagination_per_page: Resolve pagination items per page.
    normalize_bool_or_dict: Normalize config values that can be bool or dict.
    is_feature_enabled: Quick check if a feature is enabled.
    get_feature_config: Get normalized config for bool/dict features.

Example:
    >>> from bengal.config.defaults import get_default, get_max_workers
    >>> get_default("content", "excerpt_length")
    200
    >>> get_max_workers(None)  # Auto-detect based on CPU cores
    11

Note:
    This module avoids heavy dependencies for fast import time during builds.

See Also:
    - :mod:`bengal.config.loader`: Configuration loading from files.
    - :mod:`bengal.config.env_overrides`: Environment variable overrides.
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
    "validate_templates": False,  # Proactive template syntax validation during build
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
        "default_palette": "snow-lynx",
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
    # Tiered validation system:
    # - Tier 1 (build): Fast validators, always run (<100ms)
    # - Tier 2 (full): + Knowledge graph (~500ms, --full flag)
    # - Tier 3 (ci): + External link checking (~30s, --ci flag or CI env)
    # See: plan/active/rfc-build-integrated-validation.md
    "health_check": {
        "enabled": True,
        "verbose": False,
        "strict_mode": False,
        # Legacy thresholds (for backward compatibility)
        "orphan_threshold": 5,
        "super_hub_threshold": 50,
        # Semantic connectivity thresholds
        "isolated_threshold": 5,  # Max isolated pages before error
        "lightly_linked_threshold": 20,  # Max lightly-linked pages before warning
        # Connectivity level thresholds (weighted scores)
        "connectivity_thresholds": {
            "well_connected": 2.0,  # Score >= 2.0 = well connected
            "adequately_linked": 1.0,  # Score 1.0-2.0 = adequate
            "lightly_linked": 0.25,  # Score 0.25-1.0 = lightly linked
            # Score < 0.25 = isolated
        },
        # Link type weights for connectivity scoring
        "link_weights": {
            "explicit": 1.0,  # Human-authored markdown links
            "menu": 10.0,  # Navigation menu items
            "taxonomy": 1.0,  # Shared tags/categories
            "related": 0.75,  # Algorithm-computed related posts
            "topical": 0.5,  # Section hierarchy (parent → child)
            "sequential": 0.25,  # Next/prev navigation
        },
        # Tier 1: Always run (fast, <100ms)
        "build_validators": [
            "config",
            "output",
            "directives",
            "links",
            "rendering",
            "navigation",
            "menu",
            "taxonomy",
            "tracks",
        ],
        # Tier 2: Run with --full flag (~500ms)
        "full_validators": [
            "connectivity",
            "performance",
            "cache",
        ],
        # Tier 3: Run with --ci flag or in CI environment (~30s)
        "ci_validators": [
            "rss",
            "sitemap",
            "fonts",
            "assets",
        ],
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
        "ast_cache": {
            # Persist tokens into the parsed-content cache. This can increase cache size and
            # cold-build write time. Keep False until there is a stable downstream consumer.
            "persist_tokens": False,
        },
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
        config_value: User-configured value from site configuration.
            If ``None``, returns the default value from ``DEFAULTS``.

    Returns:
        Items per page (default: 10, minimum: 1).

    Example:
        >>> get_pagination_per_page(None)
        10
        >>> get_pagination_per_page(25)
        25
        >>> get_pagination_per_page(0)  # Clamped to minimum
        1
    """
    if config_value is None:
        pagination_defaults: dict[str, Any] = DEFAULTS.get("pagination", {})
        return int(pagination_defaults.get("per_page", 10))
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
        enabled_value: Any = value.get("enabled", default)
        return bool(enabled_value)

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
