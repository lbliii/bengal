"""
Site Query Mixin - Section/page lookups and page cache delegation.

Provides O(1) section lookups (by path or URL), page cache properties
(regular_pages, generated_pages, listable_pages), and registry population.
Delegates to ContentRegistry and PageCacheManager.

See Also:
- bengal/core/site/__init__.py: Site class that uses this mixin
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section


class SiteQueryMixin:
    """
    Mixin providing section lookups and page cache delegation.

    Handles:
    - get_section_by_path, get_section_by_url
    - register_sections
    - regular_pages, generated_pages, listable_pages
    - get_page_path_map, page_by_source_path
    - invalidate_page_caches, invalidate_regular_pages_cache
    """

    root_path: Path
    pages: list[Page]
    sections: list[Section]
    registry: object
    _page_cache: object

    def get_section_by_path(self, path: Path | str) -> Section | None:
        """
        Look up a section by its path (O(1) operation).

        Args:
            path: Section path (absolute, relative to content/, or relative to root)

        Returns:
            Section object if found, None otherwise
        """
        if isinstance(path, str):
            path = Path(path)

        if not path.is_absolute():
            content_relative = self.root_path / "content" / path
            if content_relative.exists():
                path = content_relative
            else:
                root_relative = self.root_path / path
                if root_relative.exists():
                    path = root_relative

        section = self.registry.get_section(path)

        if section is None:
            emit_diagnostic(
                self,
                "debug",
                "section_not_found_in_registry",
                path=str(path),
                registry_size=self.registry.section_count,
            )

        return section

    def get_section_by_url(self, url: str) -> Section | None:
        """
        Look up a section by its relative URL (O(1) operation).

        Args:
            url: Section relative URL (e.g., "/api/", "/api/core/")

        Returns:
            Section object if found, None otherwise
        """
        section = self.registry.get_section_by_url(url)

        if section is None:
            emit_diagnostic(
                self,
                "debug",
                "section_not_found_in_url_registry",
                url=url,
                registry_size=self.registry.section_count,
            )

        return section

    def register_sections(self) -> None:
        """
        Build the section registry for path-based and URL-based lookups.

        Populates ContentRegistry with all sections (recursive).
        Must be called after discover_content().
        """
        start = time.time()

        self.registry._sections_by_path.clear()
        self.registry._sections_by_url.clear()

        for section in self.sections:
            self.registry.register_sections_recursive(section)

        self.registry.increment_epoch()

        elapsed_ms = (time.time() - start) * 1000

        emit_diagnostic(
            self,
            "debug",
            "section_registry_built",
            sections=self.registry.section_count,
            elapsed_ms=f"{elapsed_ms:.2f}",
            avg_us_per_section=f"{(elapsed_ms * 1000 / self.registry.section_count):.2f}"
            if self.registry.section_count
            else "0",
        )

    @property
    def regular_pages(self) -> list[Page]:
        """Regular content pages (excludes generated taxonomy/archive pages).

        Cost: O(n) first access (n = pages), O(1) cached thereafter.
        """
        return self._page_cache.regular_pages

    @property
    def generated_pages(self) -> list[Page]:
        """Generated pages (taxonomy, archive, pagination).

        Cost: O(n) first access (n = pages), O(1) cached thereafter.
        """
        return self._page_cache.generated_pages

    @property
    def listable_pages(self) -> list[Page]:
        """Pages eligible for public listings (excludes hidden/draft).

        Cost: O(n) first access (n = pages), O(1) cached thereafter.
        """
        return self._page_cache.listable_pages

    def get_page_path_map(self) -> dict[str, Page]:
        """Cached string-keyed page lookup map for O(1) resolution."""
        return self._page_cache.get_page_path_map()

    @property
    def page_by_source_path(self) -> dict[Path, Page]:
        """O(1) page lookup by source Path (shared across orchestrators).

        Cost: O(n) first access (n = pages), O(1) cached thereafter.
        """
        return self._page_cache.page_by_source_path

    def invalidate_page_caches(self) -> None:
        """Clear all page caches. Call after adding/removing pages."""
        self._page_cache.invalidate()

    def invalidate_regular_pages_cache(self) -> None:
        """Clear only the regular_pages cache."""
        self._page_cache.invalidate_regular()
