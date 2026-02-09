"""Task: discover_content -- find pages, sections, and assets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.orchestration.pipeline.task import BuildTask

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext


def _execute(ctx: BuildContext) -> None:
    from bengal.orchestration.build.initialization import (
        phase_cache_metadata,
        phase_discovery,
        phase_template_validation,
    )

    orchestrator = ctx._orchestrator
    opts = ctx._build_options

    # Phase 1.5: Template validation (optional)
    phase_template_validation(orchestrator, ctx.cli, strict=ctx.strict)

    # Phase 2: Content discovery
    changed_sources = opts.changed_sources if opts else None
    phase_discovery(
        orchestrator,
        ctx.cli,
        ctx.incremental,
        build_context=ctx,
        build_cache=ctx.cache,
        changed_sources=changed_sources or None,
    )

    # Phase 3: Cache discovery metadata
    phase_cache_metadata(orchestrator)


TASK = BuildTask(
    name="discover_content",
    requires=frozenset({"site", "cli", "cache", "orchestrator"}),
    produces=frozenset({"discovered_pages", "discovered_sections", "discovered_assets"}),
    execute=_execute,
    skip_if=None,  # always runs (entry point)
)
