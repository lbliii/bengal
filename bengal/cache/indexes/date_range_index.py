"""Date Range Index - Index pages by year and month."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.cache.query_index import QueryIndex

if TYPE_CHECKING:
    from bengal.core.page import Page


class DateRangeIndex(QueryIndex):
    """
    Index pages by publication date (year and month buckets).

    Creates index entries for both year and year-month:
        '2024'      → All pages from 2024
        '2024-01'   → All pages from January 2024
        '2024-02'   → All pages from February 2024

    Provides O(1) lookup:
        site.indexes.date_range.get('2024')     # All 2024 posts
        site.indexes.date_range.get('2024-01')  # All January 2024 posts

    Use cases:
        - Archive pages by year/month
        - "Recent posts" filtering
        - Date-based navigation
        - Publication timelines
    """

    def __init__(self, cache_path: Path):
        super().__init__("date_range", cache_path)

    def extract_keys(self, page: Page) -> list[tuple[str, dict[str, Any]]]:
        """Extract year and year-month from page date."""
        # Get page date
        if not hasattr(page, "date") or not page.date:
            return []

        date = page.date

        # Create keys for both year and year-month
        year = str(date.year)
        month = f"{date.year}-{date.month:02d}"

        keys = [
            (year, {"type": "year", "year": date.year}),
            (month, {"type": "month", "year": date.year, "month": date.month}),
        ]

        return keys
