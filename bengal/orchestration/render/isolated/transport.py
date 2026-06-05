"""
Picklable transport records for the isolated render backend (issue #350, S3).

A separate-heap worker renders its chunk, writes the HTML straight to disk, and
returns everything the *parent* still needs for the serial merge phase (S4):
the per-page data accumulated during render (consumed by the search index /
per-page JSON / llm-full generators in postprocess), the asset dependencies
(consumed by incremental asset tracking), plus per-chunk stats and errors.

Only this small, picklable summary crosses the heap boundary — never the
unpicklable Site/snapshot graph (the fork worker inherits those via
copy-on-write; the spawn worker re-derives them).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["RenderChunkResult"]


@dataclass(frozen=True, slots=True)
class RenderChunkResult:
    """
    Result of rendering one chunk in a separate heap. Must stay picklable.

    Attributes:
        chunk_index: Index of this chunk within the partition (for ordering/logs).
        pages_rendered: Number of pages successfully rendered in this chunk.
        render_time_ms: Wall-clock render time for the chunk, in milliseconds.
        errors: ``(source_path, message)`` pairs for pages that failed to render.
        page_data: ``AccumulatedPageData`` records produced during render, to be
            replayed into the parent BuildContext during the serial merge.
        assets: ``(source_path, asset_refs)`` pairs of accumulated asset
            dependencies, to be replayed into the parent BuildContext.
        external_refs: Unresolved external reference payloads collected during
            render, for cross-subtree xref reconciliation in the merge phase.
    """

    chunk_index: int
    pages_rendered: int
    render_time_ms: float
    errors: tuple[tuple[str, str], ...] = ()
    # AccumulatedPageData instances (picklable dataclasses). Typed as Any to keep
    # this transport module free of a build_context import.
    page_data: tuple[Any, ...] = ()
    assets: tuple[tuple[str, tuple[str, ...]], ...] = ()
    external_refs: tuple[Any, ...] = field(default=())
