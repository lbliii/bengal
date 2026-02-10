"""Task: finalize_sections -- ensure all sections have index pages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.orchestration.pipeline.task import BuildTask

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext


def _skip(ctx: BuildContext) -> bool:
    """Skip when incremental and no sections were affected."""
    if ctx.incremental and isinstance(ctx.affected_sections, set):
        return len(ctx.affected_sections) == 0
    return False


def _execute(ctx: BuildContext) -> None:
    from bengal.orchestration.build.content import phase_sections

    phase_sections(ctx._orchestrator, ctx.cli, ctx.incremental, ctx.affected_sections)


TASK = BuildTask(
    name="finalize_sections",
    requires=frozenset({
        "discovered_sections",
        "affected_sections",
        "cli",
        "orchestrator",
    }),
    produces=frozenset({"finalized_sections"}),
    execute=_execute,
    skip_if=_skip,
)
