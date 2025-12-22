"""
Pagination utility for splitting long lists into pages.

Provides a generic paginator for content collections (pages, posts, tags)
with template-friendly context generation for navigation controls.

Key Features:
    - Generic type support for any item type
    - 1-indexed page numbers (user-friendly)
    - Template context generation with prev/next links
    - Configurable page window for navigation

Usage:
    >>> from bengal.utils.pagination import Paginator
    >>>
    >>> # Paginate blog posts
    >>> paginator = Paginator(posts, per_page=10)
    >>> first_page = paginator.page(1)
    >>>
    >>> # Get template context for navigation
    >>> ctx = paginator.page_context(page_number=2, base_url="/blog/")

Related Modules:
    - bengal/orchestration/archive_orchestrator.py: Uses for section archives
    - bengal/orchestration/taxonomy_orchestrator.py: Uses for tag pages
    - bengal/rendering/template_functions/: Pagination filters

See Also:
    - bengal/themes/default/templates/partials/pagination.html: Template usage
"""

from __future__ import annotations

from math import ceil
from typing import Any


class Paginator[T]:
    """
    Generic paginator for splitting a list of items into pages.

    This class provides pagination logic for any collection of items,
    producing page slices and template context for navigation controls.

    Type Parameter:
        T: The type of items being paginated (e.g., Page, dict, str)

    Attributes:
        items: Complete list of items to paginate
        per_page: Number of items per page (minimum: 1)
        num_pages: Total number of pages (computed)

    Thread Safety:
        Paginator instances are thread-safe for read operations.
        Do not modify `items` after construction.

    Example:
        >>> posts = [{"title": f"Post {i}"} for i in range(25)]
        >>> paginator = Paginator(posts, per_page=10)
        >>> paginator.num_pages
        3
        >>> len(paginator.page(1))
        10
        >>> len(paginator.page(3))
        5
    """

    def __init__(self, items: list[T], per_page: int = 10) -> None:
        """
        Initialize the paginator with items and page size.

        Args:
            items: List of items to paginate. Can be any type.
            per_page: Maximum items per page. Values < 1 are clamped to 1.

        Example:
            >>> paginator = Paginator(my_posts, per_page=15)
            >>> paginator = Paginator([], per_page=10)  # Creates 1 empty page
        """
        self.items = items
        self.per_page = max(1, per_page)  # Ensure at least 1 item per page
        self.num_pages = ceil(len(items) / self.per_page) if items else 1

    def page(self, number: int) -> list[T]:
        """
        Get items for a specific page number.

        Retrieves a slice of items for the requested page. Pages are 1-indexed
        to match user expectations (page 1 is the first page).

        Args:
            number: Page number (1-indexed). Must be between 1 and num_pages.

        Returns:
            List of items for the requested page. The last page may have
            fewer items than per_page.

        Raises:
            BengalError: If page number is less than 1 or greater than num_pages.

        Example:
            >>> paginator = Paginator(list(range(25)), per_page=10)
            >>> paginator.page(1)
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
            >>> paginator.page(3)
            [20, 21, 22, 23, 24]
            >>> paginator.page(0)
            BengalError: Page number 0 is out of range (1-3)
        """
        if number < 1 or number > self.num_pages:
            from bengal.errors import BengalError

            raise BengalError(
                f"Page number {number} is out of range (1-{self.num_pages})",
                suggestion=f"Use a page number between 1 and {self.num_pages}",
            )

        start_index = (number - 1) * self.per_page
        end_index = start_index + self.per_page

        return self.items[start_index:end_index]

    def page_context(self, page_number: int, base_url: str) -> dict[str, Any]:
        """
        Generate template context for pagination controls.

        Creates a dictionary suitable for rendering pagination UI in templates.
        Includes navigation flags, page numbers, and URL generation helpers.

        Args:
            page_number: Current page number (1-indexed).
            base_url: Base URL for pagination links. A trailing slash is
                added if not present. Example: '/posts/' or '/tags/python/'.

        Returns:
            Dictionary containing:
                - current_page (int): Current page number
                - total_pages (int): Total number of pages
                - per_page (int): Items per page
                - total_items (int): Total item count
                - has_previous (bool): True if previous page exists
                - has_next (bool): True if next page exists
                - has_prev (bool): Alias for has_previous
                - previous_page (int | None): Previous page number or None
                - next_page (int | None): Next page number or None
                - base_url (str): Normalized base URL with trailing slash
                - page_range (list[int]): Window of page numbers around current

        Example:
            >>> paginator = Paginator(posts, per_page=10)
            >>> ctx = paginator.page_context(2, "/blog/")
            >>> ctx["has_previous"]
            True
            >>> ctx["next_page"]
            3
            >>> ctx["page_range"]
            [1, 2, 3, 4]
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
        Generate a window of page numbers around the current page.

        Used for pagination UI that shows a limited set of page numbers
        (e.g., "1 2 [3] 4 5" instead of "1 2 3 ... 98 99 100").

        Args:
            current_page: Current page number (center of window).
            window: Number of pages to show on each side of current.
                Default is 2, showing 5 pages total when possible.

        Returns:
            List of page numbers in ascending order. May be shorter than
            (window * 2 + 1) at the start or end of pagination.

        Example:
            >>> paginator = Paginator(list(range(100)), per_page=10)  # 10 pages
            >>> paginator._get_page_range(5, window=2)
            [3, 4, 5, 6, 7]
            >>> paginator._get_page_range(1, window=2)
            [1, 2, 3]
            >>> paginator._get_page_range(10, window=2)
            [8, 9, 10]
        """
        start = max(1, current_page - window)
        end = min(self.num_pages, current_page + window)

        return list(range(start, end + 1))

    def __repr__(self) -> str:
        """Return a string representation showing pagination stats."""
        return (
            f"Paginator({len(self.items)} items, {self.per_page} per page, {self.num_pages} pages)"
        )
