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
- bengal.build.pipeline: Change detection pipeline
- bengal.orchestration.incremental.cleanup: Deleted file cleanup
- bengal.core.nav_tree: NavTreeCache for cached navigation

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.build.contracts.keys import CacheKey, content_key, data_key
from bengal.build.contracts.protocol import DetectionContext
from bengal.build.detectors.base import key_to_path
from bengal.build.pipeline import create_early_pipeline, create_full_pipeline
from bengal.orchestration.build.results import ChangeSummary
from bengal.orchestration.incremental.cache_manager import CacheManager
from bengal.orchestration.incremental.cleanup import cleanup_deleted_files
from bengal.orchestration.build_context import BuildContext
from bengal.utils.cache_registry import InvalidationReason, invalidate_for_reason
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache import BuildCache
    from bengal.build.tracking import DependencyTracker
    from bengal.orchestration.build.coordinator import CacheCoordinator
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
        - DetectionPipeline: Change detection via bengal.build.pipeline
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
        _early_pipeline/_full_pipeline: Detection pipelines (lazy)
    
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
        self._early_pipeline = None
        self._full_pipeline = None

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
        # Reset pipelines so they pick up the new cache
        self._early_pipeline = None
        self._full_pipeline = None
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

        change_set = self._run_pipeline(
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

        pages_to_build, assets_to_process, change_summary = self._convert_result(change_set)
        return pages_to_build, assets_to_process, change_summary

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

        change_set = self._run_pipeline(phase="full", verbose=verbose)
        pages_to_build, assets_to_process, change_summary = self._convert_result(change_set)

        summary_dict: dict[str, list[Any]] = {
            "Modified content": list(change_summary.modified_content),
            "Modified assets": list(change_summary.modified_assets),
            "Modified templates": list(change_summary.modified_templates),
            "Taxonomy changes": change_summary.taxonomy_changes,
        }
        return pages_to_build, assets_to_process, summary_dict

    def _run_pipeline(
        self,
        *,
        phase: str,
        verbose: bool,
        forced_changed_sources: set[Path] | None = None,
        nav_changed_sources: set[Path] | None = None,
    ):
        forced_keys = self._build_forced_keys(forced_changed_sources or set())
        nav_keys = self._build_forced_keys(nav_changed_sources or set())
        ctx = DetectionContext(
            cache=self.cache,
            site=self.site,
            tracker=self.tracker,
            coordinator=self.coordinator,
            verbose=verbose,
            forced_changed=forced_keys,
            nav_changed=nav_keys,
        )

        if phase == "early":
            if self._early_pipeline is None:
                self._early_pipeline = create_early_pipeline()
            return self._early_pipeline.run(ctx)

        if self._early_pipeline is None:
            self._early_pipeline = create_early_pipeline()
        early_result = self._early_pipeline.run(ctx)
        full_ctx = DetectionContext(
            cache=self.cache,
            site=self.site,
            tracker=self.tracker,
            coordinator=self.coordinator,
            verbose=verbose,
            forced_changed=forced_keys,
            nav_changed=nav_keys,
            previous=early_result,
        )
        if self._full_pipeline is None:
            self._full_pipeline = create_full_pipeline()
        return self._full_pipeline.run(full_ctx)

    def _build_forced_keys(self, paths: set[Path]) -> frozenset[CacheKey]:
        keys: set[CacheKey] = set()
        for path in paths:
            key = content_key(path, self.site.root_path)
            keys.add(key)
            try:
                path.resolve().relative_to((self.site.root_path / "data").resolve())
            except ValueError:
                continue
            keys.add(data_key(path, self.site.root_path))
        return frozenset(keys)

    def _convert_result(self, result):
        pages_by_path = self.site.page_by_source_path
        assets_by_path = {asset.source_path: asset for asset in self.site.assets}

        pages_to_build: list[Page] = []
        assets_to_process: list[Asset] = []

        for key in result.pages_to_rebuild:
            path = key_to_path(self.site.root_path, key)
            page = pages_by_path.get(path)
            if page is None:
                # Fallback to scan when cache map isn't populated.
                page = next((p for p in self.site.pages if p.source_path == path), None)
            if page is not None:
                pages_to_build.append(page)

        for key in result.assets_to_process:
            path = key_to_path(self.site.root_path, key)
            asset = assets_by_path.get(path)
            if asset is not None:
                assets_to_process.append(asset)

        change_summary = ChangeSummary(
            modified_content=[
                key_to_path(self.site.root_path, key) for key in result.content_files_changed
            ],
            modified_assets=[
                key_to_path(self.site.root_path, key) for key in result.assets_to_process
            ],
            modified_templates=[
                key_to_path(self.site.root_path, key) for key in result.templates_changed
            ],
            taxonomy_changes=list(result.affected_tags),
        )

        if result.data_files_changed:
            change_summary.extra_changes["Data file changes"] = [
                str(key_to_path(self.site.root_path, key)) for key in result.data_files_changed
            ]

        return pages_to_build, assets_to_process, change_summary

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
