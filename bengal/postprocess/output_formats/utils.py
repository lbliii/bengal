"""
Shared utilities for output format generation.

Provides common functions used across all output format generators
including text processing, URL handling, path resolution, and content
normalization. These utilities ensure consistent behavior across JSON,
TXT, index, and LLM text generators.

Functions:
    Text Processing:
        - strip_html: Remove HTML tags and normalize whitespace
        - generate_excerpt: Create truncated preview text

    URL Handling:
        - get_page_relative_url: Get URL without baseurl (for objectID)
        - get_page_public_url: Get full URL with baseurl
        - get_page_url: Alias for get_page_public_url
        - normalize_url: Normalize URL for consistent comparison

    Path Resolution:
        - get_page_json_path: Get output path for page's JSON file
        - get_page_txt_path: Get output path for page's TXT file

Implementation Notes:
    Text utilities delegate to bengal.utils.text for DRY compliance.
    URL utilities work with Page._path (internal path) and Page.href
    (public URL) to avoid baseurl duplication issues.

Example:
    >>> from bengal.postprocess.output_formats.utils import (
    ...     generate_excerpt,
    ...     get_page_json_path,
    ...     get_page_url,
    ... )
    >>>
    >>> excerpt = generate_excerpt(page.plain_text, length=200)
    >>> json_path = get_page_json_path(page)
    >>> url = get_page_url(page, site)

Related:
    - bengal.utils.text: Canonical text processing utilities
    - bengal.postprocess.output_formats: Output format generators
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
    from bengal.core.site import Site


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
    # Use _path (internal path without baseurl)
    return page._path


def get_page_public_url(page: Page, site: Site) -> str:
    """
    Get the page's public URL including baseurl.

    Args:
        page: Page to get URL for
        site: Site instance

    Returns:
        Full public URL including baseurl
    """
    # page.href already includes baseurl
    return page.href


def get_page_url(page: Page, site: Any) -> str:
    """
    Get the public URL for a page.

    Args:
        page: Page to get URL for
        site: Site instance

    Returns:
        Full public URL including baseurl
    """
    # page.href already includes baseurl
    return page.href


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
