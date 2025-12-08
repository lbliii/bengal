"""
Build orchestration for Bengal SSG.

Main coordinator that delegates build phases to specialized orchestrators.

This module has been modularized into a package structure:
- initialization.py: Phases 1-5 (fonts, discovery, cache, config, filtering)
- content.py: Phases 6-11 (sections, taxonomies, menus, indexes)
- rendering.py: Phases 13-16 (assets, render, update pages, track assets)
- finalization.py: Phases 17-21 (postprocess, cache save, stats, health, finalize)
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import TYPE_CHECKING

from bengal.orchestration.asset import AssetOrchestrator
from bengal.orchestration.content import ContentOrchestrator
from bengal.orchestration.incremental import IncrementalOrchestrator
from bengal.orchestration.menu import MenuOrchestrator
from bengal.orchestration.postprocess import PostprocessOrchestrator
from bengal.orchestration.render import RenderOrchestrator
from bengal.orchestration.section import SectionOrchestrator
from bengal.orchestration.taxonomy import TaxonomyOrchestrator
from bengal.utils.build_stats import BuildStats
from bengal.utils.logger import get_logger

from . import content, finalization, initialization, rendering

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.profile import BuildProfile


class BuildOrchestrator:
    """
    Main build coordinator that orchestrates the entire build process.

    Delegates to specialized orchestrators for each phase:
        - ContentOrchestrator: Discovery and setup
        - TaxonomyOrchestrator: Taxonomies and dynamic pages
        - MenuOrchestrator: Navigation menus
        - RenderOrchestrator: Page rendering
        - AssetOrchestrator: Asset processing
        - PostprocessOrchestrator: Sitemap, RSS, validation
        - IncrementalOrchestrator: Change detection and caching
    """

    def __init__(self, site: Site):
        """
        Initialize build orchestrator.

        Args:
            site: Site instance to build
        """
        self.site = site
        self.stats = BuildStats()
        self.logger = get_logger(__name__)

        # Initialize orchestrators
        self.content = ContentOrchestrator(site)
        self.sections = SectionOrchestrator(site)
        self.taxonomy = TaxonomyOrchestrator(site)
        self.menu = MenuOrchestrator(site)
        self.render = RenderOrchestrator(site)
        self.assets = AssetOrchestrator(site)
        self.postprocess = PostprocessOrchestrator(site)
        self.incremental = IncrementalOrchestrator(site)

    def build(
        self,
        parallel: bool = True,
        incremental: bool | None = None,
        verbose: bool = False,
        quiet: bool = False,
        profile: BuildProfile = None,
        memory_optimized: bool = False,
        strict: bool = False,
        full_output: bool = False,
        profile_templates: bool = False,
    ) -> BuildStats:
        """
        Execute full build pipeline.

        Args:
            parallel: Whether to use parallel processing
            incremental: Whether to perform incremental build (only changed files)
            verbose: Whether to show verbose console logs during build (default: False, logs go to file)
            quiet: Whether to suppress progress output (minimal output mode)
            profile: Build profile (writer, theme-dev, or dev)
            memory_optimized: Use streaming build for memory efficiency (best for 5K+ pages)
            strict: Whether to fail build on validation errors
            full_output: Show full traditional output instead of live progress
            profile_templates: Enable template profiling for performance analysis

        Returns:
            BuildStats object with build statistics
        """
        # Import profile utilities
        from bengal.utils.cli_output import init_cli_output
        from bengal.utils.profile import BuildProfile

        # Use default profile if not provided
        if profile is None:
            profile = BuildProfile.WRITER

        # Set global profile for helper functions (used by is_validator_enabled)
        from bengal.utils.profile import set_current_profile

        set_current_profile(profile)

        # Get profile configuration
        profile_config = profile.get_config()

        # Initialize CLI output system with profile
        cli = init_cli_output(profile=profile, quiet=quiet, verbose=verbose)

        # Simple phase completion messages (no live progress bar)
        # Live progress bar was removed due to UX issues (felt stuck) and performance overhead
        use_live_progress = False
        progress_manager = None
        reporter = None

        # Suppress console log noise (logs still go to file for debugging)
        from bengal.utils.logger import set_console_quiet

        if not verbose:  # Only suppress console logs if not in verbose logging mode
            set_console_quiet(True)

        # Start timing
        build_start = time.time()

        # Initialize performance collection only if profile enables it
        collector = None
        if profile_config.get("collect_metrics", False):
            from bengal.utils.performance_collector import PerformanceCollector

            collector = PerformanceCollector()
            collector.start_build()

        # Initialize stats (incremental may be None, resolve later)
        self.stats = BuildStats(parallel=parallel, incremental=bool(incremental))
        self.stats.strict_mode = strict

        self.logger.info(
            "build_start",
            parallel=parallel,
            incremental=incremental,
            root_path=str(self.site.root_path),
        )

        # Show build header
        cli.header("Building your site...")
        cli.info(f"   ↪ {self.site.root_path}")
        mode_label = "incremental" if incremental else "full"
        _auto_reason = locals().get("auto_reason")
        if _auto_reason:
            cli.detail(f"Mode: {mode_label} ({_auto_reason})", indent=1)
        else:
            cli.detail(f"Mode: {mode_label} (flag)", indent=1)
        # Show active profile
        profile_label = profile.value if profile else "writer"
        cli.detail(f"Profile: {profile_label}", indent=1)
        cli.blank()

        self.site.build_time = datetime.now()

        # Initialize cache and tracker (ALWAYS, even for full builds)
        # We need cache for cleanup of deleted files and auto-mode decision
        with self.logger.phase("initialization"):
            cache, tracker = self.incremental.initialize(enabled=True)  # Always load cache

        # Resolve incremental mode (auto when None)
        auto_reason = None
        if incremental is None:
            try:
                cache_dir = self.site.root_path / ".bengal"
                cache_path = cache_dir / "cache.json"
                cache_exists = cache_path.exists()
                cached_files = len(getattr(cache, "file_hashes", {}) or {})
                if cache_exists and cached_files > 0:
                    incremental = True
                    auto_reason = "auto: cache present"
                else:
                    incremental = False
                    auto_reason = "auto: no cache yet"
            except Exception:
                incremental = False
                auto_reason = "auto: cache check failed"

        # Record resolved mode in stats
        self.stats.incremental = bool(incremental)

        # Create BuildContext early for content caching during discovery
        # This enables build-integrated validation: validators use cached content
        # instead of re-reading from disk, saving ~4 seconds on health checks.
        from bengal.utils.build_context import BuildContext

        early_ctx = BuildContext(
            site=self.site,
            stats=self.stats,
        )

        # Phase 1: Font Processing
        initialization.phase_fonts(self, cli)

        # Phase 2: Content Discovery (with content caching for validators)
        initialization.phase_discovery(self, cli, incremental, build_context=early_ctx)

        # Phase 3: Cache Discovery Metadata
        initialization.phase_cache_metadata(self)

        # Phase 4: Config Check and Cleanup
        config_result = initialization.phase_config_check(self, cli, cache, incremental)
        incremental = config_result.incremental
        config_changed = config_result.config_changed

        # Phase 5: Incremental Filtering (determine what to build)
        filter_result = initialization.phase_incremental_filter(
            self, cli, cache, incremental, verbose, build_start
        )
        if filter_result is None:
            # No changes detected - early exit
            return self.stats
        pages_to_build = filter_result.pages_to_build
        assets_to_process = filter_result.assets_to_process
        affected_tags = filter_result.affected_tags
        changed_page_paths = filter_result.changed_page_paths
        affected_sections = filter_result.affected_sections

        # Phase 6: Section Finalization
        content.phase_sections(self, cli, incremental, affected_sections)

        # Phase 7: Taxonomies & Dynamic Pages
        affected_tags = content.phase_taxonomies(self, cache, incremental, parallel, pages_to_build)

        # Phase 8: Save Taxonomy Index
        content.phase_taxonomy_index(self)

        # Phase 9: Menus
        content.phase_menus(self, incremental, changed_page_paths)

        # Phase 10: Related Posts Index
        content.phase_related_posts(self, incremental, parallel, pages_to_build)

        # Phase 11: Query Indexes
        content.phase_query_indexes(self, cache, incremental, pages_to_build)

        # Phase 12: Update Pages List (add generated taxonomy pages)
        pages_to_build = content.phase_update_pages_list(
            self, incremental, pages_to_build, affected_tags
        )

        # Phase 13: Process Assets
        assets_to_process = rendering.phase_assets(
            self, cli, incremental, parallel, assets_to_process
        )

        # Phase 14: Render Pages (with cached content from discovery)
        ctx = rendering.phase_render(
            self,
            cli,
            incremental,
            parallel,
            quiet,
            verbose,
            memory_optimized,
            pages_to_build,
            tracker,
            profile,
            progress_manager,
            reporter,
            profile_templates=profile_templates,
            early_context=early_ctx,
        )

        # Phase 15: Update Site Pages (replace proxies with rendered pages)
        rendering.phase_update_site_pages(self, incremental, pages_to_build)

        # Phase 16: Track Asset Dependencies
        rendering.phase_track_assets(self, pages_to_build)

        # Phase 17: Post-processing
        finalization.phase_postprocess(self, cli, parallel, ctx, incremental)

        # Phase 18: Save Cache
        finalization.phase_cache_save(self, pages_to_build, assets_to_process)

        # Phase 19: Collect Final Stats
        finalization.phase_collect_stats(self, build_start)

        # Phase 20: Health Check
        with self.logger.phase("health_check"):
            finalization.run_health_check(self, profile=profile, build_context=ctx)

        # Phase 21: Finalize Build
        finalization.phase_finalize(self, verbose, collector)

        return self.stats

    def _print_rendering_summary(self) -> None:
        """Print summary of rendered pages (quiet mode)."""
        from bengal.utils.cli_output import get_cli_output

        cli = get_cli_output()

        # Count page types
        tag_pages = sum(
            1
            for p in self.site.pages
            if p.metadata.get("_generated") and "tag" in p.output_path.parts
        )
        archive_pages = sum(
            1
            for p in self.site.pages
            if p.metadata.get("_generated") and p.metadata.get("template") == "archive.html"
        )
        pagination_pages = sum(
            1
            for p in self.site.pages
            if p.metadata.get("_generated") and "/page/" in str(p.output_path)
        )
        regular_pages = len(self.site.regular_pages)

        cli.detail(f"Regular pages:    {regular_pages}", indent=1, icon="├─")
        if tag_pages:
            cli.detail(f"Tag pages:        {tag_pages}", indent=1, icon="├─")
        if archive_pages:
            cli.detail(f"Archive pages:    {archive_pages}", indent=1, icon="├─")
        if pagination_pages:
            cli.detail(f"Pagination:       {pagination_pages}", indent=1, icon="├─")
        cli.detail(f"Total:            {len(self.site.pages)} ✓", indent=1, icon="└─")

    # =========================================================================
    # Phase Methods - Wrapper methods for backward compatibility
    # These delegate to the modular phase functions
    # =========================================================================

    def _phase_fonts(self, cli) -> None:
        """Phase 1: Font Processing."""
        initialization.phase_fonts(self, cli)

    def _phase_discovery(self, cli, incremental: bool) -> None:
        """Phase 2: Content Discovery."""
        initialization.phase_discovery(self, cli, incremental)

    def _phase_cache_metadata(self) -> None:
        """Phase 3: Cache Discovery Metadata."""
        initialization.phase_cache_metadata(self)

    def _phase_config_check(self, cli, cache, incremental: bool) -> tuple[bool, bool]:
        """Phase 4: Config Check and Cleanup."""
        return initialization.phase_config_check(self, cli, cache, incremental)

    def _phase_incremental_filter(
        self, cli, cache, incremental: bool, verbose: bool, build_start: float
    ) -> tuple[list, list, set, set, set | None] | None:
        """Phase 5: Incremental Filtering."""
        return initialization.phase_incremental_filter(
            self, cli, cache, incremental, verbose, build_start
        )

    def _phase_sections(self, cli, incremental: bool, affected_sections: set | None) -> None:
        """Phase 6: Section Finalization."""
        content.phase_sections(self, cli, incremental, affected_sections)

    def _phase_taxonomies(
        self, cache, incremental: bool, parallel: bool, pages_to_build: list
    ) -> set:
        """Phase 7: Taxonomies & Dynamic Pages."""
        return content.phase_taxonomies(self, cache, incremental, parallel, pages_to_build)

    def _phase_taxonomy_index(self) -> None:
        """Phase 8: Save Taxonomy Index."""
        content.phase_taxonomy_index(self)

    def _phase_menus(self, incremental: bool, changed_page_paths: set) -> None:
        """Phase 9: Menu Building."""
        content.phase_menus(self, incremental, changed_page_paths)

    def _phase_related_posts(self, incremental: bool, parallel: bool, pages_to_build: list) -> None:
        """Phase 10: Related Posts Index."""
        content.phase_related_posts(self, incremental, parallel, pages_to_build)

    def _phase_query_indexes(self, cache, incremental: bool, pages_to_build: list) -> None:
        """Phase 11: Query Indexes."""
        content.phase_query_indexes(self, cache, incremental, pages_to_build)

    def _phase_update_pages_list(
        self, incremental: bool, pages_to_build: list, affected_tags: set
    ) -> list:
        """Phase 12: Update Pages List."""
        return content.phase_update_pages_list(self, incremental, pages_to_build, affected_tags)

    def _phase_assets(
        self, cli, incremental: bool, parallel: bool, assets_to_process: list
    ) -> list:
        """Phase 13: Process Assets."""
        return rendering.phase_assets(self, cli, incremental, parallel, assets_to_process)

    def _phase_render(
        self,
        cli,
        incremental: bool,
        parallel: bool,
        quiet: bool,
        verbose: bool,
        memory_optimized: bool,
        pages_to_build: list,
        tracker,
        profile,
        progress_manager,
        reporter,
    ):
        """Phase 14: Render Pages."""
        return rendering.phase_render(
            self,
            cli,
            incremental,
            parallel,
            quiet,
            verbose,
            memory_optimized,
            pages_to_build,
            tracker,
            profile,
            progress_manager,
            reporter,
        )

    def _phase_update_site_pages(self, incremental: bool, pages_to_build: list) -> None:
        """Phase 15: Update Site Pages."""
        rendering.phase_update_site_pages(self, incremental, pages_to_build)

    def _phase_track_assets(self, pages_to_build: list) -> None:
        """Phase 16: Track Asset Dependencies."""
        rendering.phase_track_assets(self, pages_to_build)

    def _phase_postprocess(self, cli, parallel: bool, ctx, incremental: bool) -> None:
        """Phase 17: Post-processing."""
        finalization.phase_postprocess(self, cli, parallel, ctx, incremental)

    def _phase_cache_save(self, pages_to_build: list, assets_to_process: list) -> None:
        """Phase 18: Save Cache."""
        finalization.phase_cache_save(self, pages_to_build, assets_to_process)

    def _phase_collect_stats(self, build_start: float) -> None:
        """Phase 19: Collect Final Stats."""
        finalization.phase_collect_stats(self, build_start)

    def _run_health_check(
        self, profile: BuildProfile = None, incremental: bool = False, build_context=None
    ) -> None:
        """Run health check system with profile-based filtering."""
        finalization.run_health_check(
            self, profile=profile, incremental=incremental, build_context=build_context
        )

    def _phase_finalize(self, verbose: bool, collector) -> None:
        """Phase 21: Finalize Build."""
        finalization.phase_finalize(self, verbose, collector)
