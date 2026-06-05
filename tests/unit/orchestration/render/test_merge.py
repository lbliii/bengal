"""
Unit tests for the isolated render serial-merge phase (issue #350, saga S4).

Verifies that per-chunk worker results are replayed into the parent
BuildContext so postprocess sees the whole site: accumulated page data, asset
dependencies, and reconciled unresolved external references.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from bengal.orchestration.build_context import AccumulatedPageData, BuildContext
from bengal.orchestration.render.isolated.merge import merge_chunk_results
from bengal.orchestration.render.isolated.transport import RenderChunkResult


@dataclass
class _Ref:
    """Stand-in for external_refs.resolver.UnresolvedRef (same read surface)."""

    project: str
    target: str
    source_file: Path | None = None
    line: int | None = None


def _page_data(name: str) -> AccumulatedPageData:
    return AccumulatedPageData(
        source_path=Path(f"content/{name}.md"),
        url=f"/{name}/",
        uri=f"/{name}/",
        title=name.title(),
        description="",
        date=None,
        date_iso=None,
        plain_text="body",
        excerpt="body",
        content_preview="body",
        word_count=1,
        reading_time=1,
        section="docs",
        tags=[],
        dir=f"/{name}/",
    )


def _ctx() -> BuildContext:
    # site is a namespace so _reconcile_external_refs can attach resolvers.
    return BuildContext(site=SimpleNamespace())


def test_merge_replays_page_data_and_assets() -> None:
    ctx = _ctx()
    results = [
        RenderChunkResult(
            chunk_index=0,
            pages_rendered=2,
            render_time_ms=1.0,
            page_data=(_page_data("a"), _page_data("b")),
            assets=(("content/a.md", ("/assets/x.css",)),),
        ),
        RenderChunkResult(
            chunk_index=1,
            pages_rendered=1,
            render_time_ms=1.0,
            page_data=(_page_data("c"),),
            assets=(("content/c.md", ("/assets/y.js", "/assets/z.css")),),
        ),
    ]

    summary = merge_chunk_results(ctx, results)

    assert summary.pages_rendered == 3
    assert summary.page_data_count == 3
    assert summary.asset_pages_count == 2
    # Accumulations are visible on the parent context for postprocess.
    assert ctx.accumulated_page_count == 3
    assert ctx.has_accumulated_assets
    acc = dict(ctx.get_accumulated_assets())
    assert acc[Path("content/c.md")] == {"/assets/y.js", "/assets/z.css"}


def test_merge_is_chunk_order_deterministic() -> None:
    # Results delivered out of order must merge in chunk_index order.
    r0 = RenderChunkResult(0, 1, 1.0, page_data=(_page_data("a"),))
    r1 = RenderChunkResult(1, 1, 1.0, page_data=(_page_data("b"),))
    r2 = RenderChunkResult(2, 1, 1.0, page_data=(_page_data("c"),))

    ctx = _ctx()
    merge_chunk_results(ctx, [r2, r0, r1])
    order = [d.source_path.stem for d in ctx.get_accumulated_page_data()]
    assert order == ["a", "b", "c"]


def test_merge_reconciles_external_refs_onto_site() -> None:
    ctx = _ctx()
    results = [
        RenderChunkResult(
            0, 1, 1.0, external_refs=(_Ref("python", "pathlib.Path", Path("a.md"), 3),)
        ),
        RenderChunkResult(1, 1, 1.0, external_refs=(_Ref("kida", "Markup", Path("b.md"), 9),)),
    ]

    summary = merge_chunk_results(ctx, results)

    assert summary.external_ref_count == 2
    resolvers = ctx.site._external_ref_resolvers
    assert len(resolvers) == 1
    unresolved = resolvers[0].unresolved
    assert {r.project for r in unresolved} == {"python", "kida"}


def test_merge_skips_none_results() -> None:
    ctx = _ctx()
    summary = merge_chunk_results(ctx, [None, RenderChunkResult(0, 1, 1.0), None])
    assert summary.pages_rendered == 1
    assert summary.error_count == 0


def test_merge_collects_errors() -> None:
    ctx = _ctx()
    results = [
        RenderChunkResult(0, 0, 1.0, errors=(("a.md", "ValueError: boom"),)),
        RenderChunkResult(1, 1, 1.0),
    ]
    summary = merge_chunk_results(ctx, results)
    assert summary.error_count == 1
    assert summary.errors[0][0] == "a.md"
