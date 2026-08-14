"""
Provenance-based incremental filtering for builds.

Phase wrapper around ``bengal.build.provenance``. Invalidation helpers live
with the engine so cache and orchestration do not grow parallel copies.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, cast

from bengal.build.provenance import ProvenanceCache, ProvenanceFilter
from bengal.build.provenance.artifacts import (
    collect_output_signals,
    repair_missing_page_outputs,
)
from bengal.build.provenance.artifacts import (
    missing_postprocess_artifacts as _missing_postprocess_artifacts,
)
from bengal.build.provenance.artifacts import (
    output_dir_empty as _output_dir_empty,
)
from bengal.build.provenance.artifacts import (
    search_index_repairable as _search_index_repairable,
)
from bengal.build.provenance.invalidation import (
    apply_taxonomy_cascade,
)
from bengal.build.provenance.invalidation import (
    detect_changed_data_files as _detect_changed_data_files,
)
from bengal.build.provenance.invalidation import (
    detect_changed_templates as _detect_changed_templates,
)
from bengal.build.provenance.invalidation import (
    expand_forced_changed as _expand_forced_changed,
)
from bengal.build.provenance.lookups import (
    get_pages_for_data_file as _get_pages_for_data_file,
)
from bengal.build.provenance.lookups import (
    get_pages_for_template as _get_pages_for_template,
)
from bengal.build.provenance.lookups import (
    get_taxonomy_term_pages_for_member as _get_taxonomy_term_pages_for_member,
)
from bengal.orchestration.build.results import (
    FilterResult,
    IncrementalDecision,
    RebuildReasonCode,
    SkipReasonCode,
)
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.build.provenance.filter import ProvenanceFilterResult
    from bengal.cache.build_cache import BuildCache
    from bengal.orchestration.build import BuildOrchestrator
    from bengal.output import CLIOutput
    from bengal.protocols import SiteLike
    from bengal.protocols.core import PageLike

logger = get_logger(__name__)

__all__ = [
    "RebuildReasonCode",
    "_detect_changed_data_files",
    "_detect_changed_templates",
    "_expand_forced_changed",
    "_get_pages_for_data_file",
    "_get_pages_for_template",
    "_get_taxonomy_term_pages_for_member",
    "_missing_postprocess_artifacts",
    "_output_dir_empty",
    "_search_index_repairable",
    "phase_incremental_filter_provenance",
    "record_all_page_builds",
    "record_page_build",
    "save_provenance_cache",
]


def _recover_empty_page_discovery(
    orchestrator: BuildOrchestrator,
    cli: CLIOutput,
    cache: BuildCache,
    provenance_cache: ProvenanceCache,
    provenance_filter: ProvenanceFilter,
    incremental: bool,
    build_start: float,
) -> list[PageLike] | None:
    """Re-run discovery when filtering sees zero pages. Returns pages or None on failure."""
    site = orchestrator.site
    orchestrator.logger.warning(
        "no_pages_discovered_for_filtering_attempting_recovery",
        total_pages=len(site.pages),
        incremental=incremental,
        suggestion="Re-running discovery with full discovery to recover",
    )
    from bengal.orchestration.build import initialization

    initialization.phase_discovery(
        orchestrator,
        cli,
        incremental=False,
        build_context=None,
        build_cache=cache,
    )
    pages_list = list(site.pages)
    if not pages_list:
        orchestrator.logger.error(
            "no_pages_discovered_after_recovery",
            total_pages=len(site.pages),
            content_dir=str(site.root_path / "content"),
            suggestion="Check content directory exists and contains markdown files",
        )
        cli.error("Build failed: No pages discovered after recovery")
        cli.detail(
            f"Expected pages in {site.root_path / 'content'}",
            indent=1,
        )
        orchestrator.stats.build_time_ms = (time.time() - build_start) * 1000
        return None

    orchestrator.logger.info(
        "recovery_succeeded",
        pages_found=len(pages_list),
        reason="Full discovery recovered pages",
    )
    cli.success(f"✓ Recovery succeeded: Found {len(pages_list)} pages")

    provenance_cache._ensure_loaded()
    cache_matches = True
    if provenance_cache._index:
        for page in pages_list:
            page_key = provenance_filter._get_page_key(page)
            if page_key not in provenance_cache._index:
                cache_matches = False
                break
            try:
                provenance = provenance_filter._compute_provenance(page)
                stored_hash = provenance_cache._index[page_key]
                if provenance.combined_hash != stored_hash:
                    cache_matches = False
                    break
            except Exception:
                cache_matches = False
                break

    if not cache_matches or not provenance_cache._index:
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
        asset_hash_path = provenance_cache.cache_dir / "asset_hashes.json"
        if asset_hash_path.exists():
            asset_hash_path.unlink()
        provenance_filter._asset_hashes = {}
    else:
        orchestrator.logger.debug(
            "provenance_cache_preserved_after_recovery",
            reason="Cache entries match recovered pages",
            pages_found=len(pages_list),
        )
        cli.detail(
            "Provenance cache matches - pages should be cache hits",
            indent=1,
        )
    return pages_list


def _record_rebuild_reasons(
    decision: IncrementalDecision,
    result: ProvenanceFilterResult,
    dependency_reasons: dict[str, list[str]],
) -> None:
    """Populate IncrementalDecision rebuild reasons from dependency expansion."""
    for page in result.pages_to_build:
        page_key = str(page.source_path)
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
    """
    with orchestrator.logger.phase("incremental_filtering_provenance", enabled=incremental):
        site = orchestrator.site
        site_like = cast("SiteLike", site)

        provenance_cache = ProvenanceCache(site.root_path / ".bengal" / "provenance")
        provenance_filter = ProvenanceFilter(site, provenance_cache)

        forced_changed: set[Path] = set()
        if changed_sources:
            forced_changed.update(changed_sources)
        if nav_changed_sources:
            forced_changed.update(nav_changed_sources)

        pages_list = list(site.pages)
        forced_changed, dependency_reasons = _expand_forced_changed(
            forced_changed,
            cache,
            site_like,
            pages_list,
            provenance_cache.get_dependency_index(),
        )

        filter_start = time.time()
        assets_list = list(site.assets)
        signals = collect_output_signals(site_like, pages_list, provenance_cache, provenance_filter)

        if signals.is_cold and pages_list:
            result = provenance_filter.filter(
                pages=pages_list,
                assets=assets_list,
                incremental=False,
            )
            filter_time_ms = (time.time() - filter_start) * 1000
            orchestrator._provenance_filter = provenance_filter
            orchestrator.stats.cache_hits = 0
            orchestrator.stats.cache_misses = len(result.pages_to_build)

            explain = getattr(orchestrator.options, "explain", False)
            dry_run = getattr(orchestrator.options, "dry_run", False)
            if explain or dry_run:
                decision = IncrementalDecision(
                    pages_to_build=result.pages_to_build,
                    pages_skipped_count=0,
                )
                for page in result.pages_to_build:
                    page_key = str(page.source_path)
                    decision.add_rebuild_reason(
                        page_key,
                        RebuildReasonCode.FULL_REBUILD,
                        {
                            "cold_build": True,
                            "output_missing": signals.html_missing
                            or signals.assets_missing
                            or signals.all_page_outputs_missing,
                            "no_page_provenance": signals.no_page_provenance,
                        },
                    )
                orchestrator.stats.incremental_decision = decision

            cli.info(
                f"  Provenance build: {len(result.pages_to_build)} pages, "
                f"{len(result.assets_to_process)} assets (skipped 0 cached)"
            )
            cli.detail(
                f"Filter time: {filter_time_ms:.1f}ms (cold/no-cache build, skipped verification)",
                indent=1,
            )
            integrity = signals.asset_integrity
            orchestrator.logger.info(
                "provenance_verification_skipped_cold_build",
                pages=len(result.pages_to_build),
                assets=len(result.assets_to_process),
                output_html_missing=signals.html_missing,
                output_assets_missing=signals.assets_missing,
                page_outputs_checked=signals.page_outputs_checked,
                page_outputs_missing=signals.page_outputs_missing,
                no_page_provenance=signals.no_page_provenance,
                asset_manifest_present=integrity.manifest_present,
                asset_manifest_entries=integrity.total_entries,
                missing_asset_outputs=integrity.missing_count,
            )
            return FilterResult(
                pages_to_build=result.pages_to_build,
                assets_to_process=result.assets_to_process,
                affected_tags=result.affected_tags,
                changed_page_paths=result.changed_page_paths,
                affected_sections=result.affected_sections,
            )

        if not pages_list:
            recovered = _recover_empty_page_discovery(
                orchestrator,
                cli,
                cache,
                provenance_cache,
                provenance_filter,
                incremental,
                build_start,
            )
            if recovered is None:
                return None
            pages_list = recovered
            assets_list = list(site.assets)

        result = provenance_filter.filter(
            pages=pages_list,
            assets=assets_list,
            incremental=incremental,
            forced_changed=forced_changed,
        )
        filter_time_ms = (time.time() - filter_start) * 1000

        result = apply_taxonomy_cascade(result, pages_list, incremental, dependency_reasons)

        if site.sections and len(site.cascade) == 0:
            logger.warning(
                "cascade_snapshot_empty_after_discovery",
                sections_count=len(site.sections),
                hint="discovery may not have built the cascade snapshot correctly",
            )

        decision = IncrementalDecision(
            pages_to_build=result.pages_to_build,
            pages_skipped_count=result.cache_hits,
        )
        _record_rebuild_reasons(decision, result, dependency_reasons)

        fingerprint_assets = [
            asset
            for asset in result.assets_to_process
            if asset.source_path.suffix.lower() in {".css", ".js"}
        ]

        if fingerprint_assets and not result.pages_to_build:
            asset_names = [a.source_path.name for a in fingerprint_assets]
            logger.info(
                "fingerprint_assets_forcing_full_rebuild",
                changed_assets=asset_names,
                reason=f"Fingerprinted asset(s) changed ({', '.join(asset_names)}) — rebuilding all pages because asset URLs are embedded in HTML",
            )
            result = provenance_filter.filter(
                pages=list(site.pages),
                assets=list(site.assets),
                incremental=False,
            )
            decision.fingerprint_changes = True
            decision.asset_changes = [a.source_path.name for a in fingerprint_assets]
            orchestrator.logger.info(
                "fingerprint_assets_changed_forcing_page_rebuild",
                assets_changed=len(fingerprint_assets),
                pages_to_rebuild=len(result.pages_to_build),
            )

        late_signals = collect_output_signals(
            site_like, list(site.pages), provenance_cache, provenance_filter
        )
        if (late_signals.html_missing or late_signals.assets_missing) and site.pages:
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
                        "html_missing": late_signals.html_missing,
                        "assets_missing": late_signals.assets_missing,
                    },
                )
            integrity = late_signals.asset_integrity
            orchestrator.logger.info(
                "output_missing_forcing_full_rebuild",
                pages_count=len(result.pages_to_build),
                html_missing=late_signals.html_missing,
                assets_missing=late_signals.assets_missing,
                asset_manifest_present=integrity.manifest_present,
                asset_manifest_entries=integrity.total_entries,
                missing_asset_outputs=integrity.missing_count,
                missing_asset_output_samples=list(integrity.missing_outputs),
            )

        if incremental:
            result, missing_pages = repair_missing_page_outputs(result, cache, site)
            for page in missing_pages:
                decision.add_rebuild_reason(
                    str(page.source_path),
                    RebuildReasonCode.OUTPUT_MISSING,
                    {"output_path": str(page.output_path)},
                )

        decision.pages_to_build = result.pages_to_build
        decision.pages_skipped_count = result.cache_hits

        missing_postprocess = _missing_postprocess_artifacts(site_like) if result.is_skip else ()
        if result.is_skip and not missing_postprocess:
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
            orchestrator.stats.total_pages = len(site.pages)
            orchestrator.stats.total_assets = len(site.assets)
            orchestrator.stats.total_sections = len(site.sections)
            orchestrator.stats.cache_hits = result.cache_hits
            orchestrator.stats.cache_misses = result.cache_misses
            if result.cache_hits > 0:
                avg_time_per_page = 50
                orchestrator.stats.time_saved_ms = result.cache_hits * avg_time_per_page * 0.8
            if verbose:
                for page in result.pages_skipped:
                    decision.skip_reasons[str(page.source_path)] = SkipReasonCode.NO_CHANGES
            decision.log_summary(orchestrator.logger)
            if verbose:
                decision.log_details(orchestrator.logger)
            orchestrator.stats.incremental_decision = decision
            orchestrator.stats.skipped = True
            orchestrator.stats.build_time_ms = (time.time() - build_start) * 1000
            return None
        if missing_postprocess:
            artifact_samples = [
                str(path.relative_to(site.output_dir))
                if path.is_relative_to(site.output_dir)
                else str(path)
                for path in missing_postprocess[:5]
            ]
            cli.detail(
                "Post-process artifacts missing; regenerating "
                f"{len(missing_postprocess)} file"
                f"{'s' if len(missing_postprocess) != 1 else ''}",
                indent=1,
            )
            orchestrator.logger.info(
                "postprocess_artifacts_missing_forcing_postprocess",
                missing_count=len(missing_postprocess),
                missing_samples=artifact_samples,
            )

        orchestrator.stats.cache_hits = result.cache_hits
        orchestrator.stats.cache_misses = result.cache_misses
        if result.cache_hits > 0:
            avg_time_per_page = 50
            orchestrator.stats.time_saved_ms = result.cache_hits * avg_time_per_page * 0.8

        log_kwargs: dict[str, object] = {
            "pages_to_build": len(result.pages_to_build),
            "assets_to_process": len(result.assets_to_process),
            "skipped_pages": result.cache_hits,
            "cache_hit_rate": f"{result.hit_rate:.1f}%",
            "filter_time_ms": filter_time_ms,
        }
        if missing_postprocess:
            log_kwargs["missing_postprocess_artifacts"] = len(missing_postprocess)
        if provenance_filter._mtime_short_circuit_hits > 0:
            log_kwargs["mtime_short_circuit_hits"] = provenance_filter._mtime_short_circuit_hits
        orchestrator.logger.info("incremental_work_identified_provenance", **log_kwargs)

        if verbose:
            for page in result.pages_skipped:
                decision.skip_reasons[str(page.source_path)] = SkipReasonCode.NO_CHANGES

        decision.log_summary(orchestrator.logger)
        if verbose:
            decision.log_details(orchestrator.logger)

        orchestrator.stats.incremental_decision = decision
        orchestrator._provenance_filter = provenance_filter

        pages_msg = (
            f"{len(result.pages_to_build)} page{'s' if len(result.pages_to_build) != 1 else ''}"
        )
        assets_msg = f"{len(result.assets_to_process)} asset{'s' if len(result.assets_to_process) != 1 else ''}"
        skipped_msg = f"{result.cache_hits} cached"
        cli.info(f"  Provenance build: {pages_msg}, {assets_msg} (skipped {skipped_msg})")
        cli.detail(
            f"Filter time: {filter_time_ms:.1f}ms ({result.hit_rate:.1f}% hit rate)", indent=1
        )

        return FilterResult(
            pages_to_build=result.pages_to_build,
            assets_to_process=result.assets_to_process,
            affected_tags=result.affected_tags,
            changed_page_paths=result.changed_page_paths,
            affected_sections=result.affected_sections,
        )


