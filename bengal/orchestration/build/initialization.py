"""
Initialization phases for build orchestration.

Phases 1-5: Font processing, template validation, content discovery, cache metadata, config check, incremental filtering.
"""

from __future__ import annotations

import time
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from bengal.core.section import resolve_page_section_path
from bengal.orchestration.build.results import ConfigCheckResult, FilterResult

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.cache.build_cache import BuildCache
    from bengal.orchestration.build import BuildOrchestrator
    from bengal.output import CLIOutput
    from bengal.utils.build_context import BuildContext


def phase_fonts(orchestrator: BuildOrchestrator, cli: CLIOutput) -> None:
    """
    Phase 1: Font Processing.

    Downloads Google Fonts and generates CSS if configured in site config.
    This runs before asset discovery so font CSS is available.

    Args:
        orchestrator: Build orchestrator instance
        cli: CLI output for user messages

    Side effects:
        - Creates assets/ directory if needed
        - Downloads font files to assets/fonts/
        - Generates font CSS file
        - Updates orchestrator.stats.fonts_time_ms
    """
    if "fonts" not in orchestrator.site.config:
        return

    with orchestrator.logger.phase("fonts"):
        fonts_start = time.time()
        try:
            import shutil

            from bengal.fonts import FontHelper

            # Ensure assets directory exists (source)
            assets_dir = orchestrator.site.root_path / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)

            # Process fonts (download + generate CSS to source assets)
            font_helper = FontHelper(orchestrator.site.config["fonts"])
            css_path = font_helper.process(assets_dir)

            # Also copy fonts.css to output directory so it's immediately available
            # (fonts/ directory is copied by asset pipeline, but fonts.css at root needs explicit copy)
            if css_path and css_path.exists():
                output_assets = orchestrator.site.output_dir / "assets"
                output_assets.mkdir(parents=True, exist_ok=True)
                output_css = output_assets / "fonts.css"
                # Only copy if destination doesn't exist or source is newer
                # (prevents triggering file watcher when nothing changed)
                if not output_css.exists() or css_path.stat().st_mtime > output_css.stat().st_mtime:
                    shutil.copy2(css_path, output_css)

            orchestrator.stats.fonts_time_ms = (time.time() - fonts_start) * 1000
            orchestrator.logger.info("fonts_complete")
        except Exception as e:
            cli.warning(f"Font processing failed: {e}")
            cli.info("   Continuing build without custom fonts...")
            orchestrator.logger.warning("fonts_failed", error=str(e))


