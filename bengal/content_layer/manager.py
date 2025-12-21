"""
ContentLayerManager - Orchestrates content fetching from multiple sources.

Handles source registration, parallel fetching, caching, and aggregation.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.errors import BengalConfigError, BengalError
from bengal.utils.async_compat import run_async
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.content_layer.entry import ContentEntry
    from bengal.content_layer.source import ContentSource

logger = get_logger(__name__)


@dataclass
class CachedSource:
    """Metadata about a cached source."""

    source_key: str
    cached_at: datetime
    entry_count: int
    checksum: str | None = None


class ContentLayerManager:
    """
    Manages content from multiple sources.

    Handles:
    - Source registration (local, remote, custom)
    - Parallel async fetching
    - Disk caching with TTL and invalidation
    - Aggregation of all sources into unified content list

    Example:
        >>> manager = ContentLayerManager(cache_dir=Path(".bengal/content_cache"))
        >>> manager.register_source("docs", "local", {"directory": "content/docs"})
        >>> manager.register_source("blog", "notion", {"database_id": "abc123"})
        >>> entries = manager.fetch_all_sync()
        >>> print(f"Fetched {len(entries)} content entries")
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        cache_ttl: timedelta = timedelta(hours=1),
        offline: bool = False,
    ) -> None:
        """
        Initialize content layer manager.

        Args:
            cache_dir: Directory for caching remote content (default: .bengal/content_cache)
            cache_ttl: Time-to-live for cached content (default: 1 hour)
            offline: If True, only use cached content (no network requests)
        """
        self.cache_dir = cache_dir or Path(".bengal/content_cache")
        self.cache_ttl = cache_ttl
        self.offline = offline
        self.sources: dict[str, ContentSource] = {}

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def register_source(
        self,
        name: str,
        source_type: str,
        config: dict[str, Any],
    ) -> None:
        """
        Register a content source.

        Args:
            name: Unique name for this source instance
            source_type: Type identifier ('local', 'github', 'rest', 'notion')
            config: Source-specific configuration

        Raises:
            ValueError: If source_type is unknown
        """
        from bengal.content_layer.sources import SOURCE_REGISTRY

        if source_type not in SOURCE_REGISTRY:
            available = ", ".join(sorted(SOURCE_REGISTRY.keys()))
            raise BengalConfigError(
                f"Unknown source type: {source_type!r}\n"
                f"Available types: {available}\n"
                f"For remote sources, install extras: pip install bengal[{source_type}]",
                suggestion=f"Use one of the available source types: {available}",
            )

        source_class = SOURCE_REGISTRY[source_type]
        self.sources[name] = source_class(name, config)
        logger.debug(f"Registered content source: {name} ({source_type})")

    def register_custom_source(self, name: str, source: ContentSource) -> None:
        """
        Register a custom source instance.

        Args:
            name: Unique name for this source
            source: ContentSource implementation instance
        """
        self.sources[name] = source
        logger.debug(f"Registered custom content source: {name} ({source.source_type})")

    async def fetch_all(self, use_cache: bool = True) -> list[ContentEntry]:
        """
        Fetch content from all registered sources.

        Fetches from all sources in parallel, using cache when available
        and falling back to cached content in offline mode.

        Args:
            use_cache: Whether to use cached content if available

        Returns:
            List of all content entries from all sources
        """
        if not self.sources:
            logger.debug("No content sources registered")
            return []

        # Fetch from all sources concurrently
        tasks = [
            self._fetch_source(name, source, use_cache) for name, source in self.sources.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results, logging errors
        entries: list[ContentEntry] = []
        for name, result in zip(self.sources.keys(), results, strict=True):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch from source '{name}': {result}")
                if self.offline:
                    # Try to use stale cache in offline mode
                    cached = self._load_cache(name)
                    if cached:
                        logger.warning(f"Using stale cache for '{name}' (offline mode)")
                        entries.extend(cached)
            else:
                entries.extend(result)

        logger.info(
            f"Content layer fetched {len(entries)} entries from {len(self.sources)} sources"
        )
        return entries

    async def _fetch_source(
        self,
        name: str,
        source: ContentSource,
        use_cache: bool,
    ) -> list[ContentEntry]:
        """
        Fetch content from a single source with caching.

        Args:
            name: Source name
            source: Source instance
            use_cache: Whether to check cache first

        Returns:
            List of content entries from this source
        """
        cache_key = source.get_cache_key()

        # Check if we should use cache
        if use_cache:
            cached = self._load_cache(name)
            if cached and self._is_cache_valid(name, cache_key):
                logger.debug(f"Using cached content for '{name}' ({len(cached)} entries)")
                return cached

        # Offline mode: must use cache
        if self.offline:
            cached = self._load_cache(name)
            if cached:
                logger.warning(f"Using stale cache for '{name}' (offline mode)")
                return cached
            raise BengalError(
                f"Cannot fetch from '{name}' in offline mode (no cache available)",
                suggestion="Run with online mode or ensure cache is available",
            )

        # Fetch fresh content
        logger.info(f"Fetching content from '{name}' ({source.source_type})...")
        entries: list[ContentEntry] = []

        try:
            async for entry in source.fetch_all():
                entries.append(entry)
        except Exception as e:
            # Try to fall back to cache on error
            cached = self._load_cache(name)
            if cached:
                logger.warning(f"Fetch failed for '{name}', using cached content: {e}")
                return cached
            raise

        # Save to cache
        self._save_cache(name, entries, cache_key)
        logger.info(f"Fetched {len(entries)} entries from '{name}'")

        return entries

    def _is_cache_valid(self, name: str, expected_key: str) -> bool:
        """
        Check if cached content is still valid.

        Args:
            name: Source name
            expected_key: Expected cache key (based on current config)

        Returns:
            True if cache is valid and can be used
        """
        meta_path = self.cache_dir / f"{name}.meta.json"

        if not meta_path.exists():
            return False

        try:
            meta = json.loads(meta_path.read_text())
            cached_meta = CachedSource(
                source_key=meta["source_key"],
                cached_at=datetime.fromisoformat(meta["cached_at"]),
                entry_count=meta["entry_count"],
                checksum=meta.get("checksum"),
            )

            # Check if config changed
            if cached_meta.source_key != expected_key:
                logger.debug(f"Cache key mismatch for '{name}', will refetch")
                return False

            # Check TTL
            age = datetime.now() - cached_meta.cached_at
            if age > self.cache_ttl:
                logger.debug(f"Cache expired for '{name}' (age: {age})")
                return False

            return True

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.debug(f"Invalid cache metadata for '{name}': {e}")
            return False

    def _load_cache(self, name: str) -> list[ContentEntry] | None:
        """
        Load cached entries from disk.

        Args:
            name: Source name

        Returns:
            List of cached entries, or None if cache unavailable
        """
        from bengal.content_layer.entry import ContentEntry

        cache_path = self.cache_dir / f"{name}.json"

        if not cache_path.exists():
            return None

        try:
            data = json.loads(cache_path.read_text())
            return [ContentEntry.from_dict(entry) for entry in data]
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.debug(f"Failed to load cache for '{name}': {e}")
            return None

    def _save_cache(
        self,
        name: str,
        entries: list[ContentEntry],
        cache_key: str,
    ) -> None:
        """
        Save entries to cache.

        Args:
            name: Source name
            entries: Entries to cache
            cache_key: Cache key for validation
        """
        cache_path = self.cache_dir / f"{name}.json"
        meta_path = self.cache_dir / f"{name}.meta.json"

        # Save entries
        data = [entry.to_dict() for entry in entries]
        cache_path.write_text(json.dumps(data, indent=2))

        # Save metadata
        meta = {
            "source_key": cache_key,
            "cached_at": datetime.now().isoformat(),
            "entry_count": len(entries),
        }
        meta_path.write_text(json.dumps(meta, indent=2))

        logger.debug(f"Cached {len(entries)} entries for '{name}'")

    def clear_cache(self, source_name: str | None = None) -> int:
        """
        Clear cached content.

        Args:
            source_name: Specific source to clear, or None for all

        Returns:
            Number of cache files deleted
        """
        deleted = 0

        if source_name:
            # Clear specific source
            for suffix in [".json", ".meta.json"]:
                path = self.cache_dir / f"{source_name}{suffix}"
                if path.exists():
                    path.unlink()
                    deleted += 1
        else:
            # Clear all caches
            for path in self.cache_dir.glob("*.json"):
                path.unlink()
                deleted += 1

        logger.info(f"Cleared {deleted} cache files")
        return deleted

    def get_cache_status(self) -> dict[str, dict[str, Any]]:
        """
        Get status of all cached sources.

        Returns:
            Dictionary mapping source names to cache status
        """
        status: dict[str, dict[str, Any]] = {}

        for name in self.sources:
            meta_path = self.cache_dir / f"{name}.meta.json"
            cache_path = self.cache_dir / f"{name}.json"

            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                    cached_at = datetime.fromisoformat(meta["cached_at"])
                    age = datetime.now() - cached_at
                    status[name] = {
                        "cached": True,
                        "entry_count": meta["entry_count"],
                        "cached_at": cached_at.isoformat(),
                        "age_seconds": age.total_seconds(),
                        "expired": age > self.cache_ttl,
                        "size_bytes": cache_path.stat().st_size if cache_path.exists() else 0,
                    }
                except Exception as e:
                    logger.debug(
                        "content_layer_cache_metadata_invalid",
                        source=name,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    status[name] = {"cached": False, "error": "Invalid metadata"}
            else:
                status[name] = {"cached": False}

        return status

    # =========================================================================
    # Sync convenience methods
    # =========================================================================

    def fetch_all_sync(self, use_cache: bool = True) -> list[ContentEntry]:
        """
        Synchronous wrapper for fetch_all().

        Args:
            use_cache: Whether to use cached content if available

        Returns:
            List of all content entries
        """
        return run_async(self.fetch_all(use_cache))

    def __repr__(self) -> str:
        return f"ContentLayerManager(sources={list(self.sources.keys())})"
