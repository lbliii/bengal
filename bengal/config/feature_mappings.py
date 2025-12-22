"""
Feature group mappings for ergonomic configuration.

This module maps simple feature toggles (e.g., ``features.rss: true``) to
detailed configuration settings. This allows users to enable features with
a single boolean while Bengal expands them to the full configuration.

The feature expansion happens during configuration loading, before the
configuration is used by the build system.

Supported Features:
    - ``rss``: RSS feed generation
    - ``sitemap``: XML sitemap generation
    - ``search``: Site search functionality
    - ``json``: Per-page JSON output
    - ``llm_txt``: LLM-friendly text output
    - ``validate_links``: Link validation during build
    - ``minify_assets``: Asset minification
    - ``minify_html``: HTML output minification
    - ``syntax_highlighting``: Code syntax highlighting (reserved for future use)

Module Attributes:
    FEATURE_MAPPINGS: Dictionary mapping feature names to their expanded config.

Key Functions:
    expand_features: Expand feature toggles in a configuration dictionary.
    get_available_features: List all available feature names.
    get_feature_expansion: Get the expansion mapping for a specific feature.

Example:
    >>> config = {"features": {"rss": True, "search": True}}
    >>> expanded = expand_features(config)
    >>> expanded["generate_rss"]
    True
    >>> expanded["search"]["enabled"]
    True

Note:
    Feature expansion only sets values that aren't already explicitly
    configured, preserving user overrides.

See Also:
    - :mod:`bengal.config.directory_loader`: Calls expand_features during loading.
"""

from __future__ import annotations

from typing import Any

from bengal.config.merge import get_nested_key, set_nested_key

# Feature name → detailed config mapping
# Each feature maps to one or more config keys with their values
FEATURE_MAPPINGS: dict[str, dict[str, Any]] = {
    "rss": {
        "generate_rss": True,
        "output_formats.site_wide": ["rss"],
    },
    "sitemap": {
        "generate_sitemap": True,
    },
    "search": {
        "search.enabled": True,
        "search.preload": "smart",
        "output_formats.site_wide": ["index_json"],
    },
    "json": {
        "output_formats.per_page": ["json"],
    },
    "llm_txt": {
        "output_formats.per_page": ["llm_txt"],
    },
    "validate_links": {
        "validate_links": True,
        "health.linkcheck.enabled": True,
    },
    "minify_assets": {
        "assets.minify": True,
    },
    "minify_html": {
        "minify_html": True,
        "html_output.mode": "minify",
    },
    # NOTE: syntax_highlighting is reserved for future use.
    #       Currently always enabled - parser integration not yet wired to config.
    #       MistuneParser has enable_highlighting parameter but it's not threaded
    #       through create_markdown_parser() → _get_thread_parser() chain yet.
    #       See: bengal/rendering/parsers/mistune.py for parser implementation.
    # This mapping ensures config validation doesn't complain about the feature flag.
    "syntax_highlighting": {
        "syntax_highlighting.enabled": True,
    },
}


def expand_features(config: dict[str, Any]) -> dict[str, Any]:
    """
    Expand feature toggles to detailed configuration.

    Reads from config["features"] and expands to detailed config keys.
    Only sets values if they're not already explicitly configured.

    Args:
        config: Configuration dictionary (will be modified in place)

    Returns:
        Modified config dictionary (same object)

    Examples:
        >>> config = {"features": {"rss": True, "search": True}}
        >>> expand_features(config)
        {
            "generate_rss": True,
            "output_formats": {"site_wide": ["rss"]},
            "search": {"enabled": True, "preload": "smart"}
        }

        >>> # Explicit config overrides feature expansion
        >>> config = {
        ...     "features": {"search": True},
        ...     "search": {"enabled": True, "preload": "immediate"}
        ... }
        >>> expand_features(config)
        # search.preload stays "immediate" (not overridden to "smart")
    """
    if "features" not in config:
        return config

    features = config.pop("features")

    if not isinstance(features, dict):
        return config

    for feature_name, enabled in features.items():
        if not enabled:
            continue

        if feature_name not in FEATURE_MAPPINGS:
            # Unknown feature, ignore silently (or could warn)
            continue

        mapping = FEATURE_MAPPINGS[feature_name]

        for key_path, value in mapping.items():
            # _set_if_missing handles whether to set, append, or skip
            _set_if_missing(config, key_path, value)

    return config


def _set_if_missing(config: dict[str, Any], key_path: str, value: Any) -> None:
    """
    Set a nested key only if it doesn't already exist.

    This helper preserves explicit user configuration by only setting values
    that haven't been configured. For list values, it appends unique items
    to existing lists rather than replacing them.

    Args:
        config: Configuration dictionary to modify (mutated in place).
        key_path: Dot-separated path to the key (e.g., ``"search.enabled"``).
        value: Value to set if the key doesn't exist.

    Behavior:
        - **Missing key**: Sets the value.
        - **Existing list + list value**: Appends unique items from value.
        - **Existing primitive/dict**: Does nothing (preserves user config).
    """
    keys = key_path.split(".")
    existing = get_nested_key(config, key_path)

    if existing is None:
        # Key doesn't exist, set it
        set_nested_key(config, key_path, value)
    elif isinstance(existing, list) and isinstance(value, list):
        # Both lists: extend existing (avoid duplicates)
        # Navigate to parent
        current = config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                # Can't navigate non-dict, abort
                return
            current = current[key]

        final_key = keys[-1]

        # Append unique values to existing list
        if final_key in current and isinstance(current[final_key], list):
            for item in value:
                if item not in current[final_key]:
                    current[final_key].append(item)
    # else: key already exists and not a list, don't override


def get_available_features() -> list[str]:
    """
    Get list of available feature names.

    Returns:
        List of feature names that can be used in config

    Examples:
        >>> features = get_available_features()
        >>> "rss" in features
        True
        >>> "search" in features
        True
    """
    return sorted(FEATURE_MAPPINGS.keys())


def get_feature_expansion(feature_name: str) -> dict[str, Any] | None:
    """
    Get the detailed config mapping for a feature.

    Args:
        feature_name: Name of feature (e.g., "rss")

    Returns:
        Mapping dict, or None if feature unknown

    Examples:
        >>> get_feature_expansion("rss")
        {"generate_rss": True, "output_formats.site_wide": ["rss"]}
    """
    return FEATURE_MAPPINGS.get(feature_name)
