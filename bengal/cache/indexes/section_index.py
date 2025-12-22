"""
Section index for O(1) lookup of pages by content directory.

This module provides SectionIndex, a QueryIndex implementation that indexes
pages by their section (content directory). This is Bengal's most commonly used
index, enabling fast access to all pages within a content section.

Section Detection:
    Sections are automatically detected from the directory structure:
    - content/blog/post.md → section = 'blog'
    - content/docs/guide.md → section = 'docs'
    - content/posts/2024/article.md → section = 'posts'

Template Usage:
    {# Get all blog posts #}
    {% set blog_posts = site.indexes.section.get('blog') %}

    {# Get all docs pages #}
    {% set docs = site.indexes.section.get('docs') %}

    {# List all sections #}
    {% for section in site.indexes.section.keys() %}
      {{ section }}: {{ site.indexes.section.get(section)|length }} pages
    {% endfor %}

Common Patterns:
    - Blog listing: site.indexes.section.get('blog')
    - Documentation sidebar: site.indexes.section.get('docs')
    - Project showcase: site.indexes.section.get('projects')

Related:
    - bengal.cache.query_index: Base QueryIndex class
    - bengal.cache.indexes.category_index: Content-based classification
    - bengal.core.section: Section model
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.cache.query_index import QueryIndex

if TYPE_CHECKING:
    from bengal.core.page import Page


class SectionIndex(QueryIndex):
    """
    Index pages by section (directory).

    Provides O(1) lookup of all pages in a section:
        site.indexes.section.get('blog')        # All blog posts
        site.indexes.section.get('docs')        # All docs pages

    Example frontmatter:
        # Section is automatically detected from directory structure
        # content/blog/post.md → section = 'blog'
        # content/docs/guide.md → section = 'docs'
    """

    def __init__(self, cache_path: Path):
        super().__init__("section", cache_path)

    def extract_keys(self, page: Page) -> list[tuple[str, dict[str, Any]]]:
        """Extract section name from page."""
        # Get section from page._section
        if hasattr(page, "_section") and page._section:
            section_name = page._section.name
            section_title = getattr(page._section, "title", section_name)

            return [(section_name, {"title": section_title})]

        return []
