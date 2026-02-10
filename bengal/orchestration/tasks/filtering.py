"""Task: filter_pages -- provenance-based incremental filtering."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.orchestration.pipeline.task import BuildTask

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext


def _execute(ctx: BuildContext) -> None:
    from pathlib import Path

    from bengal.orchestration.build.merkle_graph import analyze_merkle_advisory
    from bengal.orchestration.build.provenance_filter import (
        phase_incremental_filter_provenance,
    )

    opts = ctx._build_options
    changed_sources = opts.changed_sources if opts else None
    nav_changed_sources = opts.nav_changed_sources if opts else None

    feature_flags = getattr(ctx, "feature_flags", None)
    use_merkle_enforcement = bool(
        feature_flags is not None and getattr(feature_flags, "use_merkle_enforcement", False)
    )
    if use_merkle_enforcement and ctx.site is not None:
        advisory = analyze_merkle_advisory(ctx.site, ctx.site.root_path, persist=False)
        merkle_changed = {Path(path) for path in advisory.dirty_pages}
        changed_sources = set(changed_sources or set()) | merkle_changed

    filter_result = phase_incremental_filter_provenance(
        ctx._orchestrator,
        ctx.cli,
        ctx.cache,
        ctx.incremental,
        ctx.verbose,
        ctx.build_start,
        changed_sources=changed_sources or None,
        nav_changed_sources=nav_changed_sources or None,
    )

    if filter_result is None:
        # No changes detected -- mark build as skipped
        ctx.pages_to_build = []
        ctx.assets_to_process = []
        if ctx.stats is not None:
            ctx.stats.skipped = True
        return

    ctx.filter_result = filter_result
    ctx.pages_to_build = filter_result.pages_to_build
    ctx.assets_to_process = filter_result.assets_to_process
    ctx.affected_tags = filter_result.affected_tags
    ctx.changed_page_paths = filter_result.changed_page_paths
    ctx.affected_sections = filter_result.affected_sections


TASK = BuildTask(
    name="filter_pages",
    requires=frozenset({
        "discovered_pages",
        "config_check_result",
        "cache",
        "cli",
        "orchestrator",
    }),
    produces=frozenset({
        "filter_result",
        "pages_to_build",
        "assets_to_process",
        "affected_tags",
        "changed_page_paths",
        "affected_sections",
    }),
    execute=_execute,
    skip_if=None,
)
