"""
Rendering phases for build orchestration.

Phases 13-16: Asset processing, page rendering, update site pages, track asset dependencies.
Handles the rendering phase of the build pipeline, including asset fingerprinting,
page rendering, and dependency tracking for incremental builds.

Key Concepts:
    - Asset fingerprinting: Hash-based cache-busting for assets
    - Font URL rewriting: Update font references after fingerprinting
    - Page rendering: Template rendering for all pages
    - Dependency tracking: Track template and asset dependencies

Related Modules:
    - bengal.orchestration.render: Page rendering orchestration
    - bengal.orchestration.asset: Asset processing orchestration
    - bengal.cache.dependency_tracker: Dependency graph construction

See Also:
    - bengal/orchestration/build/rendering.py: Rendering phase functions
    - plan/active/rfc-build-pipeline.md: Build pipeline design
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.cache import DependencyTracker
    from bengal.cli.progress import LiveProgressManager
    from bengal.core.asset import Asset
    from bengal.core.output import OutputCollector
    from bengal.core.page import Page
    from bengal.orchestration.build import BuildOrchestrator
    from bengal.output import CLIOutput
    from bengal.utils.build_context import BuildContext
    from bengal.utils.profile import BuildProfile
    from bengal.utils.progress import ProgressReporter


def _get_top_bottleneck(total_render_ms: float) -> str | None:
    """
    Get the top rendering bottleneck from template profiler.

    Returns the slowest template function or template as a formatted string
    showing what percentage of total render time it consumed.

    Args:
        total_render_ms: Total rendering time in milliseconds

    Returns:
        Formatted string like "get_nav 42%" or None if no profiler data
    """
    from bengal.rendering.template_profiler import get_profiler

    profiler = get_profiler()
    if not profiler or total_render_ms <= 0:
        return None

    report = profiler.get_report()
    if not report:
        return None

    # Find the single biggest time consumer (function or template)
    top_item: tuple[str, float] | None = None

    # Check functions first (usually more actionable)
    functions = report.get("functions", {})
    for name, stats in functions.items():
        total_ms = stats.get("total_ms", 0)
        if top_item is None or total_ms > top_item[1]:
            top_item = (name, total_ms)

    # Also check templates
    templates = report.get("templates", {})
    for name, stats in templates.items():
        total_ms = stats.get("total_ms", 0)
        if top_item is None or total_ms > top_item[1]:
            # Shorten template names for display
            short_name = name.split("/")[-1] if "/" in name else name
            top_item = (short_name, total_ms)

    if not top_item or top_item[1] <= 0:
        return None

    name, time_ms = top_item
    pct = (time_ms / total_render_ms) * 100

    # Only show if it's a meaningful percentage (>10%)
    if pct < 10:
        return None

    # Truncate long names
    display_name = name if len(name) <= 20 else name[:17] + "..."
    return f"{display_name} {pct:.0f}%"


def _optimize_css(
    orchestrator: BuildOrchestrator,
    cli: CLIOutput,
    assets_to_process: list[Asset],
) -> None:
    """
    Generate optimized CSS based on content types and features.

    Analyzes site content to determine which CSS files are needed,
    then generates a minimal style.css with only necessary imports.
    The optimized CSS is written to the cache directory and the
    style.css asset's source is overridden to use it.

    Args:
        orchestrator: Build orchestrator instance
        cli: CLI output for user messages
        assets_to_process: List of assets (may be modified to update style.css source)

    Side effects:
        - Writes optimized CSS to .bengal/cache/assets/optimized-style.css
        - Updates style.css asset's _bundled_content to use optimized version
    """
    from bengal.orchestration.css_optimizer import CSSOptimizer

    try:
        optimizer = CSSOptimizer(orchestrator.site)
        result = optimizer.generate(report=True)

        if isinstance(result, tuple):
            optimized_css, report = result
        else:
            # No optimization possible (no manifest)
            return

        if report.get("skipped"):
            orchestrator.logger.debug("css_optimization_skipped", reason="no_manifest")
            return

        if not optimized_css:
            return

        # Write optimized CSS to cache directory for debugging
        cache_dir = orchestrator.site.root_path / ".bengal" / "cache" / "assets"
        cache_dir.mkdir(parents=True, exist_ok=True)
        optimized_file = cache_dir / "optimized-style.css"
        optimized_file.write_text(optimized_css, encoding="utf-8")

        # Find and update the style.css asset to use optimized content
        for asset in assets_to_process:
            if asset.is_css_entry_point():
                # Override the bundled content with optimized CSS
                # This will be used instead of reading from source file
                asset._bundled_content = optimized_css
                orchestrator.logger.debug(
                    "css_entry_point_optimized",
                    asset=str(asset.source_path),
                )
                break

        # Log optimization report
        reduction = report.get("reduction_percent", 0)
        included = report.get("included_count", 0)
        excluded = report.get("excluded_count", 0)

        if reduction > 0:
            orchestrator.logger.info(
                "css_optimized",
                reduction_percent=reduction,
                included_files=included,
                excluded_files=excluded,
                types=report.get("types_detected", []),
                features=report.get("features_detected", []),
            )

            # Show in CLI if verbose mode
            if orchestrator.site.config.get("verbose"):
                cli.info(f"CSS optimized: {reduction}% reduction ({included} files)")
                if report.get("types_detected"):
                    cli.info(f"  Content types: {', '.join(report['types_detected'])}")
                if report.get("features_detected"):
                    cli.info(f"  Features: {', '.join(report['features_detected'])}")

    except Exception as e:
        # CSS optimization failure should not break the build
        orchestrator.logger.warning(
            "css_optimization_failed",
            error=str(e),
            error_type=type(e).__name__,
            action="using_full_css",
        )


def _rewrite_fonts_css_urls(orchestrator: BuildOrchestrator) -> None:
    """
    Rewrite fonts.css to use fingerprinted font filenames.

    After asset fingerprinting, font files have hashed names like:
        fonts/outfit-400.6c18d579.woff2

    This function updates fonts.css to reference these fingerprinted names
    instead of the original names.

    Args:
        orchestrator: Build orchestrator instance
    """
    fonts_css_path = orchestrator.site.output_dir / "assets" / "fonts.css"
    manifest_path = orchestrator.site.output_dir / "asset-manifest.json"

    if not fonts_css_path.exists():
        return

    if not manifest_path.exists():
        return

    try:
        # Load the asset manifest
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))

        # Rewrite font URLs
        from bengal.fonts import rewrite_font_urls_with_fingerprints

        updated = rewrite_font_urls_with_fingerprints(fonts_css_path, manifest_data)

        if updated:
            orchestrator.logger.debug("fonts_css_urls_rewritten")
    except Exception as e:
        orchestrator.logger.warning("fonts_css_rewrite_failed", error=str(e))


def phase_assets(
    orchestrator: BuildOrchestrator,
    cli: CLIOutput,
    incremental: bool,
    parallel: bool,
    assets_to_process: list[Asset],
    collector: OutputCollector | None = None,
) -> list[Asset]:
    """
    Phase 13: Process Assets.

    Processes assets (copy, minify, fingerprint) before rendering so asset_url() works.

    Args:
        orchestrator: Build orchestrator instance
        cli: CLI output for user messages
        incremental: Whether this is an incremental build
        parallel: Whether to use parallel processing
        assets_to_process: List of assets to process
        collector: Optional output collector for hot reload tracking

    Returns:
        Updated assets_to_process list (may be expanded if theme assets need processing)

    Side effects:
        - Copies/processes assets to output directory
        - Updates orchestrator.stats.assets_time_ms
    """
    with orchestrator.logger.phase("assets", asset_count=len(assets_to_process), parallel=parallel):
        assets_start = time.time()

        # CRITICAL FIX: On incremental builds, if no assets changed, still need to ensure
        # theme assets are in output. This handles the case where assets directory doesn't
        # exist yet (e.g., first incremental build after initial setup)
        if incremental and not assets_to_process and orchestrator.site.theme:
            # Check if theme has assets
            from bengal.orchestration.content import ContentOrchestrator

            co = ContentOrchestrator(orchestrator.site)
            theme_dir = co._get_theme_assets_dir()
            if theme_dir and theme_dir.exists():
                # Check if output/assets directory was populated
                output_assets = orchestrator.site.output_dir / "assets"
                if not output_assets.exists() or len(list(output_assets.rglob("*"))) < 5:
                    # Theme assets not in output - re-process all assets
                    assets_to_process = orchestrator.site.assets

        # CSS Optimization: Generate minimal style.css based on content types and features
        # See: plan/drafted/rfc-css-tree-shaking.md
        css_config = orchestrator.site.config.get("css", {})
        if isinstance(css_config, dict) and css_config.get("optimize", True):
            _optimize_css(orchestrator, cli, assets_to_process)

        orchestrator.assets.process(
            assets_to_process, parallel=parallel, progress_manager=None, collector=collector
        )

        # Rewrite fonts.css to use fingerprinted font filenames
        # This must happen after asset fingerprinting is complete
        if "fonts" in orchestrator.site.config:
            _rewrite_fonts_css_urls(orchestrator)

        orchestrator.stats.assets_time_ms = (time.time() - assets_start) * 1000

        # Show phase completion
        cli.phase("Assets", duration_ms=orchestrator.stats.assets_time_ms)

        orchestrator.logger.info("assets_complete", assets_processed=len(assets_to_process))

    return assets_to_process


def _log_template_introspection(orchestrator: BuildOrchestrator, verbose: bool) -> None:
    """Log template introspection insights (verbose mode only).

    Uses Kida's introspection API to analyze templates and log:
    - Cacheable blocks (site-wide vs page-level)
    - Block dependencies
    - Optimization opportunities

    RFC: kida-template-introspection
    """
    if not verbose:
        return

    # Only works with Kida engine
    template_engine = orchestrator.site.config.get("template_engine", "jinja2")
    if template_engine != "kida":
        return

    try:
        from bengal.rendering.template_engine import get_engine

        engine = get_engine(orchestrator.site)

        # Check if this is a Kida engine with introspection
        if not hasattr(engine, "get_cacheable_blocks"):
            return

        # Analyze key templates
        templates_to_check = ["base.html", "page.html", "single.html", "list.html"]
        site_cacheable = 0
        page_cacheable = 0

        for template_name in templates_to_check:
            cacheable = engine.get_cacheable_blocks(template_name)
            if cacheable:
                for _block_name, scope in cacheable.items():
                    if scope == "site":
                        site_cacheable += 1
                    elif scope == "page":
                        page_cacheable += 1

        if site_cacheable > 0 or page_cacheable > 0:
            orchestrator.logger.info(
                "template_introspection",
                site_cacheable_blocks=site_cacheable,
                page_cacheable_blocks=page_cacheable,
                hint="Site-cacheable blocks can be rendered once per build",
            )

    except Exception as e:
        # Don't fail build if introspection fails
        orchestrator.logger.debug("template_introspection_failed", error=str(e))


def phase_render(
    orchestrator: BuildOrchestrator,
    cli: CLIOutput,
    incremental: bool,
    parallel: bool,
    quiet: bool,
    verbose: bool,
    memory_optimized: bool,
    pages_to_build: list[Page],
    tracker: DependencyTracker | None,
    profile: BuildProfile,
    progress_manager: LiveProgressManager | None,
    reporter: ProgressReporter | None,
    profile_templates: bool = False,
    early_context: BuildContext | None = None,
    changed_sources: set[Path] | None = None,
    collector: OutputCollector | None = None,
) -> BuildContext:
    """
    Phase 14: Render Pages.

    Renders all pages to HTML using templates.

    Args:
        orchestrator: Build orchestrator instance
        cli: CLI output for user messages
        incremental: Whether this is an incremental build
        parallel: Whether to use parallel processing
        quiet: Whether quiet mode is enabled
        verbose: Whether verbose mode is enabled
        memory_optimized: Whether to use streaming render
        pages_to_build: List of pages to render
        tracker: Dependency tracker
        profile: Build profile
        progress_manager: Progress manager
        reporter: Progress reporter
        profile_templates: Whether template profiling is enabled
        early_context: Optional BuildContext created during discovery phase with
                      cached content. If provided, its cached content is preserved
                      in the final context for use by validators.
        collector: Optional output collector for hot reload tracking

    Returns:
        BuildContext used for rendering (needed by postprocess)

    Side effects:
        - Renders pages to HTML
        - Updates orchestrator.stats.rendering_time_ms
    """
    quiet_mode = quiet and not verbose

    # Log template introspection insights (verbose mode, Kida only)
    _log_template_introspection(orchestrator, verbose)

    # Reset error deduplicator for this render phase (on build stats)
    if orchestrator.stats is not None:
        dedup = orchestrator.stats.get_error_deduplicator()
        dedup.reset()

    with orchestrator.logger.phase(
        "rendering",
        page_count=len(pages_to_build),
        parallel=parallel,
        memory_optimized=memory_optimized,
    ):
        rendering_start = time.time()

        # Use memory-optimized streaming if requested
        if memory_optimized:
            from bengal.orchestration.streaming import StreamingRenderOrchestrator
            from bengal.utils.build_context import BuildContext

            streaming_render = StreamingRenderOrchestrator(orchestrator.site)
            ctx = BuildContext(
                site=orchestrator.site,
                pages=pages_to_build,
                tracker=tracker,
                stats=orchestrator.stats,
                profile=profile,
                progress_manager=progress_manager,
                reporter=reporter,
                profile_templates=profile_templates,
                incremental=bool(incremental),
                output_collector=collector,
            )
            # Transfer cached content from early context (build-integrated validation)
            if early_context and early_context.has_cached_content:
                ctx._page_contents = early_context._page_contents
            # Transfer incremental state (changed pages) for validators.
            if early_context is not None:
                ctx.changed_page_paths = set(getattr(early_context, "changed_page_paths", set()))
            streaming_render.process(
                pages_to_build,
                parallel=parallel,
                quiet=quiet_mode,
                tracker=tracker,
                stats=orchestrator.stats,
                progress_manager=progress_manager,
                reporter=reporter,
                build_context=ctx,
                changed_sources=changed_sources,
            )
        else:
            from bengal.utils.build_context import BuildContext

            ctx = BuildContext(
                site=orchestrator.site,
                pages=pages_to_build,
                tracker=tracker,
                stats=orchestrator.stats,
                profile=profile,
                progress_manager=progress_manager,
                reporter=reporter,
                profile_templates=profile_templates,
                incremental=bool(incremental),
                output_collector=collector,
            )
            # Transfer cached content from early context (build-integrated validation)
            if early_context and early_context.has_cached_content:
                ctx._page_contents = early_context._page_contents
            # Transfer incremental state (changed pages) for validators.
            if early_context is not None:
                ctx.changed_page_paths = set(getattr(early_context, "changed_page_paths", set()))
        orchestrator.render.process(
            pages_to_build,
            parallel=parallel,
            quiet=quiet_mode,
            tracker=tracker,
            stats=orchestrator.stats,
            progress_manager=progress_manager,
            reporter=reporter,
            build_context=ctx,
            changed_sources=changed_sources,
        )

        orchestrator.stats.rendering_time_ms = (time.time() - rendering_start) * 1000

        # Show phase completion with page count, throughput, and top bottleneck
        page_count = len(pages_to_build)
        rendering_ms = orchestrator.stats.rendering_time_ms

        # Build details string with throughput
        detail_parts = [f"{page_count} pages"]
        if rendering_ms > 0:
            pages_per_sec = (page_count / rendering_ms) * 1000
            detail_parts.append(f"{pages_per_sec:.0f}/sec")

        # Add top bottleneck if profiling is enabled
        if profile_templates:
            bottleneck = _get_top_bottleneck(rendering_ms)
            if bottleneck:
                detail_parts.append(bottleneck)

        details = ", ".join(detail_parts)
        cli.phase(
            "Rendering",
            duration_ms=rendering_ms,
            details=details,
        )

        orchestrator.logger.info(
            "rendering_complete",
            pages_rendered=len(pages_to_build),
            errors=len(orchestrator.stats.template_errors)
            if hasattr(orchestrator.stats, "template_errors")
            else 0,
            memory_optimized=memory_optimized,
        )

    # Print rendering summary in quiet mode
    if quiet_mode:
        # Call helper method on orchestrator
        orchestrator._print_rendering_summary()

    # Show summary of suppressed duplicate errors (from build stats)
    if orchestrator.stats is not None:
        orchestrator.stats.get_error_deduplicator().display_summary()

    return ctx


def phase_update_site_pages(
    orchestrator: BuildOrchestrator,
    incremental: bool,
    pages_to_build: list[Page],
    cli: CLIOutput | None = None,
) -> None:
    """
    Phase 15: Update Site Pages.

    Updates site.pages with freshly rendered pages (for incremental builds).
    Replaces stale PageProxy objects with rendered Page objects.

    Args:
        orchestrator: Build orchestrator instance
        incremental: Whether this is an incremental build
        pages_to_build: List of freshly rendered pages
    """
    if incremental and pages_to_build:
        start = time.perf_counter()
        # Create a mapping of source_path -> rendered page
        rendered_map = {page.source_path: page for page in pages_to_build}

        # Replace stale proxies with fresh pages
        updated_pages = []
        for page in orchestrator.site.pages:
            if page.source_path in rendered_map:
                # Use the freshly rendered page
                updated_pages.append(rendered_map[page.source_path])
            else:
                # Keep the existing page (proxy or unchanged)
                updated_pages.append(page)

        orchestrator.site.pages = updated_pages

        # Log composition for debugging (helps troubleshoot incremental issues)
        if orchestrator.logger.level.value <= 10:  # DEBUG level
            page_types = {"Page": 0, "PageProxy": 0, "other": 0}
            for p in orchestrator.site.pages:
                ptype = type(p).__name__
                if ptype == "Page":
                    page_types["Page"] += 1
                elif ptype == "PageProxy":
                    page_types["PageProxy"] += 1
                else:
                    page_types["other"] += 1

            orchestrator.logger.debug(
                "site_pages_composition_before_postprocess",
                fresh_pages=page_types["Page"],
                cached_proxies=page_types["PageProxy"],
                total_pages=len(orchestrator.site.pages),
            )
        else:
            orchestrator.logger.debug(
                "site_pages_updated_after_render",
                fresh_pages=len(rendered_map),
                total_pages=len(orchestrator.site.pages),
            )
        duration_ms = (time.perf_counter() - start) * 1000
        if cli is not None:
            cli.phase(
                "Update site pages",
                duration_ms=duration_ms,
                details=f"{len(rendered_map)} updated",
            )


def phase_track_assets(
    orchestrator: BuildOrchestrator,
    pages_to_build: list[Any],
    cli: CLIOutput | None = None,
    build_context: BuildContext | None = None,
) -> None:
    """
    Phase 16: Persist Asset Dependencies.

    Persists asset dependencies that were accumulated during rendering
    (inline extraction). Assets are extracted in RenderingPipeline and
    accumulated in BuildContext for efficient batch persistence.

    Args:
        orchestrator: Build orchestrator instance
        pages_to_build: List of rendered pages
        cli: Optional CLI output handler
        build_context: BuildContext with accumulated assets from rendering
    """
    with orchestrator.logger.phase("track_assets", enabled=True):
        start = time.perf_counter()
        status = "Done"
        icon = "✓"
        details = f"{len(pages_to_build)} pages"

        try:
            from bengal.cache.asset_dependency_map import AssetDependencyMap

            asset_map = AssetDependencyMap(orchestrator.site.paths.asset_cache)

            if build_context and build_context.has_accumulated_assets:
                # Persist accumulated assets from inline extraction
                accumulated = build_context.get_accumulated_assets()
                for source_path, assets in accumulated:
                    asset_map.track_page_assets(source_path, assets)
                details = f"{len(accumulated)} pages"

                # Clear accumulated data to free memory
                build_context.clear_accumulated_assets()

            # Persist asset dependencies to disk
            asset_map.save_to_disk()

            orchestrator.logger.info(
                "asset_dependencies_tracked",
                pages_with_assets=len(asset_map.pages),
                unique_assets=len(asset_map.get_all_assets()),
            )
        except Exception as e:
            status = "Error"
            icon = "✗"
            details = "see logs"
            orchestrator.logger.warning("asset_tracking_failed", error=str(e))
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            if cli is not None:
                cli.phase(
                    "Track assets",
                    status=status,
                    duration_ms=duration_ms,
                    details=details,
                    icon=icon,
                )
