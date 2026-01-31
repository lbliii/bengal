"""
Taxonomy Index for incremental builds.

Maintains persistent index of tag-to-pages mappings to enable incremental
taxonomy updates. Instead of rebuilding the entire taxonomy structure,
incremental builds can update only affected tags.

Architecture:
- Mapping: tag_slug → [page_paths] (which pages have which tags)
- Storage: .bengal/taxonomy_index.json (compact format)
- Tracking: Built during page discovery, updated on tag changes
- Incremental: Only update affected tags, reuse unchanged tags

Performance Impact:
- Taxonomy rebuild skipped for unchanged pages (~60ms saved per 100 pages)
- Only affected tags regenerated
- Avoid full taxonomy structure rebuild
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bengal.cache.utils import (
    PersistentCacheMixin,
    check_bidirectional_invariants,
    compute_taxonomy_stats,
)
from bengal.protocols import Cacheable
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TagEntry(Cacheable):
    """
    Entry for a single tag in the index.

    Implements the Cacheable protocol for type-safe serialization.

    """

    tag_slug: str  # Normalized tag identifier
    tag_name: str  # Original tag name (for display)
    page_paths: list[str]  # Pages with this tag
    updated_at: str  # ISO timestamp of last update
    is_valid: bool = True  # Whether entry is still valid

    def to_cache_dict(self) -> dict[str, Any]:
        """Serialize to cache-friendly dictionary (Cacheable protocol)."""
        return {
            "tag_slug": self.tag_slug,
            "tag_name": self.tag_name,
            "page_paths": self.page_paths,
            "updated_at": self.updated_at,
            "is_valid": self.is_valid,
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> TagEntry:
        """Deserialize from cache dictionary (Cacheable protocol)."""
        return cls(
            tag_slug=data["tag_slug"],
            tag_name=data["tag_name"],
            page_paths=data["page_paths"],
            updated_at=data["updated_at"],
            is_valid=data.get("is_valid", True),
        )


class TaxonomyIndex(PersistentCacheMixin):
    """
    Persistent index of tag-to-pages mappings for incremental taxonomy updates.

    Purpose:
    - Track which pages have which tags
    - Enable incremental tag updates (only changed tags)
    - Avoid full taxonomy rebuild on every page change
    - Support incremental tag page generation

    Cache Format (JSON):
    {
        "version": 2,
        "tags": {
            "python": {
                "tag_slug": "python",
                "tag_name": "Python",
                "page_paths": ["content/post1.md", "content/post2.md"],
                "updated_at": "2025-10-16T12:00:00",
                "is_valid": true
            }
        },
        "page_to_tags": {
            "content/post1.md": ["python", "tutorial"],
            "content/post2.md": ["python"]
        }
    }

    Performance Optimization (RFC: Cache Algorithm Optimization):
    - Added reverse index (_page_to_tags) for O(1) page-to-tags lookup
    - get_tags_for_page(): O(t×p) → O(1)
    - remove_page_from_all_tags(): O(t×p) → O(t') where t' = tags for page

    Thread Safety:
    - All mutating operations are protected by an RLock
    - Safe for concurrent access during parallel builds

    """

    VERSION = 2  # Bumped: added page_to_tags reverse index
    CACHE_FILE = ".bengal/taxonomy_index.json"

    def __init__(self, cache_path: Path | None = None):
        """
        Initialize taxonomy index.

        Args:
            cache_path: Path to cache file (defaults to .bengal/taxonomy_index.json)
        """
        if cache_path is None:
            cache_path = Path(self.CACHE_FILE)
        self.cache_path = Path(cache_path)
        self.tags: dict[str, TagEntry] = {}
        # Reverse index for O(1) page → tags lookup (RFC: Cache Algorithm Optimization)
        self._page_to_tags: dict[str, set[str]] = {}
        # Thread safety lock for concurrent access
        self._lock = threading.RLock()
        self._load_cache()

    # =========================================================================
    # PersistentCacheMixin implementation
    # =========================================================================

    def _deserialize(self, data: dict[str, Any]) -> None:
        """Deserialize loaded data into cache state."""
        # Load tag entries
        for tag_slug, entry_data in data.get("tags", {}).items():
            self.tags[tag_slug] = TagEntry.from_cache_dict(entry_data)

        # Load reverse index
        for page, tags in data.get("page_to_tags", {}).items():
            self._page_to_tags[page] = set(tags)

        # Verify invariants after load (detect corruption early)
        violations = self._check_invariants()
        if violations:
            logger.warning(
                "taxonomy_index_corruption_detected",
                violations=violations[:5],
                total=len(violations),
                action="rebuilding_index",
            )
            self._on_version_mismatch()
            return

        logger.info(
            "taxonomy_index_loaded",
            tags=len(self.tags),
            pages_indexed=len(self._page_to_tags),
        )

    def _serialize(self) -> dict[str, Any]:
        """Serialize cache state for saving."""
        return {
            "tags": {tag_slug: entry.to_cache_dict() for tag_slug, entry in self.tags.items()},
            "page_to_tags": {page: list(tags) for page, tags in self._page_to_tags.items()},
        }

    def _on_version_mismatch(self) -> None:
        """Clear state on version mismatch."""
        self.tags = {}
        self._page_to_tags = {}

    def save_to_disk(self) -> None:
        """Save taxonomy index to disk (including reverse index)."""
        with self._lock:
            # Verify consistency before save
            violations = self._check_invariants()
            if violations:
                logger.warning(
                    "taxonomy_index_invariant_violation",
                    violations=violations[:5],
                    total=len(violations),
                    action="clearing_and_skipping_save",
                )
                self.tags.clear()
                self._page_to_tags.clear()
                return

            self._save_cache()

    # =========================================================================
    # Invariant checking using shared utility
    # =========================================================================

    def _check_invariants(self) -> list[str]:
        """
        Verify forward and reverse indexes are in sync.

        Uses shared check_bidirectional_invariants utility.
        """
        return check_bidirectional_invariants(
            forward={tag: entry for tag, entry in self.tags.items()},
            reverse=self._page_to_tags,
            forward_getter=lambda entry: set(entry.page_paths),
        )

    # =========================================================================
    # Tag operations
    # =========================================================================

    def update_tag(self, tag_slug: str, tag_name: str, page_paths: list[str]) -> None:
        """
        Update or create a tag entry.

        Maintains reverse index for O(1) page-to-tags lookup.

        Args:
            tag_slug: Normalized tag identifier
            tag_name: Original tag name for display
            page_paths: List of page paths with this tag
        """
        with self._lock:
            # Get old pages for this tag (if exists)
            old_entry = self.tags.get(tag_slug)
            old_pages = set(old_entry.page_paths) if old_entry else set()
            new_pages = set(page_paths)

            # Update reverse index: remove old mappings for pages no longer in this tag
            for page in old_pages - new_pages:
                if page in self._page_to_tags:
                    self._page_to_tags[page].discard(tag_slug)
                    # Clean up empty entries
                    if not self._page_to_tags[page]:
                        del self._page_to_tags[page]

            # Update reverse index: add new mappings
            for page in new_pages:
                if page not in self._page_to_tags:
                    self._page_to_tags[page] = set()
                self._page_to_tags[page].add(tag_slug)

            # Create/update entry
            entry = TagEntry(
                tag_slug=tag_slug,
                tag_name=tag_name,
                page_paths=page_paths,
                updated_at=datetime.now(UTC).isoformat(),
                is_valid=True,
            )
            self.tags[tag_slug] = entry

    def get_tag(self, tag_slug: str) -> TagEntry | None:
        """
        Get a tag entry by slug.

        Args:
            tag_slug: Normalized tag identifier

        Returns:
            TagEntry if found and valid, None otherwise
        """
        with self._lock:
            if tag_slug not in self.tags:
                return None

            entry = self.tags[tag_slug]
            if not entry.is_valid:
                return None

            return entry

    def get_pages_for_tag(self, tag_slug: str) -> list[str] | None:
        """
        Get pages with a specific tag.

        Args:
            tag_slug: Normalized tag identifier

        Returns:
            List of page paths or None if tag not found/invalid
        """
        entry = self.get_tag(tag_slug)
        return list(entry.page_paths) if entry else None

    def has_tag(self, tag_slug: str) -> bool:
        """
        Check if tag exists and is valid.

        Args:
            tag_slug: Normalized tag identifier

        Returns:
            True if tag exists and is valid
        """
        with self._lock:
            if tag_slug not in self.tags:
                return False

            entry = self.tags[tag_slug]
            return entry.is_valid

    def get_tags_for_page(self, page_path: Path) -> set[str]:
        """
        Get all tags for a specific page (O(1) via reverse index).

        Performance: O(1) lookup instead of O(t×p) scan.
        (RFC: Cache Algorithm Optimization)

        Args:
            page_path: Path to page

        Returns:
            Set of tag slugs for this page
        """
        with self._lock:
            page_str = str(page_path)
            # O(1) lookup via reverse index
            tags = self._page_to_tags.get(page_str, set())
            # Filter to only valid tags
            return {tag for tag in tags if tag in self.tags and self.tags[tag].is_valid}

    def get_all_tags(self) -> dict[str, TagEntry]:
        """
        Get all valid tags.

        Returns:
            Dictionary mapping tag_slug to TagEntry for valid tags
        """
        with self._lock:
            return {tag_slug: entry for tag_slug, entry in self.tags.items() if entry.is_valid}

    # =========================================================================
    # Invalidation
    # =========================================================================

    def invalidate_tag(self, tag_slug: str) -> None:
        """
        Mark a tag as invalid.

        Note: Does not remove from reverse index since tag might be revalidated.
        The get_tags_for_page() filters invalid tags.

        Args:
            tag_slug: Normalized tag identifier
        """
        with self._lock:
            if tag_slug in self.tags:
                self.tags[tag_slug].is_valid = False

    def invalidate_all(self) -> None:
        """Invalidate all tag entries."""
        with self._lock:
            for entry in self.tags.values():
                entry.is_valid = False

    def clear(self) -> None:
        """Clear all tags and reverse index."""
        with self._lock:
            self.tags.clear()
            self._page_to_tags.clear()

    def remove_page_from_all_tags(self, page_path: Path) -> set[str]:
        """
        Remove a page from all tags it belongs to (O(t') via reverse index).

        Performance: O(t') where t' = tags for this specific page,
        instead of O(t×p) scanning all tags.
        (RFC: Cache Algorithm Optimization)

        Args:
            page_path: Path to page to remove

        Returns:
            Set of affected tag slugs
        """
        with self._lock:
            page_str = str(page_path)

            # O(1) lookup of affected tags via reverse index
            affected_tags = self._page_to_tags.get(page_str, set()).copy()

            # Remove page from each affected tag's page list
            for tag_slug in affected_tags:
                if tag_slug in self.tags:
                    entry = self.tags[tag_slug]
                    if page_str in entry.page_paths:
                        entry.page_paths.remove(page_str)

            # Clean up reverse index
            if page_str in self._page_to_tags:
                del self._page_to_tags[page_str]

            return affected_tags

    # =========================================================================
    # Query helpers
    # =========================================================================

    def get_valid_entries(self) -> dict[str, TagEntry]:
        """
        Get all valid tag entries.

        Returns:
            Dictionary mapping tag_slug to TagEntry for valid entries
        """
        return {tag_slug: entry for tag_slug, entry in self.tags.items() if entry.is_valid}

    def get_invalid_entries(self) -> dict[str, TagEntry]:
        """
        Get all invalid tag entries.

        Returns:
            Dictionary mapping tag_slug to TagEntry for invalid entries
        """
        return {tag_slug: entry for tag_slug, entry in self.tags.items() if not entry.is_valid}

    def pages_changed(self, tag_slug: str, new_page_paths: list[str]) -> bool:
        """
        Check if pages for a tag have changed (enabling skipping of unchanged tag regeneration).

        This is the key optimization for Phase 2c.2: If a tag's page membership hasn't changed,
        we can skip regenerating its HTML pages entirely since the output would be identical.

        Args:
            tag_slug: Normalized tag identifier
            new_page_paths: New list of page paths for this tag

        Returns:
            True if tag pages have changed and need regeneration
            False if tag pages are identical to cached version
        """
        # New tag - always needs generation
        entry = self.get_tag(tag_slug)
        if not entry:
            return True

        # Compare as sets (order doesn't matter for HTML generation)
        # Since pages are always sorted by date in output, set comparison is sufficient
        old_paths = set(entry.page_paths)
        new_paths = set(new_page_paths)

        changed = old_paths != new_paths
        logger.debug(
            "tag_pages_comparison",
            tag_slug=tag_slug,
            old_count=len(old_paths),
            new_count=len(new_paths),
            changed=changed,
        )

        return changed

    # =========================================================================
    # Statistics using shared utility
    # =========================================================================

    def stats(self) -> dict[str, Any]:
        """
        Get taxonomy index statistics.

        Returns:
            Dictionary with index stats
        """
        return compute_taxonomy_stats(
            tags=self.tags,
            is_valid=lambda e: e.is_valid,
            get_page_paths=lambda e: e.page_paths,
            serialize=lambda e: e.to_cache_dict(),
        )
