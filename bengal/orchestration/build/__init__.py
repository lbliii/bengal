"""
Build orchestration for Bengal SSG.

Main coordinator that sets up build context and delegates to the
data-driven pipeline (``bengal.orchestration.pipeline``). This is the
primary entry point for building a Bengal site.

Package Structure:
    __init__.py  - BuildOrchestrator class (this file)
    options.py   - BuildOptions dataclass
    results.py   - Result types for phase outputs
    initialization.py, content.py, rendering.py, finalization.py, parsing.py
        Phase functions called by pipeline tasks

Pipeline Architecture (Bengal 0.2):
    build() populates a BuildContext, then calls execute_pipeline()
    with task declarations from bengal.orchestration.tasks. The
    TaskScheduler computes a dependency DAG, and the BatchExecutor
    runs independent tasks in parallel batches.

Usage::

    from bengal.orchestration.build import BuildOrchestrator, BuildOptions

    orchestrator = BuildOrchestrator(site)
    stats = orchestrator.build(BuildOptions(incremental=True))

See Also:
    bengal.orchestration.pipeline: DAG scheduler and batch executor
    bengal.orchestration.tasks: Task declarations (requires/produces)
    bengal.core.site: Site data model

"""

from __future__ import annotations

import time
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

from .options import BuildOptions

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.core.site import Site


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
        options: BuildOptions,
    ) -> BuildStats:
        """
        Execute full build pipeline.

        Args:
            options: BuildOptions dataclass with all build configuration.

        Returns:
            BuildStats object with build statistics

        Example:
            >>> from bengal.orchestration.build.options import BuildOptions
            >>> options = BuildOptions(strict=True)
            >>> stats = orchestrator.build(options)
        """

        # Store options for use in build phases (e.g., max_workers for WaveScheduler)
        self.options = options

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

        # --- Measure build startup overhead (gap before header appears) ---
        _build_entry_time = time.time()

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

        _startup_ms = (time.time() - _build_entry_time) * 1000
        logger.info(
            "build_start",
            force_sequential=force_sequential,
            incremental=incremental,
            root_path=str(self.site.root_path),
            startup_overhead_ms=f"{_startup_ms:.0f}",
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

        # Show build header with version and startup overhead
        from bengal import __version__

        # RFC: reactive-rebuild-architecture Phase 3c
        # Include startup_overhead_ms in header so users see the "blind gap" cost
        _header = f"Building your site... (Bengal v{__version__})"
        if _startup_ms > 10:  # Only show if meaningful (>10ms)
            _header += f" [startup: {_startup_ms:.0f}ms]"
        cli.header(_header)
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

        # Phase E: Load disk-cached ASTs for incremental build parsing reuse.
        # Pages with matching content hashes can skip full parsing entirely.
        from bengal.server.fragment_update import ContentASTCache

        ast_cache_dir = self.site.root_path / ".bengal" / "cache" / "ast"
        ast_loaded = ContentASTCache.load_from_disk(ast_cache_dir)
        if ast_loaded > 0:
            cli.detail(f"Loaded {ast_loaded} cached ASTs", indent=1, icon=cli.icons.arrow)

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

        # Store options and cache for phase-level optimizations
        self.site._last_build_options = options
        self.site._cache = self.incremental.cache
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

        # =====================================================================
        # Populate BuildContext for data-driven pipeline
        # =====================================================================
        early_ctx.cache = cache
        early_ctx.cli = cli
        early_ctx.build_start = build_start
        early_ctx.output_collector = output_collector
        early_ctx.incremental = bool(incremental)
        early_ctx.verbose = verbose
        early_ctx.quiet = quiet
        early_ctx.strict = strict
        early_ctx.parallel = not force_sequential
        early_ctx.memory_optimized = memory_optimized
        early_ctx.full_output = full_output
        early_ctx.profile_templates = profile_templates
        early_ctx.profile = profile
        early_ctx.progress_manager = progress_manager
        early_ctx.reporter = reporter

        # Pipeline-specific fields (accessed by tasks as ctx._orchestrator, etc.)
        early_ctx._orchestrator = self
        early_ctx._build_options = options
        early_ctx._generated_page_cache = generated_page_cache

        # =====================================================================
        # Execute data-driven pipeline
        # =====================================================================
        from bengal.orchestration.pipeline import execute_pipeline
        from bengal.orchestration.tasks import INITIAL_KEYS, all_tasks

        pipeline_result = execute_pipeline(
            tasks=all_tasks(),
            ctx=early_ctx,
            initial_keys=INITIAL_KEYS,
            parallel=not force_sequential,
            on_task_start=on_phase_start,
            on_task_complete=on_phase_complete,
        )

        # Check for pipeline failures — propagate first error
        if not pipeline_result.success:
            failed = pipeline_result.failed
            # Log all failures
            for f in failed:
                logger.error(
                    "pipeline_task_failed",
                    task=f.name,
                    duration_ms=round(f.duration_ms, 1),
                    error=str(f.error),
                )
            # If the build was skipped (filter returned None), stats already set
            if self.stats.skipped:
                self.site.set_build_state(None)
                return self.stats
            # Fail loudly for required task failures.
            first_failed = failed[0] if failed else None
            message = "Build failed: pipeline task execution error"
            original_error: Exception | None = None
            if first_failed is not None:
                original_error = first_failed.error
                message = (
                    f"Build failed in task '{first_failed.name}': "
                    f"{first_failed.error}"
                )

            if not verbose:
                from bengal.utils.observability.logger import set_console_quiet

                set_console_quiet(False)
            if collector is not None:
                collector.end_build(self.stats.to_dict())
            self.site.set_build_state(None)
            if original_error is not None:
                raise RuntimeError(message) from original_error
            raise RuntimeError(message)

        # Finalize build timing
        self.stats.build_time_ms = (time.time() - build_start) * 1000

        # Restore console logging
        if not verbose:
            from bengal.utils.observability.logger import set_console_quiet

            set_console_quiet(False)

        # Finalize performance collection
        if collector is not None:
            collector.end_build(self.stats.to_dict())

        # Clear build state (build complete)
        self.site.set_build_state(None)

        return self.stats

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
