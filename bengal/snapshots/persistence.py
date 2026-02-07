"""
Snapshot persistence for near-instant incremental builds.

Serializes SiteSnapshot to disk and reloads on subsequent builds.
By comparing content hashes, we can reuse pre-parsed HTML from the
previous build, eliminating re-parsing for unchanged pages.

Architecture:
    Build N:
        parse all pages → create snapshot → save to disk

    Build N+1:
        load previous snapshot → compare hashes → reuse parsed HTML
        only parse changed pages → merge with old snapshot data

Thread-Safety:
    File writes use atomic rename pattern to prevent corruption.

RFC: rfc-bengal-snapshot-engine (Snapshot Persistence section)

"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.snapshots.utils import compute_content_hash
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.snapshots.types import SiteSnapshot

logger = get_logger(__name__)

# Snapshot format version - increment when format changes
SNAPSHOT_VERSION = 1

# Default cache location
DEFAULT_CACHE_DIR = ".bengal/cache/snapshots"


class SnapshotCache:
    """
    Persistent cache for SiteSnapshot data.

    Stores snapshot metadata and page content hashes to enable
    fast incremental builds by reusing pre-parsed HTML.

    File Format:
        snapshot_meta.json - Metadata and page index
        snapshot_pages.json - Page content (parsed HTML, TOC, etc.)

    Example:
        cache = SnapshotCache(site.root_path / ".bengal/cache/snapshots")

        # On build start, try to load previous snapshot
        old_pages = cache.load_page_cache()

        # After parsing, save new snapshot
        cache.save(snapshot)

    """

    __slots__ = ("_cache_dir", "_meta_path", "_pages_path")

    def __init__(self, cache_dir: Path) -> None:
        """Initialize snapshot cache.

        Args:
            cache_dir: Directory for cache files (created if missing)
        """
        self._cache_dir = cache_dir
        self._meta_path = cache_dir / "snapshot_meta.json"
        self._pages_path = cache_dir / "snapshot_pages.json"

    def load_page_cache(self) -> dict[str, CachedPageData] | None:
        """
        Load cached page data from previous build.

        Returns:
            Dict mapping source_path -> CachedPageData, or None if no cache
        """
        if not self._meta_path.exists() or not self._pages_path.exists():
            logger.debug("snapshot_cache_miss", reason="files_not_found")
            return None

        try:
            # Load metadata to verify version
            with open(self._meta_path) as f:
                meta = json.load(f)

            if meta.get("version") != SNAPSHOT_VERSION:
                logger.debug(
                    "snapshot_cache_miss",
                    reason="version_mismatch",
                    cached=meta.get("version"),
                    current=SNAPSHOT_VERSION,
                )
                return None

            # Load page data
            with open(self._pages_path) as f:
                pages_data = json.load(f)

            # Convert to CachedPageData objects
            result: dict[str, CachedPageData] = {}
            for path_str, data in pages_data.items():
                result[path_str] = CachedPageData(
                    content_hash=data["content_hash"],
                    parsed_html=data["parsed_html"],
                    toc=data.get("toc", ""),
                    toc_items=tuple(data.get("toc_items", [])),
                    reading_time=data.get("reading_time", 0),
                    word_count=data.get("word_count", 0),
                    excerpt=data.get("excerpt", ""),
                )

            logger.debug(
                "snapshot_cache_hit",
                pages_cached=len(result),
                cache_time=meta.get("timestamp"),
            )
            return result

        except Exception as e:
            logger.warning(
                "snapshot_cache_load_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def save(self, snapshot: SiteSnapshot) -> None:
        """
        Save snapshot to disk for future incremental builds.

        Uses atomic write pattern to prevent corruption.

        Args:
            snapshot: SiteSnapshot to persist
        """
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Build metadata
            meta = {
                "version": SNAPSHOT_VERSION,
                "timestamp": time.time(),
                "page_count": snapshot.page_count,
                "section_count": snapshot.section_count,
            }

            # Build page cache data (only what we need for incremental)
            pages_data: dict[str, dict[str, Any]] = {}
            for page in snapshot.pages:
                pages_data[str(page.source_path)] = {
                    "content_hash": page.content_hash,
                    "parsed_html": page.parsed_html,
                    "toc": page.toc,
                    "toc_items": list(page.toc_items),
                    "reading_time": page.reading_time,
                    "word_count": page.word_count,
                    "excerpt": page.excerpt,
                }

            # Atomic write: write to temp file, then rename
            meta_tmp = self._meta_path.with_suffix(".tmp")
            pages_tmp = self._pages_path.with_suffix(".tmp")

            with open(meta_tmp, "w") as f:
                json.dump(meta, f)

            with open(pages_tmp, "w") as f:
                json.dump(pages_data, f)

            # Atomic rename
            meta_tmp.rename(self._meta_path)
            pages_tmp.rename(self._pages_path)

            logger.debug(
                "snapshot_cache_saved",
                pages=len(pages_data),
                meta_size=self._meta_path.stat().st_size,
                pages_size=self._pages_path.stat().st_size,
            )

        except Exception as e:
            logger.warning(
                "snapshot_cache_save_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Clean up temp files on error
            for tmp in [self._meta_path.with_suffix(".tmp"), self._pages_path.with_suffix(".tmp")]:
                if tmp.exists():
                    tmp.unlink()

    def clear(self) -> None:
        """Clear the snapshot cache."""
        for path in [self._meta_path, self._pages_path]:
            if path.exists():
                path.unlink()
        logger.debug("snapshot_cache_cleared")


class CachedPageData:
    """
    Cached data for a single page.

    Contains pre-parsed content that can be reused if content_hash matches.
    """

    __slots__ = (
        "content_hash",
        "excerpt",
        "parsed_html",
        "reading_time",
        "toc",
        "toc_items",
        "word_count",
    )

    def __init__(
        self,
        content_hash: str,
        parsed_html: str,
        toc: str = "",
        toc_items: tuple[dict[str, Any], ...] = (),
        reading_time: int = 0,
        word_count: int = 0,
        excerpt: str = "",
    ) -> None:
        self.content_hash = content_hash
        self.parsed_html = parsed_html
        self.toc = toc
        self.toc_items = toc_items
        self.reading_time = reading_time
        self.word_count = word_count
        self.excerpt = excerpt


def apply_cached_parsing(
    pages: list[Any],  # list[Page]
    cache: dict[str, CachedPageData],
) -> tuple[list[Any], list[Any], int]:
    """
    Apply cached parsed content to pages that haven't changed.

    Compares content hashes and copies pre-parsed HTML from cache
    for unchanged pages, eliminating re-parsing overhead.

    Args:
        pages: List of Page objects to check
        cache: Dict of path -> CachedPageData from previous build

    Returns:
        Tuple of (pages_needing_parse, pages_from_cache, cache_hits)
    """
    pages_to_parse: list[Any] = []
    pages_from_cache: list[Any] = []
    cache_hits = 0

    for page in pages:
        path_str = str(page.source_path)
        cached = cache.get(path_str)

        if cached is None:
            # New page, needs parsing
            pages_to_parse.append(page)
            continue

        # Compute current content hash
        content = getattr(page, "_source", "") or getattr(page, "content", "") or ""
        current_hash = compute_content_hash(content)

        if current_hash == cached.content_hash:
            # Content unchanged - apply cached data
            page.html_content = cached.parsed_html
            page.toc = cached.toc
            page._toc_items_cache = list(cached.toc_items)
            if hasattr(page, "_reading_time"):
                page._reading_time = cached.reading_time
            if hasattr(page, "_word_count"):
                page._word_count = cached.word_count
            if hasattr(page, "_excerpt"):
                page._excerpt = cached.excerpt

            pages_from_cache.append(page)
            cache_hits += 1
        else:
            # Content changed, needs re-parsing
            pages_to_parse.append(page)

    logger.debug(
        "snapshot_cache_applied",
        total_pages=len(pages),
        cache_hits=cache_hits,
        pages_to_parse=len(pages_to_parse),
        hit_rate=f"{cache_hits / len(pages) * 100:.1f}%" if pages else "0%",
    )

    return pages_to_parse, pages_from_cache, cache_hits
