"""Task: build_query_indexes -- pre-computed indexes for template lookups."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.orchestration.pipeline.task import BuildTask

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext


def _skip(ctx: BuildContext) -> bool:
    """Skip when incremental and no pages changed."""
    return ctx.incremental and not ctx.pages_to_build


def _execute(ctx: BuildContext) -> None:
    from bengal.orchestration.build.content import phase_query_indexes

    pages_to_build = ctx.pages_to_build or []
    phase_query_indexes(ctx._orchestrator, ctx.cache, ctx.incremental, pages_to_build)


TASK = BuildTask(
    name="build_indexes",
    requires=frozenset({
        "finalized_sections",
        "taxonomy_index",
        "pages_to_build",
        "cache",
        "orchestrator",
    }),
    produces=frozenset({"query_indexes"}),
    execute=_execute,
    skip_if=_skip,
)
