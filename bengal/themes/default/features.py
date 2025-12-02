"""
Default theme feature registry.

Each feature has:
- key: Dotted namespace string (e.g., "navigation.breadcrumbs")
- description: Human-readable description
- default: Whether enabled by default (optional, defaults to False)
- category: Category for grouping in CLI output

Feature flags allow users to declaratively enable/disable theme behaviors
via config rather than editing templates.

Example:
    [theme]
    features = [
        "navigation.breadcrumbs",
        "navigation.toc",
        "content.code.copy",
    ]

Templates check features via:
    {% if 'navigation.toc' in site.theme_config.features %}
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureInfo:
    """
    Information about a theme feature.

    Attributes:
        key: Dotted namespace string (e.g., "navigation.breadcrumbs")
        description: Human-readable description of what the feature does
        default: Whether this feature is enabled by default
        category: Category for grouping (navigation, content, search, etc.)
    """

    key: str
    description: str
    default: bool = False
    category: str = "general"


# Registry of available features for the default theme
# Organized by category for easier maintenance
FEATURES: dict[str, FeatureInfo] = {
    # ============================================================
    # Navigation Features
    # ============================================================
    "navigation.breadcrumbs": FeatureInfo(
        key="navigation.breadcrumbs",
        description="Show breadcrumb trail above content",
        default=True,
        category="navigation",
    ),
    "navigation.toc": FeatureInfo(
        key="navigation.toc",
        description="Show table of contents sidebar",
        default=True,
        category="navigation",
    ),
    "navigation.toc.sticky": FeatureInfo(
        key="navigation.toc.sticky",
        description="Make TOC sticky when scrolling",
        default=True,
        category="navigation",
    ),
    "navigation.prev_next": FeatureInfo(
        key="navigation.prev_next",
        description="Show previous/next page links at bottom",
        default=True,
        category="navigation",
    ),
    "navigation.tabs": FeatureInfo(
        key="navigation.tabs",
        description="Use tabs for top-level navigation sections",
        default=False,
        category="navigation",
    ),
    "navigation.back_to_top": FeatureInfo(
        key="navigation.back_to_top",
        description="Show back-to-top button when scrolling",
        default=True,
        category="navigation",
    ),
    # ============================================================
    # Content Features
    # ============================================================
    "content.code.copy": FeatureInfo(
        key="content.code.copy",
        description="Add copy button to code blocks",
        default=True,
        category="content",
    ),
    "content.code.annotate": FeatureInfo(
        key="content.code.annotate",
        description="Enable code annotation markers",
        default=False,
        category="content",
    ),
    "content.tabs.link": FeatureInfo(
        key="content.tabs.link",
        description="Link content tabs across page (sync selection)",
        default=False,
        category="content",
    ),
    "content.lightbox": FeatureInfo(
        key="content.lightbox",
        description="Enable image lightbox on click",
        default=True,
        category="content",
    ),
    # ============================================================
    # Search Features
    # ============================================================
    "search.suggest": FeatureInfo(
        key="search.suggest",
        description="Show search suggestions as you type",
        default=True,
        category="search",
    ),
    "search.highlight": FeatureInfo(
        key="search.highlight",
        description="Highlight search terms on result pages",
        default=True,
        category="search",
    ),
    "search.share": FeatureInfo(
        key="search.share",
        description="Enable search result sharing via URL",
        default=False,
        category="search",
    ),
    # ============================================================
    # Header Features
    # ============================================================
    "header.autohide": FeatureInfo(
        key="header.autohide",
        description="Auto-hide header when scrolling down",
        default=False,
        category="header",
    ),
    # ============================================================
    # Footer Features
    # ============================================================
    "footer.social": FeatureInfo(
        key="footer.social",
        description="Show social links in footer",
        default=True,
        category="footer",
    ),
    # ============================================================
    # Accessibility Features
    # ============================================================
    "accessibility.skip_link": FeatureInfo(
        key="accessibility.skip_link",
        description="Add skip-to-content link for keyboard users",
        default=True,
        category="accessibility",
    ),
}


def get_default_features() -> list[str]:
    """
    Get list of feature keys that are enabled by default.

    Returns:
        List of feature keys (e.g., ["navigation.toc", "content.code.copy"])

    Example:
        >>> defaults = get_default_features()
        >>> "navigation.toc" in defaults
        True
        >>> "navigation.tabs" in defaults
        False
    """
    return [key for key, info in FEATURES.items() if info.default]


def validate_features(features: list[str]) -> list[str]:
    """
    Validate feature list and return unknown features.

    Args:
        features: List of feature keys to validate

    Returns:
        List of unknown feature keys (empty if all valid)

    Example:
        >>> validate_features(["navigation.toc", "invalid.feature"])
        ['invalid.feature']
        >>> validate_features(["navigation.toc", "content.code.copy"])
        []
    """
    return [f for f in features if f not in FEATURES]


def get_features_by_category() -> dict[str, list[FeatureInfo]]:
    """
    Get features grouped by category.

    Returns:
        Dictionary mapping category names to list of FeatureInfo objects

    Example:
        >>> by_cat = get_features_by_category()
        >>> "navigation" in by_cat
        True
        >>> len(by_cat["navigation"]) > 0
        True
    """
    categories: dict[str, list[FeatureInfo]] = {}
    for info in FEATURES.values():
        if info.category not in categories:
            categories[info.category] = []
        categories[info.category].append(info)
    return categories


def get_feature_info(feature: str) -> FeatureInfo | None:
    """
    Get information about a specific feature.

    Args:
        feature: Feature key (e.g., "navigation.toc")

    Returns:
        FeatureInfo object if found, None otherwise

    Example:
        >>> info = get_feature_info("navigation.toc")
        >>> info.description
        'Show table of contents sidebar'
    """
    return FEATURES.get(feature)


def get_all_feature_keys() -> list[str]:
    """
    Get all available feature keys.

    Returns:
        List of all feature keys in alphabetical order

    Example:
        >>> keys = get_all_feature_keys()
        >>> "navigation.toc" in keys
        True
    """
    return sorted(FEATURES.keys())
