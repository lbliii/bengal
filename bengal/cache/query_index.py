"""
Query Index - Base class for queryable indexes.

Provides O(1) lookups for common page queries by pre-computing indexes
at build time. Similar to TaxonomyIndex but generalized for any page attribute.

Architecture:
- Build indexes once during build phase (O(n) cost)
- Persist to disk for incremental builds
- Template access is O(1) hash lookup
- Incrementally update only changed pages

Example:

```python
# Built-in indexes
site.indexes.section.get('blog')        # O(1) - all blog posts
site.indexes.author.get('Jane Smith')   # O(1) - posts by Jane

# Custom indexes
site.indexes.status.get('published')    # O(1) - published posts
```
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.cache.cacheable import Cacheable
from bengal.utils.hashing import hash_str
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache.build_cache import BuildCache
    from bengal.core.page import Page

logger = get_logger(__name__)


class IndexEntry(Cacheable):
    """
    A single entry in a query index.

    Represents one index key (e.g., 'blog' section, 'Jane Smith' author)
    and all pages that match that key.

    Implements the Cacheable protocol for type-safe serialization.

    Uses set for O(1) add/remove/contains operations.

    Attributes:
        key: Index key (e.g., 'blog', 'Jane Smith', '2024')
        page_paths: Set of page source paths for O(1) operations
        metadata: Extra data for display (e.g., section title, author email)
        updated_at: ISO timestamp of last update
        content_hash: Hash of page_paths for change detection
    """

    def __init__(
        self,
        key: str,
        page_paths: set[str] | None = None,
        metadata: dict[str, Any] | None = None,
        updated_at: str | None = None,
        content_hash: str = "",
    ) -> None:
        """Initialize IndexEntry."""
        self.key = key
        self.page_paths: set[str] = page_paths if page_paths is not None else set()
        self.metadata = metadata if metadata is not None else {}
        self.updated_at = updated_at if updated_at else datetime.now().isoformat()
        self.content_hash = content_hash if content_hash else self._compute_hash()

    def add_page(self, page_path: str) -> bool:
        """Add page to entry (O(1)). Returns True if page was added."""
        if page_path not in self.page_paths:
            self.page_paths.add(page_path)
            return True
        return False

    def remove_page(self, page_path: str) -> bool:
        """Remove page from entry (O(1)). Returns True if page was removed."""
        if page_path in self.page_paths:
            self.page_paths.discard(page_path)
            return True
        return False

    def __contains__(self, page_path: str) -> bool:
        """O(1) membership check."""
        return page_path in self.page_paths

    def __len__(self) -> int:
        """Return number of pages."""
        return len(self.page_paths)

    def _compute_hash(self) -> str:
        """Compute hash of page_paths for change detection."""
        # Sort for stable hash
        paths_str = json.dumps(sorted(self.page_paths), sort_keys=True)
        return hash_str(paths_str, truncate=16)

    def to_cache_dict(self) -> dict[str, Any]:
        """Serialize to cache-friendly dictionary (Cacheable protocol)."""
        return {
            "key": self.key,
            "page_paths": sorted(self.page_paths),  # Convert to sorted list for JSON
            "metadata": self.metadata,
            "updated_at": self.updated_at,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> IndexEntry:
        """Deserialize from cache dictionary (Cacheable protocol)."""
        return cls(
            key=data["key"],
            page_paths=set(data.get("page_paths", [])),
            metadata=data.get("metadata", {}),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            content_hash=data.get("content_hash", ""),
        )


class QueryIndex(ABC):
    """
    Base class for queryable indexes.

    Subclasses define:
    - What to index (e.g., by_section, by_author, by_tag)
    - How to extract keys from pages
    - Optionally: custom serialization logic

    The base class handles:
    - Index storage and persistence
    - Incremental updates
    - Change detection
    - O(1) lookups

    Example:
        class SectionIndex(QueryIndex):
            def extract_keys(self, page):
                section = page._section.name if page._section else None
                return [(section, {})] if section else []
    """

    VERSION = 1  # Schema version for cache invalidation

    def __init__(self, name: str, cache_path: Path):
        """
        Initialize query index.

        Args:
            name: Index name (e.g., 'section', 'author')
            cache_path: Path to cache file (e.g., .bengal/indexes/section_index.json)
        """
        self.name = name
        self.cache_path = Path(cache_path)
        self.entries: dict[str, IndexEntry] = {}
        self._page_to_keys: dict[str, set[str]] = {}  # Reverse index for updates
        self._load_from_disk()

    @abstractmethod
    def extract_keys(self, page: Page) -> list[tuple[str, dict[str, Any]]]:
        """
        Extract index keys from a page.

        Returns list of (key, metadata) tuples. Can return multiple keys
        for multi-valued indexes (e.g., multi-author papers, multiple tags).

        Args:
            page: Page to extract keys from

        Returns:
            List of (key, metadata) tuples

        Example:
            # Single-valued
            return [('blog', {'title': 'Blog'})]

            # Multi-valued
            return [
                ('Jane Smith', {'email': 'jane@example.com'}),
                ('Bob Jones', {'email': 'bob@example.com'})
            ]

            # Empty (skip this page)
            return []
        """
        pass

    def update_page(self, page: Page, build_cache: BuildCache) -> set[str]:
        """
        Update index for a single page.

        Handles:
        - Removing page from old keys
        - Adding page to new keys
        - Tracking affected keys for incremental regeneration

        Args:
            page: Page to update
            build_cache: Build cache for dependency tracking

        Returns:
            Set of affected index keys (need regeneration)
        """
        page_path = str(page.source_path)

        # Get old keys for this page
        old_keys = self._page_to_keys.get(page_path, set())

        # Get new keys
        new_keys_data = self.extract_keys(page)
        new_keys = {k for k, _ in new_keys_data}

        # Find changes
        removed = old_keys - new_keys
        added = new_keys - old_keys
        unchanged = old_keys & new_keys

        # Update index
        for key in removed:
            self._remove_page_from_key(key, page_path)

        for key, metadata in new_keys_data:
            self._add_page_to_key(key, page_path, metadata)

        # Update reverse index
        self._page_to_keys[page_path] = new_keys

        # Return all affected keys (for incremental regeneration)
        affected = removed | added | unchanged

        if affected:
            logger.debug(
                "index_page_updated",
                index=self.name,
                page=page_path,
                added=len(added),
                removed=len(removed),
                unchanged=len(unchanged),
            )

        return affected

    def remove_page(self, page_path: str) -> set[str]:
        """
        Remove page from all index entries.

        Args:
            page_path: Path to page source file

        Returns:
            Set of affected keys
        """
        old_keys = self._page_to_keys.get(page_path, set())

        for key in old_keys:
            self._remove_page_from_key(key, page_path)

        if page_path in self._page_to_keys:
            del self._page_to_keys[page_path]

        return old_keys

    def get(self, key: str) -> set[str]:
        """
        Get page paths for index key (O(1) lookup).

        Args:
            key: Index key

        Returns:
            Set of page paths (copy, safe to modify)
        """
        entry = self.entries.get(key)
        return entry.page_paths.copy() if entry else set()

    def keys(self) -> list[str]:
        """Get all index keys."""
        return list(self.entries.keys())

    def has_changed(self, key: str, page_paths: set[str]) -> bool:
        """
        Check if index entry changed (for skip optimization).

        Args:
            key: Index key
            page_paths: New set of page paths

        Returns:
            True if entry changed and needs regeneration
        """
        entry = self.entries.get(key)
        if not entry:
            return True  # New key

        return entry.page_paths != page_paths

    def get_metadata(self, key: str) -> dict[str, Any]:
        """
        Get metadata for index key.

        Args:
            key: Index key

        Returns:
            Metadata dict (empty if key not found)
        """
        entry = self.entries.get(key)
        return entry.metadata.copy() if entry else {}

    def save_to_disk(self) -> None:
        """Persist index to disk."""
        # Verify consistency before save (debug mode only)
        # RFC: Cache Lifecycle Hardening - Phase 3
        # Note: Check invariants unconditionally but only log violations
        # This is a simple O(n) check that detects index corruption
        violations = self._check_invariants()
        if violations:
            logger.warning(
                "query_index_invariant_violation",
                index=self.name,
                violations=violations[:5],  # First 5
                total=len(violations),
                action="saving_anyway",
            )

        data = {
            "version": self.VERSION,
            "name": self.name,
            "entries": {key: entry.to_cache_dict() for key, entry in self.entries.items()},
            "updated_at": datetime.now().isoformat(),
        }

        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            # Use atomic write
            from bengal.utils.atomic_write import AtomicFile

            with AtomicFile(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(
                "index_saved",
                index=self.name,
                path=str(self.cache_path),
                entries=len(self.entries),
            )
        except Exception as e:
            from bengal.errors import ErrorCode

            logger.warning(
                "index_save_failed",
                index=self.name,
                path=str(self.cache_path),
                error=str(e),
                error_code=ErrorCode.A004.value,  # cache_write_error
                suggestion="Cache write failed. Check disk space and permissions.",
            )

    def _load_from_disk(self) -> None:
        """Load index from disk."""
        if not self.cache_path.exists():
            logger.debug("index_not_found", index=self.name, path=str(self.cache_path))
            return

        try:
            with open(self.cache_path, encoding="utf-8") as f:
                data = json.load(f)

            # Type validation to prevent 'str' object has no attribute 'get' errors
            if not isinstance(data, dict):
                logger.warning(
                    "index_invalid_data_type",
                    index=self.name,
                    expected="dict",
                    got=type(data).__name__,
                    suggestion="Cache file corrupted. Index will be rebuilt.",
                )
                self.entries = {}
                return

            # Version check
            from bengal.errors import ErrorCode

            if data.get("version") != self.VERSION:
                logger.warning(
                    "index_version_mismatch",
                    index=self.name,
                    expected=self.VERSION,
                    found=data.get("version"),
                    error_code=ErrorCode.A002.value,  # cache_version_mismatch
                    suggestion="Cache version incompatible. Index will be rebuilt.",
                )
                self.entries = {}
                return

            # Load entries
            for key, entry_data in data.get("entries", {}).items():
                entry = IndexEntry.from_cache_dict(entry_data)
                self.entries[key] = entry

                # Build reverse index
                for page_path in entry.page_paths:
                    if page_path not in self._page_to_keys:
                        self._page_to_keys[page_path] = set()
                    self._page_to_keys[page_path].add(key)

            # Verify invariants after load (detect corruption early)
            # RFC: Cache Lifecycle Hardening - Phase 3
            violations = self._check_invariants()
            if violations:
                logger.warning(
                    "query_index_corruption_detected",
                    index=self.name,
                    violations=violations[:5],  # First 5
                    total=len(violations),
                    action="rebuilding_index",
                )
                # Clear and let it rebuild naturally
                self.entries = {}
                self._page_to_keys = {}
                return

            logger.info(
                "index_loaded",
                index=self.name,
                path=str(self.cache_path),
                entries=len(self.entries),
            )
        except Exception as e:
            from bengal.errors import ErrorCode

            logger.warning(
                "index_load_failed",
                index=self.name,
                path=str(self.cache_path),
                error=str(e),
                error_code=ErrorCode.A003.value,  # cache_read_error
                suggestion="Cache read failed. Index will be rebuilt automatically.",
            )
            self.entries = {}

    def _add_page_to_key(self, key: str, page_path: str, metadata: dict[str, Any]) -> None:
        """
        Add page to index key (O(1) via set).

        Args:
            key: Index key
            page_path: Path to page source file
            metadata: Metadata to store with this entry
        """
        if key not in self.entries:
            self.entries[key] = IndexEntry(
                key=key,
                metadata=metadata,
            )

        # O(1) set add
        if self.entries[key].add_page(page_path):
            self.entries[key].updated_at = datetime.now().isoformat()
            self.entries[key].content_hash = self.entries[key]._compute_hash()

    def _remove_page_from_key(self, key: str, page_path: str) -> None:
        """
        Remove page from index key (O(1) via set).

        Performance: O(1) instead of O(p) list.remove().
        (RFC: Cache Algorithm Optimization)

        Args:
            key: Index key
            page_path: Path to page source file
        """
        if key not in self.entries or page_path not in self.entries[key]:
            return

        # O(1) set discard
        if self.entries[key].remove_page(page_path):
            self.entries[key].updated_at = datetime.now().isoformat()
            self.entries[key].content_hash = self.entries[key]._compute_hash()

            # Remove empty entries
            if len(self.entries[key]) == 0:
                del self.entries[key]
                logger.debug("index_key_removed", index=self.name, key=key, reason="empty")

    def clear(self) -> None:
        """Clear all index data."""
        self.entries.clear()
        self._page_to_keys.clear()

    def _check_invariants(self) -> list[str]:
        """
        Verify forward and reverse indexes are in sync.

        RFC: Cache Lifecycle Hardening - Phase 3
        Detects index desync early before it causes subtle bugs.

        Returns:
            List of violations (empty if consistent)
        """
        violations: list[str] = []

        # Check 1: Every page in _page_to_keys has its keys in entries
        for page, keys in self._page_to_keys.items():
            for key in keys:
                if key not in self.entries:
                    violations.append(f"Reverse has key '{key}' for page '{page}' not in forward")
                elif page not in self.entries[key].page_paths:
                    violations.append(f"Page '{page}' in reverse for key '{key}' not in forward")

        # Check 2: Every page in entries[key].page_paths exists in _page_to_keys
        for key, entry in self.entries.items():
            for page in entry.page_paths:
                if page not in self._page_to_keys:
                    violations.append(f"Page '{page}' in forward for key '{key}' not in reverse")
                elif key not in self._page_to_keys[page]:
                    violations.append(f"Key '{key}' for page '{page}' in forward not in reverse")

        return violations

    def stats(self) -> dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Dictionary with index stats
        """
        total_pages = sum(len(entry.page_paths) for entry in self.entries.values())
        unique_pages = len(self._page_to_keys)

        return {
            "name": self.name,
            "total_keys": len(self.entries),
            "total_page_entries": total_pages,
            "unique_pages": unique_pages,
            "avg_pages_per_key": total_pages / len(self.entries) if self.entries else 0,
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"QueryIndex(name={self.name}, keys={len(self.entries)})"
