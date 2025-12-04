"""
Build cache for tracking file changes and dependencies in incremental builds.

Maintains file hashes, dependency graphs, taxonomy indexes, and validation
results across builds. Uses JSON serialization for persistence and provides
tolerant loading for version migrations.

Key Concepts:
    - File hashes: SHA256 hashes for detecting content changes
    - Dependency tracking: Templates, partials, and data files used by pages
    - Taxonomy indexes: Tag/category mappings for fast reconstruction
    - Config hash: Auto-invalidation when configuration changes
    - Version tolerance: Accepts missing/older cache versions gracefully

Related Modules:
    - bengal.orchestration.incremental: Incremental build logic using cache
    - bengal.cache.dependency_tracker: Dependency graph construction
    - bengal.cache.taxonomy_index: Taxonomy reconstruction from cache

See Also:
    - bengal/cache/build_cache.py:BuildCache class for cache structure
    - plan/active/rfc-incremental-builds.md: Incremental build design
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BuildCache:
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
        file_hashes: Mapping of file paths to their SHA256 hashes
        dependencies: Mapping of pages to their dependencies (templates, partials, etc.)
        output_sources: Mapping of output files to their source files
        taxonomy_deps: Mapping of taxonomy terms to affected pages
        page_tags: Mapping of page paths to their tags (for detecting tag changes)
        tag_to_pages: Inverted index mapping tag slug to page paths (for O(1) reconstruction)
        known_tags: Set of all tag slugs from previous build (for detecting deletions)
        parsed_content: Cached parsed HTML/TOC (Optimization #2)
        config_hash: Hash of resolved configuration (for auto-invalidation)
        last_build: Timestamp of last successful build
    """

    # Serialized schema version (persisted in cache JSON). Tolerant loader accepts missing/older.
    VERSION: int = 4  # Bumped for AST caching (Phase 3 of RFC-content-ast-architecture)

    # Instance persisted version; defaults to current VERSION
    version: int = VERSION

    file_hashes: dict[str, str] = field(default_factory=dict)
    dependencies: dict[str, set[str]] = field(default_factory=dict)
    output_sources: dict[str, str] = field(default_factory=dict)
    taxonomy_deps: dict[str, set[str]] = field(default_factory=dict)
    page_tags: dict[str, set[str]] = field(default_factory=dict)

    # Inverted index for fast taxonomy reconstruction (NEW)
    tag_to_pages: dict[str, set[str]] = field(default_factory=dict)
    known_tags: set[str] = field(default_factory=set)

    parsed_content: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Synthetic page cache (for autodoc, etc.)
    synthetic_pages: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Validation result cache: file_path → validator_name → [CheckResult dicts]
    # Structure: {file_path: {validator_name: [CheckResult.to_cache_dict(), ...]}}
    validation_results: dict[str, dict[str, list[dict[str, Any]]]] = field(default_factory=dict)

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
        if not cache_path.exists():
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

        Args:
            cache_path: Path to cache file

        Returns:
            BuildCache instance
        """
        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)

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
            logger.error(
                "cache_save_failed",
                cache_path=str(cache_path),
                error=str(e),
                error_type=type(e).__name__,
                impact="incremental_builds_disabled",
            )

    def _save_to_file(self, cache_path: Path) -> None:
        """
        Internal method to save cache to file (assumes lock is held if needed).

        Args:
            cache_path: Path to cache file
        """
        # Convert sets to lists for JSON serialization
        data = {
            "version": self.VERSION,
            "file_hashes": self.file_hashes,
            "dependencies": {k: list(v) for k, v in self.dependencies.items()},
            "output_sources": self.output_sources,
            "taxonomy_deps": {k: list(v) for k, v in self.taxonomy_deps.items()},
            "page_tags": {k: list(v) for k, v in self.page_tags.items()},
            "tag_to_pages": {k: list(v) for k, v in self.tag_to_pages.items()},  # Save tag index
            "known_tags": list(self.known_tags),  # Save known tags
            "parsed_content": self.parsed_content,  # Already in dict format
            "validation_results": self.validation_results,  # Already in dict format
            "config_hash": self.config_hash,  # Config hash for auto-invalidation
            "last_build": datetime.now().isoformat(),
        }

        # Write cache atomically (crash-safe)
        from bengal.utils.atomic_write import AtomicFile

        with AtomicFile(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.debug(
            "cache_saved",
            cache_path=str(cache_path),
            tracked_files=len(self.file_hashes),
            dependencies=len(self.dependencies),
            cached_content=len(self.parsed_content),
        )

    def hash_file(self, file_path: Path) -> str:
        """
        Generate SHA256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hex string of SHA256 hash
        """
        hasher = hashlib.sha256()

        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.warning(
                "file_hash_failed",
                file_path=str(file_path),
                error=str(e),
                error_type=type(e).__name__,
                fallback="empty_hash",
            )
            return ""

    def is_changed(self, file_path: Path) -> bool:
        """
        Check if a file has changed since last build.

        Args:
            file_path: Path to file

        Returns:
            True if file is new or has changed, False if unchanged
        """
        if not file_path.exists():
            # File was deleted
            return True

        file_key = str(file_path)
        current_hash = self.hash_file(file_path)

        if file_key not in self.file_hashes:
            # New file
            return True

        # Check if hash changed
        return self.file_hashes[file_key] != current_hash

    def update_file(self, file_path: Path) -> None:
        """
        Update the hash for a file.

        Args:
            file_path: Path to file
        """
        file_key = str(file_path)
        self.file_hashes[file_key] = self.hash_file(file_path)

    def get_cached_validation_results(
        self, file_path: Path, validator_name: str
    ) -> list[dict[str, Any]] | None:
        """
        Get cached validation results for a file and validator.

        Args:
            file_path: Path to file
            validator_name: Name of validator

        Returns:
            List of CheckResult dicts if cached and file unchanged, None otherwise
        """
        file_key = str(file_path)

        # Check if file has changed
        if self.is_changed(file_path):
            # File changed - invalidate cached results
            if file_key in self.validation_results:
                del self.validation_results[file_key]
            return None

        # File unchanged - return cached results if available
        file_results = self.validation_results.get(file_key, {})
        return file_results.get(validator_name)

    def cache_validation_results(
        self, file_path: Path, validator_name: str, results: list[Any]
    ) -> None:
        """
        Cache validation results for a file and validator.

        Args:
            file_path: Path to file
            validator_name: Name of validator
            results: List of CheckResult objects to cache
        """
        file_key = str(file_path)

        # Ensure file entry exists
        if file_key not in self.validation_results:
            self.validation_results[file_key] = {}

        # Serialize CheckResult objects to dicts
        from bengal.health.report import CheckResult

        serialized_results = []
        for result in results:
            if isinstance(result, CheckResult):
                serialized_results.append(result.to_cache_dict())
            elif isinstance(result, dict):
                # Already serialized
                serialized_results.append(result)
            else:
                # Fallback: try to serialize
                serialized_results.append(
                    result.to_cache_dict() if hasattr(result, "to_cache_dict") else {}
                )

        self.validation_results[file_key][validator_name] = serialized_results

    def invalidate_validation_results(self, file_path: Path | None = None) -> None:
        """
        Invalidate validation results for a file or all files.

        Args:
            file_path: Path to file (if None, invalidate all)
        """
        if file_path is None:
            # Invalidate all
            self.validation_results.clear()
        else:
            # Invalidate specific file
            file_key = str(file_path)
            if file_key in self.validation_results:
                del self.validation_results[file_key]

    def track_output(self, source_path: Path, output_path: Path, output_dir: Path) -> None:
        """
        Track the relationship between a source file and its output file.

        This enables cleanup of output files when source files are deleted.

        Args:
            source_path: Path to source file (e.g., content/blog/post.md)
            output_path: Absolute path to output file (e.g., /path/to/public/blog/post/index.html)
            output_dir: Site output directory (e.g., /path/to/public)
        """
        # Store as relative path from output_dir for portability
        try:
            rel_output = str(output_path.relative_to(output_dir))
            self.output_sources[rel_output] = str(source_path)
        except ValueError:
            # output_path not relative to output_dir, skip
            logger.debug("output_not_relative", output=str(output_path), output_dir=str(output_dir))

    def add_dependency(self, source: Path, dependency: Path) -> None:
        """
        Record that a source file depends on another file.

        Args:
            source: Source file (e.g., content page)
            dependency: Dependency file (e.g., template, partial, config)
        """
        source_key = str(source)
        dep_key = str(dependency)

        if source_key not in self.dependencies:
            self.dependencies[source_key] = set()

        self.dependencies[source_key].add(dep_key)

    def add_taxonomy_dependency(self, taxonomy_term: str, page: Path) -> None:
        """
        Record that a taxonomy term affects a page.

        Args:
            taxonomy_term: Taxonomy term (e.g., "tag:python")
            page: Page that uses this taxonomy term
        """
        if taxonomy_term not in self.taxonomy_deps:
            self.taxonomy_deps[taxonomy_term] = set()

        self.taxonomy_deps[taxonomy_term].add(str(page))

    def get_affected_pages(self, changed_file: Path) -> set[str]:
        """
        Find all pages that depend on a changed file.

        Args:
            changed_file: File that changed

        Returns:
            Set of page paths that need to be rebuilt
        """
        changed_key = str(changed_file)
        affected = set()

        # Check direct dependencies
        for source, deps in self.dependencies.items():
            if changed_key in deps:
                affected.add(source)

        # If the changed file itself is a source, rebuild it
        if changed_key in self.dependencies:
            affected.add(changed_key)

        return affected

    def get_previous_tags(self, page_path: Path) -> set[str]:
        """
        Get tags from previous build for a page.

        Args:
            page_path: Path to page

        Returns:
            Set of tags from previous build (empty set if new page)
        """
        return self.page_tags.get(str(page_path), set())

    def update_tags(self, page_path: Path, tags: set[str]) -> None:
        """
        Store current tags for a page (for next build's comparison).

        Args:
            page_path: Path to page
            tags: Current set of tags for the page
        """
        self.page_tags[str(page_path)] = tags

    def update_page_tags(self, page_path: Path, tags: set[str]) -> set[str]:
        """
        Update tag index when a page's tags change.

        Maintains bidirectional index:
        - page_tags: path → tags (forward)
        - tag_to_pages: tag → paths (inverted)

        This is the key method that enables O(1) taxonomy reconstruction.

        Args:
            page_path: Path to page source file
            tags: Current set of tags for this page (original case, e.g., "Python", "Web Dev")

        Returns:
            Set of affected tag slugs (tags added, removed, or modified)
        """
        page_path_str = str(page_path)
        affected_tags = set()

        # Get old tags for this page
        old_tags = self.page_tags.get(page_path_str, set())
        old_slugs = {tag.lower().replace(" ", "-") for tag in old_tags}
        new_slugs = {tag.lower().replace(" ", "-") for tag in tags}

        # Find changes
        removed_slugs = old_slugs - new_slugs
        added_slugs = new_slugs - old_slugs
        unchanged_slugs = old_slugs & new_slugs

        # Remove page from old tags
        for tag_slug in removed_slugs:
            if tag_slug in self.tag_to_pages:
                self.tag_to_pages[tag_slug].discard(page_path_str)
                # Remove empty tag entries
                if not self.tag_to_pages[tag_slug]:
                    del self.tag_to_pages[tag_slug]
                    self.known_tags.discard(tag_slug)
            affected_tags.add(tag_slug)

        # Add page to new tags
        for tag_slug in added_slugs:
            self.tag_to_pages.setdefault(tag_slug, set()).add(page_path_str)
            self.known_tags.add(tag_slug)
            affected_tags.add(tag_slug)

        # Mark unchanged tags as affected if page content changed
        # (affects sort order, which affects tag page rendering)
        affected_tags.update(unchanged_slugs)

        # Update forward index
        self.page_tags[page_path_str] = tags

        return affected_tags

    def get_pages_for_tag(self, tag_slug: str) -> set[str]:
        """
        Get all page paths for a given tag.

        Args:
            tag_slug: Tag slug (e.g., 'python', 'web-dev')

        Returns:
            Set of page path strings
        """
        return self.tag_to_pages.get(tag_slug, set()).copy()

    def get_all_tags(self) -> set[str]:
        """
        Get all known tag slugs from previous build.

        Returns:
            Set of tag slugs
        """
        return self.known_tags.copy()

    def clear(self) -> None:
        """Clear all cache data."""
        self.file_hashes.clear()
        self.dependencies.clear()
        self.output_sources.clear()
        self.taxonomy_deps.clear()
        self.page_tags.clear()
        self.tag_to_pages.clear()
        self.known_tags.clear()
        self.synthetic_pages.clear()
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
        Remove a file from the cache (useful when file is deleted).

        Args:
            file_path: Path to file
        """
        file_key = str(file_path)
        self.file_hashes.pop(file_key, None)
        self.dependencies.pop(file_key, None)

        # Remove as a dependency from other files
        for deps in self.dependencies.values():
            deps.discard(file_key)

        # Remove from taxonomy deps
        for deps in self.taxonomy_deps.values():
            deps.discard(file_key)

        # Remove page tags
        self.page_tags.pop(file_key, None)

        # Remove synthetic page cache
        self.synthetic_pages.pop(file_key, None)

    def get_stats(self) -> dict[str, int]:
        """
        Get cache statistics with logging.

        Returns:
            Dictionary with cache stats
        """
        stats = {
            "tracked_files": len(self.file_hashes),
            "dependencies": sum(len(deps) for deps in self.dependencies.values()),
            "taxonomy_terms": len(self.taxonomy_deps),
            "cached_content_pages": len(self.parsed_content),
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

    # ========================================================================
    # OPTIMIZATION #2: Parsed Content Caching
    # ========================================================================

    def store_parsed_content(
        self,
        file_path: Path,
        html: str,
        toc: str,
        toc_items: list[dict[str, Any]],
        metadata: dict[str, Any],
        template: str,
        parser_version: str,
        ast: list[dict[str, Any]] | None = None,
    ) -> None:
        """
        Store parsed content in cache (Optimization #2 + AST caching).

        This allows skipping markdown parsing when only templates change,
        resulting in 20-30% faster builds in that scenario.

        Phase 3 Enhancement (RFC-content-ast-architecture):
        - Also caches the true AST for parse-once, use-many patterns
        - AST enables faster TOC/link extraction and plain text generation

        Args:
            file_path: Path to source file
            html: Rendered HTML (post-markdown, pre-template)
            toc: Table of contents HTML
            toc_items: Structured TOC data
            metadata: Page metadata (frontmatter)
            template: Template name used
            parser_version: Parser version string (e.g., "mistune-3.0-toc2")
            ast: True AST tokens from parser (optional, for Phase 3)
        """
        # Hash metadata to detect changes
        metadata_str = json.dumps(metadata, sort_keys=True, default=str)
        metadata_hash = hashlib.sha256(metadata_str.encode()).hexdigest()

        # Calculate size for cache management
        size_bytes = len(html.encode("utf-8")) + len(toc.encode("utf-8"))
        if ast:
            # Estimate AST size (JSON serialization)
            ast_str = json.dumps(ast, default=str)
            size_bytes += len(ast_str.encode("utf-8"))

        # Store as dict (will be serialized to JSON)
        self.parsed_content[str(file_path)] = {
            "html": html,
            "toc": toc,
            "toc_items": toc_items,
            "ast": ast,  # Phase 3: Store true AST tokens
            "metadata_hash": metadata_hash,
            "template": template,
            "parser_version": parser_version,
            "timestamp": datetime.now().isoformat(),
            "size_bytes": size_bytes,
        }

    def get_parsed_content(
        self, file_path: Path, metadata: dict[str, Any], template: str, parser_version: str
    ) -> dict[str, Any] | None:
        """
        Get cached parsed content if valid (Optimization #2).

        Validates that:
        1. Content file hasn't changed (via file_hashes)
        2. Metadata hasn't changed (via metadata_hash)
        3. Template hasn't changed (via template name)
        4. Parser version matches (avoid incompatibilities)
        5. Template file hasn't changed (via dependencies)

        Args:
            file_path: Path to source file
            metadata: Current page metadata
            template: Current template name
            parser_version: Current parser version

        Returns:
            Cached data dict if valid, None if invalid or not found
        """
        key = str(file_path)

        # Check if cached
        if key not in self.parsed_content:
            return None

        cached = self.parsed_content[key]

        # Validate file hasn't changed
        if self.is_changed(file_path):
            return None

        # Validate metadata hasn't changed
        metadata_str = json.dumps(metadata, sort_keys=True, default=str)
        metadata_hash = hashlib.sha256(metadata_str.encode()).hexdigest()
        if cached.get("metadata_hash") != metadata_hash:
            return None

        # Validate template hasn't changed (name)
        if cached.get("template") != template:
            return None

        # Validate parser version (invalidate on upgrades)
        if cached.get("parser_version") != parser_version:
            return None

        # Validate template file hasn't changed (via dependencies)
        # Check if any of the page's dependencies (templates) have changed
        if key in self.dependencies:
            for dep_path in self.dependencies[key]:
                dep = Path(dep_path)
                if dep.exists() and self.is_changed(dep):
                    # Template file changed - invalidate cache
                    return None

        return cached

    def invalidate_parsed_content(self, file_path: Path) -> None:
        """
        Remove cached parsed content for a file.

        Args:
            file_path: Path to file
        """
        self.parsed_content.pop(str(file_path), None)

    def get_parsed_content_stats(self) -> dict[str, Any]:
        """
        Get parsed content cache statistics.

        Returns:
            Dictionary with cache stats
        """
        if not self.parsed_content:
            return {"cached_pages": 0, "total_size_mb": 0, "avg_size_kb": 0}

        total_size = sum(c.get("size_bytes", 0) for c in self.parsed_content.values())
        return {
            "cached_pages": len(self.parsed_content),
            "total_size_mb": total_size / 1024 / 1024,
            "avg_size_kb": (total_size / len(self.parsed_content) / 1024)
            if self.parsed_content
            else 0,
        }
