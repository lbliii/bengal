"""
Series index for O(1) lookup of pages by series.

This module provides SeriesIndex, a QueryIndex implementation that indexes pages
by their series membership, enabling efficient series navigation.

Frontmatter Format:
    series:
  name: "Building a Blog with Bengal"
  part: 1
  total: 5

Template Usage:
{# Get all pages in a series #}
{% set series_pages = site.indexes.series.get('Building a Blog with Bengal') %}

{# List all series #}
{% for series_name in site.indexes.series.keys() %}
  {{ series_name }}: {{ site.indexes.series.get(series_name)|length }} parts
{% endfor %}

Related:
- bengal.cache.query_index: Base QueryIndex class
- bengal.core.series: Series dataclass for structured series data

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.cache.query_index import QueryIndex

if TYPE_CHECKING:
    from bengal.core.page import Page


class SeriesIndex(QueryIndex):
    """
    Index pages by series.

    Supports series metadata from frontmatter:
        series:
          name: "Building a Blog with Bengal"
          part: 1
          total: 5

    Provides O(1) lookup:
        site.indexes.series.get('Building a Blog with Bengal')

    Metadata includes:
        - total: Total parts in series
        - description: Series description
        - slug: URL-safe series identifier

    """

    def __init__(self, cache_path: Path):
        super().__init__("series", cache_path)

    def extract_keys(self, page: Page) -> list[tuple[str, dict[str, Any]]]:
        """Extract series info from page metadata."""
        series_data = page.metadata.get("series")
        if not series_data:
            return []

        # Handle string format (just series name)
        if isinstance(series_data, str):
            return [(series_data, {"part": 1})]

        # Handle dict format with full details
        if isinstance(series_data, dict):
            name = series_data.get("name", "")
            if not name:
                name = series_data.get("title", "") or series_data.get("series_name", "")
            if not name:
                return []

            try:
                part = int(series_data.get("part", 1))
                total = int(series_data.get("total", 0))
            except (TypeError, ValueError):
                # Invalid part/total values in frontmatter - use defaults
                part = 1
                total = 0

            metadata: dict[str, Any] = {
                "part": part,
                "total": total,
                "description": str(series_data.get("description", "")),
            }

            # Generate slug if not provided
            slug = series_data.get("slug", "")
            if not slug:
                from bengal.utils.primitives.text import slugify

                slug = slugify(name)
            metadata["slug"] = slug

            return [(str(name), metadata)]

        return []
