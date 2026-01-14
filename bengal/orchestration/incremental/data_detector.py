"""
Data file change detection for incremental builds.

Detects changes to data/*.yaml files and determines which pages
need to be rebuilt based on data file dependencies.

Key Concepts:
- Data file changes: mtime/hash-based detection for .yaml/.json/.toml files
- Dependency lookup: Find pages that used changed data files
- Conservative fallback: Rebuild all pages if no dependency info available

Related Modules:
- bengal.cache.dependency_tracker: Tracks data file dependencies
- bengal.orchestration.incremental.change_detector: Main change detector

See Also:
- plan/rfc-incremental-build-dependency-gaps.md: Gap 1 design
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache import BuildCache, CacheCoordinator, DependencyTracker
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.orchestration.build.results import ChangeSummary

logger = get_logger(__name__)

# Supported data file extensions
DATA_FILE_EXTENSIONS = frozenset({".yaml", ".yml", ".json", ".toml"})


class DataFileDetector:
    """
    Detects changes to data files and determines affected pages.
    
    When data files change, this detector finds pages that depend on
    the changed data and marks them for rebuild.
    
    Tracking Strategy:
        Currently uses conservative approach - if any data file changes
        and we don't have dependency tracking, all pages are rebuilt.
        
        When dependency tracking is available (via TrackedData wrapper),
        only pages that accessed the changed data file are rebuilt.
    
    Performance:
        O(d) for data file scanning where d = number of data files
        O(p) for dependency lookup where p = number of pages
    
    Cache Invalidation:
        Uses CacheCoordinator for unified cache invalidation when available
        (RFC: rfc-cache-invalidation-architecture). Falls back to direct
        cache.invalidate_rendered_output() for backward compatibility.
    """

    def __init__(
        self,
        site: Site,
        cache: BuildCache,
        tracker: DependencyTracker,
        coordinator: CacheCoordinator | None = None,
    ) -> None:
        """
        Initialize data file detector.

        Args:
            site: Site instance for data directory access
            cache: BuildCache for change detection
            tracker: DependencyTracker for data file dependencies
            coordinator: Optional CacheCoordinator for unified invalidation
        """
        self.site = site
        self.cache = cache
        self.tracker = tracker
        self.coordinator = coordinator

    def check_data_files(
        self,
        *,
        pages_to_rebuild: set[Path],
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> int:
        """
        Check data files for changes and mark affected pages for rebuild.

        Scans the data/ directory for changed files and uses dependency
        tracking to determine which pages need rebuilding.

        Args:
            pages_to_rebuild: Set to add affected page paths to
            change_summary: ChangeSummary to update with data file changes
            verbose: Whether to log detailed information

        Returns:
            Number of pages added to rebuild set due to data file changes
        """
        data_dir = self.site.root_path / "data"
        if not data_dir.exists():
            return 0

        changed_data_files: list[Path] = []
        pages_added = 0

        # Scan data directory for changed files
        for data_file in data_dir.rglob("*"):
            if not data_file.is_file():
                continue
            if data_file.suffix not in DATA_FILE_EXTENSIONS:
                continue

            if self.cache.is_changed(data_file):
                changed_data_files.append(data_file)
                if verbose:
                    logger.debug(
                        "data_file_changed",
                        data_file=str(data_file.relative_to(self.site.root_path)),
                    )

        if not changed_data_files:
            return 0

        # Log the data file changes
        logger.info(
            "data_files_changed",
            count=len(changed_data_files),
            files=[str(f.relative_to(self.site.root_path)) for f in changed_data_files],
        )

        # Find pages affected by data file changes
        pages_added = self._find_affected_pages(
            changed_data_files, pages_to_rebuild, change_summary, verbose
        )

        # Update change summary
        if not hasattr(change_summary, "extra_changes"):
            change_summary.extra_changes = {}
        change_summary.extra_changes["Data file changes"] = [
            str(f.relative_to(self.site.root_path)) for f in changed_data_files
        ]

        return pages_added

    def _find_affected_pages(
        self,
        changed_data_files: list[Path],
        pages_to_rebuild: set[Path],
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> int:
        """
        Find pages affected by changed data files.

        Uses dependency tracking if available, otherwise falls back
        to conservative approach of rebuilding all pages.

        IMPORTANT: Also clears rendered output cache for affected pages.
        Without this, the cached rendered HTML would be served instead
        of re-rendering with fresh data.

        Cache Invalidation:
            Uses CacheCoordinator for unified invalidation when available
            (RFC: rfc-cache-invalidation-architecture). Falls back to direct
            cache.invalidate_rendered_output() for backward compatibility.

        Args:
            changed_data_files: List of changed data file paths
            pages_to_rebuild: Set to add affected page paths to
            change_summary: ChangeSummary for logging
            verbose: Whether to log detailed information

        Returns:
            Number of pages added to rebuild set
        """
        from bengal.cache.coordinator import PageInvalidationReason

        pages_added = 0
        pages_with_tracked_deps: set[Path] = set()

        # Try to use dependency tracking for precise rebuilds
        for data_file in changed_data_files:
            dependent_pages = self.tracker.get_pages_using_data_file(data_file)
            pages_with_tracked_deps.update(dependent_pages)

        if pages_with_tracked_deps:
            # We have dependency info - rebuild only affected pages
            for page_path in pages_with_tracked_deps:
                if page_path not in pages_to_rebuild:
                    pages_to_rebuild.add(page_path)
                    pages_added += 1
                    if verbose:
                        logger.debug(
                            "page_rebuild_data_dependency",
                            page=str(page_path),
                            reason="data_file_changed",
                        )
                # CRITICAL: Invalidate rendered output cache for this page
                # Otherwise, cached HTML bypasses template re-rendering
                # Use coordinator if available (RFC: rfc-cache-invalidation-architecture)
                if self.coordinator:
                    self.coordinator.invalidate_page(
                        page_path,
                        PageInvalidationReason.DATA_FILE_CHANGED,
                        trigger=str(changed_data_files[0]) if changed_data_files else "",
                    )
                else:
                    self.cache.invalidate_rendered_output(page_path)

            logger.info(
                "data_file_dependency_rebuild",
                affected_pages=pages_added,
                approach="tracked",
            )
        else:
            # No dependency info - conservative approach: rebuild all pages
            # This happens on first build or if TrackedData wrapper isn't used
            #
            # Note: We use a conservative heuristic here. If ANY data file changed
            # and we have no tracking, we rebuild all pages that aren't already
            # being rebuilt.
            #
            # TODO: In future, we could use a smarter heuristic like:
            # - Only rebuild pages with templates that access site.data
            # - Track data file usage at template level
            initial_rebuild_count = len(pages_to_rebuild)

            for page in self.site.pages:
                # Skip generated pages
                if page.metadata.get("_generated"):
                    continue
                if page.source_path not in pages_to_rebuild:
                    pages_to_rebuild.add(page.source_path)
                    pages_added += 1
                # CRITICAL: Invalidate rendered output cache for this page
                # Otherwise, cached HTML bypasses template re-rendering
                # Use coordinator if available (RFC: rfc-cache-invalidation-architecture)
                if self.coordinator:
                    self.coordinator.invalidate_page(
                        page.source_path,
                        PageInvalidationReason.DATA_FILE_CHANGED,
                        trigger=str(changed_data_files[0]) if changed_data_files else "",
                    )
                else:
                    self.cache.invalidate_rendered_output(page.source_path)

            logger.info(
                "data_file_dependency_rebuild",
                affected_pages=pages_added,
                approach="conservative",
                reason="no_dependency_tracking",
            )

        return pages_added

    def update_data_file_fingerprints(self) -> None:
        """
        Update fingerprints for all data files.

        Call this after a successful build to record the current state
        of data files for future change detection.
        """
        data_dir = self.site.root_path / "data"
        if not data_dir.exists():
            return

        updated_count = 0
        for data_file in data_dir.rglob("*"):
            if not data_file.is_file():
                continue
            if data_file.suffix not in DATA_FILE_EXTENSIONS:
                continue

            self.cache.update_file(data_file)
            updated_count += 1

        if updated_count > 0:
            logger.debug(
                "data_file_fingerprints_updated",
                count=updated_count,
            )
