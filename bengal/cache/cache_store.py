"""
Generic cache storage for Cacheable types.

This module provides a type-safe, generic cache storage mechanism that works
with any type implementing the Cacheable protocol. It handles:

- JSON serialization/deserialization
- Version management (tolerant loading)
- Directory creation
- Type-safe load/save operations

Design Philosophy:
    CacheStore provides a reusable cache storage layer that works with any
    Cacheable type. This eliminates the need for each cache (TaxonomyIndex,
    AssetDependencyMap, etc.) to implement its own save/load logic.

    Benefits:
    - Consistent version handling across all caches
    - Type-safe operations (mypy validates)
    - Tolerant loading (returns empty on mismatch, doesn't crash)
    - Automatic directory creation
    - Single source of truth for cache file format

Usage Example:
    from bengal.cache.cache_store import CacheStore
    from bengal.cache.taxonomy_index import TagEntry

    # Create store
    store = CacheStore(Path('.bengal/tags.json'))

    # Save entries (type-safe)
    tags = [
        TagEntry(tag_slug='python', tag_name='Python', page_paths=[], updated_at='...'),
        TagEntry(tag_slug='web', tag_name='Web', page_paths=[], updated_at='...'),
    ]
    store.save(tags, version=1)

    # Load entries (type-safe, tolerant)
    loaded_tags = store.load(TagEntry, expected_version=1)
    # Returns [] if file missing or version mismatch

See Also:
    - bengal/cache/cacheable.py - Cacheable protocol definition
    - bengal/cache/taxonomy_index.py - Example usage (TagEntry)
    - bengal/cache/asset_dependency_map.py - Example usage (AssetDependencyEntry)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from bengal.cache.cacheable import Cacheable
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# TypeVar bound to Cacheable for type-safe load operations
T = TypeVar("T", bound=Cacheable)


class CacheStore:
    """
    Generic cache storage for types implementing the Cacheable protocol.

    Provides type-safe save/load operations with version management and
    tolerant loading (returns empty list on version mismatch or missing file).

    Attributes:
        cache_path: Path to cache file (e.g., .bengal/taxonomy_index.json)

    Cache File Format:
        {
            "version": 1,
            "entries": [
                {...},  // Serialized Cacheable objects
                {...}
            ]
        }

    Version Management:
        - Each cache file has a top-level "version" field
        - On version mismatch, load() returns empty list and logs warning
        - On missing file, load() returns empty list (no warning)
        - On malformed JSON, load() returns empty list and logs error

        This "tolerant loading" approach ensures that stale or incompatible
        caches don't crash the build - they just rebuild from scratch.

    Type Safety:
        - save() accepts list of any Cacheable type
        - load() requires explicit type parameter for deserialization
        - mypy validates that type implements Cacheable protocol

    Example:
        store = CacheStore(Path('.bengal/tags.json'))

        # Save
        tags: list[TagEntry] = [...]
        store.save(tags, version=1)

        # Load (type-safe)
        loaded: list[TagEntry] = store.load(TagEntry, expected_version=1)

        # Version mismatch example
        store.save(tags, version=2)  # Bump version
        loaded = store.load(TagEntry, expected_version=1)  # Returns []

    Performance:
        - JSON serialization: ~10µs per object (depends on object complexity)
        - File I/O: ~1-5ms for typical cache files (100-1000 entries)
        - Directory creation: ~1ms (only if directory missing)
        - Version check: ~100ns (simple int comparison)

    Thread Safety:
        Not thread-safe. Cache files should only be written by build process
        (single-threaded during discovery/build phases).
    """

    def __init__(self, cache_path: Path):
        """
        Initialize cache store.

        Args:
            cache_path: Path to cache file (e.g., .bengal/taxonomy_index.json).
                       Parent directory will be created if missing.
        """
        self.cache_path = cache_path

    def save(
        self,
        entries: list[Cacheable],
        version: int = 1,
        indent: int = 2,
    ) -> None:
        """
        Save entries to cache file.

        Serializes all entries to JSON and writes to cache file. Creates
        parent directory if missing.

        Args:
            entries: List of Cacheable objects to save
            version: Cache version number (default: 1). Increment when
                    format changes (new fields, removed fields, etc.)
            indent: JSON indentation (default: 2). Use None for compact output.

        Example:
            tags = [
                TagEntry(tag_slug='python', ...),
                TagEntry(tag_slug='web', ...),
            ]
            store.save(tags, version=1)

        Raises:
            OSError: If directory creation or file write fails
            TypeError: If entries contain non-JSON-serializable data
        """
        # Serialize entries using protocol method
        data = {
            "version": version,
            "entries": [entry.to_cache_dict() for entry in entries],
        }

        # Create parent directory if missing
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file (atomic write via temp file not needed for cache)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)

        logger.debug(f"Saved {len(entries)} entries to {self.cache_path} (version {version})")

    def load(
        self,
        entry_type: type[T],
        expected_version: int = 1,
    ) -> list[T]:
        """
        Load entries from cache file (tolerant).

        Deserializes entries from JSON and validates version. If version
        mismatch or file missing, returns empty list (doesn't crash).

        This "tolerant loading" approach ensures that builds never fail due
        to stale or incompatible caches - they just rebuild from scratch.

        Args:
            entry_type: Type to deserialize (must implement Cacheable protocol).
                       Used to call from_cache_dict() classmethod.
            expected_version: Expected cache version (default: 1). If file
                            version doesn't match, returns empty list.

        Returns:
            List of deserialized entries, or [] if:
            - File doesn't exist (no warning, normal for first build)
            - Version mismatch (warning logged)
            - Malformed JSON (error logged)
            - Deserialization fails (error logged)

        Example:
            # Normal load
            tags = store.load(TagEntry, expected_version=1)

            # Version mismatch (returns [])
            store.save(tags, version=2)  # Bump version
            loaded = store.load(TagEntry, expected_version=1)  # []

        Type Safety:
            mypy validates that entry_type implements Cacheable:

                store.load(TagEntry, ...)  # ✅ OK (TagEntry implements Cacheable)
                store.load(Page, ...)      # ❌ Error (Page doesn't implement Cacheable)
        """
        # File missing (normal for first build)
        if not self.cache_path.exists():
            logger.debug(f"Cache file not found: {self.cache_path} (will rebuild)")
            return []

        try:
            # Read and parse JSON
            with open(self.cache_path, encoding="utf-8") as f:
                data = json.load(f)

            # Validate structure
            if not isinstance(data, dict):
                logger.error(
                    f"Malformed cache file {self.cache_path}: expected dict, got {type(data)}"
                )
                return []

            # Check version
            file_version = data.get("version")
            if file_version != expected_version:
                logger.warning(
                    f"Cache version mismatch: {self.cache_path} has version "
                    f"{file_version}, expected {expected_version}. Rebuilding cache."
                )
                return []

            # Deserialize entries
            entries_data = data.get("entries", [])
            if not isinstance(entries_data, list):
                logger.error(f"Malformed cache file {self.cache_path}: 'entries' is not a list")
                return []

            # Deserialize each entry using protocol method
            entries: list[T] = []
            for entry_data in entries_data:
                try:
                    entry = entry_type.from_cache_dict(entry_data)
                    entries.append(entry)
                except (KeyError, TypeError, ValueError) as e:
                    logger.error(f"Failed to deserialize entry from {self.cache_path}: {e}")
                    # Continue loading other entries (tolerant)
                    continue

            logger.debug(
                f"Loaded {len(entries)} entries from {self.cache_path} (version {file_version})"
            )
            return entries

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse cache file {self.cache_path}: {e}")
            return []
        except OSError as e:
            logger.error(f"Failed to read cache file {self.cache_path}: {e}")
            return []

    def exists(self) -> bool:
        """
        Check if cache file exists.

        Returns:
            True if cache file exists, False otherwise
        """
        return self.cache_path.exists()

    def clear(self) -> None:
        """
        Delete cache file if it exists.

        Used to force cache rebuild (e.g., after format changes).

        Example:
            store = CacheStore(Path('.bengal/tags.json'))
            store.clear()  # Force rebuild on next build
        """
        if self.cache_path.exists():
            self.cache_path.unlink()
            logger.debug(f"Cleared cache file: {self.cache_path}")
