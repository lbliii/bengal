"""
Generic cache storage for Cacheable types.

This module provides a type-safe, generic cache storage mechanism that works
with any type implementing the Cacheable protocol. It handles:

- JSON serialization/deserialization
- Zstandard compression (92-93% size reduction)
- Version management (tolerant loading)
- Directory creation
- Type-safe load/save operations
- Backward compatibility (reads both compressed and uncompressed)

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
    - 12-14x compression ratio with Zstandard (PEP 784)

Usage Example:

```python
from bengal.cache.cache_store import CacheStore
from bengal.cache.taxonomy_index import TagEntry

# Create store (compression enabled by default)
store = CacheStore(Path('.bengal/tags.json'))

# Save entries (type-safe, compressed)
tags = [
    TagEntry(tag_slug='python', tag_name='Python', page_paths=[], updated_at='...'),
    TagEntry(tag_slug='web', tag_name='Web', page_paths=[], updated_at='...'),
]
store.save(tags, version=1)

# Load entries (auto-detects format: .json.zst or .json)
loaded_tags = store.load(TagEntry, expected_version=1)
# Returns [] if file missing or version mismatch
```

See Also:
    - bengal/cache/cacheable.py - Cacheable protocol definition
    - bengal/cache/compression.py - Zstandard compression utilities
    - bengal/cache/taxonomy_index.py - Example usage (TagEntry)
    - bengal/cache/asset_dependency_map.py - Example usage (AssetDependencyEntry)
    - plan/active/rfc-zstd-cache-compression.md - Compression RFC
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

from bengal.cache.cacheable import Cacheable
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# TypeVar bound to Cacheable for type-safe load operations
T = TypeVar("T", bound=Cacheable)


class CacheStore:
    """
    Generic cache storage for types implementing the Cacheable protocol.

    Provides type-safe save/load operations with version management,
    Zstandard compression, and tolerant loading (returns empty list on
    version mismatch or missing file).

    Attributes:
        cache_path: Path to cache file (e.g., .bengal/taxonomy_index.json)
        compress: Whether to use Zstandard compression (default: True)

    Cache File Format:
        Compressed (.json.zst):
            Zstd-compressed JSON with same structure as below
            92-93% smaller, 12-14x compression ratio

        Uncompressed (.json):
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
        - On malformed data, load() returns empty list and logs error

        This "tolerant loading" approach ensures that stale or incompatible
        caches don't crash the build - they just rebuild from scratch.

    Compression:
        - Enabled by default (Python 3.14+ with compression.zstd)
        - 92-93% size reduction on typical cache files
        - <1ms compress time, <0.3ms decompress time
        - Auto-detects format on load (reads both .json.zst and .json)
        - Backward compatible: reads old uncompressed caches

    Type Safety:
        - save() accepts list of any Cacheable type
        - load() requires explicit type parameter for deserialization
        - mypy validates that type implements Cacheable protocol

    Example:
        store = CacheStore(Path('.bengal/tags.json'))

        # Save (compressed by default)
        tags: list[TagEntry] = [...]
        store.save(tags, version=1)  # Writes .json.zst

        # Load (type-safe, auto-detects format)
        loaded: list[TagEntry] = store.load(TagEntry, expected_version=1)

        # Disable compression for debugging
        store = CacheStore(Path('.bengal/tags.json'), compress=False)

    Performance:
        With compression (default):
        - Save: ~1ms (serialize + compress + write)
        - Load: ~0.5ms (read + decompress + parse)
        - Size: 12-14x smaller than JSON

        Without compression:
        - JSON serialization: ~10µs per object
        - File I/O: ~1-5ms for typical cache files

    Thread Safety:
        Not thread-safe. Cache files should only be written by build process
        (single-threaded during discovery/build phases).
    """

    def __init__(self, cache_path: Path, compress: bool = True):
        """
        Initialize cache store.

        Args:
            cache_path: Path to cache file (e.g., .bengal/taxonomy_index.json).
                       Parent directory will be created if missing.
                       With compression enabled, actual file will be .json.zst
            compress: Whether to use Zstandard compression (default: True).
                     Set to False for debugging or compatibility.
        """
        self.cache_path = cache_path
        self.compress = compress

        # Compressed path is .json.zst
        self._compressed_path: Path | None = None
        if compress:
            self._compressed_path = cache_path.with_suffix(".json.zst")

    def save(
        self,
        entries: list[Cacheable],
        version: int = 1,
        indent: int = 2,
    ) -> None:
        """
        Save entries to cache file.

        Serializes all entries to JSON and writes to cache file. Creates
        parent directory if missing. Uses Zstandard compression by default.

        Args:
            entries: List of Cacheable objects to save
            version: Cache version number (default: 1). Increment when
                    format changes (new fields, removed fields, etc.)
            indent: JSON indentation (default: 2). Only used when compression
                   is disabled; compressed files always use compact JSON.

        Example:
            tags = [
                TagEntry(tag_slug='python', ...),
                TagEntry(tag_slug='web', ...),
            ]
            store.save(tags, version=1)  # Saves as .json.zst

        Raises:
            OSError: If directory creation or file write fails
            TypeError: If entries contain non-JSON-serializable data
        """
        # Serialize entries using protocol method
        data = {
            "version": version,
            "entries": [entry.to_cache_dict() for entry in entries],
        }

        # Use compression if enabled
        if self.compress and self._compressed_path:
            from bengal.cache.compression import save_compressed

            save_compressed(data, self._compressed_path)
            logger.debug(
                f"Saved {len(entries)} entries to {self._compressed_path.name} "
                f"(version {version}, compressed)"
            )
        else:
            # Create parent directory if missing
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            # Write uncompressed JSON (using orjson if available)
            json_str = json.dumps(data, indent=indent)
            self.cache_path.write_text(json_str, encoding="utf-8")

            logger.debug(f"Saved {len(entries)} entries to {self.cache_path} (version {version})")

    def load(
        self,
        entry_type: type[T],
        expected_version: int = 1,
    ) -> list[T]:
        """
        Load entries from cache file (tolerant).

        Deserializes entries and validates version. Automatically detects
        format (compressed .json.zst or uncompressed .json). If version
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
            - Malformed data (error logged)
            - Deserialization fails (error logged)

        Example:
            # Normal load (auto-detects .json.zst or .json)
            tags = store.load(TagEntry, expected_version=1)

            # Version mismatch (returns [])
            store.save(tags, version=2)  # Bump version
            loaded = store.load(TagEntry, expected_version=1)  # []

        Type Safety:
            mypy validates that entry_type implements Cacheable:

                store.load(TagEntry, ...)  # ✅ OK (TagEntry implements Cacheable)
                store.load(Page, ...)      # ❌ Error (Page doesn't implement Cacheable)
        """
        # Try to load data (auto-detect format)
        data = self._load_data()
        if data is None:
            return []

        # Validate structure
        if not isinstance(data, dict):
            logger.error(f"Malformed cache file {self.cache_path}: expected dict, got {type(data)}")
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

    def _load_data(self) -> dict[Any, Any] | None:
        """
        Load raw data from cache file with auto-detection.

        Tries compressed format first (.json.zst), falls back to uncompressed (.json).
        This enables seamless migration from old uncompressed caches.

        Returns:
            Parsed data dict, or None if file not found or load failed
        """
        # Try compressed first (if compression enabled)
        if self._compressed_path and self._compressed_path.exists():
            try:
                from bengal.cache.compression import ZstdError, load_compressed

                data: dict[Any, Any] | None = load_compressed(self._compressed_path)
                return data
            except (ZstdError, json.JSONDecodeError, OSError) as e:
                logger.error(f"Failed to load compressed cache {self._compressed_path}: {e}")
                return None

        # Fall back to uncompressed JSON (for migration from old caches)
        if self.cache_path.exists():
            try:
                content = self.cache_path.read_text(encoding="utf-8")
                data = json.loads(content)
                return data
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Failed to load cache {self.cache_path}: {e}")
                return None

        # Neither file exists (normal for first build)
        logger.debug(f"Cache file not found: {self.cache_path} (will rebuild)")
        return None

    def exists(self) -> bool:
        """
        Check if cache file exists (compressed or uncompressed).

        Returns:
            True if cache file exists in either format, False otherwise
        """
        if self._compressed_path and self._compressed_path.exists():
            return True
        return self.cache_path.exists()

    def clear(self) -> None:
        """
        Delete cache file if it exists (both compressed and uncompressed).

        Used to force cache rebuild (e.g., after format changes).

        Example:
            store = CacheStore(Path('.bengal/tags.json'))
            store.clear()  # Force rebuild on next build
        """
        # Clear compressed file
        if self._compressed_path and self._compressed_path.exists():
            self._compressed_path.unlink()
            logger.debug(f"Cleared compressed cache: {self._compressed_path}")

        # Clear uncompressed file (for migration cleanup)
        if self.cache_path.exists():
            self.cache_path.unlink()
            logger.debug(f"Cleared cache file: {self.cache_path}")
