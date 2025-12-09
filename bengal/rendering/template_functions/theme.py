"""
Theme-related template functions and filters.

Provides filters and functions for accessing theme configuration in templates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site


def feature_enabled(feature: str, theme_config: Any) -> bool:
    """
    Check if a theme feature is enabled.

    Args:
        feature: Feature key in dotted notation (e.g., "navigation.toc")
        theme_config: Theme configuration object (from site.theme_config)

    Returns:
        True if feature is enabled

    Example:
        {{ 'navigation.toc' | feature_enabled(site.theme_config) }}
    """
    if not theme_config:
        return False
    return theme_config.has_feature(feature)


def register(env: Environment, site: Site) -> None:
    """
    Register theme-related template functions and filters.

    Args:
        env: Jinja2 environment
        site: Site instance
    """

    # Register feature_enabled filter
    # Note: We need to create a closure that captures site.theme_config
    def feature_enabled_filter(feature: str) -> bool:
        """Filter version that uses site.theme_config automatically."""
        return feature_enabled(feature, site.theme_config)

    env.filters["feature_enabled"] = feature_enabled_filter

    # Also register as a global function for explicit usage
    env.globals["feature_enabled"] = feature_enabled_filter
