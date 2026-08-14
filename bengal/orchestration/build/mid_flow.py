"""
Discovery, content, parsing, and snapshot sequencing.

Calls existing phase modules in the hardcoded order. Does not add phases.
Plugin hook timing around these groups must stay identical to the former
inline `BuildOrchestrator.build()` body.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from . import content, initialization, parsing

if TYPE_CHECKING:
    from bengal.orchestration.stats import BuildStats

    from .session import BuildSession


def run_pre_output_phases(session: BuildSession) -> BuildStats | None:
    """
    Run phases 1 through snapshot.

    Returns:
        BuildStats if incremental filtering found no work (early exit),
        otherwise None so the runner continues into output phases.
    """
    orchestrator = session.orchestrator
    cli = session.cli
    early_ctx = session.early_ctx

    # Phase 1: Font Processing
    initialization.phase_fonts(orchestrator, cli, collector=session.output_collector)

    # Phase 1b: Capability vendor provisioning (opt-in Mermaid/D3/KaTeX/Iconify)
    initialization.phase_capabilities(orchestrator, cli)

    # Phase 1.5: Template Validation (optional, controlled by config)
    initialization.phase_template_validation(orchestrator, cli, strict=session.strict)

    # === DISCOVERY PHASE GROUP (dashboard-integrated) ===
    session.run_plugin_phase("pre_discovery")
    session.notify_phase_start("discovery")
    discovery_start = time.time()

    # Phase 2: Content Discovery (with content caching for validators)
    initialization.phase_discovery(
        orchestrator,
        cli,
        session.incremental,
        build_context=early_ctx,
        build_cache=session.cache,
    )

    # Phase 3: Cache Discovery Metadata
    initialization.phase_cache_metadata(orchestrator)

    discovery_duration_ms = (time.time() - discovery_start) * 1000
    orchestrator.stats.record_phase_timing("Discovery", discovery_duration_ms)

    session.notify_phase_complete(
        "discovery",
        discovery_duration_ms,
        f"{len(orchestrator.site.pages)} pages, {len(orchestrator.site.sections)} sections",
    )
    session.run_plugin_phase("post_discovery")

    # Phase 4: Config Check and Cleanup
    filter_start = time.perf_counter()
    config_result = initialization.phase_config_check(
        orchestrator, cli, session.cache, session.incremental
    )
    session.incremental = config_result.incremental
    session.config_changed = config_result.config_changed

    # Phase 5: Incremental Filtering (determine what to build)
    from bengal.orchestration.build.provenance_filter import (
        phase_incremental_filter_provenance,
    )

    filter_result = phase_incremental_filter_provenance(
        orchestrator,
        cli,
        session.cache,
        session.incremental,
        session.verbose,
        session.build_start,
        changed_sources=session.changed_sources,
        nav_changed_sources=session.nav_changed_sources,
    )
    orchestrator.stats.record_phase_timing(
        "Config/filter",
        (time.perf_counter() - filter_start) * 1000,
    )

    if filter_result is None:
        # No changes detected - early exit
        session.fire_build_complete()
        return orchestrator.stats

    session.pages_to_build = filter_result.pages_to_build
    session.assets_to_process = filter_result.assets_to_process
    session.affected_tags = filter_result.affected_tags
    session.changed_page_paths = filter_result.changed_page_paths
    session.affected_sections = filter_result.affected_sections

    early_ctx.incremental = bool(session.incremental)
    early_ctx.changed_page_paths = set(session.changed_page_paths)
    early_ctx.config_changed = bool(session.config_changed)

    _run_content_group(session)
    _run_parsing_and_snapshot(session)
    return None


def _run_content_group(session: BuildSession) -> None:
    """Phases 6–12.5 plus URL collision detection, with content plugin hooks."""
    orchestrator = session.orchestrator
    cli = session.cli
    pages_to_build = session.pages_to_build
    assert pages_to_build is not None

    session.run_plugin_phase("pre_content")
    session.notify_phase_start("content")
    content_start = time.time()

    # Phase 6: Section Finalization
    content.phase_sections(orchestrator, cli, session.incremental, session.affected_sections)

    # Phase 7: Taxonomies & Dynamic Pages
    session.affected_tags = content.phase_taxonomies(
        orchestrator,
        session.cache,
        session.incremental,
        session.force_sequential,
        pages_to_build,
    )

    # Phase 8: Save Taxonomy Index
    content.phase_taxonomy_index(orchestrator)

    # Phase 9: Menus
    content.phase_menus(
        orchestrator, session.incremental, {str(p) for p in session.changed_page_paths}
    )

    # Phase 10: Related Posts Index
    content.phase_related_posts(
        orchestrator, session.incremental, session.force_sequential, pages_to_build
    )

    # Phase 11: Query Indexes
    content.phase_query_indexes(orchestrator, session.cache, session.incremental, pages_to_build)

    # Phase 12: Update Pages List (add generated taxonomy pages)
    pages_to_build = content.phase_update_pages_list(
        orchestrator,
        session.cache,
        session.incremental,
        pages_to_build,
        session.affected_tags,
        generated_page_cache=session.generated_page_cache,
    )

    # Phase 12.25: Variant filter (params.edition for multi-variant builds)
    params_edition = None
    params = orchestrator.site.config.get("params") or {}
    if isinstance(params, dict):
        params_edition = params.get("edition")
    if params_edition is not None and str(params_edition).strip():
        variant = str(params_edition).strip()
        pages_to_build = [p for p in pages_to_build if p.in_variant(variant)]
        orchestrator.site.pages = [p for p in orchestrator.site.pages if p.in_variant(variant)]
        orchestrator._filter_sections_by_variant(orchestrator.site.sections, variant)
        if hasattr(orchestrator.site, "invalidate_regular_pages_cache"):
            orchestrator.site.invalidate_regular_pages_cache()
    session.early_ctx.pages_to_build = list(pages_to_build)
    session.pages_to_build = pages_to_build

    # Phase 12.5: URL Collision Detection (proactive validation)
    collisions = orchestrator.site.validate_no_url_collisions(strict=session.options.strict)
    if collisions:
        collision_records = orchestrator.site.collect_url_collisions()
        cli.render_write("url_collisions.kida", collisions=collision_records)
        orchestrator.logger.warning(
            "url_collision_summary",
            count=len(collision_records),
            urls=[record.url for record in collision_records],
            _console=False,
        )

    content_duration_ms = (time.time() - content_start) * 1000
    orchestrator.stats.record_phase_timing("Content", content_duration_ms)
    taxonomy_count = (
        len(orchestrator.site.taxonomies) if hasattr(orchestrator.site, "taxonomies") else 0
    )
    session.notify_phase_complete(
        "content",
        content_duration_ms,
        f"{taxonomy_count} taxonomies, {len(session.affected_tags)} affected tags",
    )
    session.run_plugin_phase("post_content")


def _run_parsing_and_snapshot(session: BuildSession) -> None:
    """Parse all known pages, then create the immutable render snapshot."""
    orchestrator = session.orchestrator
    cli = session.cli
    pages_to_build = session.pages_to_build
    early_ctx = session.early_ctx
    assert pages_to_build is not None

    session.run_plugin_phase("pre_parsing")
    parsing_start = time.time()
    with orchestrator.logger.phase("parsing"):
        parsing.phase_parse_content(
            orchestrator,
            cli,
            pages_to_build,
            parallel=not session.force_sequential,
        )
    parsing_duration_ms = (time.time() - parsing_start) * 1000
    orchestrator.stats.record_phase_timing("Parsing", parsing_duration_ms)
    if hasattr(orchestrator.stats, "parsing_time_ms"):
        orchestrator.stats.parsing_time_ms = parsing_duration_ms

    cli.phase("Parsing", duration_ms=parsing_duration_ms, details=f"{len(pages_to_build)} pages")
    session.run_plugin_phase("post_parsing")

    session.run_plugin_phase("pre_snapshot")
    from bengal.snapshots import create_site_snapshot
    from bengal.snapshots.persistence import SnapshotCache

    snapshot_start = time.time()
    with orchestrator.logger.phase("snapshot"):
        site_snapshot = create_site_snapshot(orchestrator.site)
        snapshot_duration_ms = (time.time() - snapshot_start) * 1000
        orchestrator.stats.record_phase_timing("Snapshot", snapshot_duration_ms)
        early_ctx.snapshot = site_snapshot
        if hasattr(orchestrator.stats, "snapshot_time_ms"):
            orchestrator.stats.snapshot_time_ms = snapshot_duration_ms

        from bengal.core.nav_tree import NavTreeCache

        NavTreeCache.set_precomputed(dict(site_snapshot.navigation.nav_trees))

        from bengal.rendering.context import _get_global_contexts

        _get_global_contexts(orchestrator.site, build_context=early_ctx)

        from bengal.cache.directive_cache import configure_for_site

        configure_for_site(orchestrator.site)

        from bengal.config.hash import compute_config_hash
        from bengal.rendering.pipeline import RenderingPipeline

        cache_dir = orchestrator.site.root_path / ".bengal" / "cache" / "snapshots"
        snapshot_cache = SnapshotCache(cache_dir)
        snapshot_cache.save(
            site_snapshot,
            parser_version=RenderingPipeline(
                orchestrator.site,
                quiet=True,
                build_stats=None,
                build_context=None,
            )._get_parser_version(),
            config_hash=compute_config_hash(orchestrator.site.config),
        )

        from bengal.services.query import QueryService

        early_ctx.query_service = QueryService.from_snapshot(site_snapshot)
        try:
            from bengal.services.data import DataService

            early_ctx.data_service = DataService.from_root(orchestrator.site.root_path)
        except Exception:  # noqa: S110 -- data/ dir may not exist; service remains None
            pass
    session.run_plugin_phase("post_snapshot")
