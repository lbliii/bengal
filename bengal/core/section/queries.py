"""
Section Query Mixin - Page retrieval and collection operations.

Provides methods for retrieving pages from sections, adding pages,
sorting children, and checking section state (has index, needs auto-index).

Required Host Attributes:
- name: str
- path: Path | None
- pages: list[Page]
- subsections: list[Section]
- metadata: dict[str, Any]
- index_page: Page | None
- _emit_diagnostic: Callable

Related Modules:
bengal.core.section: Section dataclass using this mixin
bengal.core.page: Page objects contained in sections

Example:
    >>> section = site.get_section("blog")
    >>> section.regular_pages
[<Page 'post1'>, <Page 'post2'>]
    >>> section.sorted_pages
[<Page 'post2'>, <Page 'post1'>]  # Sorted by weight

"""

from __future__ import annotations

from functools import cached_property
from operator import attrgetter
from typing import TYPE_CHECKING, Any

from bengal.core.utils.sorting import DEFAULT_WEIGHT

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.core.diagnostics import DiagnosticEvent
    from bengal.core.page import Page, PageProxy
    from bengal.core.section import Section
    from bengal.protocols import PageLike

from .weighted import WeightedPage


class SectionQueryMixin:
    """
    Page collection and retrieval.

    This mixin handles:
    - Page listing (regular_pages, sorted_pages, regular_pages_recursive)
    - Section listing (sections alias)
    - Page addition (add_page)
    - Sorting (sort_children_by_weight)
    - Index page detection (has_index, needs_auto_index)
    - Recursive page retrieval (get_all_pages)

    """

    # =========================================================================
    # HOST CLASS ATTRIBUTES
    # =========================================================================
    # Type hints for attributes provided by the host dataclass.
    # These are NOT defined here - they're declared for type checking only.

    name: str
    path: Path | None
    pages: list[Page]
    subsections: list[Section]
    metadata: dict[str, Any]
    index_page: Page | None

    def _emit_diagnostic(self, event: DiagnosticEvent) -> None: ...

    # =========================================================================
    # PAGE LISTING PROPERTIES
    # =========================================================================

    @cached_property
    def regular_pages(self) -> list[Page]:
        """
        Get only regular pages (non-sections) in this section (CACHED).

        This property is cached after first access for O(1) subsequent lookups.
        Cache is invalidated when pages are added via add_page().

        Performance:
            - First access: O(n) where n = number of pages
            - Subsequent accesses: O(1) cached lookup

        Returns:
            List of regular Page objects (excludes subsections)

        Example:
            {% for page in section.regular_pages %}
              <article>{{ page.title }}</article>
            {% endfor %}
        """
        # Import here to avoid circular dependency
        from bengal.core.section import Section

        return [p for p in self.pages if not isinstance(p, Section)]

    @property
    def sections(self) -> list[Section]:
        """
        Get immediate child sections.

        Returns:
            List of child Section objects

        Example:
            {% for subsection in section.sections %}
              <h3>{{ subsection.title }}</h3>
            {% endfor %}
        """
        return self.subsections

    @cached_property
    def sorted_pages(self) -> list[Page]:
        """
        Get pages sorted by weight (ascending), then by title (CACHED).

        This property is cached after first access for O(1) subsequent lookups.
        The sort is computed once and reused across all template renders.

        Pages without a weight field are treated as having weight=float('inf')
        and appear at the end of the sorted list, after all weighted pages.
        Lower weights appear first in the list. Pages with equal weight are sorted
        alphabetically by title.

        Performance:
            - First access: O(n log n) where n = number of pages
            - Subsequent accesses: O(1) cached lookup
            - Memory cost: O(n) to store sorted list

        Returns:
            List of pages sorted by weight, then title

        Example:
            {% for page in section.sorted_pages %}
              <article>{{ page.title }}</article>
            {% endfor %}
        """

        def is_index_page(p: PageLike) -> bool:
            return p.source_path.stem in ("_index", "index")

        weighted = [
            WeightedPage(p, p.metadata.get("weight", DEFAULT_WEIGHT), p.title.lower())
            for p in self.pages
            if not is_index_page(p)
        ]
        return [wp.page for wp in sorted(weighted, key=attrgetter("weight", "title_lower"))]

    @cached_property
    def regular_pages_recursive(self) -> list[Page]:
        """
        Get all regular pages recursively (including from subsections) (CACHED).

        This property is cached after first access for O(1) subsequent lookups.
        Cache is invalidated when pages are added via add_page().

        Performance:
            - First access: O(total pages in subtree)
            - Subsequent accesses: O(1) cached lookup

        Returns:
            List of all descendant regular pages

        Example:
            <p>Total pages: {{ section.regular_pages_recursive | length }}</p>
        """
        result = list(self.regular_pages)
        for subsection in self.subsections:
            result.extend(subsection.regular_pages_recursive)
        return result

    # =========================================================================
    # PAGE MANAGEMENT METHODS
    # =========================================================================

    def add_page(self, page: Page | PageProxy) -> None:
        """
        Add a page to this section.

        Handles index page detection and metadata inheritance from index pages.
        Invalidates cached properties that depend on the pages list.

        Args:
            page: Page or PageProxy to add
        """
        from bengal.core.diagnostics import DiagnosticEvent

        is_index = page.source_path.stem in ("index", "_index")

        self.pages.append(page)

        # Invalidate cached properties that depend on pages list
        self.__dict__.pop("regular_pages", None)
        self.__dict__.pop("sorted_pages", None)
        self.__dict__.pop("regular_pages_recursive", None)

        # Set as index page if it's named index.md or _index.md
        if is_index:
            # Detect collision: both index.md and _index.md exist
            if self.index_page is not None:
                existing_name = self.index_page.source_path.stem
                new_name = page.source_path.stem
                self._emit_diagnostic(
                    DiagnosticEvent(
                        level="warning",
                        code="index_file_collision",
                        data={
                            "section": self.name,
                            "section_path": str(self.path),
                            "existing_file": f"{existing_name}.md",
                            "new_file": f"{new_name}.md",
                            "action": "preferring_underscore_version",
                            "suggestion": (
                                "Remove one of the index files - only _index.md or index.md should exist"
                            ),
                        },
                    )
                )

                # Prefer _index.md over index.md (section index convention)
                if new_name == "_index":
                    self.index_page = page
                # else: keep existing _index.md
            else:
                self.index_page = page

            # Copy metadata from index page to section
            # This allows sections to have weight, description, and other metadata
            self.metadata.update(page.metadata)

    def sort_children_by_weight(self) -> None:
        """
        Sort pages and subsections in this section by weight, then by title.

        This modifies the pages and subsections lists in place.
        Pages/sections without a weight field are treated as having weight=float('inf'),
        so they appear at the end (after all weighted items).
        Lower weights appear first in the sorted lists.

        This is typically called after content discovery is complete.
        """
        # Sort pages by weight (ascending), then title (alphabetically)
        # Unweighted pages use DEFAULT_WEIGHT (infinity) to sort last
        self.pages.sort(key=lambda p: (p.metadata.get("weight", DEFAULT_WEIGHT), p.title.lower()))

        # Sort subsections by weight (ascending), then title (alphabetically)
        # Unweighted subsections use DEFAULT_WEIGHT (infinity) to sort last
        self.subsections.sort(
            key=lambda s: (s.metadata.get("weight", DEFAULT_WEIGHT), s.title.lower())
        )

    # =========================================================================
    # INDEX PAGE DETECTION
    # =========================================================================

    def needs_auto_index(self) -> bool:
        """
        Check if this section needs an auto-generated index page.

        Returns:
            True if section needs auto-generated index (no explicit _index.md)
        """
        return self.name != "root" and self.index_page is None

    def has_index(self) -> bool:
        """
        Check if section has a valid index page.

        Returns:
            True if section has an index page (explicit or auto-generated)
        """
        return self.index_page is not None

    # =========================================================================
    # RECURSIVE RETRIEVAL
    # =========================================================================

    def get_all_pages(self, recursive: bool = True) -> list[Page]:
        """
        Get all pages in this section.

        Args:
            recursive: If True, include pages from subsections

        Returns:
            List of all pages
        """
        all_pages = list(self.pages)

        if recursive:
            for subsection in self.subsections:
                all_pages.extend(subsection.get_all_pages(recursive=True))

        return all_pages
