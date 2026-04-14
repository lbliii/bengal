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
- Phase 14: PageLike rendering (parallel or sequential)
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

import time
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
from bengal.orchestration.stats import BuildStats, ReloadHint
from bengal.orchestration.taxonomy import TaxonomyOrchestrator
from bengal.protocols.capabilities import HasErrors
from bengal.utils.observability.logger import get_logger

from . import content, finalization, initialization, parsing, rendering
from .inputs import BuildInput
from .options import BuildOptions  # noqa: TC001 — runtime re-export for health.py et al.

logger = get_logger(__name__)

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.cache.build_cache import BuildCache
    from bengal.core.site import Site
    from bengal.orchestration.build_context import BuildContext
    from bengal.output import CLIOutput
    from bengal.protocols.core import PageLike
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
        - RenderOrchestrator: PageLike rendering
        - AssetOrchestrator: Asset processing
        - PostprocessOrchestrator: Sitemap, RSS, validation
        - IncrementalOrchestrator: Change detection and caching

    """

    _provenance_filter: Any = None

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

        # Extract values from options for use in build phases
        # Parallel is now auto-detected via should_parallelize() unless force_sequential=True
        # We'll compute it when we know the page count (in rendering phase)
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
        from bengal.utils.observability.terminal import is_interactive_terminal

        use_live_progress = is_interactive_terminal() and not quiet
        progress_manager = None
        reporter = None

        if use_live_progress:
            progress_manager = LiveProgressManager(
                profile=profile,
                enabled=True,
                render_fn=cli.render,
            )

        # Suppress console log noise (logs still go to file for debugging)
        from bengal.utils.observability.logger import set_console_quiet

        if not verbose:  # Only suppress console logs if not in verbose logging mode
            set_console_quiet(True)

        # Start timing
        build_start = time.time()

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

        # Reset fast-write tracker at build start (prevents stale paths across dev-server rebuilds)
        from bengal.rendering.pipeline.output import reset_fast_write_tracker

        reset_fast_write_tracker()

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

        # Warn if incremental builds are enabled but effect tracing is not
        if incremental:
            try:
                from bengal.effects.render_integration import BuildEffectTracer

                tracer_instance = BuildEffectTracer.get_instance()
                if not tracer_instance.tracer.effects:
                    import warnings

                    warnings.warn(
                        "Incremental build enabled but no effect traces found. "
                        "Data file changes may not trigger page rebuilds. "
                        "Run a full rebuild (bengal build --no-incremental) if content seems stale.",
                        stacklevel=2,
                    )
            except Exception:  # noqa: S110
                pass  # Effect tracing may not be initialized yet on first build

        # Store options and cache for phase-level optimizations
        self.site._last_build_options = options
        self.site._cache = self.incremental.cache
        self._last_build_options = options

        # Create BuildContext early for content caching during discovery
        # This enables build-integrated validation: validators use cached content
        # instead of re-reading from disk, saving ~4 seconds on health checks.
        from bengal.orchestration.build_context import BuildContext
        from bengal.utils.concurrency.executor import CancellationToken

        early_ctx = BuildContext(
            site=self.site,
            stats=self.stats,
            cancellation_token=CancellationToken(timeout=300.0),
        )

        # Create output collector for hot reload tracking
        # This collector tracks all written files (HTML, CSS, assets) for typed reload decisions.
        output_collector = BuildOutputCollector(output_dir=self.site.output_dir)

        # Phase 0: Plugin Loading
        from bengal.plugins import load_plugins, set_active_registry

        plugin_registry = load_plugins()
        set_active_registry(plugin_registry)

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
        from bengal.orchestration.build.provenance_filter import (
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

        # Phase 6: Section Finalization
        content.phase_sections(self, cli, incremental, affected_sections)

        # Phase 7: Taxonomies & Dynamic Pages
        # Pass force_sequential - phase will compute parallel based on should_parallelize()
        affected_tags = content.phase_taxonomies(
            self, cache, incremental, force_sequential, pages_to_build
        )

        # Phase 8: Save Taxonomy Index
        content.phase_taxonomy_index(self)

        # Phase 9: Menus
        content.phase_menus(self, incremental, {str(p) for p in changed_page_paths})

        # Phase 10: Related Posts Index
        # Pass force_sequential - phase will compute parallel based on should_parallelize()
        content.phase_related_posts(self, incremental, force_sequential, pages_to_build)

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
        params_edition = None
        params = self.site.config.get("params") or {}
        if isinstance(params, dict):
            params_edition = params.get("edition")
        if params_edition is not None and str(params_edition).strip():
            variant = str(params_edition).strip()
            pages_to_build = [p for p in pages_to_build if p.in_variant(variant)]
            self.site.pages = [p for p in self.site.pages if p.in_variant(variant)]
            self._filter_sections_by_variant(self.site.sections, variant)
            if hasattr(self.site, "invalidate_regular_pages_cache"):
                self.site.invalidate_regular_pages_cache()

        # Phase 12.5: URL Collision Detection (proactive validation)
        collisions = self.site.validate_no_url_collisions(strict=options.strict)
        if collisions:
            for msg in collisions:
                logger.warning(msg, event="url_collision_detected")

        content_duration_ms = (time.time() - content_start) * 1000
        taxonomy_count = len(self.site.taxonomies) if hasattr(self.site, "taxonomies") else 0
        notify_phase_complete(
            "content",
            content_duration_ms,
            f"{taxonomy_count} taxonomies, {len(affected_tags)} affected tags",
        )

        # === PARSING PHASE (after all pages known, before snapshot) ===
        # Parse markdown content for ALL pages (including generated taxonomy pages)
        # RFC: rfc-bengal-snapshot-engine - pre-parse to avoid redundant work during rendering
        parsing_start = time.time()
        with self.logger.phase("parsing"):
            parsing.phase_parse_content(
                self,
                cli,
                pages_to_build,
                parallel=not force_sequential,
            )
        parsing_duration_ms = (time.time() - parsing_start) * 1000
        if hasattr(self.stats, "parsing_time_ms"):
            self.stats.parsing_time_ms = parsing_duration_ms

        cli.phase(
            "Parsing", duration_ms=parsing_duration_ms, details=f"{len(pages_to_build)} pages"
        )

        # === SNAPSHOT CREATION (after parsing, before rendering) ===
        # Create immutable snapshot for lock-free parallel rendering
        # Snapshot now contains pre-parsed HTML content from all pages
        from bengal.snapshots import create_site_snapshot
        from bengal.snapshots.persistence import SnapshotCache

        snapshot_start = time.time()
        with self.logger.phase("snapshot"):
            site_snapshot = create_site_snapshot(self.site)
            snapshot_duration_ms = (time.time() - snapshot_start) * 1000
            # Store snapshot in build context for rendering phase
            early_ctx.snapshot = site_snapshot
            # Store snapshot time in stats if available
            if hasattr(self.stats, "snapshot_time_ms"):
                self.stats.snapshot_time_ms = snapshot_duration_ms

            # Install pre-computed NavTrees for lock-free lookups during rendering
            from bengal.core.nav_tree import NavTreeCache

            NavTreeCache.set_precomputed(dict(site_snapshot.navigation.nav_trees))

            # Eagerly create global context wrappers (eliminates _context_lock
            # contention during parallel rendering — cache is populated before
            # any render thread starts)
            from bengal.rendering.context import _get_global_contexts

            _get_global_contexts(self.site, build_context=early_ctx)

            # Configure directive cache before parallel rendering (eliminates
            # _config_lock contention — configure_for_site() only needs to
            # run once, and doing it here ensures no racing during rendering)
            from bengal.cache.directive_cache import configure_for_site

            configure_for_site(self.site)

            # Save snapshot for incremental builds (RFC: rfc-bengal-snapshot-engine)
            # This enables near-instant parsing on subsequent builds
            cache_dir = self.site.root_path / ".bengal" / "cache" / "snapshots"
            snapshot_cache = SnapshotCache(cache_dir)
            snapshot_cache.save(site_snapshot)

            # === SERVICE INSTANTIATION (RFC: bengal-v2-architecture Phase 1) ===
            # Services operate on the frozen snapshot for thread-safe rendering.
            # Instantiated once per build, available via build context.
            from bengal.services.query import QueryService

            early_ctx.query_service = QueryService.from_snapshot(site_snapshot)
            # DataService instantiation deferred — only when data/ dir exists
            try:
                from bengal.services.data import DataService

                early_ctx.data_service = DataService.from_root(self.site.root_path)
            except Exception:  # noqa: S110
                pass  # data/ dir may not exist; service remains None

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
            not force_sequential,
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
        # Pass force_sequential - phase will compute parallel based on should_parallelize() and page count
        # Ensure early_ctx has output_collector so pipeline gets it (fixes output_collector_missing)
        early_ctx.output_collector = output_collector
        try:
            ctx = rendering.phase_render(
                self,
                cli,
                incremental,
                force_sequential,
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

        # Phase 15: Update Site Pages (replace cached pages with rendered pages)
        rendering.phase_update_site_pages(self, incremental, pages_to_build, cli=cli)

        # Phase 16: Track Asset Dependencies
        rendering.phase_track_assets(self, pages_to_build, cli=cli, build_context=ctx)

        # Record provenance for all built pages (if using provenance-based filtering)
        if hasattr(self, "_provenance_filter") and pages_to_build:
            from bengal.orchestration.build.provenance_filter import record_all_page_builds

            record_all_page_builds(self, pages_to_build, parallel=not force_sequential)

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
            self, cli, not force_sequential, ctx, incremental, collector=output_collector
        )

        # RFC: Output Cache Architecture - Update GeneratedPageCache for tag pages that were rendered
        # This enables skipping them on future builds if member content hasn't changed
        # Note: Update on ALL builds (not just incremental) to populate cache for first build
        if generated_page_cache:
            # Build content hash lookup from parsed_content cache
            content_hash_lookup: dict[str, str] = {}
            if cache and hasattr(cache, "parsed_content"):
                for path_str, entry in cache.parsed_content.items():
                    if isinstance(entry, dict):
                        content_hash = entry.get("metadata_hash", "")
                        if content_hash:
                            content_hash_lookup[path_str] = content_hash

            # Update cache for rendered tag pages
            updated_entries = 0
            tag_pages_found = 0
            tag_pages_with_posts = 0
            for page in pages_to_build:
                if page.metadata.get("type") == "tag" and page.metadata.get("_generated"):
                    tag_pages_found += 1
                    tag_slug = page.metadata.get("_tag_slug", "")
                    member_pages = page.metadata.get("_posts", [])
                    if tag_slug and member_pages:
                        tag_pages_with_posts += 1
                        # Note: We don't have rendered_html here, pass empty string
                        # The cache is primarily for member hash comparison, not HTML caching
                        generated_page_cache.update(
                            page_type="tag",
                            page_id=tag_slug,
                            member_pages=member_pages,
                            content_cache=content_hash_lookup,
                            rendered_html="",  # HTML caching optional
                            generation_time_ms=0,  # Not tracked here
                        )
                        updated_entries += 1

            logger.info(
                "generated_page_cache_updated",
                entries=updated_entries,
                tag_pages_found=tag_pages_found,
                tag_pages_with_posts=tag_pages_with_posts,
                content_hash_count=len(content_hash_lookup),
            )

        # Phase 18: Save Caches (parallel for independent caches)
        # Run cache saves concurrently since they're independent I/O operations.
        # This reduces total cache save time from sum to max of all saves.
        cache_start = time.perf_counter()

        def _save_main_cache() -> None:
            self.incremental.save_cache(pages_to_build, assets_to_process)

        def _save_generated_cache() -> None:
            if generated_page_cache:
                generated_page_cache.save()

        # Run cache saves in parallel
        from bengal.utils.concurrency.work_scope import WorkScope

        with WorkScope("CacheSave", max_workers=2) as scope:
            results = scope.map(lambda fn: fn(), [_save_main_cache, _save_generated_cache])

        for r in results:
            if r.error:
                raise r.error

        cache_duration_ms = (time.perf_counter() - cache_start) * 1000
        if cli is not None:
            cli.phase("Cache save", duration_ms=cache_duration_ms)
        self.logger.info("cache_saved")

        # Phase 19: Collect Final Stats
        finalization.phase_collect_stats(self, build_start, cli=cli)

        # Phase 19.5: Finalize Error Session (track build errors for pattern detection)
        self._finalize_error_session()

        # Populate changed_outputs from collector for hot reload decisions
        self.stats.changed_outputs = output_collector.get_outputs()

        # Compute reload_hint for smarter dev server decisions.
        # Only set "none" when we have outputs and can confidently say no reload.
        # When outputs is empty (e.g. output_collector missing from pipeline),
        # leave reload_hint=None so the trigger uses changed_files fallback.
        outputs = self.stats.changed_outputs
        if self.stats.dry_run:
            self.stats.reload_hint = ReloadHint.NONE
        elif not outputs:
            self.stats.reload_hint = None
        elif any(o.output_type.value == "html" for o in outputs):
            self.stats.reload_hint = ReloadHint.FULL
        elif all(o.output_type.value == "css" for o in outputs):
            self.stats.reload_hint = ReloadHint.CSS_ONLY
        else:
            self.stats.reload_hint = ReloadHint.FULL

        # Debug: Log output collection for hot reload diagnostics
        if self.stats.changed_outputs:
            self.logger.debug(
                "output_collector_results",
                total_outputs=len(self.stats.changed_outputs),
                html_count=sum(
                    1 for o in self.stats.changed_outputs if o.output_type.value == "html"
                ),
                css_count=sum(
                    1 for o in self.stats.changed_outputs if o.output_type.value == "css"
                ),
            )
        else:
            self.logger.warning(
                "output_collector_empty",
                pages_rendered=len(pages_to_build) if pages_to_build else 0,
            )

        finalization_duration_ms = (time.time() - finalization_start) * 1000
        notify_phase_complete(
            "finalization",
            finalization_duration_ms,
            "post-processing complete",
        )

        # === HEALTH PHASE GROUP (dashboard-integrated) ===
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
        if hasattr(self, "_provenance_filter"):
            from bengal.orchestration.build.provenance_filter import save_provenance_cache

            save_provenance_cache(self)

        # Clean up partial fast-write files if build had errors
        if self.stats.template_errors or (isinstance(self.stats, HasErrors) and self.stats.errors):
            from bengal.rendering.pipeline.output import cleanup_fast_writes

            cleaned = cleanup_fast_writes()
            if cleaned:
                logger.info("fast_write_cleanup", files_removed=cleaned)

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

        # Count page types in a single pass
        tag_pages = 0
        archive_pages = 0
        pagination_pages = 0
        for p in self.site.pages:
            meta = p.metadata
            if meta is not None and meta.get("_generated"):
                if p.output_path is not None and "tag" in p.output_path.parts:
                    tag_pages += 1
                if meta.get("template") == "archive.html":
                    archive_pages += 1
                if p.output_path is not None and "/page/" in str(p.output_path):
                    pagination_pages += 1
        regular_pages = len(self.site.regular_pages)

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
