"""
Build orchestration for Bengal SSG.

Main coordinator that delegates build phases to specialized orchestrators.
"""

from __future__ import annotations

import time
from contextlib import suppress
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
        incremental: bool = False,
        verbose: bool = False,
        quiet: bool = False,
        profile: BuildProfile = None,
        memory_optimized: bool = False,
        strict: bool = False,
        full_output: bool = False,
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

        Returns:
            BuildStats object with build statistics
        """
        # Import profile utilities
        from bengal.utils.cli_output import init_cli_output
        from bengal.utils.profile import BuildProfile

        # Use default profile if not provided
        if profile is None:
            profile = BuildProfile.WRITER

        # Get profile configuration
        profile_config = profile.get_config()

        # Initialize CLI output system with profile
        cli = init_cli_output(profile=profile, quiet=quiet, verbose=verbose)

        # Determine if we should use live progress
        # Disable if: quiet mode, verbose logging mode, full_output requested, or not a TTY
        use_live_progress = (
            not quiet
            and not verbose
            and not full_output
            and profile_config.get("live_progress", {}).get("enabled", True)
        )

        # Suppress console log noise even when not using live progress
        # (logs still go to file for debugging)
        from bengal.utils.logger import set_console_quiet

        if not verbose:  # Only suppress console logs if not in verbose logging mode
            set_console_quiet(True)

        # Create live progress manager if enabled
        progress_manager = None
        reporter = None
        if use_live_progress:
            try:
                from bengal.utils.live_progress import LiveProgressManager
                from bengal.utils.progress import LiveProgressReporterAdapter
                from bengal.utils.rich_console import should_use_rich

                if should_use_rich():
                    progress_manager = LiveProgressManager(profile)
                    progress_manager.__enter__()
                    reporter = LiveProgressReporterAdapter(progress_manager)
            except Exception as e:
                # Fallback to traditional output if live progress fails
                self.logger.warning("live_progress_init_failed", error=str(e))
                progress_manager = None

        # Start timing
        build_start = time.time()

        # Initialize performance collection only if profile enables it
        collector = None
        if profile_config.get("collect_metrics", False):
            from bengal.utils.performance_collector import PerformanceCollector

            collector = PerformanceCollector()
            collector.start_build()

        # Initialize stats
        self.stats = BuildStats(parallel=parallel, incremental=incremental)
        self.stats.strict_mode = strict

        self.logger.info(
            "build_start",
            parallel=parallel,
            incremental=incremental,
            root_path=str(self.site.root_path),
        )

        # Show build header (unless using live progress which handles its own display)
        if not progress_manager:
            cli.header("Building your site...")
            cli.info(f"   ↪ {self.site.root_path}")
            cli.blank()

        self.site.build_time = datetime.now()

        # Initialize cache and tracker (ALWAYS, even for full builds)
        # We need cache for cleanup of deleted files
        with self.logger.phase("initialization"):
            cache, tracker = self.incremental.initialize(enabled=True)  # Always load cache

        # Phase 0.5: Font Processing (before asset discovery)
        # Download Google Fonts and generate CSS if configured
        if "fonts" in self.site.config:
            with self.logger.phase("fonts"):
                fonts_start = time.time()
                try:
                    from bengal.fonts import FontHelper

                    # Ensure assets directory exists
                    assets_dir = self.site.root_path / "assets"
                    assets_dir.mkdir(parents=True, exist_ok=True)

                    # Process fonts (download + generate CSS)
                    font_helper = FontHelper(self.site.config["fonts"])
                    font_helper.process(assets_dir)

                    self.stats.fonts_time_ms = (time.time() - fonts_start) * 1000
                    self.logger.info("fonts_complete")
                except Exception as e:
                    cli.warning(f"Font processing failed: {e}")
                    cli.info("   Continuing build without custom fonts...")
                    self.logger.warning("fonts_failed", error=str(e))

        # Phase 1: Content Discovery
        content_dir = self.site.root_path / "content"
        with self.logger.phase("discovery", content_dir=str(content_dir)):
            discovery_start = time.time()

            if progress_manager:
                progress_manager.add_phase("discovery", "Discovery")
                progress_manager.start_phase("discovery")

            self.content.discover()

            self.stats.discovery_time_ms = (time.time() - discovery_start) * 1000

            if progress_manager:
                progress_manager.complete_phase(
                    "discovery", elapsed_ms=self.stats.discovery_time_ms
                )
                progress_manager.update_phase(
                    "discovery", pages=len(self.site.pages), sections=len(self.site.sections)
                )

            self.logger.info(
                "discovery_complete", pages=len(self.site.pages), sections=len(self.site.sections)
            )

        # Check if config changed (forces full rebuild)
        # Note: We check this even on full builds to populate the cache
        config_changed = self.incremental.check_config_changed()
        if incremental and config_changed:
            # Determine if this is first build or actual change
            config_files = [
                self.site.root_path / "bengal.toml",
                self.site.root_path / "bengal.yaml",
                self.site.root_path / "bengal.yml",
            ]
            config_file = next((f for f in config_files if f.exists()), None)

            # Check if config was previously cached
            if config_file and str(config_file) not in cache.file_hashes:
                cli.info("  Config not in cache - performing full rebuild")
                cli.detail("(This is normal for the first incremental build)", indent=1)
            else:
                cli.info("  Config file modified - performing full rebuild")
                if config_file:
                    cli.detail(f"Changed: {config_file.name}", indent=1)

            incremental = False
            # Don't clear cache yet - we need it for cleanup!

        # Phase 1.5: Clean up deleted files (ALWAYS, even on full builds)
        # This ensures output stays in sync with source files
        # Do this BEFORE clearing cache so we have the output_sources map
        if cache and hasattr(self.incremental, "_cleanup_deleted_files"):
            self.incremental._cleanup_deleted_files()
            # Save cache immediately so deletions are persisted
            cache_dir = self.site.root_path / ".bengal"
            cache_path = cache_dir / "cache.json"
            cache.save(cache_path)

        # Now clear cache if config changed
        if not incremental and config_changed:
            cache.clear()
            # Re-track config file hash so it's present after full build
            with suppress(Exception):
                self.incremental.check_config_changed()

        # Phase 2: Determine what to build (MOVED UP - before taxonomies/menus)
        # This is the KEY optimization: filter BEFORE expensive operations
        with self.logger.phase("incremental_filtering", enabled=incremental):
            pages_to_build = self.site.pages
            assets_to_process = self.site.assets
            affected_tags = set()
            changed_page_paths = set()
            affected_sections = None  # Track for selective section finalization

            if incremental:
                # Find what changed BEFORE generating taxonomies/menus
                pages_to_build, assets_to_process, change_summary = (
                    self.incremental.find_work_early(verbose=verbose)
                )

                # Track which pages changed (for taxonomy updates)
                changed_page_paths = {
                    p.source_path for p in pages_to_build if not p.metadata.get("_generated")
                }

                # Determine affected sections and tags from changed pages
                affected_sections = set()
                for page in pages_to_build:
                    if not page.metadata.get("_generated"):
                        if page.section:
                            affected_sections.add(str(page.section.path))
                        if page.tags:
                            for tag in page.tags:
                                affected_tags.add(tag.lower().replace(" ", "-"))

                # Track cache statistics (Phase 2)
                total_pages = len(self.site.pages)
                pages_rebuilt = len(pages_to_build)
                pages_cached = total_pages - pages_rebuilt

                self.stats.cache_hits = pages_cached
                self.stats.cache_misses = pages_rebuilt

                # Estimate time saved (approximate: 80% of rendering time for cached pages)
                if pages_rebuilt > 0 and total_pages > 0:
                    avg_time_per_page = (
                        (self.stats.rendering_time_ms / total_pages)
                        if hasattr(self.stats, "rendering_time_ms")
                        else 50
                    )
                    self.stats.time_saved_ms = pages_cached * avg_time_per_page * 0.8

                self.logger.info(
                    "incremental_work_identified",
                    pages_to_build=len(pages_to_build),
                    assets_to_process=len(assets_to_process),
                    skipped_pages=len(self.site.pages) - len(pages_to_build),
                    cache_hit_rate=f"{(pages_cached / total_pages * 100) if total_pages > 0 else 0:.1f}%",
                )

                # Check if we need to regenerate taxonomy pages
                # (This happens in dev server when site.pages is cleared but content hasn't changed)
                # If cache has tags, we need to regenerate taxonomy pages even if no content changed
                needs_taxonomy_regen = bool(cache.get_all_tags())

                if not pages_to_build and not assets_to_process and not needs_taxonomy_regen:
                    cli.success("✓ No changes detected - build skipped")
                    cli.detail(
                        f"Cached: {len(self.site.pages)} pages, {len(self.site.assets)} assets",
                        indent=1,
                    )
                    self.logger.info(
                        "no_changes_detected",
                        cached_pages=len(self.site.pages),
                        cached_assets=len(self.site.assets),
                    )
                    self.stats.skipped = True
                    self.stats.build_time_ms = (time.time() - build_start) * 1000
                    return self.stats

                # More informative incremental build message
                pages_msg = f"{len(pages_to_build)} page{'s' if len(pages_to_build) != 1 else ''}"
                assets_msg = (
                    f"{len(assets_to_process)} asset{'s' if len(assets_to_process) != 1 else ''}"
                )
                skipped_msg = f"{len(self.site.pages) - len(pages_to_build)} cached"

                cli.info(f"  Incremental build: {pages_msg}, {assets_msg} (skipped {skipped_msg})")

                # Show what changed (brief summary)
                if change_summary:
                    changed_items = []
                    for change_type, items in change_summary.items():
                        if items:
                            changed_items.append(f"{len(items)} {change_type.lower()}")
                    if changed_items:
                        cli.detail(f"Changed: {', '.join(changed_items[:3])}", indent=1)

                if verbose and change_summary:
                    cli.blank()
                    cli.info("  📝 Changes detected:")
                    for change_type, items in change_summary.items():
                        if items:
                            cli.info(f"    • {change_type}: {len(items)} file(s)")
                            for item in items[:5]:  # Show first 5
                                cli.info(f"      - {item.name if hasattr(item, 'name') else item}")
                            if len(items) > 5:
                                cli.info(f"      ... and {len(items) - 5} more")
                    cli.blank()

        # Phase 3: Section Finalization (ensure all sections have index pages)
        # Note: "Generated pages" message removed - cluttered output
        with self.logger.phase("section_finalization"):
            self.sections.finalize_sections(affected_sections=affected_sections)

            # Invalidate regular_pages cache (section finalization may add generated index pages)
            self.site.invalidate_regular_pages_cache()

            # Validate section structure
            section_errors = self.sections.validate_sections()
            if section_errors:
                self.logger.warning(
                    "section_validation_errors",
                    error_count=len(section_errors),
                    errors=section_errors[:3],
                )
                strict_mode = self.site.config.get("strict_mode", False)
                if strict_mode:
                    cli.blank()
                    cli.error("Section validation errors:")
                    for error in section_errors:
                        cli.detail(str(error), indent=1, icon="•")
                    raise Exception(
                        f"Build failed: {len(section_errors)} section validation error(s)"
                    )
                else:
                    # Warn but continue in non-strict mode
                    for error in section_errors[:3]:  # Show first 3
                        cli.warning(str(error))
                    if len(section_errors) > 3:
                        cli.warning(f"... and {len(section_errors) - 3} more errors")

        # Phase 4: Taxonomies & Dynamic Pages (INCREMENTAL OPTIMIZATION)
        with self.logger.phase("taxonomies"):
            taxonomy_start = time.time()

            if incremental and pages_to_build:
                # Incremental: Only update taxonomies for changed pages
                # This is O(changed) instead of O(all) - major optimization!
                affected_tags = self.taxonomy.collect_and_generate_incremental(
                    pages_to_build, cache
                )

                # Store affected tags for later use (related posts, etc.)
                self.site._affected_tags = affected_tags

            elif incremental and not pages_to_build:
                # Incremental but no pages changed: Still need to regenerate taxonomy pages
                # because site.pages was cleared (dev server case)
                # Use cache to rebuild taxonomies efficiently
                affected_tags = self.taxonomy.collect_and_generate_incremental([], cache)
                self.site._affected_tags = affected_tags

            elif not incremental:
                # Full build: Collect and generate everything
                self.taxonomy.collect_and_generate(parallel=parallel)

                # Mark all tags as affected (for Phase 6 - adding to pages_to_build)
                if hasattr(self.site, "taxonomies") and "tags" in self.site.taxonomies:
                    affected_tags = set(self.site.taxonomies["tags"].keys())

                # Update cache with full taxonomy data (for next incremental build)
                for page in self.site.pages:
                    if not page.metadata.get("_generated") and page.tags:
                        cache.update_page_tags(page.source_path, set(page.tags))

            self.stats.taxonomy_time_ms = (time.time() - taxonomy_start) * 1000
            if hasattr(self.site, "taxonomies"):
                self.logger.info(
                    "taxonomies_built",
                    taxonomy_count=len(self.site.taxonomies),
                    total_terms=sum(len(terms) for terms in self.site.taxonomies.values()),
                )

            # Invalidate regular_pages cache (taxonomy generation adds tag/category pages)
            self.site.invalidate_regular_pages_cache()

        # Phase 5: Menus (INCREMENTAL - skip if unchanged)
        with self.logger.phase("menus"):
            menu_start = time.time()
            # Check if config changed (forces menu rebuild)
            config_changed = incremental and self.incremental.check_config_changed()

            # Build menus (or reuse cached if unchanged)
            menu_rebuilt = self.menu.build(
                changed_pages=changed_page_paths if incremental else None,
                config_changed=config_changed,
            )

            self.stats.menu_time_ms = (time.time() - menu_start) * 1000
            self.logger.info("menus_built", menu_count=len(self.site.menu), rebuilt=menu_rebuilt)

        # Phase 5.5: Related Posts Index (NEW - Pre-compute for O(1) template access)
        # Note: This is O(n·t·p) and can be expensive at scale. Skip for large sites
        # or sites without tags to improve performance.
        should_build_related = (
            hasattr(self.site, "taxonomies")
            and "tags" in self.site.taxonomies
            and len(self.site.pages) < 5000  # Skip for large sites (>5K pages)
        )

        if should_build_related:
            with self.logger.phase("related_posts_index"):
                from bengal.orchestration.related_posts import RelatedPostsOrchestrator

                related_posts_start = time.time()
                related_posts_orchestrator = RelatedPostsOrchestrator(self.site)
                related_posts_orchestrator.build_index(limit=5, parallel=parallel)

                # Log statistics
                pages_with_related = sum(
                    1
                    for p in self.site.pages
                    if hasattr(p, "related_posts")
                    and p.related_posts
                    and not p.metadata.get("_generated")
                )
                self.stats.related_posts_time_ms = (time.time() - related_posts_start) * 1000
                self.logger.info(
                    "related_posts_built",
                    pages_with_related=pages_with_related,
                    total_pages=len(
                        [p for p in self.site.pages if not p.metadata.get("_generated")]
                    ),
                )
        else:
            # Skip related posts for large sites or sites without tags
            for page in self.site.pages:
                page.related_posts = []
            self.logger.info(
                "related_posts_skipped",
                reason="large_site_or_no_tags",
                page_count=len(self.site.pages),
                threshold=5000,
            )

        # Phase 6: Update filtered pages list (add generated pages)
        # Now that we've generated tag pages, update pages_to_build if needed
        if affected_tags:
            # Convert to set for O(1) membership and automatic deduplication
            pages_to_build_set = set(pages_to_build) if pages_to_build else set()

            # Add newly generated tag pages to rebuild set
            # OPTIMIZATION: Use site.generated_pages (cached) instead of filtering all pages
            for page in self.site.generated_pages:
                if page.metadata.get("type") in ("tag", "tag-index"):
                    # For full builds, add all taxonomy pages
                    # For incremental builds, add only affected tag pages + tag index
                    tag_slug = page.metadata.get("_tag_slug")
                    should_include = (
                        not incremental  # Full build: include all
                        or page.metadata.get("type") == "tag-index"  # Always include tag index
                        or tag_slug in affected_tags  # Include affected tag pages
                    )

                    if should_include:
                        pages_to_build_set.add(page)  # O(1) + automatic dedup

            # Convert back to list for rendering (preserves compatibility)
            pages_to_build = list(pages_to_build_set)

        # Phase 7: Process Assets (MOVED BEFORE RENDERING)
        # Assets must be processed first so asset_url() can find fingerprinted files
        with self.logger.phase("assets", asset_count=len(assets_to_process), parallel=parallel):
            assets_start = time.time()

            # Register assets phase
            if progress_manager:
                progress_manager.add_phase("assets", "Assets", total=len(assets_to_process))
                progress_manager.start_phase("assets")

            self.assets.process(
                assets_to_process, parallel=parallel, progress_manager=progress_manager
            )
            self.stats.assets_time_ms = (time.time() - assets_start) * 1000

            if progress_manager:
                progress_manager.complete_phase("assets", elapsed_ms=self.stats.assets_time_ms)

            self.logger.info("assets_complete", assets_processed=len(assets_to_process))

        # Phase 8: Render Pages (MOVED AFTER ASSETS)
        # quiet mode: suppress progress when --quiet flag is used (unless verbose overrides)
        quiet_mode = quiet and not verbose

        # Rendering phase header removed - phases are now shown via progress manager or final summary
        with self.logger.phase(
            "rendering",
            page_count=len(pages_to_build),
            parallel=parallel,
            memory_optimized=memory_optimized,
        ):
            rendering_start = time.time()

            # Register rendering phase
            if progress_manager:
                progress_manager.add_phase("rendering", "Rendering", total=len(pages_to_build))
                progress_manager.start_phase("rendering")

            # Use memory-optimized streaming if requested
            if memory_optimized:
                from bengal.orchestration.streaming import StreamingRenderOrchestrator
                from bengal.utils.build_context import BuildContext

                streaming_render = StreamingRenderOrchestrator(self.site)
                # Prepare context (future use)
                ctx = BuildContext(
                    site=self.site,
                    pages=pages_to_build,
                    tracker=tracker,
                    stats=self.stats,
                    profile=profile,
                    progress_manager=progress_manager,
                    reporter=reporter,
                )
                streaming_render.process(
                    pages_to_build,
                    parallel=parallel,
                    quiet=quiet_mode,
                    tracker=tracker,
                    stats=self.stats,
                    progress_manager=progress_manager,
                    reporter=reporter,
                    build_context=ctx,
                )
            else:
                from bengal.utils.build_context import BuildContext

                # Prepare context (future use)
                ctx = BuildContext(
                    site=self.site,
                    pages=pages_to_build,
                    tracker=tracker,
                    stats=self.stats,
                    profile=profile,
                    progress_manager=progress_manager,
                    reporter=reporter,
                )
                # Keep existing API while threading context in progressively
                self.render.process(
                    pages_to_build,
                    parallel=parallel,
                    quiet=quiet_mode,
                    tracker=tracker,
                    stats=self.stats,
                    progress_manager=progress_manager,
                    reporter=reporter,
                    build_context=ctx,
                )

            self.stats.rendering_time_ms = (time.time() - rendering_start) * 1000

            if progress_manager:
                progress_manager.complete_phase(
                    "rendering", elapsed_ms=self.stats.rendering_time_ms
                )

            self.logger.info(
                "rendering_complete",
                pages_rendered=len(pages_to_build),
                errors=len(self.stats.template_errors)
                if hasattr(self.stats, "template_errors")
                else 0,
                memory_optimized=memory_optimized,
            )

        # Print rendering summary in quiet mode
        if quiet_mode:
            self._print_rendering_summary()

        # Phase 9: Post-processing
        with self.logger.phase("postprocessing", parallel=parallel):
            postprocess_start = time.time()

            # Count postprocess tasks
            postprocess_task_count = 0
            if self.site.config.get("generate_sitemap", True):
                postprocess_task_count += 1
            if self.site.config.get("generate_rss", True):
                postprocess_task_count += 1
            if self.site.config.get("output_formats", {}).get("enabled", True):
                postprocess_task_count += 1
            if self.site.config.get("validate_links", True):
                postprocess_task_count += 1
            postprocess_task_count += 1  # special pages always run

            if progress_manager:
                progress_manager.add_phase(
                    "postprocess", "Post-process", total=postprocess_task_count
                )
                progress_manager.start_phase("postprocess")

            self.postprocess.run(
                parallel=parallel, progress_manager=progress_manager, build_context=ctx
            )

            self.stats.postprocess_time_ms = (time.time() - postprocess_start) * 1000

            if progress_manager:
                progress_manager.complete_phase(
                    "postprocess", elapsed_ms=self.stats.postprocess_time_ms
                )

            self.logger.info("postprocessing_complete")

        # Phase 9: Update cache
        # Always save cache after successful build (needed for future incremental builds)
        with self.logger.phase("cache_save"):
            self.incremental.save_cache(pages_to_build, assets_to_process)
            self.logger.info("cache_saved")

        # Collect final stats (before health check so we can include them in report)
        self.stats.total_pages = len(self.site.pages)
        self.stats.regular_pages = len(
            [p for p in self.site.pages if not p.metadata.get("_generated")]
        )
        self.stats.generated_pages = len(
            [p for p in self.site.pages if p.metadata.get("_generated")]
        )
        self.stats.total_assets = len(self.site.assets)
        self.stats.total_sections = len(self.site.sections)
        self.stats.taxonomies_count = sum(len(terms) for terms in self.site.taxonomies.values())
        self.stats.build_time_ms = (time.time() - build_start) * 1000

        # Store stats for health check validators to access
        self.site._last_build_stats = {
            "build_time_ms": self.stats.build_time_ms,
            "rendering_time_ms": self.stats.rendering_time_ms,
            "total_pages": self.stats.total_pages,
            "total_assets": self.stats.total_assets,
        }

        # Phase 10: Health Check (with profile filtering)
        with self.logger.phase("health_check"):
            self._run_health_check(profile=profile)

        # Collect memory metrics and save performance data (if enabled by profile)
        if collector:
            self.stats = collector.end_build(self.stats)
            collector.save(self.stats)

        # Log build completion
        log_data = {
            "duration_ms": self.stats.build_time_ms,
            "total_pages": self.stats.total_pages,
            "total_assets": self.stats.total_assets,
            "success": True,
        }

        # Only add memory metrics if they were collected
        if self.stats.memory_rss_mb > 0:
            log_data["memory_rss_mb"] = self.stats.memory_rss_mb
            log_data["memory_heap_mb"] = self.stats.memory_heap_mb

        self.logger.info("build_complete", **log_data)

        # Close progress manager and restore logger output
        if progress_manager:
            try:
                progress_manager.__exit__(None, None, None)
            except Exception as e:
                self.logger.warning("live_progress_close_failed", error=str(e))

        # Restore normal logger console output if we suppressed it
        if not verbose:
            set_console_quiet(False)

        # Log Pygments cache statistics (performance monitoring)
        try:
            from bengal.rendering.pygments_cache import log_cache_stats

            log_cache_stats()
        except ImportError:
            pass  # Cache not used

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
        regular_pages = sum(1 for p in self.site.pages if not p.metadata.get("_generated"))

        cli.detail(f"Regular pages:    {regular_pages}", indent=1, icon="├─")
        if tag_pages:
            cli.detail(f"Tag pages:        {tag_pages}", indent=1, icon="├─")
        if archive_pages:
            cli.detail(f"Archive pages:    {archive_pages}", indent=1, icon="├─")
        if pagination_pages:
            cli.detail(f"Pagination:       {pagination_pages}", indent=1, icon="├─")
        cli.detail(f"Total:            {len(self.site.pages)} ✓", indent=1, icon="└─")

    def _run_health_check(self, profile: BuildProfile = None) -> None:
        """
        Run health check system with profile-based filtering.

        Different profiles run different sets of validators:
        - WRITER: Basic checks (broken links, SEO)
        - THEME_DEV: Extended checks (performance, templates)
        - DEV: Full checks (all validators)

        Args:
            profile: Build profile to use for filtering validators

        Raises:
            Exception: If strict_mode is enabled and health checks fail
        """
        from bengal.health import HealthCheck

        health_config = self.site.config.get("health_check", {})

        # Check if health checks are enabled
        if isinstance(health_config, bool):
            enabled = health_config
        else:
            enabled = health_config.get("enabled", True)

        if not enabled:
            return

        # Run health checks with profile filtering
        health_check = HealthCheck(self.site)
        report = health_check.run(profile=profile)

        # Print report using CLI output
        from bengal.utils.cli_output import get_cli_output

        cli = get_cli_output()

        if health_config.get("verbose", False):
            cli.info(report.format_console(verbose=True))
        # Only print if there are issues
        elif report.has_errors() or report.has_warnings():
            cli.info(report.format_console(verbose=False))

        # Store report in stats
        self.stats.health_report = report

        # Fail build in strict mode if there are errors
        strict_mode = health_config.get("strict_mode", False)
        if strict_mode and report.has_errors():
            raise Exception(
                f"Build failed health checks: {report.error_count} error(s) found. "
                "Review output or disable strict_mode."
            )
