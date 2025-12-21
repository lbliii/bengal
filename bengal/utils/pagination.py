"""
Pagination utility for splitting long lists into pages.
"""

from __future__ import annotations

from math import ceil
from typing import Any


class Paginator[T]:
    """
    Paginator for splitting a list of items into pages.

    Usage:
        paginator = Paginator(posts, per_page=10)
        page = paginator.page(1)  # Get first page

    Attributes:
        items: List of items to paginate
        per_page: Number of items per page
        num_pages: Total number of pages
    """

    def __init__(self, items: list[T], per_page: int = 10) -> None:
        """
        Initialize the paginator.

        Args:
            items: List of items to paginate
            per_page: Number of items per page (default: 10)
        """
        self.items = items
        self.per_page = max(1, per_page)  # Ensure at least 1 item per page
        self.num_pages = ceil(len(items) / self.per_page) if items else 1

    def page(self, number: int) -> list[T]:
        """
        Get items for a specific page.

        Args:
            number: Page number (1-indexed)

        Returns:
            List of items for that page

        Raises:
            ValueError: If page number is out of range
        """
        if number < 1 or number > self.num_pages:
            from bengal.utils.exceptions import BengalError

            raise BengalError(
                f"Page number {number} is out of range (1-{self.num_pages})",
                suggestion=f"Use a page number between 1 and {self.num_pages}",
            )

        start_index = (number - 1) * self.per_page
        end_index = start_index + self.per_page

        return self.items[start_index:end_index]

    def page_context(self, page_number: int, base_url: str) -> dict[str, Any]:
        """
        Get template context for a specific page.

        Args:
            page_number: Current page number (1-indexed)
            base_url: Base URL for pagination links (e.g., '/posts/')

        Returns:
            Dictionary with pagination context for templates
        """
        # Ensure base_url ends with /
        if not base_url.endswith("/"):
            base_url += "/"

        return {
            "current_page": page_number,
            "total_pages": self.num_pages,
            "per_page": self.per_page,
            "total_items": len(self.items),
            "has_previous": page_number > 1,
            "has_next": page_number < self.num_pages,
            "has_prev": page_number > 1,  # Alias for has_previous
            "previous_page": page_number - 1 if page_number > 1 else None,
            "next_page": page_number + 1 if page_number < self.num_pages else None,
            "base_url": base_url,
            "page_range": self._get_page_range(page_number),
        }

    def _get_page_range(self, current_page: int, window: int = 2) -> list[int]:
        """
        Get a range of page numbers to display.

        Args:
            current_page: Current page number
            window: Number of pages to show on each side of current

        Returns:
            List of page numbers to display
        """
        start = max(1, current_page - window)
        end = min(self.num_pages, current_page + window)

        return list(range(start, end + 1))

    def __repr__(self) -> str:
        return (
            f"Paginator({len(self.items)} items, {self.per_page} per page, {self.num_pages} pages)"
        )
