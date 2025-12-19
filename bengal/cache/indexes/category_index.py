"""Category Index - Index pages by category."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.cache.query_index import QueryIndex

if TYPE_CHECKING:
    from bengal.core.page import Page


class CategoryIndex(QueryIndex):
    """
    Index pages by category (single-valued taxonomy).

    Unlike tags (multi-valued), categories are typically single-valued:
        category: tutorial
        category: autodoc/python
        category: guide

    Provides O(1) lookup:
        site.indexes.category.get('tutorial')      # All tutorials
        site.indexes.category.get('autodoc/python') # All API docs

    Common patterns:
        - Documentation: 'tutorial', 'guide', 'reference', 'howto'
        - Blog: 'tech', 'business', 'personal'
        - Recipes: 'appetizer', 'main-course', 'dessert'
    """

    def __init__(self, cache_path: Path):
        super().__init__("category", cache_path)

    def extract_keys(self, page: Page) -> list[tuple[str, dict[str, Any]]]:
        """Extract category from page metadata."""
        category = page.metadata.get("category")

        if category:
            # Normalize to lowercase for consistent lookups
            category_normalized = str(category).lower().strip()

            if category_normalized:
                return [(category_normalized, {"display_name": str(category)})]

        return []
