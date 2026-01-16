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
    stats = orchestrator.build(BuildOptions(parallel=True, incremental=True))

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
from bengal.orchestration.stats import BuildStats
from bengal.orchestration.taxonomy import TaxonomyOrchestrator
from bengal.utils.observability.logger import get_logger

from . import content, finalization, initialization, rendering
from .options import BuildOptions

logger = get_logger(__name__)

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.cache.build_cache import BuildCache
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.orchestration.build.results import ConfigCheckResult, FilterResult
    from bengal.output import CLIOutput
    from bengal.orchestration.build_context import BuildContext
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

        # Simple phase completion messages (no live progress bar)
        # Live progress bar was removed due to UX issues (felt stuck) and performance overhead
        use_live_progress = False
        progress_manager = None
        reporter = None

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
        # This is intentionally best-effort: if anything goes wrong, we continue
        # without diagnostics rather than impacting builds.
        if not hasattr(self.site, "diagnostics"):
            try:
                from bengal.core.diagnostics import DiagnosticsCollector

                self.site.diagnostics = DiagnosticsCollector()  # type: ignore[attr-defined]
            except Exception:
                pass

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

        # Initialize cache and tracker (ALWAYS, even for full builds)
        # We need cache for cleanup of deleted files and auto-mode decision
        with logger.phase("initialization"):
            cache, tracker = self.incremental.initialize(enabled=True)  # Always load cache
        
        # RFC: Output Cache Architecture - Initialize GeneratedPageCache for tag page caching
        # This enables skipping unchanged tag pages based on member content hashes
        from bengal.cache.generated_page_cache import GeneratedPageCache
        generated_page_cache = GeneratedPageCache(self.site.paths.state_dir / "generated_page_cache.json")
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

        # Phase 1: Font Processing
        initialization.phase_fonts(self, cli)

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
            self, cache, incremental, pages_to_build, affected_tags,
            generated_page_cache=generated_page_cache,
        )

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

        # Phase 14: Render Pages (with cached content from discovery)
        # Pass force_sequential - phase will compute parallel based on should_parallelize() and page count
        ctx = rendering.phase_render(
            self,
            cli,
            incremental,
            force_sequential,
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
        rendering.phase_track_assets(self, pages_to_build, cli=cli, build_context=ctx)

        # Record provenance for all built pages (if using provenance-based filtering)
        if hasattr(self, "_provenance_filter") and pages_to_build:
            from bengal.orchestration.build.provenance_filter import record_all_page_builds
            record_all_page_builds(self, pages_to_build)

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
        # Post-processing doesn't use parallel processing, so pass False
        finalization.phase_postprocess(
            self, cli, False, ctx, incremental, collector=output_collector
        )
        
        # RFC: Output Cache Architecture - Update GeneratedPageCache for tag pages that were rendered
        # This enables skipping them on future builds if member content hasn't changed
        # Note: Update on ALL builds (not just incremental) to populate cache for first build
        if generated_page_cache:
            # Build content hash lookup from parsed_content cache
            content_hash_lookup: dict[str, str] = {}
            if cache and hasattr(cache, 'parsed_content'):
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

        # Phase 18: Save Cache
        finalization.phase_cache_save(self, pages_to_build, assets_to_process, cli=cli)
        
        # RFC: Output Cache Architecture - Save GeneratedPageCache
        if generated_page_cache:
            generated_page_cache.save()

        # Phase 19: Collect Final Stats
        finalization.phase_collect_stats(self, build_start, cli=cli)

        # Phase 19.5: Finalize Error Session (track build errors for pattern detection)
        self._finalize_error_session()

        # Populate changed_outputs from collector for hot reload decisions
        self.stats.changed_outputs = output_collector.get_outputs()

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

        # Clear build state (build complete)
        self.site.set_build_state(None)

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
        from bengal.orchestration.build.provenance_filter import (
            phase_incremental_filter_provenance,
        )
        from bengal.orchestration.build.results import FilterResult

        return phase_incremental_filter_provenance(
            self,
            cli,
            cache,
            incremental,
            verbose,
            build_start,
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
        force_sequential: bool,
        pages_to_build: list[Page],
    ) -> set[str]:
        """Phase 7: Taxonomies & Dynamic Pages."""
        return content.phase_taxonomies(self, cache, incremental, force_sequential, pages_to_build)

    def _phase_taxonomy_index(self) -> None:
        """Phase 8: Save Taxonomy Index."""
        content.phase_taxonomy_index(self)

    def _phase_menus(self, incremental: bool, changed_page_paths: set[Path]) -> None:
        """Phase 9: Menu Building."""
        content.phase_menus(self, incremental, {str(p) for p in changed_page_paths})

    def _phase_related_posts(
        self, incremental: bool, force_sequential: bool, pages_to_build: list[Page]
    ) -> None:
        """Phase 10: Related Posts Index."""
        content.phase_related_posts(self, incremental, force_sequential, pages_to_build)

    def _phase_query_indexes(
        self, cache: BuildCache, incremental: bool, pages_to_build: list[Page]
    ) -> None:
        """Phase 11: Query Indexes."""
        content.phase_query_indexes(self, cache, incremental, pages_to_build)

    def _phase_update_pages_list(
        self, cache: BuildCache, incremental: bool, pages_to_build: list[Page], affected_tags: set[str]
    ) -> list[Page]:
        """Phase 12: Update Pages List."""
        return content.phase_update_pages_list(self, cache, incremental, pages_to_build, affected_tags)

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
        force_sequential: bool,
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
            force_sequential,
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

    def _phase_track_assets(
        self, pages_to_build: list[Page], build_context: BuildContext | None = None
    ) -> None:
        """Phase 16: Track Asset Dependencies."""
        rendering.phase_track_assets(self, pages_to_build, build_context=build_context)

    def _phase_postprocess(
        self,
        cli: CLIOutput,
        force_sequential: bool,
        ctx: BuildContext | Any | None,
        incremental: bool,
    ) -> None:
        """Phase 17: Post-processing."""
        # Post-processing doesn't use parallel processing, so pass False
        finalization.phase_postprocess(self, cli, False, ctx, incremental)

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
            if hasattr(self.stats, "errors") and self.stats.errors:
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
