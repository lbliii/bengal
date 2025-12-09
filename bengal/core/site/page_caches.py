"""
Page caching mixin for Site.

Provides cached page list properties (regular_pages, generated_pages, listable_pages)
with automatic invalidation when pages change.

Related Modules:
    - bengal.core.site.core: Main Site dataclass using this mixin
    - bengal.core.page: Page model
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page


class PageCachesMixin:
    """
    Mixin providing cached page list properties.

    Requires these attributes on the host class:
        - pages: list[Page]
        - _regular_pages_cache: list[Page] | None
        - _generated_pages_cache: list[Page] | None
        - _listable_pages_cache: list[Page] | None
        - _page_path_map: dict[str, Page] | None
        - _page_path_map_version: int
    """

    # Type hints for mixin attributes (provided by host class)
    pages: list[Page]
    _regular_pages_cache: list[Page] | None
    _generated_pages_cache: list[Page] | None
    _listable_pages_cache: list[Page] | None
    _page_path_map: dict[str, Page] | None
    _page_path_map_version: int

    @property
    def regular_pages(self) -> list[Page]:
        """
        Get only regular content pages (excludes generated taxonomy/archive pages).

        PERFORMANCE: This property is cached after first access for O(1) subsequent lookups.
        The cache is automatically invalidated when pages are modified.

        Returns:
            List of regular Page objects (excludes tag pages, archive pages, etc.)

        Example:
            {% for page in site.regular_pages %}
                <article>{{ page.title }}</article>
            {% endfor %}
        """
        if self._regular_pages_cache is not None:
            return self._regular_pages_cache

        self._regular_pages_cache = [p for p in self.pages if not p.metadata.get("_generated")]
        return self._regular_pages_cache

    @property
    def generated_pages(self) -> list[Page]:
        """
        Get only generated pages (taxonomy, archive, pagination pages).

        PERFORMANCE: This property is cached after first access for O(1) subsequent lookups.
        The cache is automatically invalidated when pages are modified.

        Returns:
            List of generated Page objects (tag pages, archive pages, pagination, etc.)

        Example:
            # Check if any tag pages need rebuilding
            for page in site.generated_pages:
                if page.metadata.get("type") == "tag":
                    # ... process tag page
        """
        if self._generated_pages_cache is not None:
            return self._generated_pages_cache

        self._generated_pages_cache = [p for p in self.pages if p.metadata.get("_generated")]
        return self._generated_pages_cache

    @property
    def listable_pages(self) -> list[Page]:
        """
        Get pages that should appear in listings (excludes hidden pages).

        This property respects the visibility system:
        - Excludes pages with `hidden: true`
        - Excludes pages with `visibility.listings: false`
        - Excludes draft pages

        Use this for:
        - "Recent posts" sections
        - Archive pages
        - Category/tag listings
        - Any public-facing page list

        Use `site.pages` when you need ALL pages including hidden ones
        (e.g., for sitemap generation where you filter separately).

        PERFORMANCE: This property is cached after first access for O(1) subsequent lookups.
        The cache is automatically invalidated when pages are modified.

        Returns:
            List of Page objects that should appear in public listings

        Example:
            {% for post in site.listable_pages | where('section', 'blog') | sort_by('date', reverse=true) | limit(5) %}
                <article>{{ post.title }}</article>
            {% endfor %}
        """
        if self._listable_pages_cache is not None:
            return self._listable_pages_cache

        self._listable_pages_cache = [p for p in self.pages if p.in_listings]
        return self._listable_pages_cache

    def get_page_path_map(self) -> dict[str, Page]:
        """
        Get cached page path lookup map for O(1) page resolution.

        Cache is automatically invalidated when page count changes,
        covering add/remove operations in dev server.

        Returns:
            Dictionary mapping source_path strings to Page objects

        Example:
            page_map = site.get_page_path_map()
            page = page_map.get("content/posts/my-post.md")
        """
        current_version = len(self.pages)
        if self._page_path_map is None or self._page_path_map_version != current_version:
            self._page_path_map = {str(p.source_path): p for p in self.pages}
            self._page_path_map_version = current_version
        return self._page_path_map

    def invalidate_page_caches(self) -> None:
        """
        Invalidate cached page lists when pages are modified.

        Call this after:
        - Adding/removing pages
        - Modifying page metadata (especially _generated flag or visibility)
        - Any operation that changes the pages list

        This ensures cached properties (regular_pages, generated_pages, listable_pages,
        page_path_map) will recompute on next access.
        """
        self._regular_pages_cache = None
        self._generated_pages_cache = None
        self._listable_pages_cache = None
        self._page_path_map = None
        self._page_path_map_version = -1

    def invalidate_regular_pages_cache(self) -> None:
        """
        Invalidate the regular_pages cache.

        Call this after modifying the pages list or page metadata that affects
        the _generated flag. More specific than invalidate_page_caches() if you
        only need to invalidate regular_pages.

        See Also:
            invalidate_page_caches(): Invalidate all page caches at once
        """
        self._regular_pages_cache = None
