"""
URL generation helpers for template engine.

Provides URL generation functions for pages and assets with baseurl support.

URL NAMING CONVENTION:
======================
Bengal uses explicit naming to prevent path/URL confusion across the codebase:

- `_path`: Site-relative path WITHOUT baseurl (internal use only)
  Example: "/docs/getting-started/"
  Use for: Internal lookups, comparisons, active trail detection, caching
  Note: Underscore prefix signals "internal only" to AI assistants

- `href`: Public URL WITH baseurl applied (for templates)
  Example: "/bengal/docs/getting-started/" (when baseurl="/bengal")
  Use for: Template href attributes, external links

TEMPLATE USAGE:
---------------
In templates, always use .href for href attributes:

    <a href="{{ page.href }}">{{ page.title }}</a>          {# Correct #}
    <a href="{{ item.href }}">{{ item.title }}</a>          {# Correct #}

The .href property automatically includes baseurl when configured.

HELPER FUNCTIONS:
-----------------
- href_for(obj, site): Get public URL for any page-like object (preferred)
- with_baseurl(path, site): Apply baseurl to a site-relative path

Related Modules:
    - bengal.core.nav_tree: NavNodeProxy provides .href (with baseurl) and ._path (without)
    - bengal.core.page: Page.href includes baseurl, Page._path does not
    - bengal.core.section: Same pattern as Page
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


def href_for(obj: Page | Mapping[str, Any] | Any, site: Site) -> str:
    """
    Get href for any object. Prefer obj.href directly.

    This is the recommended way to get URLs in template functions and filters.
    The returned URL includes baseurl and is ready for use in href attributes.

    Args:
        obj: Page, Section, Asset, NavNodeProxy, or dict-like object with href/_path

    Returns:
        Public URL with baseurl prefix (e.g., "/bengal/docs/page/")

    Example:
        # In template function
        return href_for(related_page, site)  # Returns "/bengal/docs/related/"

    Note:
        For Page/Section/Asset objects, prefer obj.href directly, which already
        includes baseurl. This function is useful for handling various
        page-like objects consistently.
    """
    # Use href property
    return obj.href


def with_baseurl(path: str, site: Site) -> str:
    """
    Apply baseurl prefix to a site-relative path.

    Converts a site_path (without baseurl) to a public URL (with baseurl).

    Args:
        path: Site-relative path starting with '/' (e.g., "/docs/page/")
        site: Site instance for baseurl config lookup

    Returns:
        Public URL with baseurl prefix (e.g., "/bengal/docs/page/")

    Example:
        # Convert site_path to public URL
        public_url = with_baseurl("/docs/getting-started/", site)
        # Returns "/bengal/docs/getting-started/" when baseurl="/bengal"

    Note:
        Handles all baseurl formats:
        - Path-only: "/bengal" → "/bengal/docs/page/"
        - Absolute: "https://example.com" → "https://example.com/docs/page/"
        - Empty: "" → "/docs/page/" (no change)
    """
    # Ensure path starts with '/'
    if not path.startswith("/"):
        path = "/" + path

    # Get baseurl from config
    try:
        baseurl_value = (site.config.get("baseurl", "") or "").rstrip("/")
        # Treat "/" as empty (root-relative)
        if baseurl_value == "/":
            baseurl_value = ""
    except Exception as e:
        logger.debug(
            "with_baseurl_config_access_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="using_empty_baseurl",
        )
        baseurl_value = ""

    if not baseurl_value:
        return path

    # Absolute baseurl (e.g., https://example.com/subpath, file:///...)
    if baseurl_value.startswith(("http://", "https://", "file://")):
        return f"{baseurl_value}{path}"

    # Path-only baseurl (e.g., /bengal)
    base_path = "/" + baseurl_value.lstrip("/")
    return f"{base_path}{path}"


def filter_dateformat(date: datetime | str | None, format: str = "%Y-%m-%d") -> str:
    """
    Format a date using strftime.

    Args:
        date: Date to format
        format: strftime format string

    Returns:
        Formatted date string
    """
    if date is None:
        return ""

    try:
        if isinstance(date, datetime):
            return str(date.strftime(format))
        return str(date)
    except (AttributeError, ValueError):
        return str(date)
