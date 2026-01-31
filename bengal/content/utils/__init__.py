"""
Content utilities for Bengal SSG.

Shared utilities for content discovery, parsing, and remote source handling.
Consolidates common patterns to reduce duplication across the content package.
"""

from __future__ import annotations

from bengal.content.utils.constants import CONTENT_EXTENSIONS
from bengal.content.utils.frontmatter import (
    extract_content_skip_frontmatter,
    parse_frontmatter,
)
from bengal.content.utils.slugify import path_to_slug, title_to_slug

__all__ = [
    "CONTENT_EXTENSIONS",
    "extract_content_skip_frontmatter",
    "parse_frontmatter",
    "path_to_slug",
    "title_to_slug",
]