def record_page_build(orchestrator: BuildOrchestrator, page) -> None:
    """Record provenance after a page is built."""
    if hasattr(orchestrator, "_provenance_filter"):
        orchestrator._provenance_filter.record_build(page)


def record_all_page_builds(
    orchestrator: BuildOrchestrator,
    pages,
    *,
    parallel: bool = True,
) -> None:
    """Record provenance for all built pages."""
    if not hasattr(orchestrator, "_provenance_filter"):
        return
    pf = orchestrator._provenance_filter
    if pf is None:
        return

    record_entries = []
    use_parallel = parallel and len(pages) > 50
    if use_parallel:
        max_workers = min(32, (os.cpu_count() or 1) + 4)
        from bengal.utils.concurrency.work_scope import WorkScope

        with WorkScope("provenance", max_workers=max_workers) as scope:
            results = scope.map(pf.build_record, pages)
            for r in results:
                if r.error:
                    raise r.error
                if r.value is not None:
                    record_entries.append(r.value)
    else:
        for page in pages:
            record_with_paths = pf.build_record(page)
            if record_with_paths is not None:
                record_entries.append(record_with_paths)

    if not record_entries:
        return

    records = [record for record, _input_paths in record_entries]
    input_paths_map = {record.page_path: input_paths for record, input_paths in record_entries}
    pf.cache.store_batch(records, input_paths_map)


def save_provenance_cache(orchestrator: BuildOrchestrator) -> None:
    """Save the provenance cache after build completes."""
    if hasattr(orchestrator, "_provenance_filter") and orchestrator._provenance_filter is not None:
        orchestrator._provenance_filter.save()
