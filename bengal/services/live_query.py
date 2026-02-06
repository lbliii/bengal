"""
Live query service — O(1) lookups on mutable Site content during builds.

RFC: bengal-v2-architecture Phase 1d

Wraps ContentRegistry with the same API surface as QueryService so that
callers can be protocol-agnostic: use LiveQueryService during discovery
(mutable Page/Section objects) and QueryService during rendering
(frozen PageSnapshot/SectionSnapshot objects).

Key Principles:
- Same API as QueryService (get_page, get_section, etc.)
- Operates on live Page/Section objects via ContentRegistry
- O(1) lookups via ContentRegistry's hash-map indexes
- Suitable for build-time queries during mutable phases
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.registry import ContentRegistry
    from bengal.core.section import Section
    from bengal.core.site import Site


@dataclass(slots=True)
class LiveQueryService:
    """
    O(1) query service for live Site content during builds.

    Wraps ContentRegistry and Site content lists to provide the same
    API surface as QueryService. Unlike QueryService (which operates on
    frozen snapshots), this operates on mutable Page/Section objects.

    Usage:
        >>> service = LiveQueryService.from_site(site)
        >>> section = service.get_section("/docs/")
        >>> page = service.get_page_by_url("/docs/getting-started/")
        >>> pages = service.get_pages_by_tag("python")
    """

    _registry: ContentRegistry
    _site: Site

    # Lazily built indexes (only constructed when needed)
    _pages_by_tag: dict[str, list[Page]] | None = None
    _pages_by_section: dict[str, list[Page]] | None = None

    @classmethod
    def from_site(cls, site: Site) -> LiveQueryService:
        """
        Create service from a live Site instance.

        Args:
            site: Site instance with populated ContentRegistry

        Returns:
            LiveQueryService wrapping the site's registry
        """
        return cls(_registry=site.registry, _site=site)

    def get_page(self, href: str) -> Page | None:
        """Get page by URL/href (O(1) via ContentRegistry)."""
        return self._registry.get_page_by_url(href)

    def get_page_by_path(self, path: Path) -> Page | None:
        """Get page by source path (O(1) via ContentRegistry)."""
        return self._registry.get_page(path)

    def get_page_by_url(self, url: str) -> Page | None:
        """Get page by output URL (O(1) via ContentRegistry)."""
        return self._registry.get_page_by_url(url)

    def get_section(self, url: str) -> Section | None:
        """Get section by URL (O(1) via ContentRegistry)."""
        return self._registry.get_section_by_url(url)

    def get_section_by_path(self, path: Path) -> Section | None:
        """Get section by path (O(1) via ContentRegistry)."""
        return self._registry.get_section(path)

    def get_pages_by_tag(self, tag: str) -> list[Page]:
        """Get all pages with a tag (O(1) after first call)."""
        if self._pages_by_tag is None:
            self._build_tag_index()
        assert self._pages_by_tag is not None
        return self._pages_by_tag.get(tag, [])

    def get_pages_by_section(self, section_url: str) -> list[Page]:
        """Get all pages in a section (O(1) after first call)."""
        if self._pages_by_section is None:
            self._build_section_index()
        assert self._pages_by_section is not None
        return self._pages_by_section.get(section_url, [])

    def _build_tag_index(self) -> None:
        """Build tag -> pages index from live site pages."""
        index: dict[str, list[Page]] = {}
        for page in self._site.pages:
            tags = getattr(page, "tags", None) or ()
            for tag in tags:
                if tag not in index:
                    index[tag] = []
                index[tag].append(page)
        self._pages_by_tag = index

    def _build_section_index(self) -> None:
        """Build section_url -> pages index from live site pages."""
        index: dict[str, list[Page]] = {}
        for page in self._site.pages:
            section = getattr(page, "_section", None)
            if section is not None:
                section_url = getattr(section, "_path", None) or ""
                if section_url:
                    if section_url not in index:
                        index[section_url] = []
                    index[section_url].append(page)
        self._pages_by_section = index
