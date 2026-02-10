"""Task: parse_content -- parse markdown for pages to build."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from bengal.orchestration.pipeline.task import BuildTask

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext


def _skip(ctx: BuildContext) -> bool:
    """Skip when there are no pages to build."""
    return not ctx.pages_to_build


def _execute(ctx: BuildContext) -> None:
    from bengal.orchestration.build.parsing import phase_parse_content

    orchestrator = ctx._orchestrator
    opts = ctx._build_options
    force_sequential = opts.force_sequential if opts else False
    changed_sources = opts.changed_sources if opts else None
    pages_to_build = ctx.pages_to_build or []

    # Parse content
    start = time.time()
    with orchestrator.logger.phase("parsing"):
        phase_parse_content(
            orchestrator,
            ctx.cli,
            pages_to_build,
            parallel=not force_sequential,
            changed_sources=changed_sources or None,
        )
    duration_ms = (time.time() - start) * 1000
    if hasattr(ctx.stats, "parsing_time_ms"):
        ctx.stats.parsing_time_ms = duration_ms

    if ctx.cli is not None:
        ctx.cli.phase("Parsing", duration_ms=duration_ms, details=f"{len(pages_to_build)} pages")

    # Persist AST cache after parsing phase has populated it.
    from bengal.server.fragment_update import ContentASTCache

    ast_cache_dir = ctx.site.root_path / ".bengal" / "cache" / "ast"
    ContentASTCache.save_to_disk(ast_cache_dir)


TASK = BuildTask(
    name="parse_content",
    requires=frozenset({"pages_to_render", "pages_to_build", "cli", "orchestrator"}),
    produces=frozenset({"parsed_pages"}),
    execute=_execute,
    skip_if=_skip,
)
