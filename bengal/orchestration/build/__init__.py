"""
Build orchestration for Bengal SSG.

Main coordinator that sequences the entire build pipeline, delegating to
specialized orchestrators for each phase. This is the primary entry point
for building a Bengal site.

Package Structure:
__init__.py (this file)
    BuildOrchestrator class - main coordinator
initialization.py
    Phases 1-5: fonts, discovery, cache, config, filtering
content.py
    Phases 6-11: sections, taxonomies, menus, related posts, indexes
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
    stats = orchestrator.build(BuildOptions(incremental=True))

See Also:
bengal.orchestration: All specialized orchestrators
bengal.core.site: Site data model
bengal.cache: Build caching infrastructure

"""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bengal.core.output import BuildOutputCollector
from bengal.orchestration.asset import AssetOrchestrator
from bengal.orchestration.build_state import BuildState
from bengal.orchestration.content import ContentOrchestrator
from bengal.orchestration.menu import MenuOrchestrator
from bengal.orchestration.postprocess import PostprocessOrchestrator
from bengal.orchestration.render import RenderOrchestrator
from bengal.orchestration.section import SectionOrchestrator
from bengal.orchestration.stats import BuildStats
from bengal.orchestration.taxonomy import TaxonomyOrchestrator
from bengal.protocols.capabilities import HasErrors
from bengal.utils.observability.logger import get_logger

from . import content, finalization, initialization, parsing, rendering, snapshot
from .inputs import BuildInput
from .options import BuildOptions

