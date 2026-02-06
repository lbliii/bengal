"""
Provenance-based incremental filtering for builds.

Replaces the old IncrementalFilterEngine with content-addressed provenance.
Provides 30x faster incremental builds with correct invalidation.

Usage in build orchestrator:
    from bengal.orchestration.build.provenance_filter import phase_incremental_filter_provenance

    # Replace phase_incremental_filter call with:
    filter_result = phase_incremental_filter_provenance(orchestrator, cli, incremental, ...)

Dependency Gap Fixes (RFC: rfc-incremental-build-dependency-gaps):
    - Data file changes now trigger dependent page rebuilds
    - Taxonomy term pages rebuild when member post metadata changes
    - Template changes now trigger dependent page rebuilds
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.build.provenance import ProvenanceCache, ProvenanceFilter
from bengal.build.provenance.filter import ProvenanceFilterResult
from bengal.orchestration.build.results import (
    FilterResult,
    IncrementalDecision,
    RebuildReasonCode,
    SkipReasonCode,
)
from bengal.utils.observability.logger import get_logger
from bengal.utils.primitives.hashing import hash_file

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.cache.build_cache import BuildCache
    from bengal.core.page import Page
    from bengal.orchestration.build import BuildOrchestrator
    from bengal.output import CLIOutput
    from bengal.protocols import SiteLike


def _detect_changed_data_files(
    cache: BuildCache,
    site: SiteLike,
) -> set[Path]:
    """
    Detect data files that have changed since last build.

    Compares current data file hashes against stored fingerprints.

    Args:
        cache: BuildCache with stored fingerprints
        site: Site instance to find data directory

    Returns:
        Set of changed data file paths
    """
    changed: set[Path] = set()
    data_dir = site.root_path / "data"

    if not data_dir.exists():
        return changed

    # Scan data directory for YAML/JSON files
    for ext in ("*.yaml", "*.yml", "*.json", "*.toml"):
        for data_file in data_dir.glob(f"**/{ext}"):
            file_key = str(data_file)
            stored = cache.file_fingerprints.get(file_key)

            if stored is None:
                # New data file - treat as changed
                changed.add(data_file)
                continue

            # Check if file changed (compare hash)
            try:
                current_hash = hash_file(data_file)
                if stored.get("hash") != current_hash:
                    changed.add(data_file)
            except OSError:
                # File error - treat as changed
                changed.add(data_file)

    if changed:
        logger.debug(
            "data_files_changed",
            count=len(changed),
            files=[str(f.name) for f in changed],
        )

    return changed


def _detect_changed_templates(
    cache: BuildCache,
    site: SiteLike,
) -> set[Path]:
    """
    Detect template files that have changed since last build.

    Compares current template file hashes against stored fingerprints.

    Args:
        cache: BuildCache with stored fingerprints
        site: Site instance to find templates directory

    Returns:
        Set of changed template file paths
    """
    changed: set[Path] = set()
    templates_dir = site.root_path / "templates"

    if not templates_dir.exists():
        return changed

    # Also check theme templates if theme is set
    theme_templates_dirs = []
    if hasattr(site, "theme_path") and site.theme_path:
        theme_templates = site.theme_path / "templates"
        if theme_templates.exists():
            theme_templates_dirs.append(theme_templates)

    # Scan all template directories
    for tpl_dir in [templates_dir] + theme_templates_dirs:
        for tpl_file in tpl_dir.glob("**/*.html"):
            file_key = str(tpl_file)
            stored = cache.file_fingerprints.get(file_key)

            if stored is None:
                # New template - treat as changed
                changed.add(tpl_file)
                continue

            # Check if file changed (compare hash)
            try:
                current_hash = hash_file(tpl_file)
                if stored.get("hash") != current_hash:
                    changed.add(tpl_file)
            except OSError:
                # File error - treat as changed
                changed.add(tpl_file)

    if changed:
        logger.debug(
            "templates_changed",
            count=len(changed),
            files=[str(f.name) for f in changed],
        )

    return changed


def _get_pages_for_data_file(
    cache: BuildCache,
    data_file: Path,
) -> set[Path]:
    """
    Find pages that depend on a data file.

    Queries the cache's dependency graph for pages that have recorded
    a dependency on the given data file.

    Args:
        cache: BuildCache with dependency tracking
        data_file: Path to the data file

    Returns:
        Set of page source paths that depend on this data file
    """
    dep_key = f"data:{data_file}"
    pages: set[Path] = set()

    for page_str, deps in cache.dependencies.items():
        if dep_key in deps:
            pages.add(Path(page_str))

    return pages


def _get_pages_for_template(
    cache: BuildCache,
    template_path: Path,
) -> set[Path]:
    """
    Find pages that use a template.

    Queries the cache's reverse dependency graph for pages that depend
    on the given template.

    Args:
        cache: BuildCache with reverse dependency tracking
        template_path: Path to the template file

    Returns:
        Set of page source paths that use this template
    """
    pages: set[Path] = set()
    template_key = str(template_path)

    # Check reverse dependencies
    dependents = cache.reverse_dependencies.get(template_key, set())
    for page_str in dependents:
        pages.add(Path(page_str))

    # Also check forward dependencies (for completeness)
    for page_str, deps in cache.dependencies.items():
        if template_key in deps:
            pages.add(Path(page_str))

    return pages


def _get_taxonomy_term_pages_for_member(
    cache: BuildCache,
    member_path: Path,
    site: SiteLike,
) -> set[Path]:
    """
    Find taxonomy term pages that list a member page.

    When a member page's metadata changes (title, date, summary),
    the taxonomy term pages listing it need to be rebuilt.

    Args:
        cache: BuildCache with taxonomy tracking
        member_path: Path to the member page that changed
        site: Site instance to find taxonomy term pages

    Returns:
        Set of taxonomy term page paths to rebuild
    """
    term_pages: set[Path] = set()
    member_key = str(member_path)

    # Get tags for this member page from cache
    tags = cache.page_tags.get(member_key, set())

    for tag in tags:
        # Find the virtual taxonomy term page for this tag
        # Taxonomy term pages are virtual (no source file), but we need
        # to identify them so they get rebuilt
        # The key format matches what track_taxonomy() uses
        tag_key = f"tag:{str(tag).lower().replace(' ', '-')}"
        term_page_key = f"_generated/tags/{tag_key}"

        # Add the term page path (virtual)
        # For virtual pages, we use a synthetic path
        term_pages.add(Path(term_page_key))

    return term_pages


def _expand_forced_changed(
    forced_changed: set[Path],
    cache: BuildCache,
    site: SiteLike,
    pages: list[Page],
) -> tuple[set[Path], dict[str, list[str]]]:
    """
    Expand forced_changed set to include dependency-triggered rebuilds.

    This is the core integration for RFC: rfc-incremental-build-dependency-gaps.

    Gap 1: Data file changes → dependent pages
    Gap 2: Member page changes → taxonomy term pages
    Gap 3: Template changes → dependent pages

    Args:
        forced_changed: Initial set of changed paths (from file watcher or content changes)
        cache: BuildCache with dependency tracking
        site: Site instance
        pages: List of all pages (for taxonomy lookup)

    Returns:
        Tuple of (expanded_forced_changed, reasons) where reasons maps
        page paths to lists of why they were added
    """
    expanded = set(forced_changed)
    reasons: dict[str, list[str]] = {}

    # Gap 1: Detect data file changes
    changed_data_files = _detect_changed_data_files(cache, site)
    for data_file in changed_data_files:
        affected_pages = _get_pages_for_data_file(cache, data_file)
        for page_path in affected_pages:
            if page_path not in expanded:
                expanded.add(page_path)
                reasons.setdefault(str(page_path), []).append(f"data_file:{data_file.name}")

    # Gap 3: Detect template changes
    changed_templates = _detect_changed_templates(cache, site)
    for template_path in changed_templates:
        affected_pages = _get_pages_for_template(cache, template_path)
        for page_path in affected_pages:
            if page_path not in expanded:
                expanded.add(page_path)
                reasons.setdefault(str(page_path), []).append(f"template:{template_path.name}")

    # Gap 2: For content pages that changed, find taxonomy term pages
    # Build a mapping of source paths to pages for efficient lookup
    page_by_source: dict[Path, Page] = {p.source_path: p for p in pages}

    # Check which changed pages have tags - their taxonomy term pages need rebuilding
    content_changes = [p for p in forced_changed if p.suffix == ".md"]
    for content_path in content_changes:
        term_pages = _get_taxonomy_term_pages_for_member(cache, content_path, site)
        for term_path in term_pages:
            if term_path not in expanded:
                expanded.add(term_path)
                reasons.setdefault(str(term_path), []).append(f"member_changed:{content_path.name}")

    if len(expanded) > len(forced_changed):
        logger.info(
            "dependency_triggered_rebuilds",
            original_count=len(forced_changed),
            expanded_count=len(expanded),
            data_file_triggered=len(changed_data_files),
            template_triggered=len(changed_templates),
            taxonomy_triggered=len(content_changes),
        )

    return expanded, reasons


def phase_incremental_filter_provenance(
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
    Phase 5: Incremental Filtering (Provenance-based).

    Uses content-addressed provenance tracking for correct cache invalidation.
    30x faster than the old IncrementalFilterEngine approach.

    Args:
        orchestrator: Build orchestrator instance
        cli: CLI output for user messages
        cache: Build cache (legacy, used for compatibility)
        incremental: Whether this is an incremental build
        verbose: Whether to show verbose output
        build_start: Build start time for duration calculation
        changed_sources: Paths to treat as changed (from file watcher)
        nav_changed_sources: Navigation-affecting changes

    Returns:
        FilterResult with pages_to_build, assets_to_process, etc.
        Returns None if build should be skipped (no changes detected)
    """
    with orchestrator.logger.phase("incremental_filtering_provenance", enabled=incremental):
        site = orchestrator.site

        # Initialize provenance cache
        provenance_cache = ProvenanceCache(site.root_path / ".bengal" / "provenance")
        provenance_filter = ProvenanceFilter(site, provenance_cache)

        # Combine changed sources from file watcher
        forced_changed: set[Path] = set()
        if changed_sources:
            forced_changed.update(changed_sources)
        if nav_changed_sources:
            forced_changed.update(nav_changed_sources)

        # RFC: rfc-incremental-build-dependency-gaps
        # Expand forced_changed to include dependency-triggered rebuilds:
        # - Data file changes → dependent pages
        # - Template changes → dependent pages
        # - Content changes → taxonomy term pages
        pages_list_for_deps = list(site.pages)
        forced_changed, dependency_reasons = _expand_forced_changed(
            forced_changed,
            cache,
            site,
            pages_list_for_deps,
        )

        # Filter pages and assets
        filter_start = time.time()
        pages_list = list(site.pages)
        assets_list = list(site.assets)

        # CRITICAL: If no pages were discovered, attempt recovery
        # This should never happen in a normal build - discovery should always find pages
        # But we can recover by re-running discovery with full discovery (bypasses cache issues)
        if not pages_list:
            orchestrator.logger.warning(
                "no_pages_discovered_for_filtering_attempting_recovery",
                total_pages=len(site.pages),
                incremental=incremental,
                suggestion="Re-running discovery with full discovery to recover",
            )
            # Force full discovery (incremental=False) to bypass any cache issues
            # This ensures we find pages even if the page discovery cache is broken
            from bengal.orchestration.build import initialization

            initialization.phase_discovery(
                orchestrator,
                cli,
                incremental=False,  # Force full discovery to recover
                build_context=None,
                build_cache=cache,  # Pass cache for autodoc dependency registration
            )
            pages_list = list(site.pages)
            if not pages_list:
                # Still no pages after recovery - this is a real error
                orchestrator.logger.error(
                    "no_pages_discovered_after_recovery",
                    total_pages=len(site.pages),
                    content_dir=str(site.root_path / "content"),
                    suggestion="Check content directory exists and contains markdown files",
                )
                cli.error("✗ Build failed: No pages discovered after recovery")
                cli.detail(
                    f"Expected pages in {site.root_path / 'content'}",
                    indent=1,
                )
                orchestrator.stats.build_time_ms = (time.time() - build_start) * 1000
                return None  # Return None to signal build failure

            # Recovery succeeded - log success
            orchestrator.logger.info(
                "recovery_succeeded",
                pages_found=len(pages_list),
                reason="Full discovery recovered pages",
            )
            cli.success(f"✓ Recovery succeeded: Found {len(pages_list)} pages")

            # Check if provenance cache entries match the recovered pages
            # If they match, we can keep the cache (no need to rebuild)
            # If they don't match, clear cache to force rebuild
            provenance_cache._ensure_loaded()
            cache_matches = True
            if provenance_cache._index:
                # Sample check: verify a few pages have matching cache entries
                sample_pages = pages_list[: min(10, len(pages_list))]
                for page in sample_pages:
                    page_key = provenance_filter._get_page_key(page)
                    if page_key not in provenance_cache._index:
                        cache_matches = False
                        break
                    # Compute provenance to check if it matches
                    try:
                        provenance = provenance_filter._compute_provenance(page)
                        stored_hash = provenance_cache._index[page_key]
                        if provenance.combined_hash != stored_hash:
                            cache_matches = False
                            break
                    except Exception:
                        # If provenance computation fails, assume mismatch
                        cache_matches = False
                        break

            if not cache_matches or not provenance_cache._index:
                # Cache doesn't match or is empty - clear it to force rebuild
                orchestrator.logger.debug(
                    "provenance_cache_cleared_after_recovery",
                    reason="Cache entries don't match recovered pages",
                    pages_found=len(pages_list),
                )
                cli.detail(
                    "Clearing provenance cache - entries don't match recovered pages",
                    indent=1,
                )
                provenance_cache.cache_dir.mkdir(parents=True, exist_ok=True)
                index_path = provenance_cache.cache_dir / "index.json"
                if index_path.exists():
                    index_path.unlink()
                provenance_cache._index = {}
                provenance_cache._loaded = False
                # Also clear asset hashes to be safe
                asset_hash_path = provenance_cache.cache_dir / "asset_hashes.json"
                if asset_hash_path.exists():
                    asset_hash_path.unlink()
                provenance_filter._asset_hashes = {}
            else:
                # Cache matches - keep it, pages should be cache hits
                orchestrator.logger.debug(
                    "provenance_cache_preserved_after_recovery",
                    reason="Cache entries match recovered pages",
                    pages_found=len(pages_list),
                )
                cli.detail(
                    "Provenance cache matches - pages should be cache hits",
                    indent=1,
                )

        result = provenance_filter.filter(
            pages=pages_list,
            assets=assets_list,
            incremental=incremental,
            forced_changed=forced_changed,
        )
        filter_time_ms = (time.time() - filter_start) * 1000

        # RFC: rfc-incremental-build-dependency-gaps - Gap 2: Taxonomy cascade
        # When content pages change, their taxonomy term pages need rebuilding.
        # Find taxonomy term pages that list any of the affected tags.
        if result.affected_tags and incremental:
            taxonomy_pages_to_add: list[Page] = []
            pages_to_build_sources = {p.source_path for p in result.pages_to_build}

            for page in pages_list:
                # Check if this is a taxonomy term page
                is_taxonomy = getattr(page, "_virtual", False) and (
                    page.metadata.get("_taxonomy_term")
                    or page.metadata.get("tag")
                    or "/tags/" in str(page.source_path)
                    or "/categories/" in str(page.source_path)
                )

                if not is_taxonomy:
                    continue

                # Get the tag/term this page represents
                term = (
                    page.metadata.get("_taxonomy_term")
                    or page.metadata.get("tag")
                    or page.metadata.get("title", "").lower()
                )

                if term and str(term).lower() in {t.lower() for t in result.affected_tags}:
                    # This taxonomy page lists a tag that was affected
                    if page.source_path not in pages_to_build_sources:
                        taxonomy_pages_to_add.append(page)
                        dependency_reasons.setdefault(str(page.source_path), []).append(
                            f"taxonomy_cascade:tag={term}"
                        )

            if taxonomy_pages_to_add:
                # Create new result with taxonomy pages added
                new_pages_to_build = list(result.pages_to_build) + taxonomy_pages_to_add
                new_pages_skipped = [
                    p for p in result.pages_skipped if p not in taxonomy_pages_to_add
                ]
                result = ProvenanceFilterResult(
                    pages_to_build=new_pages_to_build,
                    assets_to_process=result.assets_to_process,
                    pages_skipped=new_pages_skipped,
                    total_pages=result.total_pages,
                    cache_hits=len(new_pages_skipped),
                    cache_misses=len(new_pages_to_build),
                    affected_tags=result.affected_tags,
                    affected_sections=result.affected_sections,
                    changed_page_paths=result.changed_page_paths,
                )

                logger.info(
                    "taxonomy_cascade_triggered",
                    affected_tags=list(result.affected_tags),
                    taxonomy_pages_added=len(taxonomy_pages_to_add),
                )

        # Cascade snapshot sanity check.
        #
        # The cascade snapshot is built during Phase 2 (discovery) by
        # _apply_cascades() → site.build_cascade_snapshot().  It should
        # ALWAYS be populated by the time we reach filtering.  If it's
        # empty despite sections having cascade data, that signals a
        # discovery bug — log a warning so we can diagnose it.
        #
        # Previously this code conditionally rebuilt the snapshot when
        # _index.md files changed, but that is now handled correctly by
        # discovery itself: changed _index.md files are loaded fresh
        # (not from cache) because their fingerprint won't match, so the
        # snapshot built during discovery already contains the fresh data.
        if site.sections and len(site.cascade) == 0:
            logger.warning(
                "cascade_snapshot_empty_after_discovery",
                sections_count=len(site.sections),
                hint="discovery may not have built the cascade snapshot correctly",
            )

        # Initialize decision tracker for observability
        decision = IncrementalDecision(
            pages_to_build=result.pages_to_build,
            pages_skipped_count=result.cache_hits,
        )

        # Track rebuild reasons
        for page in result.pages_to_build:
            page_key = str(page.source_path)

            # Check if this page was triggered by a dependency change
            if page_key in dependency_reasons:
                for reason in dependency_reasons[page_key]:
                    if reason.startswith("data_file:"):
                        decision.add_rebuild_reason(
                            page_key,
                            RebuildReasonCode.DATA_FILE_CHANGED,
                            {"trigger": reason},
                        )
                    elif reason.startswith("template:"):
                        decision.add_rebuild_reason(
                            page_key,
                            RebuildReasonCode.TEMPLATE_CHANGED,
                            {"trigger": reason},
                        )
                    elif reason.startswith("member_changed:"):
                        decision.add_rebuild_reason(
                            page_key,
                            RebuildReasonCode.TAXONOMY_CASCADE,
                            {"trigger": reason},
                        )
            else:
                decision.add_rebuild_reason(
                    page_key,
                    RebuildReasonCode.CONTENT_CHANGED,
                    {"provenance": "content_hash_mismatch"},
                )

        # Check for fingerprint cascade (CSS/JS changes)
        fingerprint_assets = [
            asset
            for asset in result.assets_to_process
            if asset.source_path.suffix.lower() in {".css", ".js"}
        ]

        if fingerprint_assets and not result.pages_to_build:
            # Assets changed but no content changes - rebuild all pages
            # (fingerprinted URLs embedded in HTML will change)
            result = provenance_filter.filter(
                pages=list(site.pages),
                assets=list(site.assets),
                incremental=False,  # Force full rebuild
            )
            decision.fingerprint_changes = True
            decision.asset_changes = [a.source_path.name for a in fingerprint_assets]

            orchestrator.logger.info(
                "fingerprint_assets_changed_forcing_page_rebuild",
                assets_changed=len(fingerprint_assets),
                pages_to_rebuild=len(result.pages_to_build),
            )

        # Check if output directory is missing
        output_dir = site.output_dir
        output_assets_dir = output_dir / "assets"

        output_html_missing = not output_dir.exists() or len(list(output_dir.iterdir())) == 0

        # Check for CSS entry points instead of arbitrary file count
        # CSS entry points (style.css or fingerprinted style.*.css) are critical assets
        css_dir = output_assets_dir / "css"
        css_entry_missing = (
            not output_assets_dir.exists()
            or not css_dir.exists()
            or not any(css_dir.glob("style*.css"))
        )
        output_assets_missing = css_entry_missing

        if (output_html_missing or output_assets_missing) and site.pages:
            # Output was cleaned but cache is warm - force full rebuild
            result = provenance_filter.filter(
                pages=list(site.pages),
                assets=list(site.assets),
                incremental=False,
            )

            for page in result.pages_to_build:
                decision.add_rebuild_reason(
                    str(page.source_path),
                    RebuildReasonCode.OUTPUT_MISSING,
                    {
                        "html_missing": output_html_missing,
                        "assets_missing": output_assets_missing,
                    },
                )

            orchestrator.logger.info(
                "output_missing_forcing_full_rebuild",
                pages_count=len(result.pages_to_build),
                html_missing=output_html_missing,
                assets_missing=output_assets_missing,
            )

        # If specific outputs are missing, rebuild those pages even if provenance is fresh.
        if incremental and result.pages_skipped and cache and hasattr(cache, "output_sources"):
            skipped_by_source = {str(page.source_path): page for page in result.pages_skipped}
            missing_pages: list = []

            for rel_output, source_str in (cache.output_sources or {}).items():
                page = skipped_by_source.get(source_str)
                if not page:
                    continue
                output_path = site.output_dir / rel_output
                page.output_path = page.output_path or output_path
                if not output_path.exists():
                    missing_pages.append(page)
            if missing_pages:
                pages_to_build = list(result.pages_to_build) + missing_pages
                pages_skipped = [p for p in result.pages_skipped if p not in missing_pages]
                result = ProvenanceFilterResult(
                    pages_to_build=pages_to_build,
                    assets_to_process=result.assets_to_process,
                    pages_skipped=pages_skipped,
                    total_pages=result.total_pages,
                    cache_hits=len(pages_skipped),
                    cache_misses=len(pages_to_build),
                    affected_tags=result.affected_tags,
                    affected_sections=result.affected_sections,
                    changed_page_paths=result.changed_page_paths,
                )
                for page in missing_pages:
                    decision.add_rebuild_reason(
                        str(page.source_path),
                        RebuildReasonCode.OUTPUT_MISSING,
                        {"output_path": str(page.output_path)},
                    )

        # Ensure decision reflects the final result after any adjustments.
        decision.pages_to_build = result.pages_to_build
        decision.pages_skipped_count = result.cache_hits

        # Check for skip condition
        if result.is_skip:
            cli.success("✓ No changes detected - build skipped")
            cli.detail(
                f"Cached: {len(site.pages)} pages, {len(site.assets)} assets",
                indent=1,
            )
            cli.detail(f"Provenance check: {filter_time_ms:.1f}ms", indent=1)

            orchestrator.logger.info(
                "no_changes_detected_provenance",
                cached_pages=len(site.pages),
                cached_assets=len(site.assets),
                filter_time_ms=filter_time_ms,
            )

            orchestrator.stats.skipped = True
            orchestrator.stats.build_time_ms = (time.time() - build_start) * 1000
            return None

        # Update stats
        orchestrator.stats.cache_hits = result.cache_hits
        orchestrator.stats.cache_misses = result.cache_misses

        if result.cache_hits > 0:
            avg_time_per_page = 50  # Estimated ms per page render
            orchestrator.stats.time_saved_ms = result.cache_hits * avg_time_per_page * 0.8

        # Log results
        orchestrator.logger.info(
            "incremental_work_identified_provenance",
            pages_to_build=len(result.pages_to_build),
            assets_to_process=len(result.assets_to_process),
            skipped_pages=result.cache_hits,
            cache_hit_rate=f"{result.hit_rate:.1f}%",
            filter_time_ms=filter_time_ms,
        )

        # Verbose output
        if verbose:
            for page in result.pages_skipped:
                decision.skip_reasons[str(page.source_path)] = SkipReasonCode.NO_CHANGES

        decision.log_summary(orchestrator.logger)
        if verbose:
            decision.log_details(orchestrator.logger)

        orchestrator.stats.incremental_decision = decision

        # CLI output
        pages_msg = (
            f"{len(result.pages_to_build)} page{'s' if len(result.pages_to_build) != 1 else ''}"
        )
        assets_msg = f"{len(result.assets_to_process)} asset{'s' if len(result.assets_to_process) != 1 else ''}"
        skipped_msg = f"{result.cache_hits} cached"

        cli.info(f"  Provenance build: {pages_msg}, {assets_msg} (skipped {skipped_msg})")
        cli.detail(
            f"Filter time: {filter_time_ms:.1f}ms ({result.hit_rate:.1f}% hit rate)", indent=1
        )

        # Store provenance filter for later use (recording builds)
        orchestrator._provenance_filter = provenance_filter

        return FilterResult(
            pages_to_build=result.pages_to_build,
            assets_to_process=result.assets_to_process,
            affected_tags=result.affected_tags,
            changed_page_paths=result.changed_page_paths,
            affected_sections=result.affected_sections,
        )


def record_page_build(orchestrator: BuildOrchestrator, page) -> None:
    """
    Record provenance after a page is built.

    Call this after rendering each page to update the provenance cache.
    """
    if hasattr(orchestrator, "_provenance_filter"):
        orchestrator._provenance_filter.record_build(page)


def record_all_page_builds(orchestrator: BuildOrchestrator, pages) -> None:
    """
    Record provenance for all built pages.

    Call this after all pages have been rendered to update the provenance cache.
    """
    if hasattr(orchestrator, "_provenance_filter"):
        pf = orchestrator._provenance_filter
        for page in pages:
            pf.record_build(page)


def save_provenance_cache(orchestrator: BuildOrchestrator) -> None:
    """
    Save the provenance cache after build completes.

    Call this at the end of the build to persist provenance data.
    """
    if hasattr(orchestrator, "_provenance_filter"):
        orchestrator._provenance_filter.save()
