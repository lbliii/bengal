"""
URL manipulation functions for templates.

Provides 4 functions for working with URLs in templates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote, unquote

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site


def register(env: Environment, site: Site) -> None:
    """Register URL functions with Jinja2 environment."""

    # Create closures that have access to site
    def absolute_url_with_site(url: str) -> str:
        return absolute_url(url, site.config.get("baseurl", ""))

    env.filters.update(
        {
            "absolute_url": absolute_url_with_site,
            "url": absolute_url_with_site,
            "url_encode": url_encode,
            "url_decode": url_decode,
        }
    )

    env.globals.update(
        {
            "ensure_trailing_slash": ensure_trailing_slash,
        }
    )


def absolute_url(url: str, base_url: str) -> str:
    """
    Convert relative URL to absolute URL.

    Uses centralized URL normalization to ensure consistency.

    Args:
        url: Relative or absolute URL
        base_url: Base URL to prepend

    Returns:
        Absolute URL

    Example:
        {{ page.url | absolute_url }}
        # Output: https://example.com/posts/my-post/
    """
    from bengal.utils.url_normalization import normalize_url

    if not url:
        return base_url or ""

    # Already absolute (http://, https://, //)
    if url.startswith(("http://", "https://", "//")):
        return url

    # Normalize base URL
    base_url = base_url.rstrip("/") if base_url else ""

    # Normalize relative URL first
    normalized_url = normalize_url(url, ensure_trailing_slash=True)

    # Combine URLs
    # If base_url is empty or just "/", use normalized_url directly
    if not base_url or base_url == "/":
        return normalized_url

    # If normalized_url already starts with base_url, don't duplicate it
    if normalized_url.startswith(base_url):
        return normalized_url

    # Combine and normalize again to handle any edge cases
    result = base_url + normalized_url
    return normalize_url(result, ensure_trailing_slash=True)


def url_encode(text: str) -> str:
    """
    URL encode string (percent encoding).

    Encodes special characters for safe use in URLs.

    Args:
        text: Text to encode

    Returns:
        URL-encoded text

    Example:
        {{ search_query | url_encode }}
        # "hello world" -> "hello%20world"
    """
    if not text:
        return ""

    return quote(str(text))


def url_decode(text: str) -> str:
    """
    URL decode string (decode percent encoding).

    Decodes percent-encoded characters back to original form.

    Args:
        text: Text to decode

    Returns:
        URL-decoded text

    Example:
        {{ encoded_text | url_decode }}
        # "hello%20world" -> "hello world"
    """
    if not text:
        return ""

    return unquote(str(text))


def ensure_trailing_slash(url: str) -> str:
    """
    Ensure URL ends with a trailing slash.

    This is useful for constructing URLs to index files or ensuring
    consistent URL formatting.

    Args:
        url: URL to process

    Returns:
        URL with trailing slash

    Example:
        {{ page_url | ensure_trailing_slash }}
        # "https://example.com/docs" -> "https://example.com/docs/"
        # "https://example.com/docs/" -> "https://example.com/docs/"
    """
    if not url:
        return "/"

    return url if url.endswith("/") else url + "/"
