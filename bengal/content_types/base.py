"""
Base strategy class for content types.

Defines the interface that all content type strategies must implement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section

logger = get_logger(__name__)


class ContentTypeStrategy:
    """
    Base strategy for content type behavior.

    Each content type (blog, doc, autodoc/python, etc.) can have its own
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

    def filter_display_pages(self, pages: list[Page], index_page: Page | None = None) -> list[Page]:
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

    def should_paginate(self, page_count: int, config: dict[str, Any]) -> bool:
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

    def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str:
        """
        Determine which template to use for a page.

        Args:
            page: Page to get template for (optional for backward compatibility)
            template_engine: Template engine for checking template existence (optional)

        Returns:
            Template name (e.g., "blog/home.html", "doc/single.html")

        Default implementation provides sensible fallbacks:
        - Home pages: try {type}/home.html, then home.html, then index.html
        - Section indexes: try {type}/list.html, then list.html
        - Regular pages: try {type}/single.html, then single.html

        Note: For backward compatibility, if page is None, returns default_template.
        """
        # Backward compatibility: if no page provided, return default template
        if page is None:
            return self.default_template

        is_home = page.is_home or page._path == "/"
        is_section_index = page.source_path.stem == "_index"

        # Get type name (e.g., "blog", "doc")
        type_name = self._get_type_name()

        # Helper to check template existence
        def template_exists(name: str) -> bool:
            if template_engine is None:
                return False
            try:
                template_engine.env.get_template(name)
                return True
            except Exception as e:
                logger.debug(
                    "content_type_template_check_failed",
                    template=name,
                    error=str(e),
                    error_type=type(e).__name__,
                    action="returning_false",
                )
                return False

        if is_home:
            templates_to_try = [
                f"{type_name}/home.html",
                f"{type_name}/index.html",
                "home.html",
                "index.html",
            ]
        elif is_section_index:
            templates_to_try = [
                f"{type_name}/list.html",
                f"{type_name}/index.html",
                "list.html",
                "index.html",
            ]
        else:
            templates_to_try = [
                f"{type_name}/single.html",
                f"{type_name}/page.html",
                "single.html",
                "page.html",
            ]

        # Try each template in order
        for template_name in templates_to_try:
            if template_exists(template_name):
                return template_name

        # Final fallback
        return self.default_template

    def _get_type_name(self) -> str:
        """Get the type name for this strategy (e.g., "blog", "doc")."""
        # Extract type name from default_template path (e.g., "blog/list.html" -> "blog")
        if "/" in self.default_template:
            return self.default_template.split("/")[0]
        # Fallback: use class name minus "Strategy"
        class_name = self.__class__.__name__
        return class_name.replace("Strategy", "").lower()

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
