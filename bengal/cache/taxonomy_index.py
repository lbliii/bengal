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

import json
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bengal.cache.compression import load_auto, save_compressed
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

    # Aliases for test compatibility
    def to_dict(self) -> dict[str, Any]:
        """Alias for to_cache_dict (test compatibility)."""
        return self.to_cache_dict()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TagEntry:
        """Alias for from_cache_dict (test compatibility)."""
        return cls.from_cache_dict(data)


class TaxonomyIndex:
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
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load taxonomy index from disk if file exists."""
        # load_auto handles both .json.zst and .json formats
        compressed_path = self.cache_path.with_suffix(".json.zst")
        if not compressed_path.exists() and not self.cache_path.exists():
            logger.debug("taxonomy_index_not_found", path=str(self.cache_path))
            return

        try:
            # load_auto tries .json.zst first, falls back to .json
            data = load_auto(self.cache_path)

            # Version check - clear on mismatch
            from bengal.errors import ErrorCode

            if data.get("version") != self.VERSION:
                logger.warning(
                    "taxonomy_index_version_mismatch",
                    expected=self.VERSION,
                    found=data.get("version"),
                    action="clearing_cache",
                    error_code=ErrorCode.A002.value,  # cache_version_mismatch
                    suggestion="Cache version incompatible. Taxonomy index will be rebuilt.",
                )
                self.tags = {}
                self._page_to_tags = {}
                return

            # Load tag entries
            for tag_slug, entry_data in data.get("tags", {}).items():
                self.tags[tag_slug] = TagEntry.from_cache_dict(entry_data)

            # Load reverse index
            for page, tags in data.get("page_to_tags", {}).items():
                self._page_to_tags[page] = set(tags)

            # Verify invariants after load (detect corruption early)
            # RFC: Cache Lifecycle Hardening - Phase 3
            violations = self._check_invariants()
            if violations:
                logger.warning(
                    "taxonomy_index_corruption_detected",
                    violations=violations[:5],  # First 5
                    total=len(violations),
                    action="rebuilding_index",
                )
                # Clear and let it rebuild naturally
                self.tags = {}
                self._page_to_tags = {}
                return

            logger.info(
                "taxonomy_index_loaded",
                tags=len(self.tags),
                pages_indexed=len(self._page_to_tags),
                path=str(self.cache_path),
            )
        except Exception as e:
            from bengal.errors import ErrorCode

            logger.warning(
                "taxonomy_index_load_failed",
                error=str(e),
                path=str(self.cache_path),
                error_code=ErrorCode.A003.value,  # cache_read_error
                suggestion="Taxonomy cache will be rebuilt automatically.",
            )
            self.tags = {}
            self._page_to_tags = {}

    def save_to_disk(self) -> None:
        """Save taxonomy index to disk (including reverse index)."""
        with self._lock:
            # Verify consistency before save
            # RFC: Cache Lifecycle Hardening - Phase 3
            violations = self._check_invariants()
            if violations:
                logger.warning(
                    "taxonomy_index_invariant_violation",
                    violations=violations[:5],  # First 5
                    total=len(violations),
                    action="clearing_and_skipping_save",
                )
                # Don't save corrupted data - clear and let next build recreate
                self.tags.clear()
                self._page_to_tags.clear()
                return

            try:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)

                data = {
                    "version": self.VERSION,
                    "tags": {
                        tag_slug: entry.to_cache_dict() for tag_slug, entry in self.tags.items()
                    },
                    # Persist reverse index (convert sets to lists for JSON)
                    "page_to_tags": {page: list(tags) for page, tags in self._page_to_tags.items()},
                }

                # Save as compressed .json.zst format
                compressed_path = self.cache_path.with_suffix(".json.zst")
                save_compressed(data, compressed_path)

                logger.info(
                    "taxonomy_index_saved",
                    tags=len(self.tags),
                    pages_indexed=len(self._page_to_tags),
                    path=str(self.cache_path),
                )
            except Exception as e:
                from bengal.errors import ErrorCode

                logger.error(
                    "taxonomy_index_save_failed",
                    error=str(e),
                    path=str(self.cache_path),
                    error_code=ErrorCode.A004.value,  # cache_write_error
                    suggestion="Check disk space and permissions. Taxonomy index may be incomplete.",
                )

    def _check_invariants(self) -> list[str]:
        """
        Verify forward and reverse indexes are in sync.

        RFC: Cache Lifecycle Hardening - Phase 3
        Detects index desync early before it causes subtle bugs.

        Returns:
            List of violations (empty if consistent)
        """
        violations: list[str] = []

        # Check 1: Every page in _page_to_tags exists in tags[tag].page_paths
        for page, tags in self._page_to_tags.items():
            for tag in tags:
                if tag not in self.tags:
                    violations.append(
                        f"Reverse index has tag '{tag}' for page '{page}' not in forward index"
                    )
                elif page not in self.tags[tag].page_paths:
                    violations.append(
                        f"Page '{page}' in reverse index for tag '{tag}' but not in forward"
                    )

        # Check 2: Every page in tags[tag].page_paths exists in _page_to_tags
        for tag_slug, entry in self.tags.items():
            for page in entry.page_paths:
                if page not in self._page_to_tags:
                    violations.append(
                        f"Page '{page}' in forward index for tag '{tag_slug}' but not in reverse"
                    )
                elif tag_slug not in self._page_to_tags[page]:
                    violations.append(
                        f"Tag '{tag_slug}' for page '{page}' in forward but not in reverse"
                    )

        return violations

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

    def stats(self) -> dict[str, Any]:
        """
        Get taxonomy index statistics.

        Returns:
            Dictionary with index stats
        """
        valid = sum(1 for e in self.tags.values() if e.is_valid)
        invalid = len(self.tags) - valid

        total_pages = 0
        total_page_tag_pairs = 0
        for entry in self.tags.values():
            if entry.is_valid:
                total_page_tag_pairs += len(entry.page_paths)
                total_pages += len(entry.page_paths)

        # Rough estimate of unique pages (overcount due to multiple tags)
        unique_pages = set()
        for entry in self.tags.values():
            if entry.is_valid:
                unique_pages.update(entry.page_paths)

        avg_tags_per_page = 0.0
        if unique_pages:
            avg_tags_per_page = total_page_tag_pairs / len(unique_pages)

        return {
            "total_tags": len(self.tags),
            "valid_tags": valid,
            "invalid_tags": invalid,
            "total_unique_pages": len(unique_pages),
            "total_page_tag_pairs": total_page_tag_pairs,
            "avg_tags_per_page": avg_tags_per_page,
            "cache_size_bytes": len(json.dumps([e.to_cache_dict() for e in self.tags.values()])),
        }
