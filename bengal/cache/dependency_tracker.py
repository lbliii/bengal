"""
Dependency tracker for build process dependency management.

Tracks template, partial, and data file dependencies during rendering to enable
incremental builds. Records dependencies in BuildCache for change detection
and selective rebuilding.

Key Concepts:
    - Dependency tracking: Template and data file dependencies per page
    - Thread-safe tracking: Thread-local storage for parallel rendering
    - Cache integration: Dependencies stored in BuildCache
    - Incremental builds: Dependency changes trigger selective rebuilds

Related Modules:
    - bengal.cache.build_cache: Build cache persistence
    - bengal.orchestration.incremental: Incremental build logic
    - bengal.rendering.pipeline: Rendering pipeline using dependency tracking

See Also:
    - bengal/cache/dependency_tracker.py:DependencyTracker for tracking logic
    - plan/active/rfc-incremental-builds.md: Incremental build design
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.cache.build_cache import BuildCache
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site


class CacheInvalidator:
    """
    Cache invalidation logic for incremental builds.

    Tracks invalidated paths based on content, template, and config changes.
    Provides methods for selective invalidation and full cache invalidation.

    Creation:
        Direct instantiation: CacheInvalidator(config_hash, content_paths, template_paths)
            - Created by DependencyTracker for cache invalidation
            - Requires config hash and path lists

    Attributes:
        config_hash: Hash of configuration for config change detection
        content_paths: List of content file paths
        template_paths: List of template file paths
        invalidated: Set of invalidated paths

    Relationships:
        - Used by: DependencyTracker for cache invalidation
        - Uses: Path sets for invalidation tracking

    Examples:
        invalidator = CacheInvalidator(config_hash, content_paths, template_paths)
        invalidated = invalidator.invalidate_content(changed_paths)
    """

    def __init__(self, config_hash: str, content_paths: list[Path], template_paths: list[Path]):
        self.config_hash = config_hash
        self.content_paths = content_paths
        self.template_paths = template_paths
        self.invalidated: set[Path] = set()

    def invalidate_content(self, changed_paths: set[Path]) -> set[Path]:
        """Invalidate on content changes."""
        self.invalidated.update(changed_paths)
        return self.invalidated

    def invalidate_templates(self, changed_paths: set[Path]) -> set[Path]:
        """Invalidate dependent pages on template changes."""
        affected = {p for p in self.content_paths if any(t in p.parents for t in changed_paths)}
        self.invalidated.update(affected)
        return self.invalidated

    def invalidate_config(self) -> set[Path]:
        """Full invalidation on config change."""
        self.invalidated = set(self.content_paths + self.template_paths)
        return self.invalidated

    @property
    def is_stale(self) -> bool:
        """Invariant: Check if cache needs rebuild."""
        return bool(self.invalidated)


class DependencyTracker:
    """
    Tracks dependencies between pages and their templates, partials, and config files.

    Records template and data file dependencies during rendering to enable incremental
    builds. Uses thread-local storage for thread-safe parallel rendering and maintains
    dependency graphs for change detection.

    Creation:
        Direct instantiation: DependencyTracker(cache, site=None)
            - Created by IncrementalOrchestrator for dependency tracking
            - Requires BuildCache instance for dependency storage

    Attributes:
        cache: BuildCache instance for dependency storage
        site: Optional Site instance for config path access
        logger: Logger instance for dependency tracking events
        tracked_files: Mapping of file paths to page paths
        dependencies: Forward dependency graph (page → dependencies)
        reverse_dependencies: Reverse dependency graph (dependency → pages)
        current_page: Thread-local current page being processed
        invalidator: CacheInvalidator for cache invalidation

    Relationships:
        - Uses: BuildCache for dependency persistence
        - Used by: RenderingPipeline for dependency tracking during rendering
        - Used by: IncrementalOrchestrator for change detection

    Thread Safety:
        Thread-safe. Uses thread-local storage for current page tracking and
        thread-safe locks for dependency graph updates.

    Examples:
        tracker = DependencyTracker(cache, site)
        tracker.start_page(page.source_path)
        tracker.record_dependency(template_path)
        tracker.end_page()
    """

    def __init__(self, cache: BuildCache, site: Site | None = None) -> None:
        """
        Initialize the dependency tracker.

        Args:
            cache: BuildCache instance to store dependencies in
            site: Optional Site instance to get config path from
        """
        self.cache = cache
        self.site = site
        self.logger = get_logger(__name__)
        self.tracked_files: dict[Path, str] = {}
        self.dependencies: dict[Path, set[Path]] = {}
        self.reverse_dependencies: dict[Path, set[Path]] = {}
        self.lock = threading.Lock()
        # Use thread-local storage for current page to support parallel processing
        self.current_page = threading.local()
        self.content_paths: list[Path] = []
        self.template_paths: list[Path] = []
        self.invalidator = CacheInvalidator(
            self._hash_config(), self.content_paths, self.template_paths
        )
        # Performance: avoid hashing/stat'ing the same dependency files (partials/templates)
        # repeatedly during a build. This tracker is shared across threads, so use
        # the existing lock for atomic check-and-add.
        self._dependency_files_updated: set[Path] = set()

    def _update_dependency_file_once(self, path: Path) -> None:
        """
        Update a dependency file in the cache at most once per build.

        `BuildCache.update_file()` can be expensive (stat + hash), and template rendering
        may reference the same partials hundreds/thousands of times across pages.
        """
        should_update = False
        with self.lock:
            if path not in self._dependency_files_updated:
                self._dependency_files_updated.add(path)
                should_update = True

        if should_update:
            self.cache.update_file(path)

    def _hash_config(self) -> str:
        """Hash config for invalidation."""
        from bengal.utils.hashing import hash_file

        # Determine config path from site or fallback
        config_path = self.site.root_path / "bengal.toml" if self.site else Path("bengal.toml")

        try:
            return hash_file(config_path)
        except FileNotFoundError:
            return "default_config_hash"  # Fallback for tests

    def start_page(self, page_path: Path) -> None:
        """
        Mark the start of processing a page (thread-safe).

        Args:
            page_path: Path to the page being processed
        """
        self.current_page.value = page_path
        # NOTE: Do NOT update file hash here - that would invalidate the cache
        # check that happens immediately after. File hashes are updated in
        # IncrementalOrchestrator.save_cache() AFTER successful rendering.

    def track_template(self, template_path: Path) -> None:
        """
        Record that the current page depends on a template (thread-safe).

        Args:
            template_path: Path to the template file
        """
        if not hasattr(self.current_page, "value"):
            return

        self.cache.add_dependency(self.current_page.value, template_path)
        self._update_dependency_file_once(template_path)

    def track_partial(self, partial_path: Path) -> None:
        """
        Record that the current page depends on a partial/include (thread-safe).

        Args:
            partial_path: Path to the partial file
        """
        if not hasattr(self.current_page, "value"):
            return

        self.cache.add_dependency(self.current_page.value, partial_path)
        self._update_dependency_file_once(partial_path)

    def track_config(self, config_path: Path) -> None:
        """
        Record that the current page depends on the config file (thread-safe).
        All pages depend on config, so this marks it as a global dependency.

        Args:
            config_path: Path to the config file
        """
        if not hasattr(self.current_page, "value"):
            return

        self.cache.add_dependency(self.current_page.value, config_path)
        self.cache.update_file(config_path)

    def track_asset(self, asset_path: Path) -> None:
        """
        Record an asset file (for cache invalidation).

        Args:
            asset_path: Path to the asset file
        """
        self.cache.update_file(asset_path)

    def track_taxonomy(self, page_path: Path, tags: set[str]) -> None:
        """
        Record taxonomy (tags/categories) dependencies.

        When a page's tags change, tag pages need to be regenerated.

        Args:
            page_path: Path to the page
            tags: Set of tags/categories for this page
        """
        for tag in tags:
            # Normalize tag
            tag_key = f"tag:{tag.lower().replace(' ', '-')}"
            self.cache.add_taxonomy_dependency(tag_key, page_path)

    def track_cross_version_link(
        self,
        source_page: Path,
        target_version: str,
        target_path: str,
    ) -> None:
        """
        Track dependency from source page to cross-version target.

        When the target page in another version changes, the source page
        should be rebuilt to update the cross-version link.

        RFC: rfc-versioned-docs-pipeline-integration (Phase 2)

        Args:
            source_page: Path to the page containing the cross-version link
            target_version: Version ID being linked to (e.g., "v2")
            target_path: Path within the target version (e.g., "docs/guide")

        Thread Safety:
            Uses existing lock for thread-safe dependency tracking.

        Example:
            When page "v3/docs/index.md" contains [[v2:docs/guide]]:
            >>> tracker.track_cross_version_link(
            ...     source_page=Path("content/docs/index.md"),
            ...     target_version="v2",
            ...     target_path="docs/guide",
            ... )
        """
        target_key = f"xver:{target_version}:{target_path}"

        with self.lock:
            if target_key not in self.reverse_dependencies:
                self.reverse_dependencies[target_key] = set()

            self.reverse_dependencies[target_key].add(str(source_page))

        self.logger.debug(
            "cross_version_link_tracked",
            source=str(source_page),
            target_version=target_version,
            target_path=target_path,
        )

    def get_cross_version_dependents(
        self,
        changed_version: str,
        changed_path: str,
    ) -> set[Path]:
        """
        Get pages that link to a changed cross-version target.

        When a page in version X changes, this method returns all pages
        that have cross-version links pointing to that page (from any version).

        RFC: rfc-versioned-docs-pipeline-integration (Phase 2)

        Args:
            changed_version: Version ID of the changed page (e.g., "v2")
            changed_path: Path of the changed page (e.g., "docs/guide")

        Returns:
            Set of page paths that should be rebuilt because they link
            to the changed cross-version target.

        Example:
            >>> dependents = tracker.get_cross_version_dependents("v2", "docs/guide")
            >>> # Returns {Path("content/docs/index.md")} if that page links to [[v2:docs/guide]]
        """
        target_key = f"xver:{changed_version}:{changed_path}"

        with self.lock:
            dependents = self.reverse_dependencies.get(target_key, set())
            return {Path(p) for p in dependents}

    def end_page(self) -> None:
        """Mark the end of processing a page (thread-safe)."""
        if hasattr(self.current_page, "value"):
            del self.current_page.value

    def get_changed_files(self, root_path: Path) -> set[Path]:
        """
        Get all files that have changed since the last build.

        Args:
            root_path: Root path of the site

        Returns:
            Set of paths that have changed
        """
        changed = set()

        # Check all tracked files
        for file_path_str in self.cache.file_fingerprints:
            file_path = Path(file_path_str)
            if file_path.exists() and self.cache.is_changed(file_path):
                changed.add(file_path)

        if changed:
            self.logger.info(
                "changed_files_detected",
                changed_count=len(changed),
                total_tracked=len(self.cache.file_fingerprints),
                change_ratio=f"{len(changed) / len(self.cache.file_fingerprints) * 100:.1f}%",
            )

        return changed

    def find_new_files(self, current_files: set[Path]) -> set[Path]:
        """
        Find files that are new (not in cache).

        Args:
            current_files: Set of current file paths

        Returns:
            Set of new file paths
        """
        tracked_files = {Path(f) for f in self.cache.file_fingerprints}
        new_files = current_files - tracked_files

        if new_files:
            self.logger.info(
                "new_files_detected", new_count=len(new_files), total_current=len(current_files)
            )

        return new_files

    def find_deleted_files(self, current_files: set[Path]) -> set[Path]:
        """
        Find files that were deleted (in cache but not on disk).

        Args:
            current_files: Set of current file paths

        Returns:
            Set of deleted file paths
        """
        tracked_files = {Path(f) for f in self.cache.file_fingerprints}
        deleted_files = tracked_files - current_files

        if deleted_files:
            self.logger.info(
                "deleted_files_detected",
                deleted_count=len(deleted_files),
                total_tracked=len(tracked_files),
            )

        return deleted_files
