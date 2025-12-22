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

        # Show phase completion with page count
        page_count = len(pages_to_build)
        cli.phase(
            "Rendering",
            duration_ms=orchestrator.stats.rendering_time_ms,
            details=f"{page_count} pages",
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
    orchestrator: BuildOrchestrator, pages_to_build: list[Any], cli: CLIOutput | None = None
) -> None:
    """
    Phase 16: Track Asset Dependencies (Parallel).

    Extracts and caches which assets each rendered page references.
    Used for incremental builds to invalidate pages when assets change.

    Performance:
        Uses parallel extraction for sites with >5 pages. On multi-core systems,
        this provides ~3-4x speedup for large sites (100+ pages).

    Args:
        orchestrator: Build orchestrator instance
        pages_to_build: List of rendered pages
        cli: Optional CLI output handler
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Threshold below which sequential is faster (avoids thread overhead)
    PARALLEL_THRESHOLD = 5

    with orchestrator.logger.phase("track_assets", enabled=True):
        start = time.perf_counter()
        status = "Done"
        icon = "✓"
        details = f"{len(pages_to_build)} pages"
        try:
            from bengal.cache.asset_dependency_map import AssetDependencyMap
            from bengal.rendering.asset_extractor import extract_assets_from_html

            asset_map = AssetDependencyMap(orchestrator.site.paths.asset_cache)

            def extract_page_assets(page: Any) -> tuple[Any, set[str]] | None:
                """Extract assets from a single page (thread-safe)."""
                if not page.rendered_html:
                    return None
                assets = extract_assets_from_html(page.rendered_html)
                return (page.source_path, assets) if assets else None

            if len(pages_to_build) < PARALLEL_THRESHOLD:
                # Sequential for small workloads (avoid thread overhead)
                for page in pages_to_build:
                    result = extract_page_assets(page)
                    if result:
                        asset_map.track_page_assets(*result)
            else:
                # Parallel extraction for larger workloads
                max_workers = getattr(orchestrator, "max_workers", None)
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [executor.submit(extract_page_assets, p) for p in pages_to_build]
                    for future in as_completed(futures):
                        result = future.result()
                        if result:
                            source_path, assets = result
                            asset_map.track_page_assets(source_path, assets)

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
            orchestrator.logger.warning(
                "asset_tracking_failed",
                error=str(e),
            )
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
