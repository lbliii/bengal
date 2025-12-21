"""
Core BuildCache class for tracking file changes and dependencies.

Main dataclass with fields, save/load, and coordination methods. Uses mixins
for specialized functionality (file tracking, validation, taxonomy, caching).

Key Concepts:
    - File fingerprints: mtime + size for fast change detection, hash for verification
    - Dependency tracking: Templates, partials, and data files used by pages
    - Taxonomy indexes: Tag/category mappings for fast reconstruction
    - Config hash: Auto-invalidation when configuration changes
    - Version tolerance: Accepts missing/older cache versions gracefully
    - Zstandard compression: 92-93% size reduction, <1ms overhead

Related Modules:
    - bengal.orchestration.incremental: Incremental build logic using cache
    - bengal.cache.dependency_tracker: Dependency graph construction
    - bengal.cache.taxonomy_index: Taxonomy reconstruction from cache
    - bengal.cache.compression: Zstandard compression utilities

See Also:
    - plan/active/rfc-incremental-builds.md: Incremental build design
    - plan/active/rfc-orchestrator-performance-improvements.md: Performance RFC
    - plan/active/rfc-zstd-cache-compression.md: Compression RFC
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.cache.build_cache.autodoc_tracking import AutodocTrackingMixin
from bengal.cache.build_cache.file_tracking import FileTrackingMixin
from bengal.cache.build_cache.parsed_content_cache import ParsedContentCacheMixin
from bengal.cache.build_cache.rendered_output_cache import RenderedOutputCacheMixin
from bengal.cache.build_cache.taxonomy_index_mixin import TaxonomyIndexMixin
from bengal.cache.build_cache.validation_cache import ValidationCacheMixin
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


@dataclass
class BuildCache(
    FileTrackingMixin,
    ValidationCacheMixin,
    TaxonomyIndexMixin,
    ParsedContentCacheMixin,
    RenderedOutputCacheMixin,
    AutodocTrackingMixin,
):
    """
    Tracks file hashes and dependencies between builds.

    IMPORTANT PERSISTENCE CONTRACT:
    - This cache must NEVER contain object references (Page, Section, Asset objects)
    - All data must be JSON-serializable (paths, strings, numbers, lists, dicts, sets)
    - Object relationships are rebuilt each build from cached paths

    NOTE: BuildCache intentionally does NOT implement the Cacheable protocol.
    Rationale:
    - Uses pickle for performance (faster than JSON for sets/complex structures)
    - Has tolerant loader with custom version handling logic
    - Contains many specialized fields (dependencies, hashes, etc.)
    - Designed for internal build state, not type-safe caching contracts

    For type-safe caching, use types that implement the Cacheable protocol:
    - PageCore (bengal/core/page/page_core.py)
    - TagEntry (bengal/cache/taxonomy_index.py)
    - AssetDependencyEntry (bengal/cache/asset_dependency_map.py)

    Attributes:
        file_fingerprints: Mapping of file paths to {mtime, size, hash} dicts
        dependencies: Mapping of pages to their dependencies (templates, partials, etc.)
        output_sources: Mapping of output files to their source files
        taxonomy_deps: Mapping of taxonomy terms to affected pages
        page_tags: Mapping of page paths to their tags (for detecting tag changes)
        tag_to_pages: Inverted index mapping tag slug to page paths (for O(1) reconstruction)
        known_tags: Set of all tag slugs from previous build (for detecting deletions)
        parsed_content: Cached parsed HTML/TOC (Optimization #2)
        rendered_output: Cached rendered HTML (Optimization #3)
        synthetic_pages: Cached synthetic page data (autodoc, etc.)
        validation_results: Cached validation results per file/validator
        config_hash: Hash of resolved configuration (for auto-invalidation)
        last_build: Timestamp of last successful build
    """

    # Serialized schema version (persisted in cache JSON). Tolerant loader accepts missing/older.
    VERSION: int = 6  # Bumped for Sprint 4 incremental package refactor

    # Instance persisted version; defaults to current VERSION
    version: int = VERSION

    # file_fingerprints for fast mtime+size change detection
    # Structure: {path: {mtime: float, size: int, hash: str | None}}
    file_fingerprints: dict[str, dict[str, Any]] = field(default_factory=dict)
    dependencies: dict[str, set[str]] = field(default_factory=dict)
    output_sources: dict[str, str] = field(default_factory=dict)
    taxonomy_deps: dict[str, set[str]] = field(default_factory=dict)
    page_tags: dict[str, set[str]] = field(default_factory=dict)

    # Inverted index for fast taxonomy reconstruction (NEW)
    tag_to_pages: dict[str, set[str]] = field(default_factory=dict)
    known_tags: set[str] = field(default_factory=set)

    parsed_content: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Rendered output cache: fully rendered HTML (after template rendering)
    # Allows skipping both parsing AND template rendering for unchanged pages
    # Key: source_path, Value: {html, content_hash, template_hash, metadata_hash, timestamp}
    rendered_output: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Synthetic page cache (for autodoc, etc.)
    synthetic_pages: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Validation result cache: file_path → validator_name → [CheckResult dicts]
    # Structure: {file_path: {validator_name: [CheckResult.to_cache_dict(), ...]}}
    validation_results: dict[str, dict[str, list[dict[str, Any]]]] = field(default_factory=dict)

    # Autodoc dependency tracking: source_file → set[autodoc_page_paths]
    # Enables selective rebuilding of autodoc pages when their sources change
    autodoc_dependencies: dict[str, set[str]] = field(default_factory=dict)

    # URL ownership claims: url → URLClaim dict
    # Persists URL claims for incremental build safety (prevents shadowing by new content)
    # Structure: {url: {owner: str, source: str, priority: int, version: str | None, lang: str | None}}
    url_claims: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Config hash for auto-invalidation when configuration changes
    # Hash of resolved config dict (captures env vars, profiles, split configs)
    config_hash: str | None = None

    last_build: str | None = None

    def __post_init__(self) -> None:
        """Convert sets from lists after JSON deserialization."""
        # Convert dependency lists back to sets
        self.dependencies = {
            k: set(v) if isinstance(v, list) else v for k, v in self.dependencies.items()
        }
        # Convert taxonomy dependency lists back to sets
        self.taxonomy_deps = {
            k: set(v) if isinstance(v, list) else v for k, v in self.taxonomy_deps.items()
        }
        # Convert page tags lists back to sets
        self.page_tags = {
            k: set(v) if isinstance(v, list) else v for k, v in self.page_tags.items()
        }
        # Convert tag_to_pages lists back to sets
        self.tag_to_pages = {
            k: set(v) if isinstance(v, list) else v for k, v in self.tag_to_pages.items()
        }
        # Convert known_tags list back to set
        if isinstance(self.known_tags, list):
            self.known_tags = set(self.known_tags)
        # Convert autodoc_dependencies lists back to sets
        self.autodoc_dependencies = {
            k: set(v) if isinstance(v, list) else v for k, v in self.autodoc_dependencies.items()
        }
        # Parsed content is already in dict format (no conversion needed)
        # Synthetic pages is already in dict format (no conversion needed)
        # Validation results are already in dict format (no conversion needed)

    @classmethod
    def load(cls, cache_path: Path, use_lock: bool = True) -> BuildCache:
        """
        Load build cache from disk with optional file locking.

        Loader behavior:
        - Tolerant to malformed JSON: On parse errors or schema mismatches, returns a fresh
          `BuildCache` instance and logs a warning.
        - Version mismatches: Logs a warning and best-effort loads known fields.
        - File locking: Acquires shared lock to prevent reading during writes.

        Args:
            cache_path: Path to cache file
            use_lock: Whether to use file locking (default: True)

        Returns:
            BuildCache instance (empty if file doesn't exist or is invalid)
        """
        # Check both uncompressed and compressed paths
        compressed_path = cache_path.with_suffix(".json.zst")
        if not cache_path.exists() and not compressed_path.exists():
            return cls()

        try:
            # Acquire shared lock for reading (allows concurrent reads)
            if use_lock:
                from bengal.utils.file_lock import file_lock

                with file_lock(cache_path, exclusive=False):
                    return cls._load_from_file(cache_path)
            else:
                return cls._load_from_file(cache_path)

        except Exception as e:
            logger.warning(
                "cache_load_failed",
                cache_path=str(cache_path),
                error=str(e),
                error_type=type(e).__name__,
                action="using_fresh_cache",
            )
            return cls()

    @classmethod
    def _load_from_file(cls, cache_path: Path) -> BuildCache:
        """
        Internal method to load cache from file (assumes lock is held if needed).

        Auto-detects format: tries compressed (.json.zst) first, falls back to
        uncompressed (.json). This enables seamless migration.

        Args:
            cache_path: Path to cache file (base path, without .zst extension)

        Returns:
            BuildCache instance
        """
        try:
            # Try to load data (auto-detect format)
            data = cls._load_data_auto(cache_path)
            if data is None:
                return cls()

            # Tolerant versioning: accept missing version (pre-versioned files)
            found_version = data.get("version")
            if found_version is not None and found_version != cls.VERSION:
                logger.warning(
                    "cache_version_mismatch",
                    expected=cls.VERSION,
                    found=found_version,
                    action="loading_with_best_effort",
                )
                # Keep loading with best effort; fields below normalized

            # Convert lists back to sets in dependencies
            if "dependencies" in data:
                data["dependencies"] = {k: set(v) for k, v in data["dependencies"].items()}

            # Convert lists back to sets in tag_to_pages
            if "tag_to_pages" in data:
                data["tag_to_pages"] = {k: set(v) for k, v in data["tag_to_pages"].items()}

            # Convert list back to set in known_tags
            if "known_tags" in data and isinstance(data["known_tags"], list):
                data["known_tags"] = set(data["known_tags"])

            if "taxonomy_deps" in data:
                data["taxonomy_deps"] = {k: set(v) for k, v in data["taxonomy_deps"].items()}

            if "page_tags" in data:
                data["page_tags"] = {k: set(v) for k, v in data["page_tags"].items()}

            # Validation results (new in VERSION 2, tolerate missing)
            if "validation_results" not in data:
                data["validation_results"] = {}

            # Config hash (new in VERSION 3, tolerate missing)
            if "config_hash" not in data:
                data["config_hash"] = None

            # File fingerprints (new in VERSION 5, tolerate missing)
            if "file_fingerprints" not in data:
                data["file_fingerprints"] = {}

            # Autodoc dependencies (new, tolerate missing)
            if "autodoc_dependencies" not in data:
                data["autodoc_dependencies"] = {}
            else:
                # Convert lists back to sets
                data["autodoc_dependencies"] = {
                    k: set(v) for k, v in data["autodoc_dependencies"].items()
                }

            # Synthetic pages cache (tolerate missing)
            if "synthetic_pages" not in data or not isinstance(data["synthetic_pages"], dict):
                data["synthetic_pages"] = {}

            # URL claims (new, tolerate missing)
            if "url_claims" not in data or not isinstance(data["url_claims"], dict):
                data["url_claims"] = {}

            # Inject default version if missing
            if "version" not in data:
                data["version"] = cls.VERSION

            return cls(**data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(
                "cache_load_parse_failed",
                cache_path=str(cache_path),
                error=str(e),
                error_type=type(e).__name__,
                action="using_fresh_cache",
            )
            return cls()

    @classmethod
    def _load_data_auto(cls, cache_path: Path) -> dict[str, Any] | None:
        """
        Load raw data with auto-detection of format.

        Tries compressed format first (.json.zst), falls back to uncompressed (.json).

        Args:
            cache_path: Base path to cache file

        Returns:
            Parsed data dict, or None if load failed
        """
        # Try compressed first
        compressed_path = cache_path.with_suffix(".json.zst")
        if compressed_path.exists():
            try:
                from bengal.cache.compression import ZstdError, load_compressed

                logger.debug("cache_loading_compressed", path=str(compressed_path))
                return load_compressed(compressed_path)
            except (ZstdError, json.JSONDecodeError, OSError) as e:
                logger.warning(
                    "cache_compressed_load_failed",
                    path=str(compressed_path),
                    error=str(e),
                    action="trying_uncompressed",
                )

        # Fall back to uncompressed
        if cache_path.exists():
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)
                return dict(data) if isinstance(data, dict) else None

        return None

    def save(self, cache_path: Path, use_lock: bool = True) -> None:
        """
        Save build cache to disk with optional file locking.

        Persistence semantics:
        - Atomic writes: Uses `AtomicFile` (temp-write → atomic rename) to prevent partial files
          on crash/interruption.
        - File locking: Acquires exclusive lock to prevent concurrent writes.
        - Combined safety: Lock + atomic write ensures complete consistency.

        Args:
            cache_path: Path to cache file
            use_lock: Whether to use file locking (default: True)

        Raises:
            IOError: If cache file cannot be written
            json.JSONEncodeError: If cache data cannot be serialized
            LockAcquisitionError: If lock cannot be acquired (when use_lock=True)
        """
        # Ensure parent directory exists
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Acquire exclusive lock for writing
            if use_lock:
                from bengal.utils.file_lock import file_lock

                with file_lock(cache_path, exclusive=True):
                    self._save_to_file(cache_path)
            else:
                self._save_to_file(cache_path)

        except Exception as e:
            from bengal.errors import BengalCacheError, ErrorContext, enrich_error

            # Enrich error with context
            context = ErrorContext(
                file_path=cache_path,
                operation="saving build cache",
                suggestion="Check disk space and permissions. Cache will be rebuilt on next build.",
                original_error=e,
            )
            enriched = enrich_error(e, context, BengalCacheError)
            logger.error(
                "cache_save_failed",
                cache_path=str(cache_path),
                error=str(enriched),
                error_type=type(e).__name__,
                impact="incremental_builds_disabled",
            )

    def _save_to_file(self, cache_path: Path, compress: bool = True) -> None:
        """
        Internal method to save cache to file (assumes lock is held if needed).

        Uses Zstandard compression by default for 92-93% size reduction.

        Args:
            cache_path: Path to cache file (base path, will save as .json.zst)
            compress: Whether to use compression (default: True)
        """
        # Convert sets to lists for JSON serialization
        data = {
            "version": self.VERSION,
            "file_fingerprints": self.file_fingerprints,
            "dependencies": {k: list(v) for k, v in self.dependencies.items()},
            "output_sources": self.output_sources,
            "taxonomy_deps": {k: list(v) for k, v in self.taxonomy_deps.items()},
            "page_tags": {k: list(v) for k, v in self.page_tags.items()},
            "tag_to_pages": {k: list(v) for k, v in self.tag_to_pages.items()},  # Save tag index
            "known_tags": list(self.known_tags),  # Save known tags
            "parsed_content": self.parsed_content,  # Already in dict format
            "validation_results": self.validation_results,  # Already in dict format
            "autodoc_dependencies": {
                k: list(v) for k, v in self.autodoc_dependencies.items()
            },  # Autodoc source → pages
            # Cached synthetic payloads (e.g., autodoc elements)
            "synthetic_pages": self.synthetic_pages,
            "url_claims": self.url_claims,  # URL ownership claims (already dict format)
            "config_hash": self.config_hash,  # Config hash for auto-invalidation
            "last_build": datetime.now().isoformat(),
        }

        if compress:
            # Save compressed (92-93% size reduction)
            from bengal.cache.compression import save_compressed

            compressed_path = cache_path.with_suffix(".json.zst")
            save_compressed(data, compressed_path)

            logger.debug(
                "cache_saved_compressed",
                cache_path=str(compressed_path),
                tracked_files=len(self.file_fingerprints),
                dependencies=len(self.dependencies),
                cached_content=len(self.parsed_content),
            )
        else:
            # Write uncompressed (for debugging)
            from bengal.utils.atomic_write import AtomicFile

            with AtomicFile(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(
                "cache_saved",
                cache_path=str(cache_path),
                tracked_files=len(self.file_fingerprints),
                dependencies=len(self.dependencies),
                cached_content=len(self.parsed_content),
            )

    def clear(self) -> None:
        """Clear all cache data."""
        self.file_fingerprints.clear()
        self.dependencies.clear()
        self.output_sources.clear()
        self.taxonomy_deps.clear()
        self.page_tags.clear()
        self.tag_to_pages.clear()
        self.known_tags.clear()
        self.parsed_content.clear()
        self.rendered_output.clear()
        self.synthetic_pages.clear()
        self.validation_results.clear()
        self.autodoc_dependencies.clear()
        self.config_hash = None
        self.last_build = None

    def validate_config(self, current_hash: str) -> bool:
        """
        Check if cache is valid for the current configuration.

        Compares the stored config_hash with the current configuration hash.
        If they differ, the cache is automatically cleared to ensure correctness.

        This enables automatic cache invalidation when:
        - Configuration files change (bengal.toml, config/*.yaml)
        - Environment variables change (BENGAL_*)
        - Build profiles change (--profile writer)

        Args:
            current_hash: Hash of the current resolved configuration

        Returns:
            True if cache is valid (hashes match), False if cache was cleared

        Example:
            >>> from bengal.config.hash import compute_config_hash
            >>> config_hash = compute_config_hash(site.config)
            >>> if not cache.validate_config(config_hash):
            ...     logger.info("Config changed, performing full rebuild")
        """
        if self.config_hash is None:
            # First build with config hashing - store hash but don't invalidate
            logger.info(
                "config_hash_initialized",
                hash=current_hash[:8],
            )
            self.config_hash = current_hash
            return True

        if self.config_hash != current_hash:
            logger.info(
                "config_hash_changed",
                previous=self.config_hash[:8],
                current=current_hash[:8],
                action="invalidating_cache",
            )
            self.clear()
            self.config_hash = current_hash
            return False

        logger.debug(
            "config_hash_valid",
            hash=current_hash[:8],
        )
        return True

    def invalidate_file(self, file_path: Path) -> None:
        """
        Remove a file from all caches (useful when file is deleted).

        Extends FileTrackingMixin.invalidate_file with additional cache cleanup.

        Args:
            file_path: Path to file
        """
        file_key = str(file_path)

        # Call parent mixin for basic file tracking cleanup
        FileTrackingMixin.invalidate_file(self, file_path)

        # Remove from taxonomy deps
        for deps in self.taxonomy_deps.values():
            deps.discard(file_key)

        # Remove page tags
        self.page_tags.pop(file_key, None)

        # Remove parsed content cache
        self.parsed_content.pop(file_key, None)

        # Remove rendered output cache
        self.rendered_output.pop(file_key, None)

        # Remove synthetic page cache
        self.synthetic_pages.pop(file_key, None)

        # Remove validation results
        self.validation_results.pop(file_key, None)

    def get_stats(self) -> dict[str, int]:
        """
        Get cache statistics with logging.

        Returns:
            Dictionary with cache stats
        """
        stats = {
            "tracked_files": len(self.file_fingerprints),
            "dependencies": sum(len(deps) for deps in self.dependencies.values()),
            "taxonomy_terms": len(self.taxonomy_deps),
            "cached_content_pages": len(self.parsed_content),
            "cached_rendered_pages": len(self.rendered_output),
            "autodoc_source_files": len(self.autodoc_dependencies),
            "autodoc_pages_tracked": sum(
                len(pages) for pages in self.autodoc_dependencies.values()
            ),
        }

        logger.debug("cache_stats", **stats)
        return stats

    def get_page_cache(self, cache_key: str) -> dict[str, Any] | None:
        """
        Get cached data for a synthetic page.

        Args:
            cache_key: Unique cache key for the page

        Returns:
            Cached page data or None if not found
        """
        return self.synthetic_pages.get(cache_key)

    def set_page_cache(self, cache_key: str, page_data: dict[str, Any]) -> None:
        """
        Cache data for a synthetic page.

        Args:
            cache_key: Unique cache key for the page
            page_data: Page data to cache
        """
        self.synthetic_pages[cache_key] = page_data

    def invalidate_page_cache(self, cache_key: str) -> None:
        """
        Remove cached data for a synthetic page.

        Args:
            cache_key: Cache key to invalidate
        """
        self.synthetic_pages.pop(cache_key, None)

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"BuildCache(files={stats['tracked_files']}, "
            f"deps={stats['dependencies']}, "
            f"taxonomies={stats['taxonomy_terms']})"
        )
