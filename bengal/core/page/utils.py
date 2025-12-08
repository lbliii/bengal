"""
Utilities for page operations and helpers.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

# Standard frontmatter fields that are extracted to PageCore fields
# All other fields go into props
STANDARD_FIELDS = {
    # Required
    "title",
    # Common
    "description",
    "date",
    "draft",
    "weight",
    "slug",
    "url",
    "aliases",
    "lang",
    # Taxonomy
    "tags",
    "categories",
    "keywords",
    "authors",
    "category",
    # Layout
    "layout",  # Legacy, normalized to variant
    "type",
    "template",
    "variant",
    # SEO
    "canonical",
    "noindex",
    "og_image",
    "og_type",
    # Navigation
    "menu",
    "nav_title",
    "parent",
    # Advanced
    "cascade",
    "outputs",
    "resources",
    # Content
    "toc",  # Table of contents (from DocPage schema)
    # Internal/system fields (should not be in props)
    "_source_file",
    "_parse_error",
    "_parse_error_type",
    "_generated",
}


def separate_standard_and_custom_fields(
    metadata: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Separate standard frontmatter fields from custom props.

    Standard fields are extracted to PageCore fields.
    Custom fields go into props.

    Note: For markdown files, frontmatter should be flat (no props: nesting).
    The props: key is primarily for skeleton manifests (bengal skeleton apply),
    where it helps group custom data separately from structural fields.

    Args:
        metadata: Full frontmatter metadata dict (will be modified in place)

    Returns:
        Tuple of (standard_fields_dict, custom_props_dict)

    Example:
        >>> # Markdown file (flat)
        >>> metadata = {"title": "Page", "icon": "code"}
        >>> standard, props = separate_standard_and_custom_fields(metadata.copy())
        >>> standard
        {'title': 'Page'}
        >>> props
        {'icon': 'code'}

        >>> # Skeleton manifest (can use props:)
        >>> metadata = {"type": "doc", "props": {"icon": "code"}}
        >>> standard, props = separate_standard_and_custom_fields(metadata.copy())
        >>> standard
        {'type': 'doc'}
        >>> props
        {'icon': 'code'}
    """
    # Work with a copy to avoid mutating original
    metadata = metadata.copy()
    standard_fields: dict[str, Any] = {}
    custom_props: dict[str, Any] = {}

    # Handle props: in frontmatter - merge its contents into custom_props
    if "props" in metadata and isinstance(metadata["props"], dict):
        custom_props.update(metadata.pop("props"))

    # Separate standard vs custom
    for key, value in metadata.items():
        if key in STANDARD_FIELDS:
            standard_fields[key] = value
        else:
            custom_props[key] = value

    return standard_fields, custom_props


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
