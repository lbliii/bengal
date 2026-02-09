"""Task: health_check -- run validators (broken links, SEO, etc.)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.orchestration.pipeline.task import BuildTask

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext


def _skip(ctx: BuildContext) -> bool:
    """Skip in dry-run mode (profile controls which checks run)."""
    opts = ctx._build_options
    return bool(opts and opts.dry_run)


def _execute(ctx: BuildContext) -> None:
    import time

    from bengal.orchestration.build.finalization import run_health_check
    from bengal.utils.observability.logger import get_logger

    logger = get_logger(__name__)

    start = time.time()
    with logger.phase("health_check"):
        run_health_check(ctx._orchestrator, profile=ctx.profile, build_context=ctx)
    ctx.stats.health_check_time_ms = (time.time() - start) * 1000


TASK = BuildTask(
    name="health_check",
    requires=frozenset({"rendered_pages", "orchestrator"}),
    produces=frozenset({"health_report"}),
    execute=_execute,
    skip_if=_skip,
)
