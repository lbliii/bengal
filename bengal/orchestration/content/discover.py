"""Content discovery entry points for ContentOrchestrator.

``discover`` and ``discover_content`` remain methods on the facade; this
module holds their implementations so the package stays under the peel cap.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.cache.build_cache import BuildCache
    from bengal.cache.page_discovery_cache import PageDiscoveryCache
    from bengal.orchestration.build_context import BuildContext

logger = get_logger("bengal.orchestration.content")


def _strict_missing_content_dir(orchestrator: Any) -> bool:
    """Return whether missing content should fail discovery."""
    config = orchestrator.site.config

    if isinstance(config, dict):
        build_config = config.get("build", {})
        if isinstance(build_config, dict) and build_config.get("strict_mode", False):
            return True
        return bool(config.get("strict_mode", False))

    build_config = getattr(config, "build", None)
    if build_config is not None and getattr(build_config, "strict_mode", False):
        return True

    return bool(getattr(config, "strict_mode", False))


def discover(
    orchestrator: Any,
    incremental: bool = False,
    cache: PageDiscoveryCache | None = None,
    build_context: BuildContext | None = None,
    build_cache: BuildCache | None = None,
) -> None:
    """
    Discover all content and assets.

    Main entry point called during build.

    Args:
        incremental: Whether this is an incremental build (enables lazy loading)
        cache: PagePageDiscoveryCache instance (required if incremental=True)
        build_context: Optional BuildContext for caching content during discovery.
                      When provided, raw file content is cached for later use by
                      validators, eliminating redundant disk I/O during health checks.
        build_cache: Optional BuildCache for registering autodoc dependencies.
                    When provided, enables selective autodoc rebuilds.
    """
    orchestrator.discover_content(
        incremental=incremental,
        cache=cache,
        build_context=build_context,
        build_cache=build_cache,
    )
    orchestrator.discover_assets()


def discover_content(
    orchestrator: Any,
    content_dir: Path | None = None,
    incremental: bool = False,
    cache: PageDiscoveryCache | None = None,
    build_context: BuildContext | None = None,
    build_cache: BuildCache | None = None,
    warn_missing: bool = False,
) -> None:
    """
    Discover all content (pages, sections) in the content directory.

    Supports cache-based page reconstruction for incremental builds.
    When build_context is provided, raw file content is cached for later
    use by validators (build-integrated validation).

    Args:
        content_dir: Content directory path (defaults to root_path/content)
        incremental: Whether this is an incremental build (enables lazy loading)
        cache: PagePageDiscoveryCache instance (required if incremental=True)
        build_context: Optional BuildContext for caching content during discovery.
                      When provided, raw file content is cached for later use by
                      validators, eliminating redundant disk I/O during health checks.
        build_cache: Optional BuildCache for registering autodoc dependencies.
                    When provided, enables selective autodoc rebuilds.
    """
    if content_dir is None:
        content_dir = orchestrator.site.root_path / "content"

    # Ensure absolute path - relative paths break URL computation silently
    if not content_dir.is_absolute():
        original_path = str(content_dir)
        content_dir = content_dir.resolve()
        logger.debug(
            "content_dir_resolved_to_absolute",
            original=original_path,
            resolved=str(content_dir),
        )

    if not content_dir.exists():
        from bengal.errors import BengalConfigError, ErrorCode

        if orchestrator._strict_missing_content_dir():
            raise BengalConfigError(
                f"Content directory not found: {content_dir}\n"
                f"Strict mode is enabled — missing content directory is an error.",
                code=ErrorCode.C003,
                suggestion=f"Create the directory at '{content_dir}', or check "
                f"'build.content_dir' in your config",
            )

        logger.warning(
            "content_dir_not_found",
            path=str(content_dir),
            error_code=ErrorCode.D001.value,
            suggestion="Run 'bengal init' to create site structure, or check path spelling",
        )
        emit_diagnostic(
            orchestrator.site, "warning", "content_dir_not_found", path=str(content_dir)
        )
        if warn_missing:
            warnings.warn(
                f"Content directory not found: {content_dir} — "
                f"site will have zero pages. Check 'build.content_dir' in your config.",
                stacklevel=2,
            )
        return

    logger.debug(
        "discovering_content",
        path=str(content_dir),
        incremental=incremental,
        use_cache=incremental and cache is not None,
    )

    import time

    from bengal.collections import load_collections
    from bengal.content.discovery.content_discovery import ContentDiscovery

    breakdown_ms: dict[str, float] = {}
    overall_start = time.perf_counter()

    # Load collection schemas from project root (if collections.py exists)
    t0 = time.perf_counter()
    collections = load_collections(orchestrator.site.root_path)
    breakdown_ms["collections"] = (time.perf_counter() - t0) * 1000

    # Fetch remote content sources if any collections have loaders
    t0 = time.perf_counter()
    orchestrator._fetch_remote_sources(collections, content_dir)
    breakdown_ms["remote_sources"] = (time.perf_counter() - t0) * 1000

    # Check if strict validation is enabled
    build_config = (
        orchestrator.site.config.get("build", {})
        if isinstance(orchestrator.site.config, dict)
        else {}
    )
    strict_validation = build_config.get("strict_collections", False)

    t0 = time.perf_counter()
    discovery = ContentDiscovery(
        content_dir,
        site=orchestrator.site,
        collections=collections,
        strict_validation=strict_validation,
        build_context=build_context,
    )
    breakdown_ms["content_discovery_init"] = (time.perf_counter() - t0) * 1000

    # Use lazy loading if incremental build with cache
    use_cache = incremental and cache is not None
    t0 = time.perf_counter()
    orchestrator.site.sections, orchestrator.site.pages = discovery.discover(
        use_cache=use_cache, cache=cache, build_cache=build_cache
    )
    breakdown_ms["content_discovery"] = (time.perf_counter() - t0) * 1000

    # Note: Autodoc synthetic pages disabled - using traditional Markdown generation

    # Track how many pages were reconstructed from cache (for logging)
    cache_count = sum(1 for p in orchestrator.site.pages if getattr(p, "_from_cache", False))

    logger.debug(
        "raw_content_discovered",
        pages=len(orchestrator.site.pages),
        sections=len(orchestrator.site.sections),
        from_cache=cache_count,
        full_pages=len(orchestrator.site.pages) - cache_count,
    )

    # Integrate virtual autodoc pages if enabled
    # Note: Autodoc pages are NOT rendered during discovery. HTML rendering is
    # deferred to the rendering phase (after menus are built) to ensure full
    # template context (including navigation) is available.
    # Pass build_cache (not page discovery cache) for autodoc dependency registration
    t0 = time.perf_counter()
    autodoc_pages, autodoc_sections = orchestrator._discover_autodoc_content(
        cache=cache, build_cache=build_cache
    )
    breakdown_ms["autodoc"] = (time.perf_counter() - t0) * 1000
    if autodoc_pages or autodoc_sections:
        orchestrator.site.pages.extend(autodoc_pages)
        orchestrator.site.sections.extend(autodoc_sections)
        logger.info(
            "autodoc_virtual_pages_integrated",
            pages=len(autodoc_pages),
            sections=len(autodoc_sections),
        )

    # Detect features for CSS optimization (mermaid, data_tables, etc.)
    # This populates site.features_detected which CSSOptimizer uses to include
    # only necessary CSS files. Runs efficiently O(n) over all pages.
    # See: plan/drafted/rfc-css-tree-shaking.md
    t0 = time.perf_counter()
    orchestrator._detect_features(build_cache=build_cache)
    breakdown_ms["feature_detection"] = (time.perf_counter() - t0) * 1000
    logger.debug(
        "features_detected",
        features=sorted(orchestrator.site.features_detected),
        count=len(orchestrator.site.features_detected),
    )

    # Build section registry for path-based lookups (MUST come before _setup_page_references)
    # This enables O(1) section lookups via the legacy page section reference.
    t0 = time.perf_counter()
    orchestrator.site.register_sections()
    breakdown_ms["register_sections"] = (time.perf_counter() - t0) * 1000
    logger.debug("section_registry_built")

    # Set up page references for navigation
    t0 = time.perf_counter()
    orchestrator._setup_page_references()
    breakdown_ms["setup_page_references"] = (time.perf_counter() - t0) * 1000
    logger.debug("page_references_setup")

    t0 = time.perf_counter()
    orchestrator._validate_page_section_references()
    breakdown_ms["validate_page_section_references"] = (time.perf_counter() - t0) * 1000

    # Apply cascading frontmatter from sections to pages
    t0 = time.perf_counter()
    orchestrator._apply_cascades()
    breakdown_ms["cascades"] = (time.perf_counter() - t0) * 1000
    logger.debug("cascades_applied")

    # Set output paths for all pages immediately after discovery
    # This ensures page.href and page._path work correctly before rendering
    t0 = time.perf_counter()
    orchestrator._set_output_paths()
    breakdown_ms["output_paths"] = (time.perf_counter() - t0) * 1000
    logger.debug("output_paths_set")

    # Build cross-reference index for O(1) lookups
    t0 = time.perf_counter()
    orchestrator._build_xref_index()
    breakdown_ms["xref_index"] = (time.perf_counter() - t0) * 1000
    logger.debug(
        "xref_index_built", index_size=len(orchestrator.site.xref_index.get("by_path", {}))
    )

    breakdown_ms["total"] = (time.perf_counter() - overall_start) * 1000
    # Store on BuildState (fresh each build) for consumption by phase_discovery.
    _bs = orchestrator.site.build_state
    if _bs is not None:
        _bs.discovery_timing_ms = breakdown_ms
    else:
        orchestrator.site._discovery_breakdown_ms = breakdown_ms
