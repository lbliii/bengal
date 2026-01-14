"""
Autodoc dependency tracking mixin for BuildCache.

Tracks which Python source files produce which autodoc pages, enabling
selective regeneration of autodoc pages when their source files change.

Key Concepts:
- Source file tracking: Maps Python/OpenAPI source files to autodoc page paths
- Selective invalidation: Only rebuild affected autodoc pages, not all
- Orphan cleanup: Remove autodoc pages when source files are deleted
- Self-validation: Validate source file hashes for CI cache correctness

Related Modules:
- bengal.autodoc.orchestration: Creates autodoc pages with dependencies
- bengal.orchestration.incremental: Uses dependency info for selective builds
- bengal.utils.hashing: Shared hashing utilities

See Also:
- plan/rfc-autodoc-incremental-builds.md: Design rationale
- plan/rfc-ci-cache-inputs.md: CI cache validation rationale

"""

from __future__ import annotations

from dataclasses import field
from pathlib import Path
from typing import Any

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


class AutodocTrackingMixin:
    """
    Track autodoc source file to page dependencies WITH hash validation.
    
    This mixin adds dependency tracking for autodoc pages, enabling selective
    rebuilds when only specific Python/OpenAPI source files change. It also
    provides self-validation capabilities to detect stale autodoc sources
    even when CI cache keys are incorrect.
    
    Attributes:
        autodoc_dependencies: Mapping of source_file path to set of autodoc page paths
            that are generated from that source file.
        autodoc_source_metadata: Mapping of source_file path to (content_hash, mtime)
            tuple for self-validation. The mtime-first optimization skips hash
            computation when mtime is unchanged.
        
    """

    # Mixin expects these to be defined in the main dataclass
    autodoc_dependencies: dict[str, set[str]] = field(default_factory=dict)

    # NEW: source_file → (content_hash, mtime) for self-validation
    # Using tuple allows mtime-first optimization (skip hash if mtime unchanged)
    autodoc_source_metadata: dict[str, tuple[str, float]] = field(default_factory=dict)

    def _normalize_source_path(self, source_file: Path | str, site_root: Path) -> str:
        """
        Normalize source path for consistent cache keys.

        Converts absolute paths to relative (from site parent) when possible.
        This ensures cache hits across different checkout locations.

        Args:
            source_file: Path to normalize
            site_root: Site root path for computing relative paths

        Returns:
            Normalized path string (relative when possible)
        """
        path = Path(source_file)
        if path.is_absolute():
            try:
                return str(path.relative_to(site_root.parent))
            except ValueError:
                # External path outside repo - keep absolute
                return str(path)
        return str(path)

    def add_autodoc_dependency(
        self,
        source_file: Path | str,
        autodoc_page: Path | str,
        site_root: Path | None = None,
        source_hash: str | None = None,
        source_mtime: float | None = None,
    ) -> None:
        """
        Register that source_file produces autodoc_page.

        Args:
            source_file: Path to the Python/OpenAPI source file
            autodoc_page: Path to the generated autodoc page (source_path)
            site_root: Site root path for normalization (optional, uses raw path if not provided)
            source_hash: Content hash for self-validation (optional)
            source_mtime: File mtime for fast staleness check (optional)
        """
        if site_root is not None:
            source_key = self._normalize_source_path(source_file, site_root)
        else:
            source_key = str(source_file)

        page_key = str(autodoc_page)

        if source_key not in self.autodoc_dependencies:
            self.autodoc_dependencies[source_key] = set()
        self.autodoc_dependencies[source_key].add(page_key)

        # Store metadata for self-validation (if provided)
        if source_hash is not None and source_mtime is not None:
            self.autodoc_source_metadata[source_key] = (source_hash, source_mtime)

        logger.debug(
            "autodoc_dependency_registered",
            source_file=source_key,
            autodoc_page=page_key,
            has_metadata=source_hash is not None,
        )

    def get_affected_autodoc_pages(self, changed_source: Path | str) -> set[str]:
        """
        Get autodoc pages affected by a source file change.

        Args:
            changed_source: Path to the changed Python/OpenAPI source file

        Returns:
            Set of autodoc page paths that need to be rebuilt
        """
        source_key = str(changed_source)
        return self.autodoc_dependencies.get(source_key, set())

    def get_autodoc_source_files(self) -> set[str]:
        """
        Get all tracked autodoc source files.

        Returns:
            Set of all source file paths that have autodoc dependencies
        """
        return set(self.autodoc_dependencies.keys())

    def clear_autodoc_dependencies(self) -> None:
        """
        Clear all autodoc dependency mappings.

        Called when autodoc configuration changes to ensure fresh mappings.
        """
        self.autodoc_dependencies.clear()
        self.autodoc_source_metadata.clear()
        logger.debug("autodoc_dependencies_cleared")

    def remove_autodoc_source(self, source_file: Path | str) -> set[str]:
        """
        Remove a source file and return its associated autodoc pages.

        Args:
            source_file: Path to the source file being removed

        Returns:
            Set of autodoc page paths that were associated with this source
        """
        source_key = str(source_file)
        removed_pages = self.autodoc_dependencies.pop(source_key, set())

        # Also remove metadata
        self.autodoc_source_metadata.pop(source_key, None)

        if removed_pages:
            logger.debug(
                "autodoc_source_removed",
                source_file=source_key,
                affected_pages=len(removed_pages),
            )

        return removed_pages

    def get_stale_autodoc_sources(self, site_root: Path) -> set[str]:
        """
        Validate autodoc sources and return paths that have changed.

        Uses mtime-first optimization: only computes hash if mtime changed.
        This enables cache self-validation independent of CI cache keys.

        This method provides defense-in-depth: even if CI cache keys are
        incorrect, Bengal will detect stale autodoc sources and rebuild
        affected pages.

        RFC: rfc-incremental-build-observability
        When BENGAL_STRICT_INCREMENTAL is set to 'warn' or 'error', this
        method will log warnings or raise errors when fallback paths are used.

        Args:
            site_root: Site root path for resolving relative paths

        Returns:
            Set of source file paths whose content has changed since caching
        """
        from bengal.config.environment import (
            StrictIncrementalMode,
            get_strict_incremental_mode,
        )
        from bengal.utils.primitives.hashing import hash_file

        # Handle cache migration: old caches have dependencies but no metadata
        # Instead of marking all as stale (which triggers full autodoc rebuild),
        # use file fingerprints as fallback if they exist.
        if not self.autodoc_source_metadata and self.autodoc_dependencies:
            # RFC: rfc-incremental-build-observability - Strict mode check
            mode = get_strict_incremental_mode()

            if mode == StrictIncrementalMode.ERROR:
                from bengal.errors import BengalCacheError

                raise BengalCacheError(
                    "Autodoc source metadata empty but dependencies present.\n"
                    "This triggers fingerprint fallback which may be slower.\n"
                    "Fix: Ensure metadata is saved via add_autodoc_dependency().\n"
                    "Disable check: unset BENGAL_STRICT_INCREMENTAL"
                )
            elif mode == StrictIncrementalMode.WARN:
                logger.warning(
                    "autodoc_metadata_fallback",
                    msg="Using fingerprint fallback (metadata unavailable)",
                    source_count=len(self.autodoc_dependencies),
                    hint="Set BENGAL_STRICT_INCREMENTAL=error to make this an error",
                )

            # Check if we have fingerprints to use as fallback
            has_fingerprints = hasattr(self, 'file_fingerprints') and self.file_fingerprints
            if has_fingerprints:
                # Use fingerprint-based change detection instead
                stale_sources: set[str] = set()
                for source_key in self.autodoc_dependencies:
                    source = Path(source_key)
                    # Use is_changed() which checks fingerprints
                    if hasattr(self, 'is_changed') and self.is_changed(source):
                        stale_sources.add(source_key)
                if stale_sources:
                    logger.debug(
                        "autodoc_cache_migration_with_fingerprints",
                        msg="Using fingerprints for change detection (metadata unavailable)",
                        stale_count=len(stale_sources),
                        total_sources=len(self.autodoc_dependencies),
                    )
                return stale_sources
            else:
                # No fingerprints either - mark all stale (truly cold cache)
                logger.info(
                    "autodoc_cache_migration",
                    msg="No source metadata or fingerprints found, marking all autodoc stale",
                    source_count=len(self.autodoc_dependencies),
                )
                return set(self.autodoc_dependencies.keys())

        stale_sources: set[str] = set()

        for source_key, (stored_hash, stored_mtime) in self.autodoc_source_metadata.items():
            # Resolve path - keys are normalized relative to site PARENT
            # (since autodoc sources are typically outside site root, e.g., ../bengal/)
            if Path(source_key).is_absolute():
                source = Path(source_key)
            else:
                # All relative keys are relative to site parent
                source = site_root.parent / source_key

            if not source.exists():
                # Source deleted - mark as stale for cleanup
                stale_sources.add(source_key)
                logger.debug(
                    "autodoc_source_deleted",
                    source_key=source_key,
                )
                continue

            try:
                # mtime-first optimization: skip hash if mtime unchanged
                current_mtime = source.stat().st_mtime
                if current_mtime == stored_mtime:
                    continue  # Fast path: file unchanged

                # mtime changed - verify with hash (handles touch without content change)
                current_hash = hash_file(source, truncate=16)
                if current_hash != stored_hash:
                    stale_sources.add(source_key)
                    logger.debug(
                        "autodoc_source_changed",
                        source_key=source_key,
                        stored_hash=stored_hash[:8],
                        current_hash=current_hash[:8],
                    )
                else:
                    # Content unchanged, update mtime in metadata
                    self.autodoc_source_metadata[source_key] = (stored_hash, current_mtime)
            except OSError as e:
                # Can't read file - mark as stale to be safe
                logger.warning(
                    "autodoc_source_read_error",
                    source_key=source_key,
                    error=str(e),
                )
                stale_sources.add(source_key)

        if stale_sources:
            logger.info(
                "stale_autodoc_sources_detected",
                count=len(stale_sources),
                sources=list(stale_sources)[:5],
            )

        return stale_sources

    def get_autodoc_stats(self) -> dict[str, Any]:
        """
        Get statistics about autodoc dependency tracking.

        Returns:
            Dictionary with tracking stats including source count,
            page count, and metadata coverage.
        """
        total_sources = len(self.autodoc_dependencies)
        total_pages = sum(len(pages) for pages in self.autodoc_dependencies.values())
        sources_with_metadata = len(self.autodoc_source_metadata)

        return {
            "autodoc_source_files": total_sources,
            "autodoc_pages_tracked": total_pages,
            "sources_with_metadata": sources_with_metadata,
            "metadata_coverage_pct": (
                round(sources_with_metadata / total_sources * 100, 1)
                if total_sources > 0
                else 100.0
            ),
        }
