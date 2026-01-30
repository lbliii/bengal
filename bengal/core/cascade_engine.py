"""
Isolated cascade engine for applying metadata cascades.

Provides the CascadeEngine class which handles all cascade application logic
independently from Site and ContentOrchestrator. Pre-computes page-section
relationships for O(1) top-level page detection.

Public API:
CascadeEngine: Applies cascade metadata from sections to pages

Key Concepts:
Cascade: Metadata propagation from section _index.md files to all
    descendant pages. Define once at section level, apply everywhere.

Accumulation: Cascades accumulate through the hierarchy. Child sections
    inherit parent cascade and can extend/override values.

Precedence: Page-level metadata always overrides cascaded values.
    Cascades only fill in missing fields, never replace existing.

Pre-computation: Page-section relationships computed once at init
    for O(1) top-level page detection (vs O(n) per-page lookup).

Usage:
    engine = CascadeEngine(site.pages, site.sections)
    stats = engine.apply()
# stats contains: pages_processed, pages_with_cascade, etc.

Related Packages:
bengal.core.site.discovery: ContentDiscoveryMixin calls _apply_cascades()
bengal.core.section: Section objects that define cascade metadata
bengal.core.page: Page objects that receive cascaded metadata

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section


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

    def is_top_level_page(self, page: Page) -> bool:
        """
        Check if a page is top-level (not in any section).

        O(1) lookup using pre-computed set.

        Args:
            page: Page object to check

        Returns:
            True if page is not in any section, False otherwise
        """
        return page not in self._pages_in_sections

    def _clear_previous_cascades(self) -> None:
        """
        Clear previously cascaded values from all pages.
        
        This enables proper cascade refresh during incremental builds.
        When pages are loaded from cache, they may have old cascade values
        that need to be cleared before new cascades are applied.
        
        For PageProxy objects with previous cascades, forces loading to full
        Page objects to enable cascade modification.
        
        Only clears keys that were previously set by cascade (tracked in
        page.core.props['_cascade_keys']), preserving page-level frontmatter values.
        The _cascade_keys list is persisted with page.core.props in the cache.
        """
        from bengal.core.page.proxy import PageProxy
        
        # First pass: identify PageProxy objects with previous cascades and force-load them
        for i, page in enumerate(self.pages):
            if isinstance(page, PageProxy):
                cascade_keys = None
                if hasattr(page, "core") and page.core is not None:
                    cascade_keys = page.core.props.get("_cascade_keys")
                
                if cascade_keys and isinstance(cascade_keys, list) and len(cascade_keys) > 0:
                    # Force-load PageProxy to Page so cascades can be modified
                    page._ensure_loaded()
                    if page._full_page is not None:
                        # Replace proxy with full page in the list
                        self.pages[i] = page._full_page
        
        # Second pass: clear cascade values from all pages (now all are full Page objects
        # if they had previous cascades)
        for page in self.pages:
            # Get keys that were previously set by cascade
            cascade_keys = None
            if hasattr(page, "core") and page.core is not None:
                cascade_keys = page.core.props.get("_cascade_keys")
            if not cascade_keys:
                cascade_keys = page.metadata.get("_cascade_keys")
            
            if cascade_keys and isinstance(cascade_keys, list):
                # Clear those keys from metadata so new cascades can be applied
                for key in cascade_keys:
                    if key in page.metadata:
                        del page.metadata[key]
                # Clear the _cascade_keys tracking since we're about to re-apply cascades
                # Only remove if it exists (don't add empty list if not present)
                if hasattr(page, "core") and page.core is not None:
                    page.core.props.pop("_cascade_keys", None)
                if hasattr(page, "metadata") and isinstance(page.metadata, dict):
                    page.metadata.pop("_cascade_keys", None)

    def apply(self) -> dict[str, Any]:
        """
        Apply cascade metadata from sections to pages.

        Processes root-level cascades first, then recursively applies
        cascades through the section hierarchy. Returns statistics about
        what was cascaded.
        
        Cascade Refresh: Before applying cascades, any previously cascaded
        values (tracked in page._cascade_keys) are cleared. This ensures
        cascade changes are properly reflected during incremental builds
        where pages may be loaded from cache with old cascade values.

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
        
        # Clear previously cascaded values from all pages before re-applying
        # This ensures cascade changes are reflected during incremental builds
        # where pages may be loaded from cache with old cascade values.
        self._clear_previous_cascades()

        # First, collect root-level cascade from top-level pages
        root_cascade = None
        for page in self.pages:
            if self.is_top_level_page(page) and "cascade" in page.metadata:
                # Found root-level cascade - merge it
                if root_cascade is None:
                    root_cascade = {}
                root_cascade.update(page.metadata["cascade"])

        # Process only entry point sections - those whose parent is not in self.sections
        # This handles:
        # 1. Root sections (parent is None) - always entry points
        # 2. Versioned sections (parent exists but not in self.sections) - entry points
        # 3. Subsections whose parent IS in self.sections - NOT entry points, will be
        #    reached via recursion from their parent with correct accumulated cascade
        sections_set = set(self.sections)
        entry_sections = [
            s for s in self.sections
            if getattr(s, "parent", None) is None or s.parent not in sections_set
        ]
        for section in entry_sections:
            self._apply_section_cascade(section, parent_cascade=root_cascade, stats=stats)

        # Also apply root cascade to other top-level pages
        if root_cascade:
            from bengal.core.page.proxy import PageProxy
            
            for i, page in enumerate(self.pages):
                if self.is_top_level_page(page) and "cascade" not in page.metadata:
                    # For PageProxy objects, force-load to enable cascade modification
                    if isinstance(page, PageProxy):
                        page._ensure_loaded()
                        if page._full_page is not None:
                            self.pages[i] = page._full_page
                            page = page._full_page
                    
                    cascade_keys_applied = []
                    for key, value in root_cascade.items():
                        if key not in page.metadata:
                            page.metadata[key] = value
                            cascade_keys_applied.append(key)
                    
                    # Only track cascade keys if any were actually applied
                    if cascade_keys_applied:
                        page.metadata["_cascade_keys"] = cascade_keys_applied
                        if hasattr(page, "core") and page.core is not None:
                            page.core.props["_cascade_keys"] = cascade_keys_applied
                            stats["root_cascade_pages"] += 1
                            stats["cascade_keys_applied"][key] = (
                                stats["cascade_keys_applied"].get(key, 0) + 1
                            )

        return stats

    def _apply_section_cascade(
        self,
        section: Section,
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
        from bengal.core.page.proxy import PageProxy
        
        for i, page in enumerate(section.pages):
            if accumulated_cascade:
                # For PageProxy objects, force-load to enable cascade modification
                if isinstance(page, PageProxy):
                    page._ensure_loaded()
                    if page._full_page is not None:
                        section.pages[i] = page._full_page
                        page = page._full_page
                
                cascade_keys_applied = []
                for key, value in accumulated_cascade.items():
                    # Page metadata takes precedence over cascade
                    if key not in page.metadata:
                        page.metadata[key] = value
                        cascade_keys_applied.append(key)
                        stats["pages_with_cascade"] = stats.get("pages_with_cascade", 0) + 1
                        cascade_keys = stats.setdefault("cascade_keys_applied", {})
                        if not isinstance(cascade_keys, dict):
                            cascade_keys = {}
                            stats["cascade_keys_applied"] = cascade_keys
                        cascade_keys[key] = cascade_keys.get(key, 0) + 1
                
                # Only track cascade keys if any were actually applied
                if cascade_keys_applied:
                    page.metadata["_cascade_keys"] = cascade_keys_applied
                    if hasattr(page, "core") and page.core is not None:
                        page.core.props["_cascade_keys"] = cascade_keys_applied

        # Recursively apply to subsections with accumulated cascade
        for subsection in section.subsections:
            self._apply_section_cascade(subsection, accumulated_cascade, stats)
