"""
Utilities for page operations and helpers.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


def create_synthetic_page(
    title: str,
    description: str,
    url: str,
    kind: str = "page",
    type: str = "special",
    variant: str | None = None,
    draft: bool = False,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    keywords: list[str] | None = None,
    content: str = "",
) -> SimpleNamespace:
    """
    Create a synthetic page object (SimpleNamespace) that mimics the Page interface.

    Used for special pages like 404, search, and sitemap which don't have
    backing markdown files but need to be rendered using theme templates.

    Args:
        title: Page title
        description: Page description
        url: Page URL (absolute or relative to base)
        kind: Page kind (page, section, home)
        type: Component Model type (default: special)
        variant: Component Model variant (default: None)
        draft: Draft status
        metadata: Additional metadata
        tags: List of tags
        keywords: List of keywords
        content: Page content

    Returns:
        SimpleNamespace object with Page-like attributes
    """
    return SimpleNamespace(
        title=title,
        description=description,
        url=url,
        relative_url=url,
        kind=kind,
        type=type,
        variant=variant,
        draft=draft,
        metadata=metadata or {},
        tags=tags or [],
        keywords=keywords or [],
        content=content,
        # Add empty defaults for other common properties accessed in templates
        toc="",
        toc_items=[],
        reading_time=0,
        excerpt="",
        props=metadata or {},
    )

