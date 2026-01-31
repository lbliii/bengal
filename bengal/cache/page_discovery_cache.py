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

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bengal.cache.utils import PersistentCacheMixin, compute_validity_stats
from bengal.core.page.page_core import PageCore
from bengal.protocols import Cacheable
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


# PageMetadata IS PageCore - no field duplication!
# This type alias eliminates ~40 lines of duplicate field definitions.
# All fields are defined once in PageCore and automatically available here.
PageMetadata = PageCore


@dataclass
class PageDiscoveryCacheEntry(Cacheable):
    """Cache entry with metadata and validity information."""

    metadata: PageMetadata
    cached_at: str  # ISO timestamp when cached
    is_valid: bool = True  # Whether cache entry is still valid

    def to_cache_dict(self) -> dict[str, Any]:
        """Serialize to cache-friendly dictionary (Cacheable protocol)."""
        return {
            "metadata": self.metadata.to_cache_dict(),
            "cached_at": self.cached_at,
            "is_valid": self.is_valid,
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> PageDiscoveryCacheEntry:
        """Deserialize from cache dictionary (Cacheable protocol)."""
        metadata = PageCore.from_cache_dict(data["metadata"])
        return cls(
            metadata=metadata,
            cached_at=data["cached_at"],
            is_valid=data.get("is_valid", True),
        )


class PageDiscoveryCache(PersistentCacheMixin):
    """
    Persistent cache for page metadata enabling lazy page loading.

    Purpose:
    - Store page metadata (title, date, tags, section, slug)
    - Enable incremental discovery (only load changed pages)
    - Support lazy loading of full page content on demand
    - Validate cache entries to detect stale data

    Cache Format (JSON):
    {
        "version": 1,
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

    VERSION = 1
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
        self._load_cache()

    # =========================================================================
    # PersistentCacheMixin implementation
    # =========================================================================

    def _deserialize(self, data: dict[str, Any]) -> None:
        """Deserialize loaded data into cache state."""
        for path_str, entry_data in data.get("pages", {}).items():
            self.pages[path_str] = PageDiscoveryCacheEntry.from_cache_dict(entry_data)

        logger.info(
            "page_discovery_cache_loaded",
            entries=len(self.pages),
        )

    def _serialize(self) -> dict[str, Any]:
        """Serialize cache state for saving."""
        return {
            "pages": {path: entry.to_cache_dict() for path, entry in self.pages.items()},
        }

    def _on_version_mismatch(self) -> None:
        """Clear state on version mismatch."""
        self.pages = {}

    def save_to_disk(self) -> None:
        """Save cache to disk."""
        self._save_cache()

    # =========================================================================
    # Metadata operations
    # =========================================================================

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
            cached_at=datetime.now(UTC).isoformat(),
            is_valid=True,
        )
        self.pages[metadata.source_path] = entry

    # =========================================================================
    # Invalidation
    # =========================================================================

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

    # =========================================================================
    # Query helpers
    # =========================================================================

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

    # =========================================================================
    # Statistics
    # =========================================================================

    def stats(self) -> dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (total, valid, invalid)
        """
        return compute_validity_stats(
            entries=self.pages,
            is_valid=lambda e: e.is_valid,
            serialize=lambda e: e.to_cache_dict(),
        )
