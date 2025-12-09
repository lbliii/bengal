"""
URL generation helpers for template engine.

Provides URL generation functions for pages and assets with baseurl support.

Related Modules:
    - bengal.rendering.template_engine.core: Uses these helpers
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


def url_for(page: Page | Mapping[str, Any] | Any, site: Site) -> str:
    """
    Generate URL for a page with base URL support.

    Args:
        page: Page object
        site: Site instance

    Returns:
        URL path (clean, without index.html) with base URL prefix if configured
    """
    url = None

    # Use the page's relative_url property (doesn't include baseurl)
    try:
        if hasattr(page, "relative_url"):
            url = page.relative_url
    except Exception as e:
        logger.debug(
            "url_for_relative_url_access_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="trying_url_fallback",
        )
        pass

    # Fallback to page.url if relative_url not available
    if url is None:
        try:
            if hasattr(page, "url"):
                url = page.url
                # If url already includes baseurl, extract relative part
                baseurl = (site.config.get("baseurl", "") or "").rstrip("/")
                if baseurl and url.startswith(baseurl):
                    url = url[len(baseurl) :] or "/"
        except Exception as e:
            logger.debug(
                "url_for_url_access_failed",
                error=str(e),
                error_type=type(e).__name__,
                action="trying_dict_fallback",
            )
            pass

    # Support dict-like contexts (component preview/demo data)
    if url is None:
        try:
            if isinstance(page, Mapping):
                if "url" in page:
                    url = str(page["url"])
                elif "relative_url" in page:
                    url = str(page["relative_url"])
                elif "slug" in page:
                    url = f"/{page['slug']}/"
        except Exception as e:
            logger.debug(
                "url_for_dict_access_failed",
                error=str(e),
                error_type=type(e).__name__,
                action="trying_slug_fallback",
            )
            pass

    # Fallback to slug-based URL for objects
    if url is None:
        try:
            if hasattr(page, "slug"):
                url = f"/{page.slug}/"
        except Exception as e:
            logger.debug(
                "url_for_slug_access_failed",
                error=str(e),
                error_type=type(e).__name__,
                action="using_root_fallback",
            )
            if url is None:
                url = "/"

    # Ensure url is never None (type narrowing)
    if url is None:
        url = "/"

    return with_baseurl(url, site)


def with_baseurl(path: str, site: Site) -> str:
    """
    Apply base URL prefix to a path.

    Args:
        path: Relative path starting with '/'
        site: Site instance

    Returns:
        Path with base URL prefix (absolute or path-only)
    """
    # Ensure path starts with '/'
    if not path.startswith("/"):
        path = "/" + path

    # Get baseurl from config
    try:
        baseurl_value = (site.config.get("baseurl", "") or "").rstrip("/")
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
