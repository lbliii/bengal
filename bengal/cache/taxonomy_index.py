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
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from bengal.cache.cacheable import Cacheable
from bengal.utils.logger import get_logger

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
        "version": 1,
        "tags": {
            "python": {
                "tag_slug": "python",
                "tag_name": "Python",
                "page_paths": ["content/post1.md", "content/post2.md"],
                "updated_at": "2025-10-16T12:00:00",
                "is_valid": true
            }
        }
    }
    """

    VERSION = 1
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
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load taxonomy index from disk if file exists."""
        if not self.cache_path.exists():
            logger.debug("taxonomy_index_not_found", path=str(self.cache_path))
            return

        try:
            with open(self.cache_path) as f:
                data = json.load(f)

            # Validate version
            if data.get("version") != self.VERSION:
                logger.warning(
                    "taxonomy_index_version_mismatch",
                    expected=self.VERSION,
                    found=data.get("version"),
                )
                self.tags = {}
                return

            # Load tag entries
            for tag_slug, entry_data in data.get("tags", {}).items():
                self.tags[tag_slug] = TagEntry.from_cache_dict(entry_data)

            logger.info(
                "taxonomy_index_loaded",
                tags=len(self.tags),
                path=str(self.cache_path),
            )
        except Exception as e:
            logger.warning(
                "taxonomy_index_load_failed",
                error=str(e),
                path=str(self.cache_path),
            )
            self.tags = {}

    def save_to_disk(self) -> None:
        """Save taxonomy index to disk."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "version": self.VERSION,
                "tags": {tag_slug: entry.to_cache_dict() for tag_slug, entry in self.tags.items()},
            }

            with open(self.cache_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(
                "taxonomy_index_saved",
                tags=len(self.tags),
                path=str(self.cache_path),
            )
        except Exception as e:
            logger.error(
                "taxonomy_index_save_failed",
                error=str(e),
                path=str(self.cache_path),
            )

    def update_tag(self, tag_slug: str, tag_name: str, page_paths: list[str]) -> None:
        """
        Update or create a tag entry.

        Args:
            tag_slug: Normalized tag identifier
            tag_name: Original tag name for display
            page_paths: List of page paths with this tag
        """
        entry = TagEntry(
            tag_slug=tag_slug,
            tag_name=tag_name,
            page_paths=page_paths,
            updated_at=datetime.utcnow().isoformat(),
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
        return entry.page_paths if entry else None

    def has_tag(self, tag_slug: str) -> bool:
        """
        Check if tag exists and is valid.

        Args:
            tag_slug: Normalized tag identifier

        Returns:
            True if tag exists and is valid
        """
        if tag_slug not in self.tags:
            return False

        entry = self.tags[tag_slug]
        return entry.is_valid

    def get_tags_for_page(self, page_path: Path) -> set[str]:
        """
        Get all tags for a specific page (reverse lookup).

        Args:
            page_path: Path to page

        Returns:
            Set of tag slugs for this page
        """
        page_str = str(page_path)
        tags = set()
        for tag_slug, entry in self.tags.items():
            if entry.is_valid and page_str in entry.page_paths:
                tags.add(tag_slug)
        return tags

    def get_all_tags(self) -> dict[str, TagEntry]:
        """
        Get all valid tags.

        Returns:
            Dictionary mapping tag_slug to TagEntry for valid tags
        """
        return {tag_slug: entry for tag_slug, entry in self.tags.items() if entry.is_valid}

    def invalidate_tag(self, tag_slug: str) -> None:
        """
        Mark a tag as invalid.

        Args:
            tag_slug: Normalized tag identifier
        """
        if tag_slug in self.tags:
            self.tags[tag_slug].is_valid = False

    def invalidate_all(self) -> None:
        """Invalidate all tag entries."""
        for entry in self.tags.values():
            entry.is_valid = False

    def clear(self) -> None:
        """Clear all tags."""
        self.tags.clear()

    def remove_page_from_all_tags(self, page_path: Path) -> set[str]:
        """
        Remove a page from all tags it belongs to.

        Args:
            page_path: Path to page to remove

        Returns:
            Set of affected tag slugs
        """
        page_str = str(page_path)
        affected = set()

        for tag_slug, entry in self.tags.items():
            if page_str in entry.page_paths:
                entry.page_paths.remove(page_str)
                affected.add(tag_slug)

        return affected

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
