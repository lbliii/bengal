"""Task: process_assets -- copy, minify, fingerprint assets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.orchestration.pipeline.task import BuildTask

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext


def _skip(ctx: BuildContext) -> bool:
    """Skip when there are no assets to process."""
    return not ctx.assets_to_process


def _execute(ctx: BuildContext) -> None:
    from bengal.orchestration.build.rendering import phase_assets

    opts = ctx._build_options
    force_sequential = opts.force_sequential if opts else False
    assets_to_process = ctx.assets_to_process or []

    result = phase_assets(
        ctx._orchestrator,
        ctx.cli,
        ctx.incremental,
        not force_sequential,
        assets_to_process,
        collector=ctx.output_collector,
    )
    ctx.assets_to_process = result


TASK = BuildTask(
    name="process_assets",
    requires=frozenset({"discovered_assets", "cli", "orchestrator"}),
    produces=frozenset({"asset_manifest"}),
    execute=_execute,
    skip_if=_skip,
)
