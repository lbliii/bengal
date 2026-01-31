"""
URL manipulation utilities for rendering.

Provides the single source of truth for URL operations including
baseurl application and path normalization.

Usage:
    from bengal.rendering.utils.url import apply_baseurl

    url = apply_baseurl("/docs/page/", site)
    # Returns "/bengal/docs/page/" when baseurl="/bengal"
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.protocols import SiteLike

logger = get_logger(__name__)


def apply_baseurl(path: str, site: SiteLike | Any) -> str:
    """
    Apply baseurl prefix to a site-relative path.

    This is the single source of truth for baseurl application.
    Handles all baseurl formats including path-only, absolute URLs,
    and file:// protocol.

    Args:
        path: Site-relative path starting with '/' (e.g., "/docs/page/")
        site: Site instance for baseurl config lookup. Can be SiteLike
              protocol or any object with a baseurl attribute.

    Returns:
        Public URL with baseurl prefix (e.g., "/bengal/docs/page/")

    Examples:
        # Path-only baseurl
        >>> apply_baseurl("/docs/page/", site)  # baseurl="/bengal"
        '/bengal/docs/page/'

        # Absolute baseurl
        >>> apply_baseurl("/docs/page/", site)  # baseurl="https://example.com"
        'https://example.com/docs/page/'

        # Empty baseurl
        >>> apply_baseurl("/docs/page/", site)  # baseurl=""
        '/docs/page/'

        # File protocol
        >>> apply_baseurl("/docs/page/", site)  # baseurl="file:///path"
        'file:///path/docs/page/'

    Note:
        Handles various baseurl formats:
        - Path-only: "/bengal" → "/bengal/docs/page/"
        - Absolute: "https://example.com" → "https://example.com/docs/page/"
        - File: "file:///path" → "file:///path/docs/page/"
        - Empty: "" → "/docs/page/" (no change)

    """
    # Ensure path starts with '/'
    if not path.startswith("/"):
        path = "/" + path

    # Get baseurl from site with error handling
    baseurl_value = _get_baseurl(site)

    if not baseurl_value:
        return path

    # Handle absolute URLs (http://, https://, file://)
    if baseurl_value.startswith(("http://", "https://", "file://")):
        return f"{baseurl_value}{path}"

    # Path-only baseurl (e.g., /bengal)
    base_path = "/" + baseurl_value.lstrip("/")
    return f"{base_path}{path}"


def _get_baseurl(site: SiteLike | Any) -> str:
    """
    Extract baseurl from site object with error handling.

    Args:
        site: Site instance or any object with baseurl attribute

    Returns:
        Baseurl string, stripped of trailing slashes. Empty string if not found.
    """
    try:
        raw_baseurl = getattr(site, "baseurl", "") if site is not None else ""

        # Guard against mocks/non-strings
        if raw_baseurl is None or not isinstance(raw_baseurl, str):
            raw_baseurl = ""

        baseurl_value = raw_baseurl.rstrip("/")

        # Treat "/" as empty (root-relative)
        if baseurl_value == "/":
            baseurl_value = ""

        return baseurl_value

    except Exception as e:
        logger.debug(
            "baseurl_access_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="using_empty_baseurl",
        )
        return ""


def normalize_url_path(path: str) -> str:
    """
    Normalize a URL path for consistent handling.

    Ensures path starts with '/' and removes duplicate slashes.

    Args:
        path: URL path to normalize

    Returns:
        Normalized path starting with '/'

    Examples:
        >>> normalize_url_path("docs/page/")
        '/docs/page/'
        >>> normalize_url_path("//docs//page//")
        '/docs/page/'
        >>> normalize_url_path("")
        '/'

    """
    if not path:
        return "/"

    # Ensure leading slash
    if not path.startswith("/"):
        path = "/" + path

    # Remove duplicate slashes (but preserve protocol slashes)
    import re

    path = re.sub(r"(?<!:)//+", "/", path)

    return path
