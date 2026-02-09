"""Task: build_related_posts -- pre-compute related posts index."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.orchestration.pipeline.task import BuildTask

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext


def _skip(ctx: BuildContext) -> bool:
    """Skip when no related posts config or no pages to build."""
    if ctx.site is None:
        return True
    related_config = ctx.site.config.get("related", {})
    if not related_config.get("enabled", False):
        return True
    return not ctx.pages_to_build


def _execute(ctx: BuildContext) -> None:
    from bengal.orchestration.build.content import phase_related_posts

    opts = ctx._build_options
    force_sequential = opts.force_sequential if opts else False
    pages_to_build = ctx.pages_to_build or []
    phase_related_posts(ctx._orchestrator, ctx.incremental, force_sequential, pages_to_build)


TASK = BuildTask(
    name="build_related",
    requires=frozenset({"discovered_pages", "orchestrator"}),
    produces=frozenset({"related_index"}),
    execute=_execute,
    skip_if=_skip,
)
