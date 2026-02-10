"""Task: check_config -- detect configuration changes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.orchestration.pipeline.task import BuildTask

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext


def _execute(ctx: BuildContext) -> None:
    from bengal.orchestration.build.initialization import phase_config_check

    orchestrator = ctx._orchestrator
    result = phase_config_check(orchestrator, ctx.cli, ctx.cache, ctx.incremental)
    ctx.incremental = result.incremental
    ctx.config_changed = result.config_changed


TASK = BuildTask(
    name="check_config",
    requires=frozenset({"site", "cache", "cli", "orchestrator"}),
    produces=frozenset({"config_check_result"}),
    execute=_execute,
    skip_if=None,  # always runs (fast)
)
