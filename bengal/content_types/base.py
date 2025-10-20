"""
Base strategy class for content types.

Defines the interface that all content type strategies must implement.
"""


from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section


class ContentTypeStrategy:
    """
    Base strategy for content type behavior.

    Each content type (blog, doc, api-reference, etc.) can have its own
    strategy that defines:
    - How pages are sorted
    - What pages are shown in list views
    - Whether pagination is used
    - What template to use
    """

    # Class-level defaults
    default_template = "index.html"
    allows_pagination = False

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """
        Sort pages for display in list views.

        Args:
            pages: List of pages to sort

        Returns:
            Sorted list of pages

        Default: Sort by weight (ascending), then title (alphabetical)
        """
        return sorted(pages, key=lambda p: (p.metadata.get("weight", 999999), p.title.lower()))

    def filter_display_pages(
        self, pages: list[Page], index_page: Page | None = None
    ) -> list[Page]:
        """
        Filter which pages to show in list views.

        Args:
            pages: All pages in the section
            index_page: The section's index page (to exclude from lists)

        Returns:
            Filtered list of pages

        Default: Exclude the index page itself
        """
        if index_page:
            return [p for p in pages if p != index_page]
        return list(pages)

    def should_paginate(self, page_count: int, config: dict) -> bool:
        """
        Determine if this content type should use pagination.

        Args:
            page_count: Number of pages in section
            config: Site configuration

        Returns:
            True if pagination should be used

        Default: No pagination unless explicitly enabled
        """
        if not self.allows_pagination:
            return False

        threshold = config.get("pagination", {}).get("threshold", 20)
        return page_count > threshold

    def get_template(self) -> str:
        """
        Get the template name for this content type.

        Returns:
            Template path (e.g., "blog/list.html")
        """
        return self.default_template

    def detect_from_section(self, section: Section) -> bool:
        """
        Determine if this strategy applies to a section based on heuristics.

        Override this in subclasses to provide auto-detection logic.

        Args:
            section: Section to analyze

        Returns:
            True if this strategy should be used for this section

        Default: False (must be explicitly set)
        """
        return False
