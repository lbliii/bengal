"""
Section building and sorting for content discovery.

This module handles creating sections from directories, building section
hierarchies, and sorting sections/pages by weight. Extracted from
content_discovery.py per RFC: rfc-modularize-large-files.

Classes:
SectionBuilder: Creates and organizes Section hierarchies.

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.core.section import Section
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page, PageProxy

logger = get_logger(__name__)


class SectionBuilder:
    """
    Creates and organizes Section hierarchies.

    Handles:
    - Section creation from directories
    - Section hierarchy building
    - Weight-based sorting of sections and pages

    Attributes:
        site: Optional Site reference for configuration
        sections: List of top-level sections
        pages: List of all discovered pages

    Example:
            >>> builder = SectionBuilder(site=site)
            >>> section = builder.create_section(Path("content/blog"), name="blog")
            >>> builder.sort_all_sections()

    """

    def __init__(self, site: Any | None = None):
        """
        Initialize the section builder.

        Args:
            site: Optional Site reference for configuration
        """
        self.site = site
        self.sections: list[Section] = []
        self.pages: list[Page | PageProxy] = []

    def create_section(self, path: Path, name: str | None = None) -> Section:
        """
        Create a Section from a directory path.

        Args:
            path: Path to the directory
            name: Optional name override (defaults to directory name)

        Returns:
            New Section instance
        """
        return Section(
            name=name or path.name,
            path=path,
            _site=self.site,
        )

    def add_section(self, section: Section) -> None:
        """
        Add a top-level section.

        Only adds if section has content (pages or subsections).

        Args:
            section: Section to add
        """
        if section.pages or section.subsections:
            self.sections.append(section)

    def add_page(self, page: Page | PageProxy, section: Section | None = None) -> None:
        """
        Add a page to tracking and optionally to a section.

        Args:
            page: Page to add
            section: Optional section to add page to
        """
        if section:
            section.add_page(page)
        self.pages.append(page)

    def add_versioned_sections_recursive(self, version_container: Section) -> None:
        """
        Extract content sections from _versions hierarchy and add to sections.

        The _versions directory structure is:
            _versions/
                v1/
                    docs/           <- This is a content section (add to sections)
                        about/      <- This is a subsection (already linked via docs)
                v2/
                    docs/

        We skip _versions itself and version-id directories (v1, v2), but add their
        content sections (docs, etc.) so they're accessible for version-filtered
        navigation.

        Args:
            version_container: The _versions or _shared section after walking
        """
        for version_section in version_container.subsections:
            for content_section in version_section.subsections:
                if content_section.pages or content_section.subsections:
                    self.sections.append(content_section)
                    logger.debug(
                        "versioned_section_added",
                        section_name=content_section.name,
                        version=version_section.name,
                        page_count=len(content_section.pages),
                        subsection_count=len(content_section.subsections),
                    )

    def sort_all_sections(self) -> None:
        """
        Sort all sections and their children by weight.

        Recursively sorts:
        - Pages within each section
        - Subsections within each section
        - Top-level sections

        Called after content discovery is complete.
        """
        logger.debug("sorting_sections_by_weight", total_sections=len(self.sections))

        for section in self.sections:
            self._sort_section_recursive(section)

        self.sections.sort(key=lambda s: (s.metadata.get("weight", 0), s.title.lower()))

        logger.debug("sections_sorted", total_sections=len(self.sections))

    def _sort_section_recursive(self, section: Section) -> None:
        """
        Recursively sort a section and all its subsections.

        Args:
            section: Section to sort
        """
        section.sort_children_by_weight()

        for subsection in section.subsections:
            self._sort_section_recursive(subsection)

    def get_top_level_counts(self) -> tuple[int, int]:
        """
        Get counts of top-level sections and pages.

        PERF: Uses O(n) set-based membership instead of O(n²) nested iteration.
        Pre-computes set of all pages in sections, then counts pages not in that set.

        Returns:
            Tuple of (top_level_section_count, top_level_page_count)
        """
        top_level_sections = len(
            [s for s in self.sections if not hasattr(s, "parent") or s.parent is None]
        )

        # PERF: Build set of all pages in any section (O(sections × pages_per_section))
        # Then use O(1) set membership instead of O(sections × pages_per_section) per page
        pages_in_sections: set[int] = set()
        for section in self.sections:
            for page in section.pages:
                pages_in_sections.add(id(page))

        # O(n) filter using O(1) set lookup
        top_level_pages = sum(1 for p in self.pages if id(p) not in pages_in_sections)

        return top_level_sections, top_level_pages
