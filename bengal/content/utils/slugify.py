"""
Slug generation utilities.

Provides consistent slug generation from paths and titles across all
content sources (local, GitHub, Notion, REST).
"""

from __future__ import annotations

import re
from pathlib import Path

from bengal.utils.paths.normalize import to_posix


def path_to_slug(rel_path: Path | str, *, handle_index: bool = True) -> str:
    """
    Convert relative path to URL-friendly slug.

    Handles:
    - Extension removal (.md, .markdown, etc.)
    - Path separator normalization (backslash → forward slash)
    - Index file handling (path/index → path)

    Args:
        rel_path: Path relative to content directory
        handle_index: If True, strip trailing /index from slugs

    Returns:
        URL-friendly slug

    Example:
        >>> path_to_slug(Path("docs/getting-started.md"))
        'docs/getting-started'
        >>> path_to_slug("blog/2024/index.md")
        'blog/2024'
        >>> path_to_slug("index.md")
        'index'

    """
    # Handle Path or str
    path = Path(rel_path) if isinstance(rel_path, str) else rel_path

    # Remove extension
    slug = str(path.with_suffix(""))

    # Normalize separators (Windows backslash → forward slash)
    slug = to_posix(slug)

    # Handle index files
    if handle_index:
        if slug.endswith("/index") or slug == "index":
            slug = slug.rsplit("/index", 1)[0] or "index"

    return slug


def title_to_slug(title: str) -> str:
    """
    Convert title string to URL-friendly slug.

    Handles:
    - Lowercasing
    - Removing special characters
    - Replacing spaces with hyphens
    - Collapsing multiple hyphens

    Args:
        title: Page or document title

    Returns:
        URL-friendly slug

    Example:
        >>> title_to_slug("Getting Started with Bengal!")
        'getting-started-with-bengal'
        >>> title_to_slug("API Reference (v2)")
        'api-reference-v2'

    """
    slug = title.lower()
    # Remove non-word characters except spaces and hyphens
    slug = re.sub(r"[^\w\s-]", "", slug)
    # Replace spaces and multiple hyphens with single hyphen
    slug = re.sub(r"[-\s]+", "-", slug)
    # Strip leading/trailing hyphens
    return slug.strip("-")
