"""
Doc-tree partitioner for the isolated (separate-heap) render backend.

Issue #350, saga S3. Splits the render set into ``num_chunks`` independent
chunks, one per separate-heap worker. The only correctness requirement is that
the partition is a *cover*: every page is assigned to exactly one chunk. Beyond
that, the partition aims to:

- **balance** estimated render cost across chunks, so the slowest chunk (the
  Amdahl tail of the parallel render) is as short as possible; and
- be **deterministic** — a pure function of the page list (which is itself
  deterministic after discovery+parse) — so the same build always produces the
  same chunking, a prerequisite for byte-reproducible output.

Two strategies:

- ``"balanced"`` (default): longest-processing-time-first (LPT) bin packing by
  estimated cost. Best tail behaviour; ignores tree structure.
- ``"section"``: keep each top-level section's pages together (cache locality /
  coherent subtrees), packing whole sections into the least-loaded chunk and
  splitting only sections too large to fit evenly.

Chunks are returned as lists of *indices* into the input ``pages`` sequence, so
callers can map them back to either mutable pages (fork) or page keys (spawn).
"""

from __future__ import annotations

import heapq
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bengal.protocols.core import PageLike

__all__ = ["estimate_render_cost", "partition_pages"]

# Fixed per-page overhead (template setup, context build, write) so that a chunk
# of many tiny pages is not estimated as ~free. Tuned as a rough constant in
# "characters-equivalent" units; only relative magnitude matters for balancing.
_BASE_PAGE_COST = 2000


def estimate_render_cost(page: PageLike) -> int:
    """
    Estimate a page's relative render cost.

    Uses the parsed HTML length as a proxy for template/transform work (longer
    parsed content ⇒ more rendering), plus a fixed per-page overhead. Falls back
    to raw source length, then to the base cost, so the function never raises.
    """
    for attr in ("html_content", "parsed_html", "content"):
        value = getattr(page, attr, None)
        if isinstance(value, str) and value:
            return _BASE_PAGE_COST + len(value)
    return _BASE_PAGE_COST


def _lpt_pack(costed: list[tuple[int, int]], num_chunks: int) -> list[list[int]]:
    """
    Longest-processing-time-first bin packing.

    Args:
        costed: list of (cost, index), already sorted by descending cost then
            ascending index for determinism.
        num_chunks: number of bins.

    Returns:
        ``num_chunks`` lists of indices; each inner list is sorted ascending.
    """
    # Min-heap of (load, chunk_id); assign each item to the least-loaded chunk.
    heap: list[tuple[int, int]] = [(0, c) for c in range(num_chunks)]
    heapq.heapify(heap)
    bins: list[list[int]] = [[] for _ in range(num_chunks)]
    for cost, idx in costed:
        load, chunk_id = heapq.heappop(heap)
        bins[chunk_id].append(idx)
        heapq.heappush(heap, (load + cost, chunk_id))
    for b in bins:
        b.sort()
    return bins


def _section_key(page: PageLike) -> str:
    """Stable top-level grouping key for a page (its top path component)."""
    src = getattr(page, "source_path", None)
    if src is None:
        return ""
    parts = src.parts
    # Group by the first directory under content (parts[-1] is the file itself).
    return parts[1] if len(parts) > 2 else (parts[0] if parts else "")


def partition_pages(
    pages: Sequence[PageLike],
    num_chunks: int,
    strategy: str = "balanced",
) -> list[list[int]]:
    """
    Partition pages into ``num_chunks`` cost-balanced, deterministic chunks.

    Args:
        pages: render set (must be a stable, deterministic ordering).
        num_chunks: desired number of chunks; clamped to ``[1, len(pages)]``.
        strategy: ``"balanced"`` (LPT by cost) or ``"section"`` (group by
            top-level section, then LPT-pack the section groups).

    Returns:
        A list of index-lists covering ``range(len(pages))`` exactly once. Empty
        chunks are dropped, so the result may have fewer than ``num_chunks``
        entries when there are fewer pages than chunks.
    """
    n = len(pages)
    if n == 0:
        return []
    num_chunks = max(1, min(num_chunks, n))

    if strategy == "section":
        # Sum cost per top-level section, LPT-pack sections, then expand to pages.
        groups: dict[str, list[int]] = {}
        for i, page in enumerate(pages):
            groups.setdefault(_section_key(page), []).append(i)
        group_costs: list[tuple[int, str]] = [
            (sum(estimate_render_cost(pages[i]) for i in idxs), key) for key, idxs in groups.items()
        ]
        # Sort by descending cost, ascending key for determinism.
        group_costs.sort(key=lambda gc: (-gc[0], gc[1]))
        heap: list[tuple[int, int]] = [(0, c) for c in range(num_chunks)]
        heapq.heapify(heap)
        bins: list[list[int]] = [[] for _ in range(num_chunks)]
        for cost, key in group_costs:
            load, chunk_id = heapq.heappop(heap)
            bins[chunk_id].extend(groups[key])
            heapq.heappush(heap, (load + cost, chunk_id))
        for b in bins:
            b.sort()
        return [b for b in bins if b]

    # Default: balanced LPT over individual pages.
    costed = sorted(
        ((estimate_render_cost(page), i) for i, page in enumerate(pages)),
        key=lambda ci: (-ci[0], ci[1]),
    )
    return [b for b in _lpt_pack(costed, num_chunks) if b]
