"""Task: validate_urls -- detect URL collisions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.orchestration.pipeline.task import BuildTask
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext

logger = get_logger(__name__)


def _execute(ctx: BuildContext) -> None:
    opts = ctx._build_options
    strict = opts.strict if opts else False

    collisions = ctx.site.validate_no_url_collisions(strict=strict)
    if collisions:
        for msg in collisions:
            logger.warning(msg, event="url_collision_detected")


TASK = BuildTask(
    name="validate_urls",
    requires=frozenset({"taxonomy_pages", "site"}),
    produces=frozenset({"url_validation"}),
    execute=_execute,
    skip_if=None,  # always runs (fast, important)
)
