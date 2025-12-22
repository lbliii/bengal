"""
Built-in query indexes for O(1) page lookups.

This package provides pre-built QueryIndex implementations for common page
attributes. These indexes are computed at build time and enable fast template
lookups without iterating through all pages.

Available Indexes:
    SectionIndex: Index pages by content directory (section).
        Lookup: site.indexes.section.get('blog')  # All blog posts

    AuthorIndex: Index pages by author (supports multi-author).
        Lookup: site.indexes.author.get('Jane Smith')  # Posts by Jane

    CategoryIndex: Index pages by category (single-valued taxonomy).
        Lookup: site.indexes.category.get('tutorial')  # All tutorials

    DateRangeIndex: Index pages by year and year-month.
        Lookup: site.indexes.date_range.get('2024')  # All 2024 posts
        Lookup: site.indexes.date_range.get('2024-01')  # January 2024

Performance:
    - Build time: O(n) where n = number of pages
    - Lookup time: O(1) hash lookup
    - Memory: ~100 bytes per index entry

Template Usage:
    {% set blog_posts = site.indexes.section.get('blog') %}
    {% set janes_posts = site.indexes.author.get('Jane Smith') %}
    {% set archives_2024 = site.indexes.date_range.get('2024') %}

Custom Indexes:
    Create custom indexes by subclassing QueryIndex:

    class StatusIndex(QueryIndex):
        def __init__(self, cache_path: Path):
            super().__init__("status", cache_path)

        def extract_keys(self, page: Page) -> list[tuple[str, dict[str, Any]]]:
            status = page.metadata.get("status", "draft")
            return [(status, {})]

Related:
    - bengal.cache.query_index: Base QueryIndex class
    - bengal.cache.query_index_registry: Index registration and lifecycle
"""

from __future__ import annotations

from bengal.cache.indexes.author_index import AuthorIndex
from bengal.cache.indexes.category_index import CategoryIndex
from bengal.cache.indexes.date_range_index import DateRangeIndex
from bengal.cache.indexes.section_index import SectionIndex

__all__ = ["SectionIndex", "AuthorIndex", "CategoryIndex", "DateRangeIndex"]
