"""Task: postprocess -- sitemap, RSS, output formats."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.orchestration.pipeline.task import BuildTask

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext


def _skip(ctx: BuildContext) -> bool:
    """Skip when nothing was rendered."""
    opts = ctx._build_options
    if opts and opts.dry_run:
        return True
    return not ctx.pages_to_build


def _execute(ctx: BuildContext) -> None:
    from bengal.orchestration.build.finalization import phase_postprocess

    opts = ctx._build_options
    force_sequential = opts.force_sequential if opts else False

    phase_postprocess(
        ctx._orchestrator,
        ctx.cli,
        not force_sequential,
        ctx,
        ctx.incremental,
        collector=ctx.output_collector,
    )

    # Update GeneratedPageCache for tag pages
    _update_generated_page_cache(ctx)


def _update_generated_page_cache(ctx: BuildContext) -> None:
    """Persist tag page member hashes for future incremental skipping."""
    from bengal.utils.observability.logger import get_logger

    logger = get_logger(__name__)
    generated_page_cache = ctx._generated_page_cache
    if not generated_page_cache:
        return

    cache = ctx.cache
    pages_to_build = ctx.pages_to_build or []

    content_hash_lookup: dict[str, str] = {}
    if cache and hasattr(cache, "parsed_content"):
        for path_str, entry in cache.parsed_content.items():
            if isinstance(entry, dict):
                content_hash = entry.get("metadata_hash", "")
                if content_hash:
                    content_hash_lookup[path_str] = content_hash

    updated = 0
    for page in pages_to_build:
        if page.metadata.get("type") == "tag" and page.metadata.get("_generated"):
            tag_slug = page.metadata.get("_tag_slug", "")
            member_pages = page.metadata.get("_posts", [])
            if tag_slug and member_pages:
                generated_page_cache.update(
                    page_type="tag",
                    page_id=tag_slug,
                    member_pages=member_pages,
                    content_cache=content_hash_lookup,
                    rendered_html="",
                    generation_time_ms=0,
                )
                updated += 1

    logger.info("generated_page_cache_updated", entries=updated)


TASK = BuildTask(
    name="postprocess",
    requires=frozenset({"rendered_pages", "cli", "orchestrator"}),
    produces=frozenset({"postprocess_outputs"}),
    execute=_execute,
    skip_if=_skip,
)
