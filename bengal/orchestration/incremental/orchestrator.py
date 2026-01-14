"""
Main IncrementalOrchestrator coordinating incremental build components.

This module provides the IncrementalOrchestrator class that coordinates
cache management, change detection, and rebuild filtering through specialized
component classes.

Key Concepts:
- Component delegation: Work delegated to focused component classes
- Phase-based detection: Early (pre-taxonomy) and full (post-taxonomy)

Related Modules:
- bengal.orchestration.incremental.cache_manager: Cache operations
- bengal.orchestration.incremental.change_detector: Change detection
- bengal.orchestration.incremental.cleanup: Deleted file cleanup
- bengal.core.nav_tree: NavTreeCache for cached navigation

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.orchestration.build.results import ChangeSummary
from bengal.orchestration.incremental.cache_manager import CacheManager
from bengal.orchestration.incremental.change_detector import ChangeDetector
from bengal.orchestration.incremental.cleanup import cleanup_deleted_files
from bengal.orchestration.build_context import BuildContext
from bengal.utils.cache_registry import InvalidationReason, invalidate_for_reason
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache import BuildCache, CacheCoordinator, DependencyTracker
    from bengal.core.asset import Asset
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


class IncrementalOrchestrator:
    """
    Orchestrates incremental build logic for efficient rebuilds.
    
    Coordinates cache management, change detection, dependency tracking, and
    selective rebuilding through specialized component classes. Uses file hashes,
    dependency graphs, and taxonomy indexes to minimize rebuild work.
    
    Component Delegation:
        - CacheManager: Cache loading, saving, and migration
        - ChangeDetector: Unified change detection with phase parameter
        - cleanup: Deleted file cleanup
    
    Creation:
        Direct instantiation: IncrementalOrchestrator(site)
            - Created by BuildOrchestrator when incremental builds enabled
            - Requires Site instance with content populated
    
    Attributes:
        site: Site instance for incremental builds
        cache: BuildCache instance for build state persistence
        tracker: DependencyTracker instance for dependency graph construction
        _cache_manager: CacheManager instance for cache operations
        _change_detector: ChangeDetector instance for change detection (lazy)
    
    Example:
            >>> orchestrator = IncrementalOrchestrator(site)
            >>> cache, tracker = orchestrator.initialize(enabled=True)
            >>> pages, assets, summary = orchestrator.find_work_early()
        
    """

    def __init__(self, site: Site) -> None:
        """
        Initialize incremental orchestrator.

        Args:
            site: Site instance for incremental builds
        """
        self.site = site
        self.cache: BuildCache | None = None
        self.tracker: DependencyTracker | None = None
        self.coordinator: CacheCoordinator | None = None

        # Component instances
        self._cache_manager = CacheManager(site)
        self._change_detector: ChangeDetector | None = None

    def initialize(self, enabled: bool = False) -> tuple[BuildCache, DependencyTracker]:
        """
        Initialize cache and dependency tracker for incremental builds.

        Delegates to CacheManager for cache operations.

        Args:
            enabled: Whether incremental builds are enabled

        Returns:
            Tuple of (BuildCache, DependencyTracker) instances
        """
        self.cache, self.tracker = self._cache_manager.initialize(enabled)
        # Expose coordinator for use by detectors
        self.coordinator = self._cache_manager.coordinator
        return self.cache, self.tracker

    def check_config_changed(self) -> bool:
        """
        Check if configuration has changed (requires full rebuild).

        Delegates to CacheManager for config validation. If config changed,
        uses centralized cache registry to invalidate all CONFIG_CHANGED caches.

        Returns:
            True if config changed (cache was invalidated)
        """
        # Sync cache state with cache manager
        self._cache_manager.cache = self.cache
        config_changed = self._cache_manager.check_config_changed()

        if config_changed:
            # Use centralized cache registry for coordinated invalidation
            # This replaces manual NavTreeCache.invalidate() + invalidate_version_page_index()
            invalidated = invalidate_for_reason(InvalidationReason.CONFIG_CHANGED)
            logger.debug("caches_invalidated", reason="config_changed", caches=invalidated)

            # Invalidate site version dict caches (site.versions, site.latest_version)
            # These cache .to_dict() results for template performance
            # Note: Site caches aren't in the registry (they're instance-level, not global)
            if hasattr(self.site, "invalidate_version_caches"):
                self.site.invalidate_version_caches()
                logger.debug("site_version_dict_cache_invalidated", reason="config_changed")

        return config_changed

    def find_work_early(
        self,
        verbose: bool = False,
        forced_changed_sources: set[Path] | None = None,
        nav_changed_sources: set[Path] | None = None,
    ) -> tuple[list[Page], list[Asset], ChangeSummary]:
        """
        Find pages/assets that need rebuilding (early phase - before taxonomy).

        This is called BEFORE taxonomies/menus are generated, so it only checks
        content/asset changes. Generated pages will be determined later.

        Invalidates NavTreeCache when structural changes are detected:
        - New pages added
        - Pages deleted
        - Navigation-affecting metadata changed (title, weight, icon)

        Args:
            verbose: Whether to collect detailed change information
            forced_changed_sources: Paths explicitly changed (from watcher)
            nav_changed_sources: Paths with navigation-affecting changes

        Returns:
            Tuple of (pages_to_build, assets_to_process, change_summary)
        """
        if not self.cache or not self.tracker:
            from bengal.errors import BengalError, ErrorCode

            raise BengalError(
                "Cache not initialized - call initialize() first",
                code=ErrorCode.B010,
                suggestion="Call IncrementalBuildOrchestrator.initialize() before using this method",
            )

        # Lazy initialization of change detector
        if self._change_detector is None:
            self._change_detector = ChangeDetector(self.site, self.cache, self.tracker)

        change_set = self._change_detector.detect_changes(
            phase="early",
            verbose=verbose,
            forced_changed_sources=forced_changed_sources,
            nav_changed_sources=nav_changed_sources,
        )

        # Invalidate caches if structural changes detected
        # Structural changes: new/deleted pages or nav-affecting metadata
        has_structural_changes = bool(change_set.change_summary.modified_content) or bool(
            nav_changed_sources
        )
        if has_structural_changes:
            # Use centralized cache registry for coordinated invalidation
            invalidated = invalidate_for_reason(InvalidationReason.STRUCTURAL_CHANGE)
            logger.debug("caches_invalidated", reason="structural_changes", caches=invalidated)

        return (
            change_set.pages_to_build,
            change_set.assets_to_process,
            change_set.change_summary,
        )

    def find_work(
        self, verbose: bool = False
    ) -> tuple[list[Page], list[Asset], dict[str, list[Any]]]:
        """
        Find pages/assets that need rebuilding (full phase - after taxonomy).

        This is called AFTER taxonomies/menus are generated, so it can include
        generated pages in the rebuild set based on tag changes.

        Args:
            verbose: Whether to collect detailed change information

        Returns:
            Tuple of (pages_to_build, assets_to_process, change_summary)
        """
        if not self.cache or not self.tracker:
            from bengal.errors import BengalError, ErrorCode

            raise BengalError(
                "Cache not initialized - call initialize() first",
                code=ErrorCode.B010,
                suggestion="Call IncrementalBuildOrchestrator.initialize() before using this method",
            )

        # Lazy initialization of change detector
        if self._change_detector is None:
            self._change_detector = ChangeDetector(self.site, self.cache, self.tracker)

        change_set = self._change_detector.detect_changes(
            phase="full",
            verbose=verbose,
        )

        summary_dict: dict[str, list[Any]] = {
            "Modified content": list(change_set.change_summary.modified_content),
            "Modified assets": list(change_set.change_summary.modified_assets),
            "Modified templates": list(change_set.change_summary.modified_templates),
            "Taxonomy changes": change_set.change_summary.extra_changes.get("Taxonomy changes", []),
        }

        return change_set.pages_to_build, change_set.assets_to_process, summary_dict

    def process(self, change_type: str, changed_paths: set[str]) -> None:
        """
        Bridge-style process for testing incremental invalidation.

        ⚠️  TEST BRIDGE ONLY - See docstring for details.
        """
        if not self.tracker:
            from bengal.errors import BengalError, ErrorCode

            raise BengalError(
                "Tracker not initialized - call initialize() first",
                code=ErrorCode.B010,
                suggestion="Call IncrementalBuildOrchestrator.initialize() before using this method",
            )

        import sys

        if "pytest" not in sys.modules:
            logger.warning(
                "IncrementalOrchestrator.process() is a test bridge. "
                "Use run() or full_build() for production builds."
            )

        context = BuildContext(site=self.site, pages=self.site.pages, tracker=self.tracker)

        path_set: set[Path] = {Path(p) for p in changed_paths}
        invalidated: set[Path]
        if change_type == "content":
            invalidated = self.tracker.invalidator.invalidate_content(path_set)
        elif change_type == "template":
            invalidated = self.tracker.invalidator.invalidate_templates(path_set)
        elif change_type == "config":
            invalidated = self.tracker.invalidator.invalidate_config()
        else:
            invalidated = set()

        for path in invalidated:
            self._write_output(path, context)

    def _write_output(self, path: Path, context: BuildContext) -> None:
        """Write placeholder output for test bridge."""
        import datetime

        content_dir = self.site.root_path / "content"
        rel: Path | str
        try:
            rel = path.relative_to(content_dir)
        except ValueError:
            rel = path.name

        from pathlib import Path as _P

        rel_html = _P(rel).with_suffix(".html")
        if rel_html.stem in ("index", "_index"):
            rel_html = rel_html.parent / "index.html"
        else:
            rel_html = rel_html.parent / rel_html.stem / "index.html"

        output_path = self.site.output_dir / rel_html
        output_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().isoformat()
        diagnostic_content = (
            f"[TEST BRIDGE] Updated at {timestamp}\nSource: {path}\nOutput: {rel_html}"
        )
        output_path.write_text(diagnostic_content)

    def full_rebuild(self, pages: list[Any], context: BuildContext) -> None:
        """Full rebuild placeholder (unused)."""
        pass

    def _cleanup_deleted_files(self) -> None:
        """Clean up output files for deleted source files."""
        if self.cache:
            cleanup_deleted_files(self.site, self.cache)

    def save_cache(self, pages_built: list[Page], assets_processed: list[Asset]) -> None:
        """
        Update cache with processed files.

        Delegates to CacheManager.

        Args:
            pages_built: Pages that were built
            assets_processed: Assets that were processed
        """
        self._cache_manager.cache = self.cache
        self._cache_manager.save(pages_built, assets_processed)

    def _check_shared_content_changes(
        self, forced_changed_sources: set[Path] | None = None
    ) -> bool:
        """
        Check if any _shared/ content has changed.

        When shared content changes, ALL versioned pages need rebuilding since
        shared content is injected into every version.

        Args:
            forced_changed_sources: Optional set of paths explicitly changed

        Returns:
            True if any shared content has changed
        """
        if not self.site.versioning_enabled:
            return False

        if not self.cache:
            return False

        version_config = getattr(self.site, "version_config", None)
        if not version_config:
            return False

        # Check if any forced changes are in shared paths
        content_dir = self.site.root_path / "content"
        if forced_changed_sources:
            for path in forced_changed_sources:
                for shared_path in version_config.shared:
                    shared_dir = content_dir / shared_path
                    try:
                        path.relative_to(shared_dir)
                        return True  # Path is in shared dir
                    except ValueError:
                        continue

        # Check if any shared files have changed via cache
        for shared_path in version_config.shared:
            shared_dir = content_dir / shared_path
            if not shared_dir.exists():
                continue

            for file_path in shared_dir.rglob("*.md"):
                if self.cache.is_changed(file_path):
                    return True

        return False
