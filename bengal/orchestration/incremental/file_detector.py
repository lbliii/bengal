"""
File-level change detection for pages and assets.

Handles checking individual pages and assets for changes, with support
for parallel processing on large workloads.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger
from bengal.utils.workers import WorkloadType, get_optimal_workers, should_parallelize

if TYPE_CHECKING:
    from bengal.cache import BuildCache, DependencyTracker
    from bengal.core.asset import Asset
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site
    from bengal.orchestration.build.results import ChangeSummary

logger = get_logger(__name__)

# Note: PARALLEL_THRESHOLD and DEFAULT_MAX_WORKERS are deprecated
# in favor of should_parallelize() and get_optimal_workers()
# Kept for backwards compatibility if accessed directly
PARALLEL_THRESHOLD = 50
DEFAULT_MAX_WORKERS = min(8, (os.cpu_count() or 4))


class FileChangeDetector:
    """
    Detects changes in content files (pages and assets).

    Uses parallel processing for large workloads (workload-aware threshold).
    For smaller sets, sequential is faster due to thread overhead.

    Performance:
        - Sequential: O(n) × stat call latency
        - Parallel: O(n/workers) × stat call latency + thread overhead
        - Break-even: ~50 files on typical SSD
    """

    def __init__(
        self,
        site: Site,
        cache: BuildCache,
        tracker: DependencyTracker,
    ) -> None:
        """
        Initialize file change detector.

        Args:
            site: Site instance for configuration
            cache: BuildCache for change detection
            tracker: DependencyTracker for taxonomy tracking
        """
        self.site = site
        self.cache = cache
        self.tracker = tracker

    def _get_max_workers(self) -> int | None:
        """Get max_workers from config, supporting both Config and dict."""
        config = self.site.config
        if hasattr(config, "build"):
            return config.build.max_workers
        build_section = config.get("build", {})
        if isinstance(build_section, dict):
            return build_section.get("max_workers")
        return config.get("max_workers")

    def check_pages(
        self,
        *,
        pages_to_check: list[Page],
        changed_sections: set[Section] | None,
        all_changed: set[Path],
        pages_to_rebuild: set[Path],
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> None:
        """Check pages for changes.

        Uses parallel processing for large page sets (workload-aware threshold).
        For smaller sets, sequential is faster due to thread overhead.
        """
        # Filter pages first (cheap in-memory operations)
        pages_to_scan: list[Page] = []
        for page in pages_to_check:
            if page.metadata.get("_generated"):
                continue
            # Skip if page is in an unchanged section
            if (
                changed_sections is not None
                and hasattr(page, "_section")
                and page._section
                and page._section not in changed_sections
            ):
                continue
            pages_to_scan.append(page)

        if not pages_to_scan:
            return

        # Choose sequential or parallel based on workload size
        # File change detection is I/O-bound (stat calls)
        if not should_parallelize(len(pages_to_scan), workload_type=WorkloadType.IO_BOUND):
            self._check_pages_sequential(
                pages_to_scan, all_changed, pages_to_rebuild, change_summary, verbose
            )
        else:
            self._check_pages_parallel(
                pages_to_scan, all_changed, pages_to_rebuild, change_summary, verbose
            )

    def _check_pages_sequential(
        self,
        pages: list[Page],
        all_changed: set[Path],
        pages_to_rebuild: set[Path],
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> None:
        """Sequential page checking for small workloads."""
        for page in pages:
            if self.cache.should_bypass(page.source_path, all_changed):
                pages_to_rebuild.add(page.source_path)
                if verbose:
                    change_summary.modified_content.append(page.source_path)
                if page.tags:
                    self.tracker.track_taxonomy(page.source_path, set(page.tags))

    def _check_pages_parallel(
        self,
        pages: list[Page],
        all_changed: set[Path],
        pages_to_rebuild: set[Path],
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> None:
        """Parallel page checking for large workloads.

        Thread-safe: Uses lock for result collection.
        """
        max_workers = get_optimal_workers(
            len(pages),
            workload_type=WorkloadType.IO_BOUND,
            config_override=self._get_max_workers(),
        )
        results_lock = Lock()

        def check_single_page(page: Page) -> tuple[Path, bool, list[str] | None]:
            """Check a single page (thread-safe, no shared state mutation)."""
            changed = self.cache.should_bypass(page.source_path, all_changed)
            tags = list(page.tags) if changed and page.tags else None
            return (page.source_path, changed, tags)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(check_single_page, p): p for p in pages}

            for future in as_completed(futures):
                try:
                    source_path, changed, tags = future.result()
                    if changed:
                        with results_lock:
                            pages_to_rebuild.add(source_path)
                            if verbose:
                                change_summary.modified_content.append(source_path)
                        if tags:
                            self.tracker.track_taxonomy(source_path, set(tags))
                except Exception as e:
                    page = futures[future]
                    logger.warning(
                        "page_change_check_failed",
                        page=str(page.source_path),
                        error=str(e),
                    )

    def check_assets(
        self,
        *,
        forced_changed: set[Path],
        assets_to_process: list[Asset],
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> None:
        """Check assets for changes.

        Uses parallel processing for large asset sets (workload-aware threshold).
        """
        assets = self.site.assets
        if not assets:
            return

        # Asset change detection is I/O-bound (stat calls)
        if not should_parallelize(len(assets), workload_type=WorkloadType.IO_BOUND):
            # Sequential for small workloads
            for asset in assets:
                if self.cache.should_bypass(asset.source_path, forced_changed):
                    assets_to_process.append(asset)
                    if verbose:
                        change_summary.modified_assets.append(asset.source_path)
        else:
            # Parallel for large workloads
            self._check_assets_parallel(
                assets, forced_changed, assets_to_process, change_summary, verbose
            )

    def _check_assets_parallel(
        self,
        assets: list[Asset],
        forced_changed: set[Path],
        assets_to_process: list[Asset],
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> None:
        """Parallel asset checking for large workloads."""
        max_workers = get_optimal_workers(
            len(self.site.assets),
            workload_type=WorkloadType.IO_BOUND,
            config_override=self._get_max_workers(),
        )
        results_lock = Lock()

        def check_single_asset(asset: Asset) -> tuple[Asset, bool]:
            """Check a single asset (thread-safe)."""
            changed = self.cache.should_bypass(asset.source_path, forced_changed)
            return (asset, changed)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(check_single_asset, a): a for a in assets}

            for future in as_completed(futures):
                try:
                    asset, changed = future.result()
                    if changed:
                        with results_lock:
                            assets_to_process.append(asset)
                            if verbose:
                                change_summary.modified_assets.append(asset.source_path)
                except Exception as e:
                    asset = futures[future]
                    logger.warning(
                        "asset_change_check_failed",
                        asset=str(asset.source_path),
                        error=str(e),
                    )