logger = get_logger(__name__)

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.cache.build_cache import BuildCache
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.orchestration.build_context import BuildContext
    from bengal.output import CLIOutput
    from bengal.utils.observability.performance_collector import PerformanceCollector
    from bengal.utils.observability.profile import BuildProfile


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
        self.options: BuildOptions | None = None  # Set during build() call

        # Import directly to avoid self-import through __getattr__
        from bengal.orchestration.incremental import IncrementalOrchestrator

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
        options: BuildOptions | BuildInput,
    ) -> BuildStats:
        """
        Execute full build pipeline.

        Args:
            options: BuildOptions or BuildInput with all build configuration.
                BuildInput provides a complete serializable record for debugging.

        Returns:
            BuildStats object with build statistics

        Example:
            >>> from bengal.orchestration.build.options import BuildOptions
            >>> options = BuildOptions(strict=True)
            >>> stats = orchestrator.build(options)
        """
        # Normalize to BuildInput for consistent input handling
        if isinstance(options, BuildInput):
            build_input = options
            options = build_input.options
        else:
            build_input = BuildInput.from_options(options, self.site.root_path)

        # Store for use in build phases (e.g., max_workers for WaveScheduler)
        self.options = options
        self.current_input: BuildInput = build_input

        # Per-phase parallelism: fan-out phases stay parallel, content
        # phases go sequential under dev server (3.14t ThreadPoolExecutor hang).
        parallel = options.phase_parallel()
        force_sequential = options.force_sequential
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

        # Explain mode options (RFC: rfc-incremental-build-observability Phase 2)
        explain = options.explain
        dry_run = options.dry_run

        # Extract phase callbacks
        on_phase_start = options.on_phase_start
        on_phase_complete = options.on_phase_complete

        # Helper to safely call phase callbacks
        def notify_phase_start(phase_name: str) -> None:
            """Notify dashboard that a phase is starting."""
            if on_phase_start is not None:
                try:
                    on_phase_start(phase_name)
                except Exception as e:
                    logger.debug("phase_callback_error", phase=phase_name, error=str(e))

        def notify_phase_complete(phase_name: str, duration_ms: float, details: str = "") -> None:
            """Notify dashboard that a phase completed."""
            if on_phase_complete is not None:
                try:
                    on_phase_complete(phase_name, duration_ms, details)
                except Exception as e:
                    logger.debug("phase_callback_error", phase=phase_name, error=str(e))

        # Import profile utilities
        from bengal.output import init_cli_output
        from bengal.utils.observability.profile import BuildProfile

        # Use default profile if not provided
        if profile is None:
            profile = BuildProfile.WRITER

        # Set global profile for helper functions (used by is_validator_enabled)
        from bengal.utils.observability.profile import set_current_profile

        set_current_profile(profile)

        # Get profile configuration
        profile_config = profile.get_config()

        # Initialize CLI output system with profile
        cli = init_cli_output(profile=profile, quiet=quiet, verbose=verbose)

        # Live progress bar for rendering phase
        # Re-enabled with improved throttled updates in WaveScheduler (RFC: rfc-bengal-snapshot-engine)
        # Shows real-time progress during the rendering phase which can take 10+ seconds
        from bengal.utils.observability.cli_progress import LiveProgressManager
        from bengal.utils.observability.rich_console import should_use_rich

        use_live_progress = should_use_rich() and not quiet
        progress_manager = None
        reporter = None

        if use_live_progress:
            progress_manager = LiveProgressManager(profile=profile, enabled=True)

        # Suppress console log noise (logs still go to file for debugging)
        from bengal.utils.observability.logger import set_console_quiet

        if not verbose:  # Only suppress console logs if not in verbose logging mode
            set_console_quiet(True)

        # Start timing
        build_start = time.time()

        # RFC: rfc-cache-generation-id — shared ID for BuildCache and ProvenanceCache
        self._build_id = str(uuid.uuid4())

        # Clear directory creation cache to ensure robustness if output was cleaned
        from bengal.rendering.pipeline.thread_local import get_created_dirs

        get_created_dirs().clear()

        # Initialize performance collection only if profile enables it
        collector = None
        if profile_config.get("collect_metrics", False):
            from bengal.utils.observability.performance_collector import PerformanceCollector

            # Only enable tracemalloc if profile explicitly requests memory tracking
            # tracemalloc has ~2-5x overhead alone, ~100x with cProfile
            track_memory = profile_config.get("track_memory", False)
            collector = PerformanceCollector(
                metrics_dir=self.site.paths.metrics_dir,
                track_memory=track_memory,
            )
            collector.start_build()

        # Initialize stats (incremental may be None, resolve later)
        self.stats = BuildStats(parallel=False, incremental=bool(incremental))
        self.stats.strict_mode = strict

        logger.info(
            "build_start",
            force_sequential=force_sequential,
            incremental=incremental,
            root_path=str(self.site.root_path),
        )

        # Attach a diagnostics collector for core-model events (core must not log).
        # Only set when none exists to preserve custom sinks or re-entry diagnostics.
        if getattr(self.site, "diagnostics", None) is None:
            from bengal.core.diagnostics import DiagnosticsCollector

            self.site.diagnostics = DiagnosticsCollector()

        # Show build header with version
        from bengal import __version__

        cli.header(f"Building your site... (Bengal v{__version__})")
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

        # Create fresh BuildState for this build
        build_state = BuildState(
            build_time=self.site.build_time,
            incremental=bool(incremental),
            dev_mode=self.site.dev_mode,
        )
        self.site.set_build_state(build_state)

        # Initialize cache (ALWAYS, even for full builds)
        # We need cache for cleanup of deleted files and auto-mode decision
        with logger.phase("initialization"):
            cache = self.incremental.initialize(enabled=True)  # Always load cache

        # RFC: Output Cache Architecture - Initialize GeneratedPageCache for tag page caching
        # This enables skipping unchanged tag pages based on member content hashes
        from bengal.cache.generated_page_cache import GeneratedPageCache

        generated_page_cache = GeneratedPageCache(
            self.site.paths.state_dir / "generated_page_cache.json"
        )
        # Note: GeneratedPageCache loads automatically in __init__

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
                logger.debug(
                    "incremental_cache_check_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                incremental = False
                auto_reason = "auto: cache check failed"

        # Record resolved mode in stats
        self.stats.incremental = bool(incremental)

        # Store options and cache on BuildState for phase-level optimizations
        self.site.build_state.last_build_options = options
        self.site.build_state.cache = self.incremental.cache
        self._last_build_options = options

        # Create BuildContext early for content caching during discovery
        # This enables build-integrated validation: validators use cached content
        # instead of re-reading from disk, saving ~4 seconds on health checks.
        from bengal.orchestration.build_context import BuildContext

        early_ctx = BuildContext(
            site=self.site,
            stats=self.stats,
        )

        # Create output collector for hot reload tracking
        # This collector tracks all written files (HTML, CSS, assets) for typed reload decisions.
        output_collector = BuildOutputCollector(output_dir=self.site.output_dir)

        # Phase 1: Font Processing
        initialization.phase_fonts(self, cli, collector=output_collector)

        # Phase 1.5: Template Validation (optional, controlled by config)
        initialization.phase_template_validation(self, cli, strict=strict)

        # === DISCOVERY PHASE GROUP (dashboard-integrated) ===
        notify_phase_start("discovery")
        discovery_start = time.time()

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

        discovery_duration_ms = (time.time() - discovery_start) * 1000

        notify_phase_complete(
            "discovery",
            discovery_duration_ms,
            f"{len(self.site.pages)} pages, {len(self.site.sections)} sections",
        )

        # Phase 4: Config Check and Cleanup
        config_result = initialization.phase_config_check(self, cli, cache, incremental)
        incremental = config_result.incremental
        config_changed = config_result.config_changed

        # Phase 5: Incremental Filtering (determine what to build)
        # Always use provenance-based filtering (replaces old IncrementalFilterEngine)
        from bengal.orchestration.build.provenance_orchestration import (
            phase_incremental_filter_provenance,
        )

        filter_result = phase_incremental_filter_provenance(
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

        # === CONTENT PHASE GROUP (dashboard-integrated) ===
        notify_phase_start("content")
        content_start = time.time()
        cli.detail("Content phase (taxonomies, menus, related posts)...", indent=1)

        # Memory diagnostics: BENGAL_DEBUG_MEMORY=1 runs GC before content phase and
        # enables tracemalloc to help diagnose leaks that can cause content phase hangs.
        if os.environ.get("BENGAL_DEBUG_MEMORY"):
            import gc

            gc.collect()
            if not getattr(self, "_tracemalloc_started", False):
                try:
                    import tracemalloc

                    tracemalloc.start()
                    self._tracemalloc_started = True
                except Exception:
                    pass

        # Phase 6: Section Finalization
        content.phase_sections(self, cli, incremental, affected_sections)

        # Phase 7: Taxonomies & Dynamic Pages (fan-in: mutates site.taxonomies)
        affected_tags = content.phase_taxonomies(
            self, cache, incremental, not parallel.taxonomy, pages_to_build
        )

        # Phase 8: Save Taxonomy Index
        content.phase_taxonomy_index(self)

        # Phase 9: Menus
        content.phase_menus(self, incremental, {str(p) for p in changed_page_paths})

        # Phase 10: Related Posts Index (fan-in: mutates shared index)
        content.phase_related_posts(self, incremental, not parallel.related_posts, pages_to_build)

        # Phase 11: Query Indexes
        content.phase_query_indexes(self, cache, incremental, pages_to_build)

        # Phase 12: Update Pages List (add generated taxonomy pages)
        # RFC: Output Cache Architecture - Pass GeneratedPageCache to skip unchanged tag pages
        pages_to_build = content.phase_update_pages_list(
            self,
            cache,
            incremental,
            pages_to_build,
            affected_tags,
            generated_page_cache=generated_page_cache,
        )

        # Phase 12.25: Variant filter (params.edition for multi-variant builds)
        pages_to_build = content.phase_variant_filter(self, pages_to_build)

        # Phase 12.5: URL Collision Detection (proactive validation)
        content.phase_url_collision_check(self, options.strict)

        # Finalize PageIdentity for all pages (frozen hot-path struct)
        for page in pages_to_build:
            page.finalize_identity()

        content_duration_ms = (time.time() - content_start) * 1000
        taxonomy_count = len(self.site.taxonomies) if hasattr(self.site, "taxonomies") else 0
        cli.phase(
            "Content",
            duration_ms=content_duration_ms,
            details=f"{taxonomy_count} taxonomies, {len(affected_tags)} affected tags",
        )
        notify_phase_complete(
            "content",
            content_duration_ms,
            f"{taxonomy_count} taxonomies, {len(affected_tags)} affected tags",
        )

        # Memory diagnostics: print tracemalloc top allocations after content phase
        if os.environ.get("BENGAL_DEBUG_MEMORY") and getattr(self, "_tracemalloc_started", False):
            try:
                import tracemalloc

                mem_snapshot = tracemalloc.take_snapshot()
                top = mem_snapshot.statistics("lineno")[:10]
                cli.detail("[BENGAL_DEBUG_MEMORY] Top 10 allocations:", indent=1)
                for stat in top:
                    frame = stat.traceback[0] if stat.traceback else None
                    loc = f"{frame.filename}:{frame.lineno}" if frame else "?"
                    cli.detail(f"  {stat.size / 1024:.1f} KB @ {loc}", indent=1)
            except Exception:
                pass

        # === PARSING PHASE (after all pages known, before snapshot) ===
        # Parse markdown content for ALL pages (including generated taxonomy pages)
        # RFC: rfc-bengal-snapshot-engine - pre-parse to avoid redundant work during rendering
        parsing_start = time.time()
        with self.logger.phase("parsing"):
            parsing.phase_parse_content(
                self,
                cli,
                pages_to_build,
                parallel=parallel.parsing,
            )
        parsing_duration_ms = (time.time() - parsing_start) * 1000
        if hasattr(self.stats, "parsing_time_ms"):
            self.stats.parsing_time_ms = parsing_duration_ms

        cli.phase(
            "Parsing", duration_ms=parsing_duration_ms, details=f"{len(pages_to_build)} pages"
        )

        # === SNAPSHOT CREATION (after parsing, before rendering) ===
        snapshot.phase_snapshot(self, cli, early_ctx, pages_to_build, force_sequential)

        # === DRY-RUN MODE: Skip output-producing phases ===
        # RFC: rfc-incremental-build-observability Phase 2
        # In dry-run mode, we skip rendering, assets, postprocessing, and health
        # but still collect incremental decision data for --explain output
        if dry_run:
            cli.info("  Dry-run mode: skipping rendering and output phases")
            self.stats.build_time_ms = (time.time() - build_start) * 1000
            self.stats.dry_run = True

            # Clear build state (build complete)
            self.site.set_build_state(None)

            return self.stats

        # === ASSETS PHASE GROUP (dashboard-integrated) ===
        notify_phase_start("assets")
        assets_start = time.time()

        # Phase 13: Process Assets
        # Asset processing is I/O-bound and benefits from parallel execution
        # AssetOrchestrator has smart threshold (MIN_ITEMS_FOR_PARALLEL=5) to avoid overhead
        assets_to_process = rendering.phase_assets(
            self,
            cli,
            incremental,
            parallel.assets,
            assets_to_process,
            collector=output_collector,
        )

        assets_duration_ms = (time.time() - assets_start) * 1000
        notify_phase_complete(
            "assets",
            assets_duration_ms,
            f"{len(assets_to_process) if assets_to_process else 0} assets processed",
        )

        # === RENDERING PHASE GROUP (dashboard-integrated) ===
        notify_phase_start("rendering")
        rendering_start = time.time()

        # Set up live progress display for rendering (the longest phase)
        if progress_manager:
            total_pages = len(pages_to_build) if pages_to_build else 0
            # IMPORTANT: start() must come BEFORE add_phase() to enable Rich Live display
            progress_manager.start()  # Start the Rich Live display
            progress_manager.add_phase("rendering", "Rendering", total=total_pages)
            progress_manager.start_phase("rendering")

        # Phase 14: Render Pages (with cached content from discovery)
        # RFC: rfc-build-orchestrator-phase-groups — pass early_ctx through directly
        # (no second BuildContext). Populate remaining fields before phase_render.
        early_ctx.pages = pages_to_build
        early_ctx.profile = profile
        early_ctx.progress_manager = progress_manager
        early_ctx.reporter = reporter
        early_ctx.profile_templates = profile_templates
        early_ctx.output_collector = output_collector
        try:
            ctx = rendering.phase_render(
                self,
                cli,
                incremental,
                not parallel.rendering,
                quiet,
                verbose,
                memory_optimized,
                pages_to_build,
                profile,
                progress_manager,
                reporter,
                profile_templates=profile_templates,
                early_context=early_ctx,
                changed_sources=changed_sources,
                collector=output_collector,
            )
        finally:
            # Stop progress display after rendering (success or failure)
            if progress_manager:
                rendering_elapsed_ms = (time.time() - rendering_start) * 1000
                progress_manager.complete_phase("rendering", elapsed_ms=rendering_elapsed_ms)
                progress_manager.stop()

        # Phase 15: Update Site Pages (replace proxies with rendered pages)
        rendering.phase_update_site_pages(self, incremental, pages_to_build, cli=cli)

        # Phase 16: Track Asset Dependencies
        rendering.phase_track_assets(self, pages_to_build, cli=cli, build_context=ctx)

        # Record provenance for all built pages (if using provenance-based filtering)
        if hasattr(self, "_provenance_filter") and pages_to_build:
            from bengal.orchestration.build.provenance_orchestration import record_all_page_builds

            record_all_page_builds(self, pages_to_build, parallel=parallel.rendering)

        rendering_duration_ms = (time.time() - rendering_start) * 1000
        notify_phase_complete(
            "rendering",
            rendering_duration_ms,
            f"{len(pages_to_build) if pages_to_build else 0} pages rendered",
        )

        # === FINALIZATION PHASE GROUP (dashboard-integrated) ===
        notify_phase_start("finalization")
        finalization_start = time.time()

        # Phase 17: Post-processing
        # Enable parallel post-processing for independent tasks (sitemap, RSS, output formats)
        finalization.phase_postprocess(
            self, cli, parallel.postprocess, ctx, incremental, collector=output_collector
        )

        # RFC: Output Cache Architecture - Update GeneratedPageCache for tag pages that were rendered
        finalization.phase_update_generated_cache(self, pages_to_build, cache, generated_page_cache)

        # Phase 18: Save Caches (parallel for independent caches)
        finalization.phase_cache_save_parallel(
            self,
            pages_to_build,
            assets_to_process,
            generated_page_cache,
            cli=cli,
        )

        # Phase 19: Collect Final Stats
        finalization.phase_collect_stats(self, build_start, cli=cli)

        # Phase 19.5: Finalize Error Session (track build errors for pattern detection)
        self._finalize_error_session()

        # Populate changed_outputs and compute reload_hint for hot reload decisions
        finalization.phase_compute_reload_hint(
            self.stats,
            output_collector,
            pages_rendered=len(pages_to_build) if pages_to_build else 0,
        )

        finalization_duration_ms = (time.time() - finalization_start) * 1000
        notify_phase_complete(
            "finalization",
            finalization_duration_ms,
            "post-processing complete",
        )

        # === HEALTH PHASE GROUP (dashboard-integrated) ===
        if not options.fast:
            notify_phase_start("health")
            health_start = time.time()

            # Phase 20: Health Check
            with logger.phase("health_check"):
                finalization.run_health_check(self, profile=profile, build_context=ctx)

            health_duration_ms = (time.time() - health_start) * 1000
            health_report = getattr(self.stats, "health_report", None)
            health_summary = ""
            if health_report:
                passed = health_report.total_passed
                total = health_report.total_checks
                health_summary = f"{passed}/{total} checks passed"
            notify_phase_complete("health", health_duration_ms, health_summary)

        # Phase 21: Finalize Build
        finalization.phase_finalize(self, verbose, collector)

        # Save provenance cache if using provenance-based filtering
        finalization.phase_save_provenance(self)

        # Wait for background snapshot save before reporting build complete
        save_thread = getattr(self, "_snapshot_save_thread", None)
        if save_thread is not None:
            save_thread.join(timeout=10)

        # Clear build state (build complete)
        self.site.set_build_state(None)

        return self.stats

    def _filter_sections_by_variant(self, sections: list[Any], variant: str) -> None:
        """Filter section pages by variant; invalidate cached properties."""
        for section in sections:
            section.pages = [p for p in section.pages if p.in_variant(variant)]
            section.__dict__.pop("regular_pages", None)
            section.__dict__.pop("sorted_pages", None)
            section.__dict__.pop("regular_pages_recursive", None)
            self._filter_sections_by_variant(section.subsections, variant)

    def _print_rendering_summary(self) -> None:
        """Print summary of rendered pages (quiet mode)."""
        from bengal.output import get_cli_output

        cli = get_cli_output()

        # Single-pass classification (FLOW audit Finding 12)
        tag_pages = archive_pages = pagination_pages = regular_pages = 0
        for p in self.site.pages:
            if not p.is_generated:
                regular_pages += 1
            elif p.output_path is not None and "tag" in p.output_path.parts:
                tag_pages += 1
            elif p.assigned_template == "archive.html":
                archive_pages += 1
            elif p.output_path is not None and "/page/" in str(p.output_path):
                pagination_pages += 1

        cli.detail(f"Regular pages:    {regular_pages}", indent=1, icon="├─")
        if tag_pages:
            cli.detail(f"Tag pages:        {tag_pages}", indent=1, icon="├─")
        if archive_pages:
            cli.detail(f"Archive pages:    {archive_pages}", indent=1, icon="├─")
        if pagination_pages:
            cli.detail(f"Pagination:       {pagination_pages}", indent=1, icon="├─")
        cli.detail(f"Total:            {len(self.site.pages)} ✓", indent=1, icon="└─")

    def _finalize_error_session(self) -> None:
        """
        Record build errors in session for pattern detection and summary.

        Tracks orchestration errors in the error session to enable:
        - Build summaries including orchestration failures
        - Pattern detection for recurring build issues
        - Error aggregation across build phases
        """
        try:
            from bengal.errors import get_session, record_error

            session = get_session()

            # Record any errors collected during build phases
            if isinstance(self.stats, HasErrors) and self.stats.errors:
                for error in self.stats.errors:
                    if hasattr(error, "phase"):
                        record_error(
                            error,
                            file_path=f"build:{error.phase}",
                            build_phase=error.phase,
                        )
                    else:
                        record_error(error, file_path="build:unknown")

            # Log session summary if errors occurred
            summary = session.get_summary()
            if summary["total_errors"] > 0:
                logger.info(
                    "build_error_session_summary",
                    total_errors=summary["total_errors"],
                    by_phase=summary["errors_by_phase"],
                    recurring_patterns=summary["recurring_errors"],
                )
        except Exception as e:
            # Don't fail build on session tracking errors
            logger.debug(
                "error_session_finalize_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
