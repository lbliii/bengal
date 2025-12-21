"""
File tracking mixin for BuildCache.

Provides methods for tracking file changes, hashing, and dependency management.
Used as a mixin by the main BuildCache class.

Key Concepts:
    - File fingerprints: mtime + size for fast change detection
    - SHA256 hashing: Reliable content change detection
    - Dependency tracking: Template, partial, and data file dependencies
    - Output tracking: Source → output file mapping for cleanup

Related Modules:
    - bengal.cache.build_cache.core: Main BuildCache class
    - bengal.orchestration.incremental: Incremental build logic
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.hashing import hash_file
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class FileTrackingMixin:
    """
    Mixin providing file tracking, hashing, and dependency management.

    Requires these attributes on the host class:
        - file_fingerprints: dict[str, dict[str, Any]]
        - dependencies: dict[str, set[str]]
        - output_sources: dict[str, str]
    """

    # Type hints for mixin attributes (provided by host class)
    file_fingerprints: dict[str, dict[str, Any]]
    dependencies: dict[str, set[str]]
    output_sources: dict[str, str]

    def hash_file(self, file_path: Path) -> str:
        """
        Generate SHA256 hash of a file.

        Delegates to centralized hash_file utility for consistent behavior.

        Args:
            file_path: Path to file

        Returns:
            Hex string of SHA256 hash
        """
        try:
            return hash_file(file_path)
        except Exception as e:
            logger.warning(
                "file_hash_failed",
                file_path=str(file_path),
                error=str(e),
                error_type=type(e).__name__,
                fallback="empty_hash",
            )
            return ""

    def should_bypass(self, source_path: Path, changed_sources: set[Path] | None = None) -> bool:
        """
        Determine if cache should be bypassed for a source file.

        This is the single source of truth for cache bypass decisions
        (RFC: rfc-incremental-hot-reload-invariants).

        Cache bypass is required when:
        1. File is in the changed_sources set (explicit change from file watcher)
        2. File hash differs from cached hash (is_changed check)

        Args:
            source_path: Path to source file
            changed_sources: Set of paths explicitly marked as changed (from file watcher)

        Returns:
            True if cache should be bypassed, False if cache can be used
        """
        # Check explicit change set first (fast path)
        if changed_sources and source_path in changed_sources:
            return True

        # Fall back to hash-based change detection
        return self.is_changed(source_path)

    def is_changed(self, file_path: Path) -> bool:
        """
        Check if a file has changed since last build.

        Performance Optimization (RFC: orchestrator-performance-improvements):
            - Fast path: mtime + size check (single stat call, no file read)
            - Slow path: SHA256 hash only when mtime/size mismatch detected
            - Handles edge cases: touch/rsync may change mtime but not content

        Note:
            Prefer using should_bypass() which combines this check with
            changed_sources for correct incremental build behavior.

        Args:
            file_path: Path to file

        Returns:
            True if file is new or has changed, False if unchanged
        """
        if not file_path.exists():
            # File was deleted
            return True

        file_key = str(file_path)

        # Check fingerprint first (fast path)
        if file_key in self.file_fingerprints:
            cached = self.file_fingerprints[file_key]
            try:
                stat = file_path.stat()

                # Fast path: mtime + size unchanged = definitely no change
                if cached.get("mtime") == stat.st_mtime and cached.get("size") == stat.st_size:
                    return False

                # mtime or size changed - verify with hash (handles touch/rsync)
                cached_hash = cached.get("hash")
                if cached_hash:
                    current_hash = self.hash_file(file_path)
                    if current_hash == cached_hash:
                        # Content unchanged despite mtime change (e.g., touch)
                        # Update mtime/size in fingerprint for future fast path
                        self.file_fingerprints[file_key] = {
                            "mtime": stat.st_mtime,
                            "size": stat.st_size,
                            "hash": cached_hash,
                        }
                        return False
                    return True  # Hash differs, file changed

                # No cached hash, fall through to treat as changed
                return True

            except OSError:
                # Can't stat file, treat as changed
                return True

        # New file (not in any cache)
        return True

    def update_file(self, file_path: Path) -> None:
        """
        Update the fingerprint for a file (mtime + size + hash).

        Performance Optimization:
            Stores full fingerprint for fast change detection on subsequent builds.
            Uses mtime + size for fast path, hash for verification.

        Args:
            file_path: Path to file
        """
        file_key = str(file_path)

        try:
            stat = file_path.stat()
            file_hash = self.hash_file(file_path)

            # Store full fingerprint
            self.file_fingerprints[file_key] = {
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "hash": file_hash,
            }

        except FileNotFoundError:
            # File was deleted - remove from tracking silently
            # This commonly happens when switching from markdown-based autodoc to virtual pages
            if file_key in self.file_fingerprints:
                del self.file_fingerprints[file_key]
            logger.debug(
                "file_removed_from_tracking",
                file_path=str(file_path),
                reason="file_not_found",
            )
        except OSError as e:
            logger.warning(
                "file_update_failed",
                file_path=str(file_path),
                error=str(e),
                error_type=type(e).__name__,
            )

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

    def invalidate_file(self, file_path: Path) -> None:
        """
        Remove a file from the cache (useful when file is deleted).

        Note: This is a partial invalidation. Full invalidation of related
        caches (parsed_content, rendered_output, etc.) should be handled
        by the main BuildCache class.

        Args:
            file_path: Path to file
        """
        file_key = str(file_path)
        self.file_fingerprints.pop(file_key, None)
        self.dependencies.pop(file_key, None)

        # Remove as a dependency from other files
        for deps in self.dependencies.values():
            deps.discard(file_key)
