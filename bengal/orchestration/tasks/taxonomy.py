"""Task: build_taxonomies -- collect terms, generate tag pages, save index."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.orchestration.pipeline.task import BuildTask

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext


def _skip(ctx: BuildContext) -> bool:
    """Skip when no taxonomies are configured."""
    if ctx.site is None:
        return True
    tax_config = ctx.site.config.get("taxonomies", {})
    return not tax_config


def _execute(ctx: BuildContext) -> None:
    from bengal.orchestration.build.content import (
        phase_taxonomies,
        phase_taxonomy_index,
        phase_update_pages_list,
    )

    orchestrator = ctx._orchestrator
    opts = ctx._build_options
    force_sequential = opts.force_sequential if opts else False
    pages_to_build = ctx.pages_to_build or []

    # Phase 7: Taxonomy collection and page generation
    affected_tags = phase_taxonomies(
        orchestrator, ctx.cache, ctx.incremental, force_sequential, pages_to_build
    )
    ctx.affected_tags = affected_tags

    # Phase 8: Save taxonomy index (consolidated here, was separate phase)
    phase_taxonomy_index(orchestrator)

    # Phase 12: Update pages list with generated taxonomy pages
    pages_to_build = phase_update_pages_list(
        orchestrator,
        ctx.cache,
        ctx.incremental,
        pages_to_build,
        affected_tags,
        generated_page_cache=ctx._generated_page_cache,
    )
    ctx.pages_to_build = pages_to_build


TASK = BuildTask(
    name="build_taxonomies",
    requires=frozenset({
        "discovered_pages",
        "filter_result",
        "cache",
        "orchestrator",
    }),
    produces=frozenset({"taxonomy_pages", "taxonomy_index"}),
    execute=_execute,
    skip_if=_skip,
)
