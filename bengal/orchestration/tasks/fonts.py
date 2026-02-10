"""Task: resolve_fonts -- download Google Fonts and generate CSS."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.orchestration.pipeline.task import BuildTask

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext


def _skip(ctx: BuildContext) -> bool:
    """Skip when no fonts are configured."""
    site = ctx.site
    if site is None:
        return True
    fonts_config = site.config.get("fonts", {})
    return not fonts_config.get("google_fonts", [])


def _execute(ctx: BuildContext) -> None:
    from bengal.orchestration.build.initialization import phase_fonts

    phase_fonts(ctx._orchestrator, ctx.cli)


TASK = BuildTask(
    name="resolve_fonts",
    requires=frozenset({"site", "cli", "orchestrator"}),
    produces=frozenset({"font_css"}),
    execute=_execute,
    skip_if=_skip,
)
