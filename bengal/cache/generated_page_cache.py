"""
Generated page output cache for Bengal SSG.

RFC: Output Cache Architecture - Caches rendered output for generated pages
(tag pages, section archives, API docs) based on their computed content hashes.

Key Insight:
Generated pages are expensive to render but their content is deterministic
based on member pages. By tracking member content hashes, we can skip
regeneration when member content hasn't changed.

Performance:
- Converts O(n) rendering to O(1) hash comparison for unchanged content
- Targets 24x speedup (12s → <500ms for generated pages)
- ~95% cache hit rate for unchanged content

Cache Strategy:
1. Compute hash of all member page content hashes
2. If combined hash matches cached entry, skip regeneration
3. Otherwise, regenerate and update cache

UNIFICATION: This replaces the legacy TaxonomyIndex by tracking both
membership AND content hashes.

Thread Safety:
Uses threading.Lock for atomic updates to entries dict during parallel builds.

Compression:
Uses Zstandard compression for cached HTML (if stored) via bengal.cache.compression.

Related Modules:
- bengal.cache.taxonomy_index: Legacy index (unified into this)
- bengal.orchestration.taxonomy: Uses for tag page caching
- bengal.orchestration.section: Uses for section archive caching
- bengal.rendering.pipeline.output: Content hash embedding

"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger
from bengal.utils.primitives.hashing import hash_str

if TYPE_CHECKING:
    from bengal.core.page import Page

logger = get_logger(__name__)

# Cache format version - increment when schema changes
GENERATED_PAGE_CACHE_VERSION = 1


@dataclass
class GeneratedPageCacheEntry:
    """
    Cache entry for a generated page.

    RFC: Output Cache Architecture - Tracks member page hashes and optionally
    caches the rendered HTML output.

    Attributes:
        page_type: Type of generated page ("tag", "section-archive", "api-doc")
        page_id: Unique identifier ("python", "docs/reference", "Site.build")
        content_hash: Hash computed from combined member hashes
        template_hash: Hash of template used (invalidates cache if changed)
        member_hashes: Mapping of source_path → content_hash for members
        cached_html: Compressed HTML output (only for pages < 100KB)
        last_generated: ISO timestamp of last generation
        generation_time_ms: Time taken to render
        is_compressed: Whether cached_html is compressed

    """

    # Identity
    page_type: str  # "tag", "section-archive", "api-doc"
    page_id: str  # "python", "docs/reference", "Site.build"

    # Content hash (computed from combined member hashes)
    content_hash: str = ""

    # Template hash - invalidates cache if template changes
    template_hash: str = ""

    # Dependencies (pages that affect this generated page's content)
    member_hashes: dict[str, str] = field(default_factory=dict)

    # Cached output (optional, for fast regeneration)
    # Only stored for pages under threshold to limit memory usage
    cached_html: str | None = None

    # Metadata
    last_generated: str = ""
    generation_time_ms: int = 0
    is_compressed: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "page_type": self.page_type,
            "page_id": self.page_id,
            "content_hash": self.content_hash,
            "template_hash": self.template_hash,
            "member_hashes": self.member_hashes,
            "cached_html": self.cached_html,
            "last_generated": self.last_generated,
            "generation_time_ms": self.generation_time_ms,
            "is_compressed": self.is_compressed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GeneratedPageCacheEntry:
        """Create from dictionary."""
        return cls(
            page_type=data.get("page_type", ""),
            page_id=data.get("page_id", ""),
            content_hash=data.get("content_hash", ""),
            template_hash=data.get("template_hash", ""),
            member_hashes=data.get("member_hashes", {}),
            cached_html=data.get("cached_html"),
            last_generated=data.get("last_generated", ""),
            generation_time_ms=data.get("generation_time_ms", 0),
            is_compressed=data.get("is_compressed", False),
        )


class GeneratedPageCache:
    """
    Cache for generated page output.

    RFC: Output Cache Architecture - Caches generated pages (tag pages,
    section archives, API docs) based on member page content hashes.

    UNIFICATION: This replaces the legacy TaxonomyIndex by tracking
    both membership AND content hashes.

    Cache Strategy:
    1. Compute hash of all member page content hashes
    2. If combined hash matches cached entry, skip regeneration
    3. Otherwise, regenerate and update cache

    Thread Safety:
    Uses threading.Lock for atomic updates during parallel builds.

    Attributes:
        cache_path: Path to cache file (.bengal/generated_page_cache.json.zst)
        entries: Mapping of cache_key → GeneratedPageCacheEntry
        html_cache_threshold: Max HTML size to cache (default: 100KB)

    Example:
        >>> cache = GeneratedPageCache(site.paths.generated_page_cache)
        >>> if cache.should_regenerate("tag", "python", member_pages, content_cache):
        ...     html = render_tag_page(tag="python", pages=member_pages)
        ...     cache.update("tag", "python", member_pages, content_cache, html, 100)
        ... else:
        ...     html = cache.get_cached_html("tag", "python")

    """

    def __init__(
        self,
        cache_path: Path,
        html_cache_threshold: int = 100_000,
    ) -> None:
        """
        Initialize generated page cache.

        Args:
            cache_path: Path to cache file
            html_cache_threshold: Max HTML size to cache (bytes, default 100KB)

        """
        self.cache_path = cache_path
        self.html_cache_threshold = html_cache_threshold
        self.entries: dict[str, GeneratedPageCacheEntry] = {}
        self._lock = threading.Lock()
        self._dirty = False
        self._load()

    def _load(self) -> None:
        """Load cache from disk using load_auto (supports zst)."""
        if not self.cache_path.exists():
            # Also check for .zst version
            zst_path = self.cache_path.with_suffix(".json.zst")
            if not zst_path.exists():
                return

        try:
            from bengal.cache.compression import load_auto

            data = load_auto(self.cache_path)

            # Check version
            version = data.get("version", 0)
            if version < GENERATED_PAGE_CACHE_VERSION:
                logger.info(
                    "generated_page_cache_version_mismatch",
                    file_version=version,
                    current_version=GENERATED_PAGE_CACHE_VERSION,
                    action="starting_fresh",
                )
                return

            # Load entries
            entries_data = data.get("entries", {})
            for key, entry_data in entries_data.items():
                self.entries[key] = GeneratedPageCacheEntry.from_dict(entry_data)

            logger.debug(
                "generated_page_cache_loaded",
                entries=len(self.entries),
                path=str(self.cache_path),
            )

        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning(
                "generated_page_cache_load_failed",
                path=str(self.cache_path),
                error=str(e),
                error_type=type(e).__name__,
                action="starting_fresh",
            )

    def save(self) -> None:
        """Persist cache to disk using save_compressed."""
        if not self._dirty:
            return

        try:
            from bengal.cache.compression import save_compressed

            data = {
                "version": GENERATED_PAGE_CACHE_VERSION,
                "entries": {key: entry.to_dict() for key, entry in self.entries.items()},
            }

            # Save to .json.zst
            zst_path = self.cache_path.with_suffix(".json.zst")
            save_compressed(data, zst_path)
            self._dirty = False

            logger.debug(
                "generated_page_cache_saved",
                entries=len(self.entries),
                path=str(zst_path),
            )

        except Exception as e:
            logger.warning(
                "generated_page_cache_save_failed",
                path=str(self.cache_path),
                error=str(e),
                error_type=type(e).__name__,
            )

    def get_cache_key(self, page_type: str, page_id: str) -> str:
        """Generate cache key for generated page."""
        return f"{page_type}:{page_id}"

    def compute_member_hash(
        self,
        member_pages: list[Page],
        content_cache: dict[str, str],
    ) -> str:
        """
        Compute combined hash of all member page content.

        This is the key optimization: instead of rendering the generated
        page to check if it changed, we compare the combined hash of
        member content hashes.

        If member content is unchanged, generated output is unchanged.

        Args:
            member_pages: List of Page objects contributing to generated page
            content_cache: Mapping of source_path → content_hash

        Returns:
            Combined hash string (16 chars)

        """
        # Sort for deterministic ordering
        member_hashes = sorted(
            content_cache.get(str(p.source_path), "")
            for p in member_pages
            if hasattr(p, "source_path")
        )
        combined = "|".join(member_hashes)
        return hash_str(combined, truncate=16)

    def should_regenerate(
        self,
        page_type: str,
        page_id: str,
        member_pages: list[Page],
        content_cache: dict[str, str],
        template_hash: str = "",
    ) -> bool:
        """
        Check if generated page needs regeneration.

        Returns True if:
        - No cache entry exists
        - Member content has changed
        - Template has changed (Risk 6 mitigation)
        - Cache entry is corrupted

        Args:
            page_type: Type of generated page ("tag", "section-archive", etc.)
            page_id: Unique identifier for this page
            member_pages: List of Page objects contributing to this page
            content_cache: Mapping of source_path → content_hash
            template_hash: Hash of template used for rendering (optional)

        Returns:
            True if regeneration needed, False if cached

        """
        key = self.get_cache_key(page_type, page_id)

        with self._lock:
            entry = self.entries.get(key)

        if entry is None:
            return True

        # Check template hash first (fast path for template changes)
        if template_hash and entry.template_hash and template_hash != entry.template_hash:
            logger.debug(
                "generated_page_cache_template_changed",
                page_type=page_type,
                page_id=page_id,
            )
            return True

        current_hash = self.compute_member_hash(member_pages, content_cache)

        if current_hash != entry.content_hash:
            logger.debug(
                "generated_page_cache_content_changed",
                page_type=page_type,
                page_id=page_id,
                old_hash=entry.content_hash[:8],
                new_hash=current_hash[:8],
            )
            return True

        return False

    def update(
        self,
        page_type: str,
        page_id: str,
        member_pages: list[Page],
        content_cache: dict[str, str],
        rendered_html: str,
        generation_time_ms: int,
        template_hash: str = "",
    ) -> None:
        """
        Update cache after regeneration.

        Args:
            page_type: Type of generated page
            page_id: Unique identifier
            member_pages: Pages contributing to this generated page
            content_cache: Source path → content hash mapping
            rendered_html: Rendered HTML output
            generation_time_ms: Time taken to render
            template_hash: Hash of template(s) used for rendering

        """
        key = self.get_cache_key(page_type, page_id)
        member_hash = self.compute_member_hash(member_pages, content_cache)

        # Only cache HTML under threshold
        cached_html = None
        if len(rendered_html) < self.html_cache_threshold:
            cached_html = rendered_html

        entry = GeneratedPageCacheEntry(
            page_type=page_type,
            page_id=page_id,
            content_hash=member_hash,
            template_hash=template_hash,
            member_hashes={
                str(p.source_path): content_cache.get(str(p.source_path), "")
                for p in member_pages
                if hasattr(p, "source_path")
            },
            cached_html=cached_html,
            last_generated=datetime.now(UTC).isoformat(),
            generation_time_ms=generation_time_ms,
            is_compressed=False,
        )

        with self._lock:
            self.entries[key] = entry
            self._dirty = True

        logger.debug(
            "generated_page_cache_updated",
            page_type=page_type,
            page_id=page_id,
            member_count=len(member_pages),
            html_cached=cached_html is not None,
            generation_time_ms=generation_time_ms,
        )

    def get_cached_html(self, page_type: str, page_id: str) -> str | None:
        """
        Get cached HTML if available and valid.

        Args:
            page_type: Type of generated page
            page_id: Unique identifier

        Returns:
            Cached HTML string, or None if not cached

        """
        key = self.get_cache_key(page_type, page_id)

        with self._lock:
            entry = self.entries.get(key)

        return entry.cached_html if entry else None

    def invalidate(self, page_type: str, page_id: str) -> bool:
        """
        Invalidate a specific cache entry.

        Args:
            page_type: Type of generated page
            page_id: Unique identifier

        Returns:
            True if entry was removed, False if not found

        """
        key = self.get_cache_key(page_type, page_id)

        with self._lock:
            if key in self.entries:
                del self.entries[key]
                self._dirty = True
                return True

        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self.entries.clear()
            self._dirty = True

        logger.info("generated_page_cache_cleared")

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics

        """
        with self._lock:
            entries_with_html = sum(1 for e in self.entries.values() if e.cached_html is not None)
            total_html_size = sum(
                len(e.cached_html) for e in self.entries.values() if e.cached_html
            )

            return {
                "total_entries": len(self.entries),
                "entries_with_html": entries_with_html,
                "html_cache_rate": (
                    entries_with_html / len(self.entries) * 100 if self.entries else 0
                ),
                "total_html_size_bytes": total_html_size,
                "by_type": self._count_by_type(),
            }

    def _count_by_type(self) -> dict[str, int]:
        """Count entries by page type."""
        counts: dict[str, int] = {}
        for entry in self.entries.values():
            counts[entry.page_type] = counts.get(entry.page_type, 0) + 1
        return counts
