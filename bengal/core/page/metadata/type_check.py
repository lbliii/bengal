"""
Page metadata type-check mixin - is_home, is_section, is_page, kind, is_generated.
"""

from __future__ import annotations

from bengal.core.page.types import TOCItem


class PageMetadataTypeCheckMixin:
    """Type predicates: is_home, is_section, is_page, kind, is_generated."""

    toc: str | None
    _toc_items_cache: list[TOCItem] | None
    metadata: object
    _raw_metadata: object

    @property
    def toc_items(self) -> list[TOCItem]:
        """Get structured TOC data (lazy evaluation)."""
        if self._toc_items_cache is None and self.toc:
            from bengal.utils.toc import extract_toc_structure

            self._toc_items_cache = extract_toc_structure(self.toc)
        return self._toc_items_cache if self._toc_items_cache is not None else []

    @property
    def is_generated(self) -> bool:
        """Check if this is a generated page (tag indexes, archives, pagination)."""
        raw = getattr(self, "_raw_metadata", None)
        if raw is not None and hasattr(raw, "get") and raw.get("_generated"):
            return True
        return bool(self.metadata.get("_generated"))

    @property
    def is_home(self) -> bool:
        """Check if this page is the home page."""
        return self._path == "/" or self.slug in ("index", "_index", "home")

    @property
    def is_section(self) -> bool:
        """Check if this page is a section page."""
        from bengal.core.section import Section

        return isinstance(self, Section)

    @property
    def is_page(self) -> bool:
        """Check if this is a regular page (not a section)."""
        return not self.is_section

    @property
    def kind(self) -> str:
        """Get the kind of page: 'home', 'section', or 'page'."""
        if self.is_home:
            return "home"
        if self.is_section:
            return "section"
        return "page"
