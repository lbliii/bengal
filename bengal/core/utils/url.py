"""
URL building utilities.

Provides helpers for URL construction and baseurl application.
Used by Page, Section, and Asset models for generating template-ready URLs.

Functions:
    apply_baseurl: Prepend baseurl to a site-relative path
    get_baseurl: Extract baseurl from config or site object

"""

from __future__ import annotations

from typing import Any


def apply_baseurl(path: str, baseurl: str | None) -> str:
    """
    Apply baseurl prefix to a site-relative path.

    Handles edge cases:
    - Empty or "/" baseurl: returns path unchanged
    - Normalizes slashes to prevent double-slashes
    - Ensures path starts with /

    Args:
        path: Site-relative path (e.g., "/docs/guide/")
        baseurl: Base URL prefix (e.g., "/bengal" or "https://example.com")

    Returns:
        Full URL with baseurl applied

    Example:
        >>> apply_baseurl("/docs/guide/", "/bengal")
        '/bengal/docs/guide/'
        >>> apply_baseurl("/docs/guide/", "")
        '/docs/guide/'
        >>> apply_baseurl("/docs/guide/", None)
        '/docs/guide/'
    """
    # Normalize baseurl
    if not baseurl or baseurl == "/":
        return path

    baseurl = baseurl.rstrip("/")

    # Ensure path starts with /
    if not path.startswith("/"):
        path = "/" + path

    return f"{baseurl}{path}"


def get_baseurl(site_or_config: Any) -> str:
    """
    Extract baseurl from a site object or config dict.

    Handles multiple config structures:
    - Site object with config attribute
    - Config object with site.baseurl
    - Dict with nested site.baseurl
    - Dict with flat baseurl

    Args:
        site_or_config: Site object, Config object, or dict

    Returns:
        Baseurl string (empty string if not configured)

    Example:
        >>> get_baseurl(site)
        '/bengal'
        >>> get_baseurl({"site": {"baseurl": "/docs"}})
        '/docs'
    """
    # Handle Site object
    config = site_or_config.config if hasattr(site_or_config, "config") else site_or_config

    # Try Config object attribute access
    if hasattr(config, "site"):
        site_attr = getattr(config, "site", None)
        if site_attr is not None:
            baseurl = getattr(site_attr, "baseurl", None)
            if baseurl is not None:
                return str(baseurl)

    # Try dict access - flat first (allows runtime overrides)
    if hasattr(config, "get"):
        flat_baseurl = config.get("baseurl")
        if flat_baseurl is not None:
            return str(flat_baseurl)

        # Try nested site.baseurl
        site_section = config.get("site", {})
        if isinstance(site_section, dict):
            baseurl = site_section.get("baseurl")
            if baseurl is not None:
                return str(baseurl)

    return ""


def get_site_origin(site_or_config: Any) -> str:
    """
    Extract absolute site origin for share URLs and meta tags.

    Uses url if set, else baseurl when it is absolute (starts with http).
    Returns empty string when no absolute origin is configured.

    Args:
        site_or_config: Site object or config dict

    Returns:
        Absolute origin (e.g. "https://example.com") or ""
    """
    config = site_or_config.config if hasattr(site_or_config, "config") else site_or_config

    # Prefer explicit url (Hugo-style)
    url = None
    if hasattr(config, "get"):
        url = config.get("url")
        if not url:
            site_section = config.get("site")
            if isinstance(site_section, dict):
                url = site_section.get("url")
            elif hasattr(site_section, "url"):
                url = getattr(site_section, "url", None)
    if url and isinstance(url, str) and url.strip().lower().startswith(("http://", "https://")):
        return url.strip().rstrip("/")

    # Fallback: baseurl when absolute
    baseurl = get_baseurl(site_or_config)
    if baseurl.strip().lower().startswith(("http://", "https://")):
        return baseurl.strip().rstrip("/")

    return ""
