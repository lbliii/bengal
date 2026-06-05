"""
Doc-tree / content-file partitioner for the isolated (separate-heap) render backend.

Issue #350. Splits a build's work into ``num_chunks`` independent shards, one per
separate-heap worker. The only correctness requirement is that the partition is a
*cover*: every unit is assigned to exactly one shard. Beyond that, the partition
aims to:

- **balance** estimated cost across shards, so the slowest shard (the Amdahl tail
  of the parallel phase) is as short as possible; and
- be **deterministic** — a pure function of its input sequence — so the same build
  always produces the same sharding, a prerequisite for byte-reproducible output.

Two units of work, two entry points:

- :func:`partition_pages` (saga S3) shards *already-parsed* pages by parsed-HTML
  length — the input to the Phase-1 fork-after-parse render backend.
- :func:`partition_content_files` (saga S12) shards *discovered content files*
  **before** they are parsed, costed by on-disk byte size — the input to the
  Phase-2 shard-parallel build, where each worker parses *and* renders its own
  ~1/N of the corpus (so the parent never holds the whole parsed graph). Pair it
  with :func:`discover_content_files`, which enumerates the source files a worker
  must parse without parsing them itself.

Both strategies (``"balanced"`` LPT bin-packing / ``"section"`` keep-subtrees-
together) share one deterministic packing core (:func:`_partition_indices`), so a
page shard and a file shard balance and tie-break identically.

Shards are returned as lists of *indices* into the input sequence, so callers can
map them back to mutable pages (fork), page keys (spawn), or content-file records.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from bengal.protocols.core import PageLike

__all__ = [
    "ContentFile",
    "discover_content_files",
    "estimate_file_cost",
    "estimate_render_cost",
    "partition_content_files",
    "partition_pages",
]

# Fixed per-page overhead (template setup, context build, write) so that a chunk
# of many tiny pages is not estimated as ~free. Tuned as a rough constant in
# "characters-equivalent" units; only relative magnitude matters for balancing.
_BASE_PAGE_COST = 2000

# Fixed per-file overhead for the pre-parse cost model (parse + template + context
# + write). Independent of _BASE_PAGE_COST because the units differ (raw source
# bytes vs parsed-HTML length); only relative magnitude matters for balancing.
_BASE_FILE_COST = 2000


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


def estimate_render_cost(page: PageLike) -> int:
    """
    Estimate a parsed page's relative render cost.

    Uses the parsed HTML length as a proxy for template/transform work (longer
    parsed content ⇒ more rendering), plus a fixed per-page overhead. Falls back
    to raw source length, then to the base cost, so the function never raises.
    """
    for attr in ("html_content", "parsed_html", "content"):
        value = getattr(page, attr, None)
        if isinstance(value, str) and value:
            return _BASE_PAGE_COST + len(value)
    return _BASE_PAGE_COST


def estimate_file_cost(size_bytes: int) -> int:
    """
    Estimate a content file's relative cost from its on-disk size (pre-parse).

    On-disk byte size is the only cost signal available before parsing; longer
    source ⇒ more parse + render work. A fixed per-file overhead keeps a shard of
    many tiny files from being estimated as ~free. Negative sizes (a bad stat) are
    floored to 0 so the function never returns less than the base cost.
    """
    return _BASE_FILE_COST + max(0, size_bytes)


# ---------------------------------------------------------------------------
# Deterministic packing core (shared by both entry points)
# ---------------------------------------------------------------------------


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


def _partition_indices(
    costs: Sequence[int],
    section_keys: Sequence[str],
    num_chunks: int,
    strategy: str,
) -> list[list[int]]:
    """
    Partition ``range(len(costs))`` into deterministic, cost-balanced shards.

    The single packing core behind both :func:`partition_pages` and
    :func:`partition_content_files`: callers pre-compute a per-index ``costs`` list
    (and, for the section strategy, a parallel ``section_keys`` list) from their own
    item type, so the balancing/tie-break behaviour is identical for pages and files.

    Args:
        costs: per-index relative cost (same length as the item sequence).
        section_keys: per-index top-level grouping key (used only by ``"section"``).
        num_chunks: desired shard count; clamped to ``[1, len(costs)]``.
        strategy: ``"balanced"`` (LPT over individual items) or ``"section"``
            (group by key, then LPT-pack whole groups).

    Returns:
        A list of index-lists covering ``range(len(costs))`` exactly once. Empty
        shards are dropped, so the result may have fewer than ``num_chunks`` entries
        when there are fewer items than shards.
    """
    n = len(costs)
    if n == 0:
        return []
    num_chunks = max(1, min(num_chunks, n))

    if strategy == "section":
        # Sum cost per top-level group, LPT-pack groups, then expand to indices.
        groups: dict[str, list[int]] = {}
        for i, key in enumerate(section_keys):
            groups.setdefault(key, []).append(i)
        # Sort by descending group cost, ascending key for determinism.
        group_costs = sorted(
            ((sum(costs[i] for i in idxs), key) for key, idxs in groups.items()),
            key=lambda gc: (-gc[0], gc[1]),
        )
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

    # Default: balanced LPT over individual items.
    costed = sorted(
        ((costs[i], i) for i in range(n)),
        key=lambda ci: (-ci[0], ci[1]),
    )
    return [b for b in _lpt_pack(costed, num_chunks) if b]


# ---------------------------------------------------------------------------
# Parsed-page partitioner (saga S3 — Phase-1 fork-after-parse backend)
# ---------------------------------------------------------------------------


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
    Partition parsed pages into ``num_chunks`` cost-balanced, deterministic chunks.

    Args:
        pages: render set (must be a stable, deterministic ordering).
        num_chunks: desired number of chunks; clamped to ``[1, len(pages)]``.
        strategy: ``"balanced"`` (LPT by parsed-HTML cost) or ``"section"`` (group
            by top-level section, then LPT-pack the section groups).

    Returns:
        A list of index-lists covering ``range(len(pages))`` exactly once. Empty
        chunks are dropped, so the result may have fewer than ``num_chunks`` entries
        when there are fewer pages than chunks.
    """
    costs = [estimate_render_cost(page) for page in pages]
    keys = [_section_key(page) for page in pages] if strategy == "section" else [""] * len(pages)
    return _partition_indices(costs, keys, num_chunks, strategy)


