"""
Page discovery cache for incremental builds with lazy loading.

This module provides caching of page metadata (title, date, tags, section, slug)
to enable skipping full content parsing for unchanged pages. Metadata is loaded
from cache, with full content loaded lazily via PageProxy when accessed.

Key Types:
    PageMetadata: Type alias for PageCore - the cacheable page metadata.
        Contains all fields needed for navigation, filtering, and display
        without loading full page content.

    PageDiscoveryCacheEntry: Cache entry wrapper with validity tracking.
        Includes metadata, cache timestamp, and validity flag.

    PageDiscoveryCache: Main cache class for storing/loading page metadata.
        Handles persistence, validation, and invalidation.

Architecture:
    - Metadata: source_path → PageMetadata (minimal navigation data)
    - Lazy Loading: Full content via PageProxy when needed
    - Storage: .bengal/page_metadata.json (JSON format)
    - Validation: File hash comparison to detect stale entries

Performance Impact:
    - Skip parsing: ~80ms saved per 100 unchanged pages
    - Memory efficient: Only metadata in memory until content accessed
    - Incremental: Only changed pages fully parsed

Caching Flow:
    1. Discovery phase checks cache for existing metadata
    2. If valid (hash matches), use cached PageMetadata
    3. If invalid/missing, parse file and cache new metadata
    4. Templates access metadata directly (fast)
    5. Content accessed lazily via PageProxy (when needed)

Related:
    - bengal.core.page.page_core: PageCore (= PageMetadata) definition
    - bengal.core.page.proxy: PageProxy for lazy loading
    - bengal.orchestration.incremental: Uses this cache for builds
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from bengal.core.page.page_core import PageCore
from bengal.utils.atomic_write import AtomicFile
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


# PageMetadata IS PageCore - no field duplication!
# This type alias eliminates ~40 lines of duplicate field definitions.
# All fields are defined once in PageCore and automatically available here.
PageMetadata = PageCore


@dataclass
class PageDiscoveryCacheEntry:
    """Cache entry with metadata and validity information."""

    metadata: PageMetadata
    cached_at: str  # ISO timestamp when cached
    is_valid: bool = True  # Whether cache entry is still valid

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": asdict(self.metadata),  # asdict() works directly with PageCore
            "cached_at": self.cached_at,
            "is_valid": self.is_valid,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> PageDiscoveryCacheEntry:
        # PageMetadata = PageCore, so PageCore(**data) works
        metadata = PageCore(**data["metadata"])
        return PageDiscoveryCacheEntry(
            metadata=metadata,
            cached_at=data["cached_at"],
            is_valid=data.get("is_valid", True),
        )


class PageDiscoveryCache:
    """
    Persistent cache for page metadata enabling lazy page loading.

    Purpose:
    - Store page metadata (title, date, tags, section, slug)
    - Enable incremental discovery (only load changed pages)
    - Support lazy loading of full page content on demand
    - Validate cache entries to detect stale data

    Cache Format (JSON):
    {
        "pages": {
            "content/index.md": {
                "metadata": {
                    "source_path": "content/index.md",
                    "title": "Home",
                    ...
                },
                "cached_at": "2025-10-16T12:00:00",
                "is_valid": true
            }
        }
    }

    Note: If cache format changes, load will fail and cache rebuilds automatically.
    """

    CACHE_FILE = ".bengal/page_metadata.json"

    def __init__(self, cache_path: Path | None = None):
        """
        Initialize cache.

        Args:
            cache_path: Path to cache file (defaults to .bengal/page_metadata.json)
        """
        if cache_path is None:
            cache_path = Path(self.CACHE_FILE)
        self.cache_path = Path(cache_path)
        self.pages: dict[str, PageDiscoveryCacheEntry] = {}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load cache from disk if it exists."""
        if not self.cache_path.exists():
            logger.debug("page_discovery_cache_not_found", path=str(self.cache_path))
            return

        try:
            with open(self.cache_path) as f:
                data = json.load(f)

            # Load cache entries (no version check - just fail and rebuild if format changed)
            for path_str, entry_data in data.get("pages", {}).items():
                self.pages[path_str] = PageDiscoveryCacheEntry.from_dict(entry_data)

            logger.info(
                "page_discovery_cache_loaded",
                entries=len(self.pages),
                path=str(self.cache_path),
            )
        except Exception as e:
            from bengal.errors import BengalCacheError, ErrorContext, enrich_error

            # Enrich error with context
            context = ErrorContext(
                file_path=self.cache_path,
                operation="loading page discovery cache",
                suggestion="Cache file may be corrupted. It will be rebuilt automatically.",
                original_error=e,
            )
            enriched = enrich_error(e, context, BengalCacheError)
            logger.warning(
                "page_discovery_cache_load_failed",
                error=str(enriched),
                path=str(self.cache_path),
            )
            self.pages = {}

    def save_to_disk(self) -> None:
        """Save cache to disk."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "pages": {path: entry.to_dict() for path, entry in self.pages.items()},
            }

            # Atomic write to avoid partial/corrupt files on crash
            with AtomicFile(self.cache_path, "w", encoding="utf-8") as f:
                # Use custom default handler for datetime objects
                json.dump(data, f, indent=2, default=str)

            logger.info(
                "page_discovery_cache_saved",
                entries=len(self.pages),
                path=str(self.cache_path),
            )
        except Exception as e:
            logger.error(
                "page_discovery_cache_save_failed",
                error=str(e),
                path=str(self.cache_path),
            )

    def has_metadata(self, source_path: Path) -> bool:
        """
        Check if metadata is cached for a page.

        Args:
            source_path: Path to source file

        Returns:
            True if valid metadata exists in cache
        """
        path_str = str(source_path)
        if path_str not in self.pages:
            return False

        entry = self.pages[path_str]
        return entry.is_valid

    def get_metadata(self, source_path: Path) -> PageMetadata | None:
        """
        Get cached metadata for a page.

        Args:
            source_path: Path to source file

        Returns:
            PageMetadata if found and valid, None otherwise
        """
        path_str = str(source_path)
        if path_str not in self.pages:
            return None

        entry = self.pages[path_str]
        if not entry.is_valid:
            return None

        return entry.metadata

    def add_metadata(self, metadata: PageMetadata) -> None:
        """
        Add or update metadata in cache.

        Args:
            metadata: PageMetadata to cache
        """
        entry = PageDiscoveryCacheEntry(
            metadata=metadata,
            cached_at=datetime.utcnow().isoformat(),
            is_valid=True,
        )
        self.pages[metadata.source_path] = entry

    def invalidate(self, source_path: Path) -> None:
        """
        Mark a cache entry as invalid.

        Args:
            source_path: Path to source file to invalidate
        """
        path_str = str(source_path)
        if path_str in self.pages:
            self.pages[path_str].is_valid = False

    def invalidate_all(self) -> None:
        """Invalidate all cache entries."""
        for entry in self.pages.values():
            entry.is_valid = False

    def clear(self) -> None:
        """Clear all cache entries."""
        self.pages.clear()

    def get_valid_entries(self) -> dict[str, PageMetadata]:
        """
        Get all valid cached metadata entries.

        Returns:
            Dictionary mapping source_path to PageMetadata for valid entries
        """
        return {path: entry.metadata for path, entry in self.pages.items() if entry.is_valid}

    def get_invalid_entries(self) -> dict[str, PageMetadata]:
        """
        Get all invalid cached metadata entries.

        Returns:
            Dictionary mapping source_path to PageMetadata for invalid entries
        """
        return {path: entry.metadata for path, entry in self.pages.items() if not entry.is_valid}

    def validate_entry(self, source_path: Path, current_file_hash: str) -> bool:
        """
        Validate a cache entry against current file hash.

        Args:
            source_path: Path to source file
            current_file_hash: Current hash of source file

        Returns:
            True if cache entry is valid (hash matches), False otherwise
        """
        metadata = self.get_metadata(source_path)
        if metadata is None:
            return False

        if metadata.file_hash is None:
            # No hash stored, can't validate
            return True

        return metadata.file_hash == current_file_hash

    def stats(self) -> dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (total, valid, invalid)
        """
        valid = sum(1 for e in self.pages.values() if e.is_valid)
        invalid = len(self.pages) - valid

        return {
            "total_entries": len(self.pages),
            "valid_entries": valid,
            "invalid_entries": invalid,
            "cache_size_bytes": len(json.dumps([e.to_dict() for e in self.pages.values()])),
        }
