"""
Runtime session for one `BuildOrchestrator.build()` call.

Holds mutable sequencing state (options, collectors, plugin hooks) so
`runner.py` can dispatch existing phase modules without adding phases.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bengal.core.output import BuildOutputCollector
from bengal.orchestration.build.inputs import BuildInput
from bengal.orchestration.build.options import BuildCompletionPolicy, BuildOptions
from bengal.orchestration.build_state import BuildState
from bengal.orchestration.stats import BuildStats

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.cache.build_cache import BuildCache
    from bengal.cache.generated_page_cache import GeneratedPageCache
    from bengal.core.asset import Asset
    from bengal.core.output import OutputCollector
    from bengal.orchestration.build import BuildOrchestrator
    from bengal.orchestration.build_context import BuildContext
    from bengal.output import CLIOutput
    from bengal.protocols.core import PageLike
    from bengal.utils.observability.cli_progress import LiveProgressManager
    from bengal.utils.observability.performance_collector import PerformanceCollector
    from bengal.utils.observability.profile import BuildProfile


@dataclass
class BuildSession:
    """Mutable state threaded through one build's phase sequence."""

    orchestrator: BuildOrchestrator
    options: BuildOptions
    build_input: BuildInput
    force_sequential: bool
    incremental: bool | None
    verbose: bool
    quiet: bool
    profile: BuildProfile
    memory_optimized: bool
    strict: bool
    profile_templates: bool
    changed_sources: set[Path] | None
    nav_changed_sources: set[Path] | None
    serve_ready_policy: bool
    dry_run: bool
    cli: CLIOutput
    build_start: float
    cache: BuildCache
    generated_page_cache: GeneratedPageCache
    early_ctx: BuildContext
    output_collector: OutputCollector
    artifact_collector: OutputCollector
    plugin_registry: Any
    progress_manager: LiveProgressManager | None = None
    reporter: Any = None
    collector: PerformanceCollector | None = None
    build_complete_fired: bool = False
    pages_to_build: list[PageLike] | None = None
    assets_to_process: list[Asset] | None = None
    affected_tags: set[str] = field(default_factory=set)
    changed_page_paths: set[Path] = field(default_factory=set)
    affected_sections: set[str] | None = None
    config_changed: bool = False
    ctx: BuildContext | None = None

    def notify_phase_start(self, phase_name: str) -> None:
        """Notify dashboard that a phase is starting."""
        on_phase_start = self.options.on_phase_start
        if on_phase_start is not None:
            try:
                on_phase_start(phase_name)
            except Exception as e:
                self.orchestrator.logger.debug(
                    "phase_callback_error", phase=phase_name, error=str(e)
                )

    def notify_phase_complete(self, phase_name: str, duration_ms: float, details: str = "") -> None:
        """Notify dashboard that a phase completed."""
        on_phase_complete = self.options.on_phase_complete
        if on_phase_complete is not None:
            try:
                on_phase_complete(phase_name, duration_ms, details)
            except Exception as e:
                self.orchestrator.logger.debug(
                    "phase_callback_error", phase=phase_name, error=str(e)
                )

    def run_plugin_phase(self, phase_name: str) -> None:
        """Run registered plugin callbacks for a build lifecycle phase."""
        from bengal.plugins.integration import apply_plugin_phase_hooks

        apply_plugin_phase_hooks(
            self.plugin_registry, phase_name, self.orchestrator.site, self.early_ctx
        )

    def fire_build_complete(self) -> None:
        """Fire the build_complete hook at most once for this build."""
        if self.build_complete_fired:
            return
        self.build_complete_fired = True
        self.run_plugin_phase("build_complete")