# ---------------------------------------------------------------------------
# Content-file sharder (saga S12 — Phase-2 shard-parallel build, pre-parse)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ContentFile:
    """A discovered content source file plus its pre-parse cost signal.

    The unit the Phase-2 shard-parallel build assigns to a worker *before* parsing:
    the worker reads ``source_path`` from its own heap, parses it, and renders the
    resulting page(s). ``size_bytes`` (on-disk size) is the cost proxy used to
    balance shards; ``section_key`` is the top-level grouping key for the
    ``"section"`` strategy. Frozen + identity-by-path so a file list is hashable and
    deterministically orderable.
    """

    source_path: Path
    size_bytes: int
    section_key: str = ""


def partition_content_files(
    files: Sequence[ContentFile],
    num_shards: int,
    strategy: str = "balanced",
) -> list[list[int]]:
    """
    Partition discovered content files into ``num_shards`` cost-balanced shards.

    The pre-parse analog of :func:`partition_pages`: costs come from on-disk byte
    size (:func:`estimate_file_cost`) rather than parsed-HTML length, since the
    files have not been parsed yet. Deterministic and a strict cover, so each
    worker's shard plus the barrier reduce reproduces the whole-site output.

    Args:
        files: discovered content files (use :func:`discover_content_files`); must
            be a stable, deterministic ordering (it sorts by path).
        num_shards: desired number of shards; clamped to ``[1, len(files)]``.
        strategy: ``"balanced"`` (LPT by file size) or ``"section"`` (group by
            top-level section, then LPT-pack the section groups).

    Returns:
        A list of index-lists covering ``range(len(files))`` exactly once. Empty
        shards are dropped, so the result may have fewer than ``num_shards`` entries
        when there are fewer files than shards.
    """
    costs = [estimate_file_cost(f.size_bytes) for f in files]
    keys = [f.section_key for f in files] if strategy == "section" else [""] * len(files)
    return _partition_indices(costs, keys, num_shards, strategy)


