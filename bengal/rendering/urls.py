"""
Centralized URL generation for all template engines.

This module provides a single source of truth for URL generation functions
that need consistent behavior across all template engines:

- resolve_asset_url: Asset URLs with fingerprinting
- resolve_tag_url: Tag URLs with i18n prefix support
- resolve_relative_url: Relative URLs with baseurl

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

if TYPE_CHECKING:
    from bengal.core.site import Site

__all__ = [
    "resolve_asset_url",
    "resolve_tag_url",
    "apply_baseurl",
]


def resolve_tag_url(tag: str, site: Site, page: Any = None) -> str:
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


def apply_baseurl(path: str, site: Site) -> str:
    """
    Apply baseurl prefix to a path.

    Handles various baseurl formats:
    - Path prefix: /bengal
    - Absolute URL: https://example.com
    - File protocol: file:///path

    Args:
        path: Relative path (e.g., '/tags/python/')
        site: Site instance

    Returns:
        URL with baseurl applied
    """
    baseurl = (site.config.get("baseurl", "") or "").rstrip("/")

    if not baseurl:
        return path

    if not path.startswith("/"):
        path = "/" + path

    if baseurl.startswith(("http://", "https://", "file://")):
        return f"{baseurl}{path}"
    else:
        base_path = "/" + baseurl.lstrip("/")
        return f"{base_path}{path}"
