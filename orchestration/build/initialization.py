"""
Initialization phases for build orchestration.

Phases 1-5: Font processing, content discovery, cache metadata, config check, incremental filtering.
"""

from __future__ import annotations

import time
from contextlib import suppress
from typing import TYPE_CHECKING

from bengal.utils.sections import resolve_page_section_path

if TYPE_CHECKING:
    from bengal.orchestration.build import BuildOrchestrator


def phase_fonts(orchestrator: BuildOrchestrator, cli) -> None:
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
            from bengal.fonts import FontHelper

            # Ensure assets directory exists
            assets_dir = orchestrator.site.root_path / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)

            # Process fonts (download + generate CSS)
            font_helper = FontHelper(orchestrator.site.config["fonts"])
            font_helper.process(assets_dir)

            orchestrator.stats.fonts_time_ms = (time.time() - fonts_start) * 1000
            orchestrator.logger.info("fonts_complete")
        except Exception as e:
            cli.warning(f"Font processing failed: {e}")
            cli.info("   Continuing build without custom fonts...")
            orchestrator.logger.warning("fonts_failed", error=str(e))


def phase_discovery(orchestrator: BuildOrchestrator, cli, incremental: bool) -> None:
    """
    Phase 2: Content Discovery.

    Discovers all content files in the content/ directory and creates Page objects.
    For incremental builds, uses cached page metadata for lazy loading.

    Args:
        orchestrator: Build orchestrator instance
        cli: CLI output for user messages
        incremental: Whether this is an incremental build

    Side effects:
        - Populates orchestrator.site.pages with discovered pages
        - Populates orchestrator.site.sections with discovered sections
        - Updates orchestrator.stats.discovery_time_ms
    """
    content_dir = orchestrator.site.root_path / "content"
    with orchestrator.logger.phase("discovery", content_dir=str(content_dir)):
        discovery_start = time.time()

        # Load cache for incremental builds (lazy loading)
        page_discovery_cache = None
        if incremental:
            try:
                from bengal.cache.page_discovery_cache import PageDiscoveryCache

                page_discovery_cache = PageDiscoveryCache(
                    orchestrator.site.root_path / ".bengal" / "page_metadata.json"
                )
            except Exception as e:
                orchestrator.logger.debug(
                    "page_discovery_cache_load_failed_for_lazy_loading",
                    error=str(e),
                )
                # Continue without cache - will do full discovery

        # Discover with optional lazy loading
        orchestrator.content.discover(incremental=incremental, cache=page_discovery_cache)

        orchestrator.stats.discovery_time_ms = (time.time() - discovery_start) * 1000

        # Show phase completion
        cli.phase("Discovery", duration_ms=orchestrator.stats.discovery_time_ms)

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

            page_cache = PageDiscoveryCache(
                orchestrator.site.root_path / ".bengal" / "page_metadata.json"
            )

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
    orchestrator: BuildOrchestrator, cli, cache, incremental: bool
) -> tuple[bool, bool]:
    """
    Phase 4: Config Check and Cleanup.

    Checks if config file changed (forces full rebuild) and cleans up deleted files.

    Args:
        orchestrator: Build orchestrator instance
        cli: CLI output for user messages
        cache: Build cache
        incremental: Whether this is an incremental build

    Returns:
        Tuple of (updated_incremental, config_changed) - incremental may be
        set to False if config changed

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
        if config_file and str(config_file) not in cache.file_hashes:
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
        cache_dir = orchestrator.site.root_path / ".bengal"
        cache_path = cache_dir / "cache.json"
        cache.save(cache_path)

    # Now clear cache if config changed
    if not incremental and config_changed:
        cache.clear()
        # Re-track config file hash so it's present after full build
        with suppress(Exception):
            orchestrator.incremental.check_config_changed()

    return incremental, config_changed


def phase_incremental_filter(
    orchestrator: BuildOrchestrator,
    cli,
    cache,
    incremental: bool,
    verbose: bool,
    build_start: float,
) -> tuple[list, list, set, set, set | None] | None:
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
        Tuple of (pages_to_build, assets_to_process, affected_tags,
                 changed_page_paths, affected_sections)
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
            pages_to_build, assets_to_process, change_summary = (
                orchestrator.incremental.find_work_early(verbose=verbose)
            )

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

        return (
            pages_to_build,
            assets_to_process,
            affected_tags,
            changed_page_paths,
            affected_sections,
        )
