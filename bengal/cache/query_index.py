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
from dataclasses import dataclass, field
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


@dataclass
class IndexEntry(Cacheable):
    """
    A single entry in a query index.

    Represents one index key (e.g., 'blog' section, 'Jane Smith' author)
    and all pages that match that key.

    Implements the Cacheable protocol for type-safe serialization.

    Attributes:
        key: Index key (e.g., 'blog', 'Jane Smith', '2024')
        page_paths: List of page source paths (strings, not Page objects)
        metadata: Extra data for display (e.g., section title, author email)
        updated_at: ISO timestamp of last update
        content_hash: Hash of page_paths for change detection
    """

    key: str
    page_paths: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    content_hash: str = ""

    def __post_init__(self) -> None:
        """Compute content hash if not provided."""
        if not self.content_hash:
            self.content_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute hash of page_paths for change detection."""
        # Sort for stable hash
        paths_str = json.dumps(sorted(self.page_paths), sort_keys=True)
        return hash_str(paths_str, truncate=16)

    def to_cache_dict(self) -> dict[str, Any]:
        """Serialize to cache-friendly dictionary (Cacheable protocol)."""
        return {
            "key": self.key,
            "page_paths": self.page_paths,
            "metadata": self.metadata,
            "updated_at": self.updated_at,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> IndexEntry:
        """Deserialize from cache dictionary (Cacheable protocol)."""
        return cls(
            key=data["key"],
            page_paths=data.get("page_paths", []),
            metadata=data.get("metadata", {}),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            content_hash=data.get("content_hash", ""),
        )

    # Aliases for backward compatibility
    def to_dict(self) -> dict[str, Any]:
        """Alias for to_cache_dict (backward compatibility)."""
        return self.to_cache_dict()

    @staticmethod
    def from_dict(data: dict[str, Any]) -> IndexEntry:
        """Alias for from_cache_dict (backward compatibility)."""
        return IndexEntry.from_cache_dict(data)


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

    def get(self, key: str) -> list[str]:
        """
        Get page paths for index key (O(1) lookup).

        Args:
            key: Index key

        Returns:
            List of page paths (copy, safe to modify)
        """
        entry = self.entries.get(key)
        return entry.page_paths.copy() if entry else []

    def keys(self) -> list[str]:
        """Get all index keys."""
        return list(self.entries.keys())

    def has_changed(self, key: str, page_paths: list[str]) -> bool:
        """
        Check if index entry changed (for skip optimization).

        Compares page_paths as sets (order doesn't matter for most use cases).

        Args:
            key: Index key
            page_paths: New list of page paths

        Returns:
            True if entry changed and needs regeneration
        """
        entry = self.entries.get(key)
        if not entry:
            return True  # New key

        # Compare as sets
        return set(entry.page_paths) != set(page_paths)

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
            logger.warning(
                "index_save_failed",
                index=self.name,
                path=str(self.cache_path),
                error=str(e),
            )

    def _load_from_disk(self) -> None:
        """Load index from disk."""
        if not self.cache_path.exists():
            logger.debug("index_not_found", index=self.name, path=str(self.cache_path))
            return

        try:
            with open(self.cache_path, encoding="utf-8") as f:
                data = json.load(f)

            # Version check
            if data.get("version") != self.VERSION:
                logger.warning(
                    "index_version_mismatch",
                    index=self.name,
                    expected=self.VERSION,
                    found=data.get("version"),
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

            logger.info(
                "index_loaded",
                index=self.name,
                path=str(self.cache_path),
                entries=len(self.entries),
            )
        except Exception as e:
            logger.warning(
                "index_load_failed",
                index=self.name,
                path=str(self.cache_path),
                error=str(e),
            )
            self.entries = {}

    def _add_page_to_key(self, key: str, page_path: str, metadata: dict[str, Any]) -> None:
        """
        Add page to index key.

        Args:
            key: Index key
            page_path: Path to page source file
            metadata: Metadata to store with this entry
        """
        if key not in self.entries:
            self.entries[key] = IndexEntry(
                key=key,
                page_paths=[],
                metadata=metadata,
            )

        if page_path not in self.entries[key].page_paths:
            self.entries[key].page_paths.append(page_path)
            self.entries[key].updated_at = datetime.now().isoformat()
            self.entries[key].content_hash = self.entries[key]._compute_hash()

    def _remove_page_from_key(self, key: str, page_path: str) -> None:
        """
        Remove page from index key.

        Args:
            key: Index key
            page_path: Path to page source file
        """
        if key in self.entries and page_path in self.entries[key].page_paths:
            self.entries[key].page_paths.remove(page_path)
            self.entries[key].updated_at = datetime.now().isoformat()
            self.entries[key].content_hash = self.entries[key]._compute_hash()

            # Remove empty entries
            if not self.entries[key].page_paths:
                del self.entries[key]
                logger.debug("index_key_removed", index=self.name, key=key, reason="empty")

    def clear(self) -> None:
        """Clear all index data."""
        self.entries.clear()
        self._page_to_keys.clear()

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
