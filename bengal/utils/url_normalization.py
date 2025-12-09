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

    # Handle absolute URLs (http://, https://, //)
    # Don't normalize these - return as-is
    if url.startswith(("http://", "https://", "//")):
        return url

    # Ensure starts with /
    url = "/" + url.lstrip("/")

    # Normalize multiple consecutive slashes (except after protocol)
    url = re.sub(r"(?<!:)/{2,}", "/", url)

    # Handle root case
    if url == "/":
        return "/"

    # Ensure trailing slash if requested
    if ensure_trailing_slash and not url.endswith("/"):
        url += "/"

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
