"""
Base strategy class for content types.

This module defines ContentTypeStrategy, the abstract base class that all
content type strategies must implement. Strategies encapsulate type-specific
behavior for sorting, filtering, pagination, and template selection.

Architecture:
    ContentTypeStrategy follows the Strategy Pattern, allowing different content
    types (blog, docs, tutorial, etc.) to define their own behavior while
    maintaining a consistent interface. Strategies are stateless and can be
    shared across sections.

Class Attributes:
    - default_template: Fallback template when no specific template is found
    - allows_pagination: Whether this content type supports pagination

Extension Points:
    Subclasses should override:
    - sort_pages(): Define custom sort order
    - filter_display_pages(): Control which pages appear in lists
    - should_paginate(): Custom pagination logic
    - get_template(): Template resolution strategy
    - detect_from_section(): Auto-detection heuristics

Example:
    >>> class BlogStrategy(ContentTypeStrategy):
    ...     default_template = "blog/list.html"
    ...     allows_pagination = True
    ...
    ...     def sort_pages(self, pages):
    ...         return sorted(pages, key=lambda p: p.date, reverse=True)

Related:
    - bengal/content_types/strategies.py: Concrete strategy implementations
    - bengal/content_types/registry.py: Strategy registration and lookup
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

    ContentTypeStrategy defines the interface for content type-specific behavior.
    Each content type (blog, doc, tutorial, changelog, etc.) can have its own
    strategy that customizes:

    - **Sorting**: How pages are ordered in list views (e.g., by date, weight)
    - **Filtering**: Which pages appear in section listings
    - **Pagination**: Whether and how pagination is applied
    - **Template Selection**: Which templates are used for list/single views

    Subclasses should override methods to provide custom behavior. The base
    implementation provides sensible defaults that work for generic content.

    Class Attributes:
        default_template: Fallback template path when no specific template
            is found. Subclasses should override this.
        allows_pagination: Whether this content type supports pagination.
            Set to True for content types with many items (e.g., blog).

    Example:
        >>> class NewsStrategy(ContentTypeStrategy):
        ...     default_template = "news/list.html"
        ...     allows_pagination = True
        ...
        ...     def sort_pages(self, pages):
        ...         # Sort by date, newest first
        ...         return sorted(pages, key=lambda p: p.date, reverse=True)
        ...
        ...     def detect_from_section(self, section):
        ...         return section.name.lower() in ("news", "announcements")

    See Also:
        - BlogStrategy: Example of chronological content strategy
        - DocsStrategy: Example of weight-based content strategy
    """

    # Class-level defaults
    default_template = "index.html"
    allows_pagination = False

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """
        Sort pages for display in list views.

        Override this method to customize page ordering for your content type.
        The default implementation sorts by weight (ascending), then title
        (alphabetical), which works well for documentation and generic pages.

        Args:
            pages: List of Page objects to sort.

        Returns:
            New sorted list of pages. Does not modify the input list.

        Example:
            >>> # Default behavior: sort by weight, then title
            >>> strategy = ContentTypeStrategy()
            >>> sorted_pages = strategy.sort_pages(section.pages)

            >>> # Blog override: sort by date, newest first
            >>> def sort_pages(self, pages):
            ...     return sorted(pages, key=lambda p: p.date or datetime.min, reverse=True)
        """
        return sorted(pages, key=lambda p: (p.metadata.get("weight", 999999), p.title.lower()))

    def filter_display_pages(self, pages: list[Page], index_page: Page | None = None) -> list[Page]:
        """
        Filter which pages to show in list views.

        Override this method to customize which pages appear in section listings.
        The default implementation excludes the index page (``_index.md``) itself,
        since it typically serves as the list page rather than a list item.

        Args:
            pages: All pages in the section to filter.
            index_page: The section's index page to exclude from the list.
                Pass None to include all pages.

        Returns:
            Filtered list of pages suitable for display in list templates.

        Example:
            >>> # Default: exclude index page
            >>> display_pages = strategy.filter_display_pages(section.pages, section.index)

            >>> # Custom: also exclude draft pages
            >>> def filter_display_pages(self, pages, index_page=None):
            ...     filtered = super().filter_display_pages(pages, index_page)
            ...     return [p for p in filtered if not p.metadata.get("draft")]
        """
        if index_page:
            return [p for p in pages if p != index_page]
        return list(pages)

    def should_paginate(self, page_count: int, config: dict[str, Any]) -> bool:
        """
        Determine if this content type should use pagination.

        Pagination is only applied when:
        1. The strategy's ``allows_pagination`` is True
        2. The page count exceeds the configured threshold

        Args:
            page_count: Number of pages in the section.
            config: Site configuration dict containing pagination settings.
                Looks for ``config["pagination"]["threshold"]`` (default: 20).

        Returns:
            True if pagination should be applied to this section.

        Example:
            >>> # Check if blog section needs pagination
            >>> if strategy.should_paginate(len(posts), site.config):
            ...     pages = paginate(posts, per_page=10)

        Note:
            The threshold is configurable in site config:
            ``pagination.threshold: 20``
        """
        if not self.allows_pagination:
            return False

        threshold = config.get("pagination", {}).get("threshold", 20)
        return page_count > threshold

    def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str:
        """
        Determine which template to use for a page.

        Implements a fallback chain to find the most appropriate template:

        - **Home pages**: ``{type}/home.html`` → ``home.html`` → ``index.html``
        - **Section indexes**: ``{type}/list.html`` → ``list.html`` → ``index.html``
        - **Regular pages**: ``{type}/single.html`` → ``single.html`` → ``page.html``

        The method checks template existence in order and returns the first
        template that exists, falling back to ``default_template`` if none found.

        Args:
            page: Page to get template for. If None, returns ``default_template``
                for backward compatibility.
            template_engine: Template engine instance for checking template
                existence. If None, skips existence checks and returns based
                on page type heuristics.

        Returns:
            Template path string (e.g., ``"blog/single.html"``).

        Example:
            >>> template = strategy.get_template(page, template_engine)
            >>> rendered = template_engine.render(template, page=page)

        Note:
            Subclasses can override this method entirely for custom template
            resolution logic, or override ``_get_type_name()`` to customize
            the type prefix used in template paths.
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
        """
        Get the type name for this strategy.

        Used to construct template paths like ``{type}/list.html``. The type
        name is extracted from the ``default_template`` path or derived from
        the class name.

        Returns:
            Type name string (e.g., ``"blog"``, ``"doc"``, ``"tutorial"``).

        Example:
            >>> class BlogStrategy(ContentTypeStrategy):
            ...     default_template = "blog/list.html"
            >>> BlogStrategy()._get_type_name()
            'blog'
        """
        # Extract type name from default_template path (e.g., "blog/list.html" -> "blog")
        if "/" in self.default_template:
            return self.default_template.split("/")[0]
        # Fallback: use class name minus "Strategy"
        class_name = self.__class__.__name__
        return class_name.replace("Strategy", "").lower()

    def detect_from_section(self, section: Section) -> bool:
        """
        Determine if this strategy applies to a section based on heuristics.

        Override this method in subclasses to provide auto-detection logic.
        Auto-detection allows Bengal to infer content types from section
        structure without explicit configuration.

        Common detection heuristics include:
        - Section name patterns (e.g., "blog", "docs", "tutorials")
        - Page metadata patterns (e.g., pages with dates → blog)
        - Directory structure conventions

        Args:
            section: Section to analyze for content type detection.

        Returns:
            True if this strategy should be used for this section.
            The default implementation returns False, requiring explicit
            content type configuration.

        Example:
            >>> class BlogStrategy(ContentTypeStrategy):
            ...     def detect_from_section(self, section):
            ...         # Detect by section name
            ...         if section.name.lower() in ("blog", "posts", "news"):
            ...             return True
            ...         # Detect by page metadata (most pages have dates)
            ...         dated_pages = sum(1 for p in section.pages if p.date)
            ...         return dated_pages > len(section.pages) * 0.6

        Note:
            Detection order matters. In ``detect_content_type()``, strategies
            are tried in priority order, so more specific detectors should
            run before generic ones.
        """
        return False