def discover_content_files(
    content_dir: Path,
    *,
    site: object | None = None,
) -> list[ContentFile]:
    """
    Enumerate the content *source files* under ``content_dir`` without parsing them.

    The pre-parse front door of the shard-parallel build: produces the file list
    that :func:`partition_content_files` shards across workers. Reuses
    :class:`~bengal.content.discovery.directory_walker.DirectoryWalker` for the
    traversal so the file selection (content-extension filter, hidden/underscore
    skip rules with the ``_index``/``_versions``/``_shared`` exceptions, symlink-loop
    detection, sorted listing) is byte-for-byte the same set
    :class:`~bengal.content.discovery.content_discovery.ContentDiscovery` parses —
    the cover guarantee the barrier reduce depends on. The result is sorted by path
    *components* (``Path.parts``), so the index→file mapping is deterministic and
    independent of both filesystem listing order and the OS path separator — a
    plain ``str(path)`` sort would interleave a sibling file into a directory's
    subtree differently on POSIX (``/``) vs Windows (``\\``), shifting shards.

    Scope: this enumerates source files (each once). Configurations that *multiply*
    pages from a single source — i18n ``prefix`` translations and folder-based
    versioning (``_versions``/``_shared`` clones) — yield the same *file* set; the
    per-file page multiplication is reconstructed worker-side (S13) or the build
    falls back to the thread path (the gate's contract). Pass ``site`` so the walker
    can honour the build's versioning configuration when deciding which ``_``-prefixed
    directories are content.

    Args:
        content_dir: the site's content root (absolute or relative; the returned
            paths are joined to it, matching ContentDiscovery).
        site: optional Site reference (for versioning-aware skip rules).

    Returns:
        A deterministically ordered list of :class:`ContentFile`. Empty if
        ``content_dir`` does not exist.
    """
    # Deferred import: the orchestration→content edge is layering-legal, but Bengal's
    # import graph is fragile, so keep it off the module-load path.
    from bengal.content.discovery.directory_walker import DirectoryWalker

    if not content_dir.exists():
        return []

    walker = DirectoryWalker(content_dir, site)
    walker.reset()

    files: list[ContentFile] = []

    def _walk(directory: Path) -> None:
        # walk_directory applies should_skip_item, is_content_file, the content-
        # extension filter, and check_symlink_loop, yielding (path, is_file).
        for item, is_file in walker.walk_directory(directory):
            if is_file:
                files.append(_content_file_for(item, content_dir))
            else:
                _walk(item)

    _walk(content_dir)

    # Sort by path *components* (not str(path)) for a total ordering that is
    # independent of both filesystem listing order and the OS path separator, so
    # the index→file mapping (and thus the shard assignment + barrier reduce order)
    # is identical on every platform. str(path) would embed os.sep ('/' vs '\\'),
    # whose differing ordinal flips a sibling file vs a directory subtree across OSes.
    files.sort(key=lambda f: f.source_path.parts)
    return files


def _content_file_for(path: Path, content_dir: Path) -> ContentFile:
    """Build a :class:`ContentFile` for a discovered file (stat for size; never raises)."""
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    return ContentFile(
        source_path=path,
        size_bytes=size,
        section_key=_file_section_key(path, content_dir),
    )


def _file_section_key(path: Path, content_dir: Path) -> str:
    """Top-level section for a file (the first directory under ``content_dir``).

    Mirrors :func:`_section_key`'s intent for not-yet-parsed files: a top-level file
    (no containing directory under the content root) has an empty key.
    """
    try:
        rel = path.relative_to(content_dir)
    except ValueError:
        return ""
    return rel.parts[0] if len(rel.parts) > 1 else ""
