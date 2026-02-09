"""Task: build_menus -- build navigation menus."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.orchestration.pipeline.task import BuildTask

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext


def _skip(ctx: BuildContext) -> bool:
    """Skip when incremental and no pages changed."""
    return ctx.incremental and not ctx.changed_page_paths


def _execute(ctx: BuildContext) -> None:
    from bengal.orchestration.build.content import phase_menus

    changed_paths = {str(p) for p in ctx.changed_page_paths} if ctx.changed_page_paths else set()
    phase_menus(ctx._orchestrator, ctx.incremental, changed_paths)


TASK = BuildTask(
    name="build_menus",
    requires=frozenset({"finalized_sections", "orchestrator"}),
    produces=frozenset({"menu_tree"}),
    execute=_execute,
    skip_if=_skip,
)
