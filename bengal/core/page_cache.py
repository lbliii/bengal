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
    built on first access and cleared by invalidate().

    Args:
        pages_fn: Callable returning the current list of pages (e.g., lambda: site.pages)
    """

    __slots__ = (
        "_generated",
        "_listable",
        "_lock",
        "_pages_fn",
        "_path_map",
        "_path_map_version",
        "_regular",
        "_source_path_map",
    )

    def __init__(self, pages_fn: Callable[[], list[PageLike]]) -> None:
        self._pages_fn = pages_fn
        self._regular: list[PageLike] | None = None
        self._generated: list[PageLike] | None = None
        self._listable: list[PageLike] | None = None
        self._path_map: dict[str, PageLike] | None = None
        self._path_map_version: int = -1
        self._source_path_map: dict[Path, PageLike] | None = None
        self._lock = threading.Lock()

    @property
    def regular_pages(self) -> list[PageLike]:
        """Regular content pages (excludes generated taxonomy/archive pages)."""
        if self._regular is not None:
            return self._regular
        with self._lock:
            if self._regular is not None:
                return self._regular
            self._regular = [p for p in self._pages_fn() if not p.metadata.get("_generated")]
        return self._regular

    @property
    def generated_pages(self) -> list[PageLike]:
        """Generated pages (taxonomy, archive, pagination)."""
        if self._generated is not None:
            return self._generated
        with self._lock:
            if self._generated is not None:
                return self._generated
            self._generated = [p for p in self._pages_fn() if p.metadata.get("_generated")]
        return self._generated

    @property
    def listable_pages(self) -> list[PageLike]:
        """Pages eligible for public listings (excludes hidden/draft)."""
        if self._listable is not None:
            return self._listable
        with self._lock:
            if self._listable is not None:
                return self._listable
            self._listable = [p for p in self._pages_fn() if p.in_listings]
        return self._listable

    def get_page_path_map(self) -> dict[str, PageLike]:
        """
        Cached string-keyed page lookup map for O(1) resolution.

        Auto-invalidates when page count changes (covers add/remove in dev server).
        """
        pages = self._pages_fn()
        current_version = len(pages)
        if self._path_map is None or self._path_map_version != current_version:
            with self._lock:
                if self._path_map is None or self._path_map_version != current_version:
                    self._path_map = {str(p.source_path): p for p in pages}
                    self._path_map_version = current_version
        return self._path_map

    @property
    def page_by_source_path(self) -> dict[Path, PageLike]:
        """O(1) page lookup by source Path (shared across orchestrators)."""
        if self._source_path_map is None:
            with self._lock:
                if self._source_path_map is None:
                    self._source_path_map = {p.source_path: p for p in self._pages_fn()}
        return self._source_path_map

    def invalidate(self) -> None:
        """Clear all caches. Call after adding/removing pages or modifying metadata."""
        self._regular = None
        self._generated = None
        self._listable = None
        self._path_map = None
        self._path_map_version = -1
        self._source_path_map = None

    def invalidate_regular(self) -> None:
        """Clear only the regular_pages cache."""
        self._regular = None
