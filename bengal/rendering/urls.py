"""
Centralized URL generation for all template engines.

This module provides a single source of truth for URL generation functions
that need consistent behavior across all template engines:

- resolve_asset_url: Asset URLs with fingerprinting
- resolve_tag_url: Tag URLs with i18n prefix support
- apply_baseurl: Apply baseurl prefix to paths

Template engine adapters should use these instead of implementing their own logic.

Usage in adapters:
    from bengal.rendering.urls import resolve_asset_url, resolve_tag_url

    def asset_url(path: str) -> str:
        return resolve_asset_url(path, site, page)

    def tag_url(tag: str) -> str:
        return resolve_tag_url(tag, site, page)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Re-export asset URL for convenience
from bengal.rendering.assets import resolve_asset_url

# Re-export URL utilities from consolidated module
from bengal.rendering.utils.url import apply_baseurl

if TYPE_CHECKING:
    from bengal.protocols import SiteLike

__all__ = [
    "apply_baseurl",
    "resolve_asset_url",
    "resolve_tag_url",
]


def resolve_tag_url(tag: str, site: SiteLike, page: Any = None) -> str:
    """
    Generate a tag URL with i18n prefix support.

    This is the single source of truth for tag URL generation.
    Handles i18n prefixes and baseurl.

    Args:
        tag: Tag name
        site: Site instance
        page: Optional page context (for language detection)

    Returns:
        Tag URL ready for use in HTML

    Example:
            >>> resolve_tag_url('python', site)
            '/bengal/tags/python/'
            >>> resolve_tag_url('python', site, page)  # Page has lang='es'
            '/bengal/es/tags/python/'

    """
    from bengal.rendering.template_functions.taxonomies import tag_url as base_tag_url

    # Get locale-aware prefix
    i18n = site.config.get("i18n", {}) or {}
    strategy = i18n.get("strategy", "none")
    default_lang = i18n.get("default_language", "en")
    default_in_subdir = bool(i18n.get("default_in_subdir", False))
    lang = getattr(page, "lang", None) if page else None

    prefix = ""
    if strategy == "prefix" and lang and (default_in_subdir or lang != default_lang):
        prefix = f"/{lang}"

    # Generate tag URL
    relative_url = f"{prefix}{base_tag_url(tag)}"

    # Apply base URL prefix
    return apply_baseurl(relative_url, site)
