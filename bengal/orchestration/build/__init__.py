"""
Build orchestration for Bengal SSG.

Main coordinator that sequences the entire build pipeline, delegating to
specialized orchestrators for each phase. This is the primary entry point
for building a Bengal site.

Package Structure:
    __init__.py (this file)
        BuildOrchestrator class - main coordinator
    initialization.py
        Phases 1-5: fonts, template validation, discovery, cache, config, filtering
    content.py
        Phases 6-12: sections, taxonomies, taxonomy index, menus, related posts, query indexes, update pages list
    rendering.py
        Phases 13-16: assets, render, update pages, track dependencies
    finalization.py
        Phases 17-21: postprocess, cache save, stats, health, finalize
    options.py
        BuildOptions dataclass for build configuration
    results.py
        Result types for phase outputs

Build Phases:
    The build executes 21 phases in sequence. Key phases include:
    - Phase 2: Content discovery (pages, sections, assets)
    - Phase 6: Section finalization (ensure indexes exist)
    - Phase 7: Taxonomy collection and page generation
    - Phase 9: Menu building
    - Phase 13: Asset processing
    - Phase 14: Page rendering (parallel or sequential)
    - Phase 17: Post-processing (sitemap, RSS, output formats)
    - Phase 20: Health checks and validation

Usage:
    from bengal.orchestration.build import BuildOrchestrator, BuildOptions

    orchestrator = BuildOrchestrator(site)
    stats = orchestrator.build(BuildOptions(parallel=True, incremental=True))

See Also:
    bengal.orchestration: All specialized orchestrators
    bengal.core.site: Site data model
    bengal.cache: Build caching infrastructure
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bengal.core.output import BuildOutputCollector
from bengal.orchestration.asset import AssetOrchestrator
from bengal.orchestration.content import ContentOrchestrator
from bengal.orchestration.menu import MenuOrchestrator
from bengal.orchestration.postprocess import PostprocessOrchestrator
from bengal.orchestration.render import RenderOrchestrator
from bengal.orchestration.section import SectionOrchestrator
from bengal.orchestration.stats import BuildStats
from bengal.orchestration.taxonomy import TaxonomyOrchestrator
from bengal.utils.logger import get_logger

from . import content, finalization, initialization, rendering
from .options import BuildOptions

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.cache.build_cache import BuildCache
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.orchestration.build.results import ConfigCheckResult, FilterResult
    from bengal.output import CLIOutput
    from bengal.utils.build_context import BuildContext
    from bengal.utils.performance_collector import PerformanceCollector
    from bengal.utils.profile import BuildProfile


def __getattr__(name: str) -> Any:
    """
    Lazily expose optional orchestration types without creating import cycles.

    Some tests and callers patch/inspect `bengal.orchestration.build.IncrementalOrchestrator`.
    We keep that surface stable while avoiding eager imports at module import time.
    """
    if name == "IncrementalOrchestrator":
        from bengal.orchestration.incremental import IncrementalOrchestrator

        return IncrementalOrchestrator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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

        # Import via this module's lazy surface to avoid circular imports and to
        # preserve a stable patch/inspection target for tests and callers.
        from bengal.orchestration.build import IncrementalOrchestrator

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
        options: BuildOptions | None = None,
        *,
        parallel: bool = True,
        incremental: bool | None = None,
        verbose: bool = False,
        quiet: bool = False,
        profile: BuildProfile | None = None,
        memory_optimized: bool = False,
        strict: bool = False,
        full_output: bool = False,
        profile_templates: bool = False,
        changed_sources: set[Path] | None = None,
        nav_changed_sources: set[Path] | None = None,
        structural_changed: bool = False,
    ) -> BuildStats:
        """
        Execute full build pipeline.

        Args:
            options: BuildOptions dataclass with all build configuration.
                    If provided, individual parameters are ignored.
            parallel: Whether to use parallel processing
            incremental: Whether to perform incremental build (only changed files)
            verbose: Whether to show verbose console logs during build (default: False, logs go to file)
            quiet: Whether to suppress progress output (minimal output mode)
            profile: Build profile (writer, theme-dev, or dev)
            memory_optimized: Use streaming build for memory efficiency (best for 5K+ pages)
            strict: Whether to fail build on validation errors
            full_output: Show full traditional output instead of live progress
            profile_templates: Enable template profiling for performance analysis
            structural_changed: Whether structural changes occurred (file create/delete/move).
                               Forces full content discovery when True, even in incremental mode.

        Returns:
            BuildStats object with build statistics

        Example:
            >>> from bengal.orchestration.build.options import BuildOptions
            >>> options = BuildOptions(parallel=True, strict=True)
            >>> stats = orchestrator.build(options)
            >>>
            >>> # Or using individual parameters
            >>> stats = orchestrator.build(parallel=True, strict=True)
        """
        # Resolve options: use provided BuildOptions or construct from individual params
        if options is None:
            options = BuildOptions(
                parallel=parallel,
                incremental=incremental,
                verbose=verbose,
                quiet=quiet,
                profile=profile,
                memory_optimized=memory_optimized,
                strict=strict,
                full_output=full_output,
                profile_templates=profile_templates,
                changed_sources=changed_sources or set(),
                nav_changed_sources=nav_changed_sources or set(),
                structural_changed=structural_changed,
            )

        # Extract values from options for use in build phases
        parallel = options.parallel
        incremental = options.incremental
        verbose = options.verbose
        quiet = options.quiet
        profile = options.profile
        memory_optimized = options.memory_optimized
        strict = options.strict
        full_output = options.full_output
        profile_templates = options.profile_templates
        changed_sources = options.changed_sources or None
        nav_changed_sources = options.nav_changed_sources or None
        structural_changed = options.structural_changed
        # Import profile utilities
        from bengal.output import init_cli_output
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

        # Create output collector for hot reload tracking
        output_collector = BuildOutputCollector(self.site.output_dir)

        # Clear directory creation cache to ensure robustness if output was cleaned
        from bengal.rendering.pipeline.thread_local import get_created_dirs

        get_created_dirs().clear()

        # Initialize performance collection only if profile enables it
        collector = None
        if profile_config.get("collect_metrics", False):
            from bengal.utils.performance_collector import PerformanceCollector

            collector = PerformanceCollector(metrics_dir=self.site.paths.metrics_dir)
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

        # Attach a diagnostics collector for core-model events (core must not log).
        # This is intentionally best-effort: if anything goes wrong, we continue
        # without diagnostics rather than impacting builds.
        if not hasattr(self.site, "diagnostics"):
            try:
                from bengal.core.diagnostics import DiagnosticsCollector

                self.site.diagnostics = DiagnosticsCollector()  # type: ignore[attr-defined]
            except Exception:
                pass

        # Show build header
        cli.header("Building your site...")
        mode_label = "incremental" if incremental else "full"
        _auto_reason = locals().get("auto_reason")
        profile_label = profile.value if profile else "writer"

        if _auto_reason:
            cli.detail(
                f"{self.site.root_path} | {mode_label} ({_auto_reason}) | {profile_label}",
                indent=1,
                icon=cli.icons.arrow,
            )
        else:
            cli.detail(
                f"{self.site.root_path} | {mode_label} | {profile_label}",
                indent=1,
                icon=cli.icons.arrow,
            )
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
                cache_path = self.site.paths.build_cache
                cache_exists = cache_path.exists()
                cached_files = len(cache.file_fingerprints)
                if cache_exists and cached_files > 0:
                    incremental = True
                    auto_reason = "auto: cache present"
                else:
                    incremental = False
                    auto_reason = "auto: no cache yet"
            except Exception as e:
                self.logger.debug(
                    "incremental_cache_check_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
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

        # Phase 1.5: Template Validation (optional, controlled by config)
        initialization.phase_template_validation(self, cli, strict=strict)

        # Phase 2: Content Discovery (with content caching for validators)
        # Pass BuildCache for autodoc dependency registration
        initialization.phase_discovery(
            self,
            cli,
            incremental,
            build_context=early_ctx,
            build_cache=cache,
        )

        # Phase 3: Cache Discovery Metadata
        initialization.phase_cache_metadata(self)

        # Phase 4: Config Check and Cleanup
        config_result = initialization.phase_config_check(self, cli, cache, incremental)
        incremental = config_result.incremental
        config_changed = config_result.config_changed

        # Phase 5: Incremental Filtering (determine what to build)
        filter_result = initialization.phase_incremental_filter(
            self,
            cli,
            cache,
            incremental,
            verbose,
            build_start,
            changed_sources=changed_sources,
            nav_changed_sources=nav_changed_sources,
        )
        if filter_result is None:
            # No changes detected - early exit
            return self.stats
        pages_to_build = filter_result.pages_to_build
        assets_to_process = filter_result.assets_to_process
        affected_tags = filter_result.affected_tags
        changed_page_paths = filter_result.changed_page_paths
        affected_sections = filter_result.affected_sections

        # Propagate incremental state into the shared BuildContext so later phases (especially
        # health validators) can make safe incremental decisions without re-scanning everything.
        early_ctx.incremental = bool(incremental)
        early_ctx.changed_page_paths = set(changed_page_paths)

        # Phase 6: Section Finalization
        content.phase_sections(self, cli, incremental, affected_sections)

        # Phase 7: Taxonomies & Dynamic Pages
        affected_tags = content.phase_taxonomies(self, cache, incremental, parallel, pages_to_build)

        # Phase 8: Save Taxonomy Index
        content.phase_taxonomy_index(self)

        # Phase 9: Menus
        content.phase_menus(self, incremental, {str(p) for p in changed_page_paths})

        # Phase 10: Related Posts Index
        content.phase_related_posts(self, incremental, parallel, pages_to_build)

        # Phase 11: Query Indexes
        content.phase_query_indexes(self, cache, incremental, pages_to_build)

        # Phase 12: Update Pages List (add generated taxonomy pages)
        pages_to_build = content.phase_update_pages_list(
            self, incremental, pages_to_build, affected_tags
        )

        # Phase 12.5: URL Collision Detection (proactive validation)
        # See: plan/drafted/rfc-url-collision-detection.md
        collisions = self.site.validate_no_url_collisions(strict=options.strict)
        if collisions:
            for msg in collisions:
                self.logger.warning(msg, event="url_collision_detected")

        # Phase 13: Process Assets
        assets_to_process = rendering.phase_assets(
            self, cli, incremental, parallel, assets_to_process, collector=output_collector
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
            changed_sources=changed_sources,
            collector=output_collector,
        )

        # Phase 15: Update Site Pages (replace proxies with rendered pages)
        rendering.phase_update_site_pages(self, incremental, pages_to_build, cli=cli)

        # Phase 16: Track Asset Dependencies
        rendering.phase_track_assets(self, pages_to_build, cli=cli)

        # Phase 17: Post-processing
        finalization.phase_postprocess(
            self, cli, parallel, ctx, incremental, collector=output_collector
        )

        # Phase 18: Save Cache
        finalization.phase_cache_save(self, pages_to_build, assets_to_process, cli=cli)

        # Phase 19: Collect Final Stats
        finalization.phase_collect_stats(self, build_start, cli=cli)

        # Phase 20: Health Check
        with self.logger.phase("health_check"):
            finalization.run_health_check(self, profile=profile, build_context=ctx)

        # Phase 21: Finalize Build
        finalization.phase_finalize(self, verbose, collector)

        # Populate stats with typed outputs for hot reload
        self.stats.changed_outputs = output_collector.get_outputs()

        return self.stats

    def _print_rendering_summary(self) -> None:
        """Print summary of rendered pages (quiet mode)."""
        from bengal.output import get_cli_output

        cli = get_cli_output()

        # Count page types
        tag_pages = sum(
            1
            for p in self.site.pages
            if p.metadata is not None
            and p.metadata.get("_generated")
            and p.output_path is not None
            and "tag" in p.output_path.parts
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
    # Phase Methods - Wrapper methods that delegate to modular phase functions
    # =========================================================================

    def _phase_fonts(self, cli: CLIOutput) -> None:
        """Phase 1: Font Processing."""
        initialization.phase_fonts(self, cli)

    def _phase_discovery(
        self, cli: CLIOutput, incremental: bool, build_cache: BuildCache | None = None
    ) -> None:
        """Phase 2: Content Discovery."""
        initialization.phase_discovery(self, cli, incremental, build_cache=build_cache)

    def _phase_cache_metadata(self) -> None:
        """Phase 3: Cache Discovery Metadata."""
        initialization.phase_cache_metadata(self)

    def _phase_config_check(
        self, cli: CLIOutput, cache: BuildCache, incremental: bool
    ) -> ConfigCheckResult:
        """Phase 4: Config Check and Cleanup."""
        from bengal.orchestration.build.results import ConfigCheckResult

        return initialization.phase_config_check(self, cli, cache, incremental)

    def _phase_incremental_filter(
        self,
        cli: CLIOutput,
        cache: BuildCache,
        incremental: bool,
        verbose: bool,
        build_start: float,
    ) -> FilterResult:
        """Phase 5: Incremental Filtering."""
        from bengal.orchestration.build.results import FilterResult

        return initialization.phase_incremental_filter(
            self, cli, cache, incremental, verbose, build_start
        )

    def _phase_sections(
        self, cli: CLIOutput, incremental: bool, affected_sections: set[str] | None
    ) -> None:
        """Phase 6: Section Finalization."""
        content.phase_sections(self, cli, incremental, affected_sections)

    def _phase_taxonomies(
        self,
        cache: BuildCache,
        incremental: bool,
        parallel: bool,
        pages_to_build: list[Page],
    ) -> set[str]:
        """Phase 7: Taxonomies & Dynamic Pages."""
        return content.phase_taxonomies(self, cache, incremental, parallel, pages_to_build)

    def _phase_taxonomy_index(self) -> None:
        """Phase 8: Save Taxonomy Index."""
        content.phase_taxonomy_index(self)

    def _phase_menus(self, incremental: bool, changed_page_paths: set[Path]) -> None:
        """Phase 9: Menu Building."""
        content.phase_menus(self, incremental, {str(p) for p in changed_page_paths})

    def _phase_related_posts(
        self, incremental: bool, parallel: bool, pages_to_build: list[Page]
    ) -> None:
        """Phase 10: Related Posts Index."""
        content.phase_related_posts(self, incremental, parallel, pages_to_build)

    def _phase_query_indexes(
        self, cache: BuildCache, incremental: bool, pages_to_build: list[Page]
    ) -> None:
        """Phase 11: Query Indexes."""
        content.phase_query_indexes(self, cache, incremental, pages_to_build)

    def _phase_update_pages_list(
        self, incremental: bool, pages_to_build: list[Page], affected_tags: set[str]
    ) -> list[Page]:
        """Phase 12: Update Pages List."""
        return content.phase_update_pages_list(self, incremental, pages_to_build, affected_tags)

    def _phase_assets(
        self,
        cli: CLIOutput,
        incremental: bool,
        parallel: bool,
        assets_to_process: list[Any],
    ) -> list[Any]:
        """Phase 13: Process Assets."""
        return rendering.phase_assets(self, cli, incremental, parallel, assets_to_process)

    def _phase_render(
        self,
        cli: CLIOutput,
        incremental: bool,
        parallel: bool,
        quiet: bool,
        verbose: bool,
        memory_optimized: bool,
        pages_to_build: list[Page],
        tracker: Any,
        profile: BuildProfile | None,
        progress_manager: Any | None,
        reporter: Any | None,
    ) -> None:
        """Phase 14: Render Pages."""
        rendering.phase_render(
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

    def _phase_update_site_pages(self, incremental: bool, pages_to_build: list[Page]) -> None:
        """Phase 15: Update Site Pages."""
        rendering.phase_update_site_pages(self, incremental, pages_to_build)

    def _phase_track_assets(self, pages_to_build: list[Page]) -> None:
        """Phase 16: Track Asset Dependencies."""
        rendering.phase_track_assets(self, pages_to_build)

    def _phase_postprocess(
        self,
        cli: CLIOutput,
        parallel: bool,
        ctx: BuildContext | Any | None,
        incremental: bool,
    ) -> None:
        """Phase 17: Post-processing."""
        finalization.phase_postprocess(self, cli, parallel, ctx, incremental)

    def _phase_cache_save(self, pages_to_build: list[Page], assets_to_process: list[Any]) -> None:
        """Phase 18: Save Cache."""
        finalization.phase_cache_save(self, pages_to_build, assets_to_process)

    def _phase_collect_stats(self, build_start: float) -> None:
        """Phase 19: Collect Final Stats."""
        finalization.phase_collect_stats(self, build_start)

    def _run_health_check(
        self,
        profile: BuildProfile | None = None,
        incremental: bool = False,
        build_context: BuildContext | Any | None = None,
    ) -> None:
        """Run health check system with profile-based filtering."""
        finalization.run_health_check(
            self, profile=profile, incremental=incremental, build_context=build_context
        )

    def _phase_finalize(self, verbose: bool, collector: PerformanceCollector | None) -> None:
        """Phase 21: Finalize Build."""
        finalization.phase_finalize(self, verbose, collector)
