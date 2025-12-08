"""
Shared utilities for output format generation.

Provides common functions used across all output format generators
including text processing, URL handling, and path resolution.

Note:
    Text utilities delegate to bengal.utils.text for DRY compliance.
    See RFC: plan/active/rfc-code-quality-improvements.md
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger
from bengal.utils.text import normalize_whitespace
from bengal.utils.text import strip_html as _strip_html_base

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.core.page import Page


def strip_html(text: str) -> str:
    """
    Remove HTML tags from text and normalize whitespace.

    Delegates to bengal.utils.text.strip_html with additional whitespace
    normalization specific to output format generation.

    Args:
        text: HTML text

    Returns:
        Plain text with HTML tags, entities, and excess whitespace removed
    """
    if not text:
        return ""

    # Use canonical implementation for tag stripping and entity decoding
    text = _strip_html_base(text, decode_entities=True)

    # Normalize whitespace (specific to output formats - collapse to single space)
    return normalize_whitespace(text, collapse=True)


def generate_excerpt(text: str, length: int = 200) -> str:
    """
    Generate excerpt from text using character-based truncation.

    Note: This uses character-based truncation for backward compatibility
    with output format generation. For word-based truncation, use
    bengal.utils.text.generate_excerpt directly.

    Args:
        text: Source text (may contain HTML)
        length: Maximum character length

    Returns:
        Excerpt string, truncated at word boundary with ellipsis
    """
    if not text:
        return ""

    # Strip HTML first
    text = strip_html(text)

    if len(text) <= length:
        return text

    # Find last space before limit (preserve word boundary)
    excerpt = text[:length].rsplit(" ", 1)[0]
    return excerpt + "..."


def get_page_relative_url(page: Page, site: Any) -> str:
    """
    Get clean relative URL for page (without baseurl).

    Args:
        page: Page to get URL for
        site: Site instance

    Returns:
        Relative URL string (without baseurl)
    """
    # Prefer relative_url for postprocessing (guaranteed to be without baseurl)
    if hasattr(page, "relative_url"):
        relative_url = page.relative_url
        if callable(relative_url):
            try:
                result = relative_url()
                if isinstance(result, str):
                    return result
            except Exception as e:
                # Ignore exceptions from relative_url() to allow fallback to other URL methods
                logger.debug(
                    "output_format_relative_url_failed",
                    page=str(page.source_path) if hasattr(page, "source_path") else None,
                    error=str(e),
                    error_type=type(e).__name__,
                    action="trying_url_fallback",
                )
                pass
        elif isinstance(result := relative_url, str):
            return result

    # Fallback: try url property, but STRIP baseurl if present
    # page.url may include baseurl, so we need to remove it
    if hasattr(page, "url"):
        url = page.url
        if callable(url):
            try:
                url = url()
            except Exception as e:
                logger.debug(
                    "postprocess_page_url_callable_failed",
                    page=str(getattr(page, "source_path", "unknown")),
                    error=str(e),
                    error_type=type(e).__name__,
                    action="using_none_url",
                )
                url = None

        if isinstance(url, str):
            # Strip baseurl from url if present
            baseurl = ""
            if site and hasattr(site, "config") and isinstance(site.config, dict):
                baseurl = site.config.get("baseurl", "") or ""

            if baseurl and baseurl != "/" and url.startswith(baseurl):
                # Remove baseurl prefix to get relative URL
                url = url[len(baseurl) :]
                # Ensure leading slash
                if not url.startswith("/"):
                    url = "/" + url

            if url:
                return url

    # Build from output_path
    output_path = getattr(page, "output_path", None)
    if not output_path:
        return f"/{getattr(page, 'slug', page.source_path.stem)}/"

    # Handle invalid output paths
    if str(output_path) in (".", "..") or output_path.name == "":
        return f"/{getattr(page, 'slug', page.source_path.stem)}/"

    try:
        output_dir = getattr(site, "output_dir", None)
        if output_dir:
            rel_path = output_path.relative_to(output_dir)
            url = f"/{rel_path}".replace("\\", "/")
            # Clean up /index.html
            url = url.replace("/index.html", "/")
            return url
    except ValueError:
        # output_path is not relative to output_dir; fall back to slug-based URL below
        pass

    return f"/{getattr(page, 'slug', page.source_path.stem)}/"


def get_page_url(page: Page, site: Any) -> str:
    """
    Get the public URL for a page.

    Args:
        page: Page to get URL for
        site: Site instance

    Returns:
        Full public URL including baseurl
    """
    # Get the page's public URL (relative to site root)
    page_url = getattr(page, "url", None) or getattr(page, "permalink", None)

    if not page_url:
        # Fallback: construct from output_path
        output_path = getattr(page, "output_path", None)
        if output_path:
            output_dir = getattr(site, "output_dir", None)
            if output_dir:
                try:
                    relative_path = output_path.relative_to(output_dir)
                    page_url = "/" + str(relative_path).replace("\\", "/")
                except ValueError:
                    page_url = "/" + output_path.name
            else:
                page_url = "/" + output_path.name

    if not page_url:
        # Last fallback: use source path
        source_path = getattr(page, "source_path", None)
        if source_path:
            page_url = "/" + Path(source_path).stem

    # Ensure page_url starts with /
    if page_url and not page_url.startswith("/"):
        page_url = "/" + page_url

    # Get baseurl from site
    baseurl = ""
    if hasattr(site, "config") and isinstance(site.config, dict):
        baseurl = site.config.get("site", {}).get("baseurl", "")
    elif hasattr(site, "baseurl"):
        baseurl = site.baseurl or ""

    # Clean baseurl
    if baseurl and baseurl != "/":
        baseurl = baseurl.rstrip("/")
        if not baseurl.startswith("/"):
            baseurl = "/" + baseurl
    elif baseurl == "/":
        baseurl = ""

    # Combine baseurl and page_url
    if baseurl and page_url:
        # Avoid double slashes
        if page_url.startswith("/"):
            return baseurl + page_url
        return f"{baseurl}/{page_url}"

    return page_url or "/"


def get_page_json_path(page: Page) -> Path | None:
    """
    Get the output path for a page's JSON file.

    Args:
        page: Page to get JSON path for

    Returns:
        Path for the JSON file, or None if output_path not available
    """
    output_path = getattr(page, "output_path", None)
    if not output_path:
        return None

    # Handle invalid output paths (e.g., Path('.'))
    if str(output_path) in (".", "..") or output_path.name == "":
        return None

    # If output is index.html, put index.json next to it
    if output_path.name == "index.html":
        return output_path.parent / "index.json"

    # If output is page.html, put page.json next to it
    return output_path.with_suffix(".json")


def get_page_txt_path(page: Page) -> Path | None:
    """
    Get the output path for a page's TXT file.

    Args:
        page: Page to get TXT path for

    Returns:
        Path for the TXT file, or None if output_path not available
    """
    output_path = getattr(page, "output_path", None)
    if not output_path:
        return None

    # Handle invalid output paths (e.g., Path('.'))
    if str(output_path) in (".", "..") or output_path.name == "":
        return None

    # If output is index.html, put index.txt next to it
    if output_path.name == "index.html":
        return output_path.parent / "index.txt"

    # If output is page.html, put page.txt next to it
    return output_path.with_suffix(".txt")


def normalize_url(url: str) -> str:
    """
    Normalize a URL for consistent comparison.

    Args:
        url: URL to normalize

    Returns:
        Normalized URL with consistent formatting
    """
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://", "/")):
        url = "/" + url
    return url.rstrip("/") or "/"
