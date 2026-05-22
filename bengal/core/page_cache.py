"""
Page cache manager - lazy caches over a site's page list.

Extracted from Site's PAGE CACHES section. Provides cached filtered views
of pages (regular, generated, listable) and O(1) lookup maps by path.

All caches are built lazily on first access and invalidated explicitly
via invalidate() or invalidate_regular().
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from bengal.protocols.core import PageLike


class PageCacheManager:
    """
    Manages lazy page caches for a Site instance.

    Holds filtered views (regular_pages, generated_pages, listable_pages)
    and O(1) lookup maps (by string path, by Path object). Each cache is
    built on first access and cleared by invalidate(). Cached values also
    self-invalidate when the page list token changes, which covers same-length
    list replacement and in-place page reclassification.

    Args:
        pages_fn: Callable returning the current list of pages (e.g., lambda: site.pages)
    """

    __slots__ = (
        "_generated",
        "_generated_token",
        "_listable",
        "_listable_token",
        "_lock",
        "_pages_fn",
        "_path_map",
        "_path_map_token",
        "_regular",
        "_regular_token",
        "_source_path_map",
        "_source_path_map_token",
    )

    def __init__(self, pages_fn: Callable[[], list[PageLike]]) -> None:
        self._pages_fn = pages_fn
        self._regular: list[PageLike] | None = None
        self._regular_token: tuple[object, ...] | None = None
        self._generated: list[PageLike] | None = None
        self._generated_token: tuple[object, ...] | None = None
        self._listable: list[PageLike] | None = None
        self._listable_token: tuple[object, ...] | None = None
        self._path_map: dict[str, PageLike] | None = None
        self._path_map_token: tuple[object, ...] | None = None
        self._source_path_map: dict[Path, PageLike] | None = None
        self._source_path_map_token: tuple[object, ...] | None = None
        self._lock = threading.Lock()

    def _regular_view_token(self, pages: list[PageLike]) -> tuple[tuple[int, bool], ...]:
        """Return token fields that affect regular/generated page views."""
        return tuple((id(page), bool(page.metadata.get("_generated"))) for page in pages)

    def _listable_view_token(self, pages: list[PageLike]) -> tuple[tuple[int, bool], ...]:
        """Return token fields that affect listable page views."""
        return tuple((id(page), bool(page.in_listings)) for page in pages)

    def _path_map_view_token(self, pages: list[PageLike]) -> tuple[tuple[int, Path], ...]:
        """Return token fields that affect source-path lookup maps."""
        return tuple((id(page), page.source_path) for page in pages)

    @property
    def regular_pages(self) -> list[PageLike]:
        """Regular content pages (excludes generated taxonomy/archive pages)."""
        pages = self._pages_fn()
        token = self._regular_view_token(pages)
        if self._regular is not None and self._regular_token == token:
            return self._regular
        with self._lock:
            if self._regular is not None and self._regular_token == token:
                return self._regular
            self._regular = [p for p in pages if not p.metadata.get("_generated")]
            self._regular_token = token
        return self._regular

    @property
    def generated_pages(self) -> list[PageLike]:
        """Generated pages (taxonomy, archive, pagination)."""
        pages = self._pages_fn()
        token = self._regular_view_token(pages)
        if self._generated is not None and self._generated_token == token:
            return self._generated
        with self._lock:
            if self._generated is not None and self._generated_token == token:
                return self._generated
            self._generated = [p for p in pages if p.metadata.get("_generated")]
            self._generated_token = token
        return self._generated

    @property
    def listable_pages(self) -> list[PageLike]:
        """Pages eligible for public listings (excludes hidden/draft)."""
        pages = self._pages_fn()
        token = self._listable_view_token(pages)
        if self._listable is not None and self._listable_token == token:
            return self._listable
        with self._lock:
            if self._listable is not None and self._listable_token == token:
                return self._listable
            self._listable = [p for p in pages if p.in_listings]
            self._listable_token = token
        return self._listable

    def get_page_path_map(self) -> dict[str, PageLike]:
        """
        Cached string-keyed page lookup map for O(1) resolution.

        Auto-invalidates when the page-list token changes.
        """
        pages = self._pages_fn()
        token = self._path_map_view_token(pages)
        if self._path_map is None or self._path_map_token != token:
            with self._lock:
                if self._path_map is None or self._path_map_token != token:
                    self._path_map = {str(p.source_path): p for p in pages}
                    self._path_map_token = token
        return self._path_map

    @property
    def page_by_source_path(self) -> dict[Path, PageLike]:
        """O(1) page lookup by source Path (shared across orchestrators)."""
        pages = self._pages_fn()
        token = self._path_map_view_token(pages)
        if self._source_path_map is None or self._source_path_map_token != token:
            with self._lock:
                if self._source_path_map is None or self._source_path_map_token != token:
                    self._source_path_map = {p.source_path: p for p in pages}
                    self._source_path_map_token = token
        return self._source_path_map

    def invalidate(self) -> None:
        """Clear all caches. Call after adding/removing pages or modifying metadata."""
        self._regular = None
        self._regular_token = None
        self._generated = None
        self._generated_token = None
        self._listable = None
        self._listable_token = None
        self._path_map = None
        self._path_map_token = None
        self._source_path_map = None
        self._source_path_map_token = None

    def invalidate_regular(self) -> None:
        """Clear only the regular_pages cache."""
        self._regular = None
        self._regular_token = None
