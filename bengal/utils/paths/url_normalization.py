"""
URL Normalization Utilities

Centralized URL normalization and validation for Bengal SSG.
All URL construction should use these utilities to ensure consistency.

Design Principles:
- Single source of truth for URL normalization
- Normalize at construction time, not access time
- Validate URLs when created
- Handle edge cases (multiple slashes, trailing slashes, etc.)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def _collapse_slashes(url: str) -> str:
    """Replace runs of consecutive slashes with a single slash (pure string ops)."""
    if "//" not in url:
        return url
    parts = url.split("/")
    out = [parts[0]]
    for p in parts[1:]:
        if p or out[-1:] != [""]:
            out.append(p)
        elif out and out[-1] == "":
            continue
        else:
            out.append(p)
    result = "/".join(p for p in out if p) or ""
    if url.startswith("/"):
        result = "/" + result
    return result


def normalize_url(url: str, ensure_trailing_slash: bool = True) -> str:
    """
    Normalize a relative URL to a consistent format.

    Rules:
    - Always starts with /
    - No multiple consecutive slashes (except after protocol)
    - Trailing slash for directory-like URLs (if ensure_trailing_slash=True)
    - Root is "/"

    Args:
        url: URL to normalize (can be empty, relative, or absolute)
        ensure_trailing_slash: Whether to ensure trailing slash (default: True)

    Returns:
        Normalized URL string

    Examples:
            >>> normalize_url("api/bengal")
            '/api/bengal/'
            >>> normalize_url("/api//bengal/")
            '/api/bengal/'
            >>> normalize_url("/api")
            '/api/'
            >>> normalize_url("")
            '/'
            >>> normalize_url("/")
            '/'
            >>> normalize_url("/api/bengal", ensure_trailing_slash=False)
            '/api/bengal'

    """
    if not url:
        return "/"

    # Handle absolute URLs (http://, https://)
    if url.startswith(("http://", "https://")):
        return url

    # Handle protocol-relative URLs (// followed by non-slash)
    if url.startswith("//") and len(url) > 2 and url[2] != "/":
        return url

    # Ensure starts with /
    if not url.startswith("/"):
        url = "/" + url

    # Collapse consecutive slashes (string ops, no regex)
    if "//" in url:
        url = _collapse_slashes(url)

    # Handle root case
    if url == "/":
        return "/"

    # Handle trailing slash based on option
    if ensure_trailing_slash:
        if not url.endswith("/"):
            url = url + "/"
    else:
        url = url.rstrip("/") or "/"

    return url


def join_url_paths(*parts: str) -> str:
    """
    Join URL path components, normalizing slashes.

    Args:
        *parts: URL path components to join

    Returns:
        Normalized joined URL

    Examples:
            >>> join_url_paths("/api", "bengal")
            '/api/bengal/'
            >>> join_url_paths("/api/", "/bengal/")
            '/api/bengal/'
            >>> join_url_paths("api", "bengal", "core")
            '/api/bengal/core/'

    """
    # Filter out empty parts
    filtered_parts = [p for p in parts if p]

    if not filtered_parts:
        return "/"

    # Join parts, removing leading/trailing slashes from each part
    cleaned_parts = []
    for part in filtered_parts:
        cleaned = part.strip("/")
        if cleaned:
            cleaned_parts.append(cleaned)

    if not cleaned_parts:
        return "/"

    # Join with single slashes
    url = "/" + "/".join(cleaned_parts) + "/"

    # Normalize any double slashes that might have been introduced
    return normalize_url(url, ensure_trailing_slash=True)


def validate_url(url: str) -> bool:
    """
    Validate that a URL is in correct format.

    Args:
        url: URL to validate

    Returns:
        True if URL is valid, False otherwise

    """
    if not url:
        return False

    # Must start with /
    if not url.startswith("/"):
        return False

    # No multiple consecutive slashes (except after protocol)
    return not re.search(r"(?<!:)/{2,}", url)


def split_url_path(url: str) -> list[str]:
    """
    Split a URL path into its component segments.

    Strips leading/trailing slashes and splits on '/'. Returns empty list
    for root or empty URLs.

    Consolidates the common pattern:
        url.strip("/").split("/")

    Found in:
    - bengal/analysis/content_intelligence.py
    - bengal/analysis/links/patterns.py
    - bengal/postprocess/xref_index.py
    - bengal/postprocess/speculation.py
    - bengal/rendering/template_functions/navigation/breadcrumbs.py
    - bengal/rendering/pipeline/json_accumulator.py

    Args:
        url: URL path to split (e.g., "/api/bengal/core/")

    Returns:
        List of path segments

    Examples:
        >>> split_url_path("/api/bengal/core/")
        ['api', 'bengal', 'core']
        >>> split_url_path("api/bengal")
        ['api', 'bengal']
        >>> split_url_path("/")
        []
        >>> split_url_path("")
        []
        >>> split_url_path("single")
        ['single']

    """
    stripped = url.strip("/")
    return stripped.split("/") if stripped else []


def clean_md_path(path: str) -> str:
    """
    Clean a markdown file path for URL use.

    Removes the .md extension and strips leading/trailing slashes.

    Consolidates the common pattern:
        path.replace(".md", "").strip("/")

    Found in:
    - bengal/analysis/graph/builder.py
    - bengal/rendering/template_functions/crossref.py
    - bengal/rendering/plugins/cross_references.py

    Args:
        path: File path potentially ending in .md (e.g., "docs/guide.md")

    Returns:
        Cleaned path without .md extension

    Examples:
        >>> clean_md_path("docs/guide.md")
        'docs/guide'
        >>> clean_md_path("/api/reference.md/")
        'api/reference'
        >>> clean_md_path("api/reference")
        'api/reference'
        >>> clean_md_path("README.md")
        'README'

    """
    return path.replace(".md", "").strip("/")


def strip_path_params(path: str) -> str:
    """
    Remove OpenAPI-style path parameter braces for URL-safe slugs.

    Converts /orders/{orderId} to /orders/orderId so path_to_slug produces
    clean URLs without encoded braces (%7B%7D). Preserves param names to
    avoid collisions (e.g. GET /orders vs GET /orders/{orderId}).

    Args:
        path: URL path potentially containing {param} placeholders

    Returns:
        Path with braces stripped (param names preserved)

    Examples:
        >>> strip_path_params("/orders/{orderId}")
        '/orders/orderId'
        >>> strip_path_params("/users/{userId}/posts/{postId}")
        '/users/userId/posts/postId'
        >>> strip_path_params("/api/v1/users")
        '/api/v1/users'
    """
    return re.sub(r"\{([^}]+)\}", r"\1", path)


def path_to_slug(path: str) -> str:
    """
    Convert a URL path to a slug by replacing slashes with hyphens.

    Strips leading/trailing slashes and converts all internal slashes
    to hyphens for use as IDs or file prefixes.

    Consolidates the common pattern:
        path.strip("/").replace("/", "-")

    Found in:
    - bengal/autodoc/orchestration/page_builders.py
    - bengal/rendering/template_functions/openapi.py
    - bengal/postprocess/xref_index.py
    - bengal/postprocess/social_cards.py

    Args:
        path: URL path (e.g., "/api/bengal/core/")

    Returns:
        Hyphenated slug (e.g., "api-bengal-core")

    Examples:
        >>> path_to_slug("/api/bengal/core/")
        'api-bengal-core'
        >>> path_to_slug("api/bengal")
        'api-bengal'
        >>> path_to_slug("/")
        ''
        >>> path_to_slug("single")
        'single'
        >>> path_to_slug(strip_path_params("/orders/{orderId}"))
        'orders-orderId'

    """
    return path.strip("/").replace("/", "-")
