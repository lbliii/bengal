"""
Initialization phases for build orchestration.

Phases 1-5: Font processing, template validation, content discovery, cache metadata, config check, incremental filtering.
"""

from __future__ import annotations

import time
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from bengal.orchestration.build.results import (
    ConfigCheckResult,
)

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.cache.build_cache import BuildCache
    from bengal.orchestration.build import BuildOrchestrator
    from bengal.orchestration.build_context import BuildContext
    from bengal.output import CLIOutput


def _check_autodoc_output_missing(orchestrator: BuildOrchestrator, cache: BuildCache) -> bool:
    """
    Check if autodoc output directories are missing.

    This handles warm CI builds where the .bengal cache is restored but
    site/public/api/ (or other autodoc output) was not cached and is empty.
    The cache might think nothing changed (source files unchanged), but the
    virtual pages need to be regenerated.

    Args:
        orchestrator: Build orchestrator instance
        cache: BuildCache for checking autodoc dependencies

    Returns:
        True if autodoc output is missing and needs regeneration

    """
    # Skip if no autodoc dependencies tracked (nothing to check)
    if not hasattr(cache, "autodoc_tracker") or not cache.autodoc_tracker.autodoc_dependencies:
        return False

    # Get autodoc config
    autodoc_config = orchestrator.site.config.get("autodoc", {})
    if not autodoc_config:
        return False

    output_dir = orchestrator.site.output_dir
    prefixes_to_check: list[str] = []

    # Collect enabled autodoc prefixes
    if autodoc_config.get("python", {}).get("enabled", False):
        python_prefix = autodoc_config.get("python", {}).get("output_prefix", "")
        if not python_prefix:
            # Auto-derive from source_dirs (same logic as autodoc validator)
            source_dirs = autodoc_config.get("python", {}).get("source_dirs", [])
            if source_dirs:
                from pathlib import Path as PathLib

                pkg_name = PathLib(source_dirs[0]).name
                python_prefix = f"api/{pkg_name}"
            else:
                python_prefix = "api"
        prefixes_to_check.append(python_prefix)

    if autodoc_config.get("cli", {}).get("enabled", False):
        cli_prefix = autodoc_config.get("cli", {}).get("output_prefix", "cli")
        prefixes_to_check.append(cli_prefix)

    if autodoc_config.get("openapi", {}).get("enabled", False):
        openapi_prefix = autodoc_config.get("openapi", {}).get("output_prefix", "")
        if openapi_prefix:
            prefixes_to_check.append(openapi_prefix)

    if not prefixes_to_check:
        return False

    # Check if any autodoc output directory is missing or empty
    for prefix in prefixes_to_check:
        prefix_dir = output_dir / prefix
        if not prefix_dir.exists():
            # Directory doesn't exist - autodoc output is missing
            return True
        # Check for at least one index.html (indicates pages were generated)
        if not list(prefix_dir.rglob("index.html")):
            return True

    return False


def _check_special_pages_missing(orchestrator: BuildOrchestrator) -> bool:
    """
    Check if special pages (graph, search) are missing from output.

    This handles warm CI builds where the .bengal cache is restored but
    special pages (graph/, search/) were not cached and are missing.
    The cache thinks nothing changed, but special pages need to be generated.

    Only checks when main output exists (index.html) - if output is completely
    missing, other checks already handle forcing a full rebuild.

    Args:
        orchestrator: Build orchestrator instance

    Returns:
        True if any enabled special page is missing from output

    """
    from bengal.config.defaults import get_feature_config

    output_dir = orchestrator.site.output_dir

    # Skip this check if output doesn't exist yet - the main output_html_missing
    # check will handle triggering a full rebuild
    if not output_dir.exists() or not (output_dir / "index.html").exists():
        return False

    # Check graph page (enabled by default)
    graph_cfg = get_feature_config(orchestrator.site.config, "graph")
    if graph_cfg.get("enabled", True):
        graph_path = graph_cfg.get("path", "/graph/") or "/graph/"
        graph_dir = output_dir / graph_path.strip("/")
        if not (graph_dir / "index.html").exists():
            return True

    # Check search page (enabled by default)
    search_cfg = get_feature_config(orchestrator.site.config, "search")
    if search_cfg.get("enabled", True):
        search_path = search_cfg.get("path", "/search/") or "/search/"
        search_dir = output_dir / search_path.strip("/")
        if not (search_dir / "index.html").exists():
            return True

    return False


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

    # Optimization: Skip font processing if only content files changed and fonts exist
    # (prevents redundant FontHelper.process calls during hot reload)
    options = getattr(orchestrator, "_last_build_options", None)
    if options and options.incremental and options.changed_sources:
        # Check if any changed source is NOT a content file
        content_extensions = {".md", ".markdown", ".html", ".txt", ".ipynb"}
        non_content_changes = [
            s for s in options.changed_sources if s.suffix.lower() not in content_extensions
        ]

        fonts_css = orchestrator.site.root_path / "assets" / "fonts.css"
        if not non_content_changes and fonts_css.exists():
            orchestrator.logger.debug("fonts_skipped", reason="only_content_changed")
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
                    from bengal.errors import BengalRenderingError, ErrorCode

                    raise BengalRenderingError(
                        f"Template validation failed with {len(errors)} error(s). "
                        "Fix template syntax errors or disable strict mode.",
                        code=ErrorCode.R002,
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
    changed_sources: set[Path] | None = None,
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
        changed_sources: Optional set of changed file paths from the file watcher.
                        When set and all paths are content files (.md/.markdown),
                        expensive phases like autodoc scanning are skipped.
                        (RFC: reactive-rebuild-architecture Phase 1a)

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
            changed_sources=changed_sources,
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
            # Prefer BuildState (fresh each build), fall back to Site field
            _bs = getattr(orchestrator.site, "build_state", None)
            breakdown = (
                getattr(_bs, "discovery_timing_ms", None) if _bs is not None
                else getattr(orchestrator.site, "_discovery_breakdown_ms", None)
            )
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