def prepare_build_session(
    orchestrator: BuildOrchestrator,
    options: BuildOptions | BuildInput,
) -> BuildSession:
    """
    Normalize options, initialize CLI/cache/context, and fire `build_start`.

    Plugin `build_complete` is not fired here; the runner's try/finally owns
    that teardown contract (issue #437).
    """
    # Normalize to BuildInput for consistent input handling
    if isinstance(options, BuildInput):
        build_input = options
        options = build_input.options
    else:
        build_input = BuildInput.from_options(options, orchestrator.site.root_path)

    # Store for use in build phases (e.g., max_workers for WaveScheduler)
    orchestrator.options = options
    orchestrator.current_input = build_input

    force_sequential = options.force_sequential
    incremental = options.incremental
    verbose = options.verbose
    quiet = options.quiet
    profile = options.profile
    memory_optimized = options.memory_optimized
    strict = options.strict
    profile_templates = options.profile_templates
    changed_sources = options.changed_sources or None
    nav_changed_sources = options.nav_changed_sources or None
    serve_ready_policy = options.completion_policy is BuildCompletionPolicy.SERVE_READY
    dry_run = options.dry_run

    logger = orchestrator.logger

    # Import profile utilities inside the call so tests can patch source modules.
    from bengal.output import init_cli_output
    from bengal.utils.observability.profile import BuildProfile

    if profile is None:
        profile = BuildProfile.WRITER

    from bengal.utils.observability.profile import set_current_profile

    set_current_profile(profile)

    profile_config = profile.get_config()
    cli = init_cli_output(profile=profile, quiet=quiet, verbose=verbose)

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

    from bengal.utils.observability.logger import set_console_quiet

    if not verbose:
        set_console_quiet(True)

    build_start = time.time()

    from bengal.rendering.pipeline.thread_local import get_created_dirs

    get_created_dirs().clear()

    collector = None
    if profile_config.get("collect_metrics", False):
        from bengal.utils.observability.performance_collector import PerformanceCollector

        track_memory = profile_config.get("track_memory", False)
        collector = PerformanceCollector(
            metrics_dir=orchestrator.site.config_service.paths.metrics_dir,
            track_memory=track_memory,
        )
        collector.start_build()

    orchestrator.stats = BuildStats(parallel=False, incremental=bool(incremental))
    orchestrator.stats.strict_mode = strict
    orchestrator.stats.completion_policy = options.completion_policy.value
    orchestrator.stats.change_census = build_input.change_census.to_dict()

    logger.info(
        "build_start",
        force_sequential=force_sequential,
        incremental=incremental,
        root_path=str(orchestrator.site.root_path),
        change_census=orchestrator.stats.change_census,
    )

    if getattr(orchestrator.site, "diagnostics", None) is None:
        from bengal.core.diagnostics import DiagnosticsCollector

        orchestrator.site.diagnostics = DiagnosticsCollector()

    from bengal import __version__

    cli.header(f"Building your site... (Bengal v{__version__})")
    mode_label = "incremental" if incremental else "full"
    _auto_reason = locals().get("auto_reason")
    profile_label = profile.value if profile else "writer"

    if _auto_reason:
        cli.detail(
            f"{orchestrator.site.root_path} | {mode_label} ({_auto_reason}) | {profile_label}",
            indent=1,
            icon=cli.icons.arrow,
        )
    else:
        cli.detail(
            f"{orchestrator.site.root_path} | {mode_label} | {profile_label}",
            indent=1,
            icon=cli.icons.arrow,
        )
    cli.blank()

    orchestrator.site.build_time = datetime.now()

    from bengal.rendering.pipeline.output import reset_fast_write_tracker

    reset_fast_write_tracker()

    from bengal.rendering.assets import drain_asset_fallback_aggregator

    drain_asset_fallback_aggregator()

    build_state = BuildState(
        build_time=orchestrator.site.build_time,
        incremental=bool(incremental),
        dev_mode=orchestrator.site.dev_mode,
    )
    orchestrator.site.set_build_state(build_state)

    initialization_start = time.perf_counter()
    with logger.phase("initialization"):
        cache = orchestrator.incremental.initialize(enabled=True)
    orchestrator.stats.record_phase_timing(
        "Initialization",
        (time.perf_counter() - initialization_start) * 1000,
    )

    from bengal.cache.generated_page_cache import GeneratedPageCache

    generated_page_cache = GeneratedPageCache(
        orchestrator.site.config_service.paths.state_dir / "generated_page_cache.json"
    )

    if incremental is None:
        try:
            cache_path = orchestrator.site.config_service.paths.build_cache
            cache_exists = cache_path.exists()
            cached_files = len(cache.file_fingerprints)
            incremental = bool(cache_exists and cached_files > 0)
        except Exception as e:
            logger.debug(
                "incremental_cache_check_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            incremental = False

    orchestrator.stats.incremental = bool(incremental)

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
                    stacklevel=4,
                )
        except Exception:  # noqa: S110 -- effect tracing may not be initialized yet on first build
            pass

    orchestrator.site._last_build_options = options
    orchestrator.site._cache = orchestrator.incremental.cache
    orchestrator._last_build_options = options

    from bengal.orchestration.build_context import BuildContext
    from bengal.utils.concurrency.executor import CancellationToken

    early_ctx = BuildContext(
        site=orchestrator.site,
        stats=orchestrator.stats,
        cancellation_token=CancellationToken(timeout=300.0),
    )
    early_ctx.cache = orchestrator.incremental.cache

    output_collector = BuildOutputCollector(output_dir=orchestrator.site.output_dir)
    artifact_collector = BuildOutputCollector(output_dir=orchestrator.site.output_dir)
    early_ctx.artifact_collector = artifact_collector

    from bengal.plugins import load_plugins, set_active_registry

    plugin_registry = load_plugins()
    set_active_registry(plugin_registry)

    session = BuildSession(
        orchestrator=orchestrator,
        options=options,
        build_input=build_input,
        force_sequential=force_sequential,
        incremental=incremental,
        verbose=verbose,
        quiet=quiet,
        profile=profile,
        memory_optimized=memory_optimized,
        strict=strict,
        profile_templates=profile_templates,
        changed_sources=changed_sources,
        nav_changed_sources=nav_changed_sources,
        serve_ready_policy=serve_ready_policy,
        dry_run=dry_run,
        cli=cli,
        build_start=build_start,
        cache=cache,
        generated_page_cache=generated_page_cache,
        early_ctx=early_ctx,
        output_collector=output_collector,
        artifact_collector=artifact_collector,
        plugin_registry=plugin_registry,
        progress_manager=progress_manager,
        reporter=reporter,
        collector=collector,
    )
    session.run_plugin_phase("build_start")
    return session
