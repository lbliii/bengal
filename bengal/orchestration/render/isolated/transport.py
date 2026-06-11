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
from datetime import date, datetime
from pathlib import Path
from typing import Any

__all__ = ["RenderChunkResult", "picklable_metadata"]

# Values that pickle cleanly AND that ``PageArtifact._freeze_json`` already treats verbatim
# (str/int/float/bool/None passthrough; Path → str; date/datetime → isoformat). Anything else
# is stringified below, exactly as ``_freeze_json`` does, so the transform is a no-op under the
# page-artifact cache's eventual freeze.
_FREEZE_TRIVIAL = (str, int, float, bool, type(None), Path, datetime, date)


def picklable_metadata(value: Any) -> Any:
    """Return a picklable copy of a page-metadata value, freeze-identical to the original.

    Generated pages (tag/tag-index/archive) inject live ``Page``/``Section`` refs and
    ``MappingProxyType`` into ``page.metadata`` (``_tags``/``_posts``/``_paginator``/``_section``)
    so the page can resolve its listing at render time. Those land in
    ``AccumulatedPageData.raw_metadata`` (a shallow ``dict(page.metadata)``) and are **unpicklable**
    across the shard worker → parent boundary — the only thing in the render result that is. The
    in-process path never pickles them, and when the page-artifact cache *does* serialize
    ``raw_metadata`` it stringifies every such ref via :func:`PageArtifact._freeze_json`.

    This mirrors that freeze: recurse plain containers, leave freeze-trivial leaves untouched, and
    stringify anything else (live refs, ``MappingProxyType``, callables). The result pickles, and
    ``_freeze_json(picklable_metadata(v)) == _freeze_json(v)`` for every ``v`` — so both the rendered
    output (which reads computed fields, never ``raw_metadata``) and the page-artifact cache stay
    byte-identical thread-vs-shard. Applied shard-side only; the thread path is untouched.
    """
    if isinstance(value, _FREEZE_TRIVIAL):
        return value
    # MappingProxyType is NOT a dict subclass, so it falls through to ``str(value)`` below —
    # matching ``_freeze_json`` (which only descends genuine ``dict``s).
    if isinstance(value, dict):
        return {key: picklable_metadata(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [picklable_metadata(item) for item in value]
    return str(value)


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
