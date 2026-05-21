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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

# Re-export asset URL for convenience
from bengal.rendering.assets import resolve_asset_url

# Re-export URL utilities from consolidated module
from bengal.rendering.utils.url import apply_baseurl

if TYPE_CHECKING:
    from bengal.protocols import SiteLike

__all__ = [
    "RenderURLContext",
    "apply_baseurl",
    "resolve_asset_url",
    "resolve_tag_url",
    "url_for",
    "url_for_path",
]


@dataclass(frozen=True, slots=True)
class RenderURLContext:
    """
    Per-render URL context for resolving generated links.

    Git-backed versioned builds check out each version into the same content
    paths, so section URLs cannot be correct without knowing which version is
    being rendered. This context carries that render-local state while keeping
    core Page and Section objects passive.
    """

    site: SiteLike | Any
    page: Any = None
    version_id: str | None = None
    language: str | None = None

    @classmethod
    def for_page(cls, site: SiteLike | Any, page: Any = None) -> RenderURLContext:
        """Create URL context from a site and optional current page."""
        version_id = getattr(page, "version", None) if page is not None else None
        if version_id is None:
            version_id = _site_current_version_id(site)
        language = getattr(page, "lang", None) or getattr(site, "current_language", None)
        return cls(site=site, page=page, version_id=version_id, language=language)


def url_for(
    target: Any,
    context: RenderURLContext,
    *,
    version: str | None = "current",
    baseurl: bool = True,
) -> str:
    """
    Resolve a generated URL for a target in a render context.

    Args:
        target: Page, Section, SectionSnapshot, PageSnapshot, or string path.
        context: Current render URL context.
        version: "current", "latest", an explicit version id, or None.
        baseurl: Apply the site's configured baseurl when true.

    Returns:
        Template-ready URL when baseurl is true, otherwise a site-relative path.
    """
    if target is None:
        return ""

    site = context.site or getattr(target, "_site", None)
    if isinstance(target, str):
        path = _normalize_literal_url(target, site)
    elif _looks_like_section(target):
        from bengal.rendering.section_urls import get_path_for_version

        version_id = _resolve_version_id(context, target, version)
        path = get_path_for_version(target, version_id, site)
    else:
        path = _object_site_path(target, site)

    if not baseurl or _is_special_url(path):
        return path
    return apply_baseurl(path, site)


def url_for_path(
    path: str,
    context: RenderURLContext,
    *,
    baseurl: bool = True,
) -> str:
    """Resolve a literal template path without applying version rewrites."""
    return url_for(path, context, version=None, baseurl=baseurl)


def _resolve_version_id(context: RenderURLContext, target: Any, version: str | None) -> str | None:
    if version is None:
        return None
    if version == "current":
        return getattr(target, "version", None) or context.version_id
    if version == "latest":
        return _site_latest_version_id(context.site)
    return version


def _site_current_version_id(site: SiteLike | Any) -> str | None:
    current = getattr(site, "current_version", None)
    if isinstance(current, dict):
        value = current.get("id")
        return str(value) if value else None
    value = getattr(current, "id", None)
    return str(value) if value else None


def _site_latest_version_id(site: SiteLike | Any) -> str | None:
    version_config = getattr(site, "version_config", None)
    latest = getattr(version_config, "latest_version", None)
    if latest is not None:
        value = getattr(latest, "id", None)
        return str(value) if value else None

    latest_dict = getattr(site, "latest_version", None)
    if isinstance(latest_dict, dict):
        value = latest_dict.get("id")
        return str(value) if value else None
    return None


def _looks_like_section(target: Any) -> bool:
    return hasattr(target, "subsections") or hasattr(target, "sorted_subsections")


def _object_site_path(target: Any, site: SiteLike | Any) -> str:
    path = getattr(target, "_path", None) or getattr(target, "href", None) or "/"
    if not isinstance(path, str):
        return "/"
    return _strip_baseurl(path, site)


def _normalize_literal_url(path: str, site: SiteLike | Any) -> str:
    if not path:
        return ""
    if _is_special_url(path):
        return path
    return _strip_baseurl(path, site)


def _strip_baseurl(path: str, site: SiteLike | Any) -> str:
    if not path.startswith("/"):
        return path

    baseurl = _site_baseurl(site)
    if baseurl and path.startswith(f"{baseurl}/"):
        return path[len(baseurl) :]
    if baseurl and path == baseurl:
        return "/"
    return path


def _site_baseurl(site: SiteLike | Any) -> str:
    value = getattr(site, "baseurl", "") if site is not None else ""
    if not isinstance(value, str):
        return ""
    value = value.rstrip("/")
    if not value or value == "/":
        return ""
    if not value.startswith(("/", "//")) and not urlsplit(value).scheme:
        return f"/{value}"
    return value


def _is_special_url(path: str) -> bool:
    return path.startswith(("#", "//")) or bool(urlsplit(path).scheme)


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
