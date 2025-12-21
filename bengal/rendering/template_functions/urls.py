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

    def href_filter(path: str) -> str:
        """Apply baseurl to path. For manual paths in templates."""
        from bengal.rendering.template_engine.url_helpers import with_baseurl

        return with_baseurl(path, site)

    env.filters.update(
        {
            "absolute_url": absolute_url_with_site,
            "url": absolute_url_with_site,
            "href": href_filter,
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
    Detects file URLs (with extensions) and does not add trailing slashes to them.

    Args:
        url: Relative or absolute URL
        base_url: Base URL to prepend

    Returns:
        Absolute URL

    Example:
        {{ page.href | absolute_url }}
        # Output: https://example.com/posts/my-post/
        {{ '/index.json' | absolute_url }}
        # Output: /index.json (no trailing slash for file URLs)
    """
    from bengal.utils.url_normalization import normalize_url

    if not url:
        return base_url or ""

    # Already absolute (http://, https://, //)
    if url.startswith(("http://", "https://", "//")):
        return url

    # Normalize base URL
    base_url = base_url.rstrip("/") if base_url else ""

    # Detect if this is a file URL (has a file extension)
    # File URLs should NOT get trailing slashes
    # Common file extensions: .json, .xml, .txt, .js, .css, .html, etc.
    last_segment = url.rsplit("/", 1)[-1] if "/" in url else url
    has_file_extension = "." in last_segment and not last_segment.startswith(".")

    # Normalize relative URL - don't add trailing slash for file URLs
    normalized_url = normalize_url(url, ensure_trailing_slash=not has_file_extension)

    # Combine URLs
    # If base_url is empty or just "/", use normalized_url directly
    if not base_url or base_url == "/":
        return normalized_url

    # If normalized_url already starts with base_url, don't duplicate it
    if normalized_url.startswith(base_url):
        return normalized_url

    # Combine and normalize again to handle any edge cases
    result = base_url + normalized_url
    return normalize_url(result, ensure_trailing_slash=not has_file_extension)


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