def phase_template_validation(
    orchestrator: BuildOrchestrator,
    cli: CLIOutput,
    strict: bool = False,
) -> list[Any]:
    """
    Phase 1.5: Template Validation (optional).

    Proactively validates all template syntax before rendering begins.
    This catches template errors early, providing faster feedback.

    Only runs if `[build] validate_templates = true` in site config.

    Args:
        orchestrator: Build orchestrator instance
        cli: CLI output for user messages
        strict: Whether to fail build on template errors

    Returns:
        List of TemplateRenderError objects found during validation.
        Empty list if validation is disabled or all templates are valid.

    Side effects:
        - Creates TemplateEngine for validation
        - Adds errors to orchestrator.stats.template_errors
        - May fail build if strict mode and errors found
    """
    # Check if template validation is enabled
    validate_templates = orchestrator.site.config.get("validate_templates", False)
    if not validate_templates:
        orchestrator.logger.debug("template_validation_skipped", reason="disabled in config")
        return []

    from bengal.errors import BengalRenderingError

    with orchestrator.logger.phase("template_validation"):
        validation_start = time.time()

        try:
            from bengal.rendering.engines import create_engine

            # Create template engine for validation
            engine = create_engine(orchestrator.site)

            # Validate all templates
            errors = engine.validate_templates()

            validation_time_ms = (time.time() - validation_start) * 1000

            # Add errors to build stats
            for error in errors:
                orchestrator.stats.add_template_error(error)

            if errors:
                # Report errors
                cli.warning(f"Found {len(errors)} template syntax error(s)")
                for error in errors:
                    template_name = getattr(error.template_context, "template_name", "unknown")
                    line = getattr(error.template_context, "line_number", "?")
                    cli.detail(f"  • {template_name}:{line} - {error.message[:80]}")

                orchestrator.logger.warning(
                    "template_validation_errors",
                    error_count=len(errors),
                    duration_ms=validation_time_ms,
                )

                # In strict mode, fail the build
                if strict:
                    from bengal.errors import BengalRenderingError

                    raise BengalRenderingError(
                        f"Template validation failed with {len(errors)} error(s). "
                        "Fix template syntax errors or disable strict mode.",
                        suggestion="Review template errors above and fix syntax issues, or set build.strict_mode=false",
                    )
            else:
                cli.phase("Templates", duration_ms=validation_time_ms, details="validated")
                orchestrator.logger.info(
                    "template_validation_complete",
                    error_count=0,
                    duration_ms=validation_time_ms,
                )

            return errors

        except (RuntimeError, BengalRenderingError):
            # Re-raise strict mode failures
            raise
        except Exception as e:
            # Log other errors but don't fail build
            cli.warning(f"Template validation failed: {e}")
            cli.info("   Continuing build without template validation...")
            orchestrator.logger.warning(
                "template_validation_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return []


def phase_discovery(
    orchestrator: BuildOrchestrator,
    cli: CLIOutput,
    incremental: bool,
    build_context: BuildContext | None = None,
    build_cache: BuildCache | None = None,
) -> None:
    """
    Phase 2: Content Discovery.

    Discovers all content files in the content/ directory and creates Page objects.
    For incremental builds, uses cached page metadata for lazy loading.

    When build_context is provided, raw file content is cached during discovery
    for later use by validators (build-integrated validation), eliminating
    ~4 seconds of redundant disk I/O during health checks.

    Args:
        orchestrator: Build orchestrator instance
        cli: CLI output for user messages
        incremental: Whether this is an incremental build
        build_context: Optional BuildContext for caching content during discovery.
                      When provided, enables build-integrated validation optimization.
        build_cache: Optional BuildCache for registering autodoc dependencies.
                    When provided, enables selective autodoc rebuilds.

    Side effects:
        - Populates orchestrator.site.pages with discovered pages
        - Populates orchestrator.site.sections with discovered sections
        - Updates orchestrator.stats.discovery_time_ms
        - Caches file content in build_context (if provided)
        - Registers autodoc dependencies in build_cache (if provided)
    """
    content_dir = orchestrator.site.root_path / "content"
    with orchestrator.logger.phase("discovery", content_dir=str(content_dir)):
        discovery_start = time.time()
        content_ms: float | None = None
        assets_ms: float | None = None

        # Load cache for incremental builds (lazy loading)
        page_discovery_cache = None
        if incremental:
            try:
                from bengal.cache.page_discovery_cache import PageDiscoveryCache

                page_discovery_cache = PageDiscoveryCache(orchestrator.site.paths.page_cache)
            except Exception as e:
                orchestrator.logger.debug(
                    "page_discovery_cache_load_failed_for_lazy_loading",
                    error=str(e),
                )
                # Continue without cache - will do full discovery

        # Load cached URL claims for incremental build safety
        # Pre-populate registry with claims from pages not being rebuilt
        if incremental and build_cache and hasattr(build_cache, "url_claims"):
            try:
                if orchestrator.site.url_registry and build_cache.url_claims:
                    orchestrator.site.url_registry.load_from_dict(build_cache.url_claims)
                    orchestrator.logger.debug(
                        "url_claims_loaded_from_cache",
                        claim_count=len(build_cache.url_claims),
                    )
            except Exception as e:
                orchestrator.logger.debug(
                    "url_claims_cache_load_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    action="continuing_without_cached_claims",
                )

        # Discover content and assets.
        # We time these separately so the Discovery phase can report a useful breakdown.
        content_start = time.time()
        orchestrator.content.discover_content(
            incremental=incremental,
            cache=page_discovery_cache,
            build_context=build_context,
            build_cache=build_cache,
        )
        content_ms = (time.time() - content_start) * 1000

        assets_start = time.time()
        orchestrator.content.discover_assets()
        assets_ms = (time.time() - assets_start) * 1000

        # Log content cache stats if enabled
        if build_context and build_context.has_cached_content:
            orchestrator.logger.debug(
                "content_cache_populated",
                cached_pages=build_context.content_cache_size,
            )

        orchestrator.stats.discovery_time_ms = (time.time() - discovery_start) * 1000

        # Phase details (shown only when CLI profile enables details).
        details: str | None = None
        if content_ms is not None and assets_ms is not None:
            details = f"content {int(content_ms)}ms, assets {int(assets_ms)}ms"
            # If we have a richer breakdown from content discovery, include the top 2 items.
            breakdown = getattr(orchestrator.site, "_discovery_breakdown_ms", None)
            if isinstance(breakdown, dict) and content_ms >= 500:
                candidates = [
                    (k, v)
                    for k, v in breakdown.items()
                    if isinstance(v, (int, float)) and k not in {"total"}
                ]
                candidates.sort(key=lambda kv: kv[1], reverse=True)
                top = [(k, int(v)) for k, v in candidates[:2] if v >= 50]
                if top:
                    details += "; " + ", ".join(f"{k} {v}ms" for k, v in top)

        # Show phase completion
        cli.phase("Discovery", duration_ms=orchestrator.stats.discovery_time_ms, details=details)

        orchestrator.logger.info(
            "discovery_complete",
            pages=len(orchestrator.site.pages),
            sections=len(orchestrator.site.sections),
        )


def phase_cache_metadata(orchestrator: BuildOrchestrator) -> None:
    """
    Phase 3: Cache Discovery Metadata.

    Saves page discovery metadata to cache for future incremental builds.
    This enables lazy loading of unchanged pages.

    Side effects:
        - Normalizes page core paths to relative
        - Persists page metadata to .bengal/page_metadata.json
    """
    with orchestrator.logger.phase("cache_discovery_metadata", enabled=True):
        try:
            from bengal.cache.page_discovery_cache import PageDiscoveryCache

            page_cache = PageDiscoveryCache(orchestrator.site.paths.page_cache)

            # Extract metadata from discovered pages (AFTER cascades applied)
            for page in orchestrator.site.pages:
                # Normalize paths to relative before caching (prevents absolute path leakage)
                page.normalize_core_paths()
                # THE BIG PAYOFF: Just use page.core directly! (PageMetadata = PageCore)
                page_cache.add_metadata(page.core)

            # Persist cache to disk
            page_cache.save_to_disk()

            orchestrator.logger.info(
                "page_discovery_cache_saved",
                entries=len(page_cache.pages),
                path=str(page_cache.cache_path),
            )
        except Exception as e:
            orchestrator.logger.warning(
                "page_discovery_cache_save_failed",
                error=str(e),
            )


def phase_config_check(
    orchestrator: BuildOrchestrator, cli: CLIOutput, cache: BuildCache, incremental: bool
) -> ConfigCheckResult:
    """
    Phase 4: Config Check and Cleanup.

    Checks if config file changed (forces full rebuild) and cleans up deleted files.

    Args:
        orchestrator: Build orchestrator instance
        cli: CLI output for user messages
        cache: Build cache
        incremental: Whether this is an incremental build

    Returns:
        ConfigCheckResult with incremental flag (may be False if config changed)
        and config_changed flag.

    Side effects:
        - Cleans up output files for deleted source files
        - Clears cache if config changed
    """
    # Check if config changed (forces full rebuild)
    # Note: We check this even on full builds to populate the cache
    config_changed = orchestrator.incremental.check_config_changed()

    if incremental and config_changed:
        # Determine if this is first build or actual change
        config_files = [
            orchestrator.site.root_path / "bengal.toml",
            orchestrator.site.root_path / "bengal.yaml",
            orchestrator.site.root_path / "bengal.yml",
        ]
        config_file = next((f for f in config_files if f.exists()), None)

        # Check if config was previously cached
        if config_file and str(config_file) not in cache.file_fingerprints:
            cli.info("  Config not in cache - performing full rebuild")
            cli.detail("(This is normal for the first incremental build)", indent=1)
        else:
            cli.info("  Config file modified - performing full rebuild")
            if config_file:
                cli.detail(f"Changed: {config_file.name}", indent=1)

        incremental = False
        # Don't clear cache yet - we need it for cleanup!

    # Clean up deleted files (ALWAYS, even on full builds)
    # This ensures output stays in sync with source files
    # Do this BEFORE clearing cache so we have the output_sources map
    if cache and hasattr(orchestrator.incremental, "_cleanup_deleted_files"):
        orchestrator.incremental._cleanup_deleted_files()
        # Save cache immediately so deletions are persisted
        cache.save(orchestrator.site.paths.build_cache)

    # Now clear cache if config changed
    if not incremental and config_changed:
        cache.clear()
        # Re-track config file hash so it's present after full build
        with suppress(Exception):
            orchestrator.incremental.check_config_changed()

    return ConfigCheckResult(incremental=incremental, config_changed=config_changed)


def phase_incremental_filter(
    orchestrator: BuildOrchestrator,
    cli: CLIOutput,
    cache: BuildCache,
    incremental: bool,
    verbose: bool,
    build_start: float,
    changed_sources: set[Path] | None = None,
    nav_changed_sources: set[Path] | None = None,
) -> FilterResult | None:
    """
    Phase 5: Incremental Filtering.

    Determines which pages and assets need to be built based on what changed.
    This is the KEY optimization: filter BEFORE expensive operations.

    Args:
        orchestrator: Build orchestrator instance
        cli: CLI output for user messages
        cache: Build cache
        incremental: Whether this is an incremental build
        verbose: Whether to show verbose output
        build_start: Build start time for duration calculation

    Returns:
        FilterResult with pages_to_build, assets_to_process, affected_tags,
        changed_page_paths, and affected_sections.
        Returns None if build should be skipped (no changes detected)

    Side effects:
        - Updates orchestrator.stats with cache hit/miss statistics
        - May return early if no changes detected
    """
    with orchestrator.logger.phase("incremental_filtering", enabled=incremental):
        pages_to_build = orchestrator.site.pages
        assets_to_process = orchestrator.site.assets
        affected_tags = set()
        changed_page_paths = set()
        affected_sections = None  # Track for selective section finalization

        if incremental:
            # Find what changed BEFORE generating taxonomies/menus
            pages_to_build, assets_to_process, change_summary_obj = (
                orchestrator.incremental.find_work_early(
                    verbose=verbose,
                    forced_changed_sources=changed_sources,
                    nav_changed_sources=nav_changed_sources,
                )
            )
            # Convert ChangeSummary to dict
            change_summary = change_summary_obj.to_dict()

            # Track which pages changed (for taxonomy updates)
            changed_page_paths = {
                p.source_path for p in pages_to_build if not p.metadata.get("_generated")
            }

            # Determine affected sections and tags from changed pages
            affected_sections = set()
            for page in pages_to_build:
                if not page.metadata.get("_generated"):
                    # Safely check if page has a section (may be None for root-level pages)
                    # Use shared helper to normalize section path
                    section_path = resolve_page_section_path(page)
                    if section_path:
                        affected_sections.add(section_path)
                    if page.tags:
                        for tag in page.tags:
                            affected_tags.add(tag.lower().replace(" ", "-"))

            # Track cache statistics
            total_pages = len(orchestrator.site.pages)
            pages_rebuilt = len(pages_to_build)
            pages_cached = total_pages - pages_rebuilt

            orchestrator.stats.cache_hits = pages_cached
            orchestrator.stats.cache_misses = pages_rebuilt

            # Estimate time saved (approximate: 80% of rendering time for cached pages)
            if pages_rebuilt > 0 and total_pages > 0:
                avg_time_per_page = (
                    (orchestrator.stats.rendering_time_ms / total_pages)
                    if hasattr(orchestrator.stats, "rendering_time_ms")
                    else 50
                )
                orchestrator.stats.time_saved_ms = pages_cached * avg_time_per_page * 0.8

            orchestrator.logger.info(
                "incremental_work_identified",
                pages_to_build=len(pages_to_build),
                assets_to_process=len(assets_to_process),
                skipped_pages=len(orchestrator.site.pages) - len(pages_to_build),
                cache_hit_rate=f"{(pages_cached / total_pages * 100) if total_pages > 0 else 0:.1f}%",
            )

            # Check if we need to regenerate taxonomy pages
            needs_taxonomy_regen = bool(cache.get_all_tags())

            if not pages_to_build and not assets_to_process and not needs_taxonomy_regen:
                cli.success("✓ No changes detected - build skipped")
                cli.detail(
                    f"Cached: {len(orchestrator.site.pages)} pages, {len(orchestrator.site.assets)} assets",
                    indent=1,
                )
                orchestrator.logger.info(
                    "no_changes_detected",
                    cached_pages=len(orchestrator.site.pages),
                    cached_assets=len(orchestrator.site.assets),
                )
                orchestrator.stats.skipped = True
                orchestrator.stats.build_time_ms = (time.time() - build_start) * 1000
                return None  # Signal early exit

            # More informative incremental build message
            pages_msg = f"{len(pages_to_build)} page{'s' if len(pages_to_build) != 1 else ''}"
            assets_msg = (
                f"{len(assets_to_process)} asset{'s' if len(assets_to_process) != 1 else ''}"
            )
            skipped_msg = f"{len(orchestrator.site.pages) - len(pages_to_build)} cached"

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

        return FilterResult(
            pages_to_build=pages_to_build,
            assets_to_process=assets_to_process,
            affected_tags=affected_tags,
            changed_page_paths=changed_page_paths,
            affected_sections=affected_sections,
        )
