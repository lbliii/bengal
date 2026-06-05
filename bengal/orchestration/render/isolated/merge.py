"""
Serial merge phase for the isolated render backend — issue #350, saga S4.

A separate-heap worker accumulates per-page data and asset dependencies into its
*own* (forked or re-derived) ``BuildContext`` copy; the parent's context never
sees them. Postprocess, however, reads those accumulations from the parent
context to build the search index, per-page JSON, ``llm-full.txt`` and the
incremental asset map. This module replays each worker's accumulations back into
the parent context so postprocess produces the same site-global artifacts it
would after an in-process render.

Genuinely cross-chunk artifacts (sitemap, RSS, taxonomies, nav, xref) are
produced by the parent's existing postprocess/content phases from ``site.pages``
metadata, which the parent retains intact — so the merge only needs to restore
the *render-time* accumulations, not re-aggregate the whole site.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bengal.orchestration.build_context import BuildContext

    from .transport import RenderChunkResult

__all__ = ["MergeSummary", "merge_chunk_results"]


@dataclass
class MergeSummary:
    """Outcome of merging worker results into the parent BuildContext."""

    pages_rendered: int = 0
    page_data_count: int = 0
    asset_pages_count: int = 0
    error_count: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)


def merge_chunk_results(
    build_context: BuildContext,
    results: Sequence[RenderChunkResult | None],
) -> MergeSummary:
    """
    Replay separate-heap workers' accumulations into the parent context.

    Args:
        build_context: The parent's BuildContext (consumed by postprocess).
        results: Per-chunk results returned by the workers. ``None`` entries
            (a worker that crashed before returning) are skipped.

    Returns:
        A :class:`MergeSummary` describing what was merged, for logging/stats.
    """
    summary = MergeSummary()

    # Merge in chunk order for deterministic accumulation ordering — postprocess
    # generators sort before serializing, but a stable order keeps logs and any
    # order-sensitive consumer reproducible.
    for result in sorted((r for r in results if r is not None), key=lambda r: r.chunk_index):
        summary.pages_rendered += result.pages_rendered

        for data in result.page_data:
            build_context.accumulate_page_data(data)
            summary.page_data_count += 1

        for src_str, refs in result.assets:
            build_context.accumulate_page_assets(Path(src_str), set(refs))
            summary.asset_pages_count += 1

        if result.errors:
            summary.errors.extend(result.errors)

    summary.error_count = len(summary.errors)
    return summary
