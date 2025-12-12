"""
Isolated cascade engine for applying metadata cascades.

This module provides the CascadeEngine class which handles all cascade
application logic independently from Site and ContentOrchestrator.

The engine pre-computes page-section relationships for O(1) top-level
page detection, improving performance from O(n²) to O(n).
"""

from __future__ import annotations

from typing import Any


class CascadeEngine:
    """
    Isolated cascade application logic with pre-computed O(1) lookups.

    Handles metadata cascading where section _index.md files can define
    cascade metadata that propagates to descendant pages. This allows
    setting common metadata at the section level rather than repeating
    it on every page.

    Pre-computes page-section relationships to avoid O(n²) lookups
    when determining if a page is top-level (not in any section).

    Attributes:
        pages: All pages in the site
        sections: All sections in the site
        _pages_in_sections: Pre-computed set of pages that belong to sections (O(1) lookup)
    """

    def __init__(self, pages: list[Any], sections: list[Any]) -> None:
        """
        Initialize cascade engine with site pages and sections.

        Args:
            pages: List of all Page objects in the site
            sections: List of all Section objects in the site
        """
        self.pages = pages
        self.sections = sections
        # Pre-compute set of all pages that belong to any section
        # This converts O(sections) lookup to O(1)
        self._pages_in_sections = self._compute_pages_in_sections(sections)

    def _compute_pages_in_sections(self, sections: list[Any]) -> set[Any]:
        """
        Pre-compute set of all pages that belong to any section.

        This enables O(1) lookup later instead of searching all sections
        for each page. Called once during initialization.

        Args:
            sections: List of Section objects

        Returns:
            Set of Page objects that belong to at least one section
        """
        pages = set()
        for section in sections:
            # Use get_all_pages to recursively get pages from section and subsections
            pages.update(section.get_all_pages(recursive=True))
        return pages

    def is_top_level_page(self, page: Any) -> bool:
        """
        Check if a page is top-level (not in any section).

        O(1) lookup using pre-computed set.

        Args:
            page: Page object to check

        Returns:
            True if page is not in any section, False otherwise
        """
        return page not in self._pages_in_sections

    def apply(self) -> dict[str, Any]:
        """
        Apply cascade metadata from sections to pages.

        Processes root-level cascades first, then recursively applies
        cascades through the section hierarchy. Returns statistics about
        what was cascaded.

        Returns:
            Dictionary with cascade statistics:
            - pages_processed: Total pages in site
            - pages_with_cascade: Pages that received cascade values
            - root_cascade_pages: Pages affected by root cascade
            - cascade_keys_applied: Count of each cascaded key
        """
        stats: dict[str, Any] = {
            "pages_processed": len(self.pages),
            "pages_with_cascade": 0,
            "root_cascade_pages": 0,
            "cascade_keys_applied": {},
        }

        # First, collect root-level cascade from top-level pages
        root_cascade = None
        for page in self.pages:
            if self.is_top_level_page(page) and "cascade" in page.metadata:
                # Found root-level cascade - merge it
                if root_cascade is None:
                    root_cascade = {}
                root_cascade.update(page.metadata["cascade"])

        # Process all top-level sections with root cascade
        # (they will recurse to subsections)
        for section in self.sections:
            self._apply_section_cascade(section, parent_cascade=root_cascade, stats=stats)

        # Also apply root cascade to other top-level pages
        if root_cascade:
            for page in self.pages:
                if self.is_top_level_page(page) and "cascade" not in page.metadata:
                    for key, value in root_cascade.items():
                        if key not in page.metadata:
                            page.metadata[key] = value
                            stats["root_cascade_pages"] += 1
                            stats["cascade_keys_applied"][key] = (
                                stats["cascade_keys_applied"].get(key, 0) + 1
                            )

        return stats

    def _apply_section_cascade(
        self,
        section: Any,
        parent_cascade: dict[str, Any] | None = None,
        stats: dict[str, Any] | None = None,
    ) -> None:
        """
        Recursively apply cascade metadata to a section and its descendants.

        Cascade metadata accumulates through the hierarchy - child sections
        inherit from parent and can override/extend it.

        Args:
            section: Section to apply cascade to
            parent_cascade: Cascade metadata inherited from parent sections
            stats: Statistics dictionary to update (for tracking what was cascaded)
        """
        if stats is None:
            stats = {"pages_with_cascade": 0, "cascade_keys_applied": {}}

        # Merge parent cascade with this section's cascade
        accumulated_cascade = {}

        if parent_cascade:
            accumulated_cascade.update(parent_cascade)

        if "cascade" in section.metadata:
            # Section's cascade extends/overrides parent cascade
            accumulated_cascade.update(section.metadata["cascade"])

        # Apply accumulated cascade to all pages in this section
        # (but only for keys not already defined in page metadata)
        for page in section.pages:
            if accumulated_cascade:
                for key, value in accumulated_cascade.items():
                    # Page metadata takes precedence over cascade
                    if key not in page.metadata:
                        page.metadata[key] = value
                        stats["pages_with_cascade"] = stats.get("pages_with_cascade", 0) + 1
                        cascade_keys = stats.setdefault("cascade_keys_applied", {})
                        if not isinstance(cascade_keys, dict):
                            cascade_keys = {}
                            stats["cascade_keys_applied"] = cascade_keys
                        cascade_keys[key] = cascade_keys.get(key, 0) + 1

        # Recursively apply to subsections with accumulated cascade
        for subsection in section.subsections:
            self._apply_section_cascade(subsection, accumulated_cascade, stats)
