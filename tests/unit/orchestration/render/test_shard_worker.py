"""
Parse-leg parity tests for the Phase-2 shard worker (issue #350, saga S13.2).

The worker parses its OWN shard of content files into its own heap (no shared
parsed graph — the COW-free core). The load-bearing claim: re-parsing a file shard
in isolation produces pages byte-identical to what the in-process discovery+parse
produced for those same files. We compare through the S13.1 ``page_view_from_live_page``
lens, which captures every field a worker contributes to the global RenderPlan
(title/href/output_path/excerpt/meta_description/toc_items/reading_time/word_count/
tags/content_hash/metadata/section_path/template_name).

Run on the small deterministic fixtures (NOT test-large, which has a random-posts
widget). Each fixture is built once.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from bengal.orchestration.build.options import BuildOptions
from bengal.orchestration.render.isolated.partition import discover_content_files
from bengal.orchestration.render.isolated.shard_worker import parse_shard, render_shard
from bengal.snapshots.render_plan import page_view_from_live_page

if TYPE_CHECKING:
    from bengal.core.site import Site

ROOTS = ["test-basic", "test-taxonomy", "test-product", "test-navigation"]


def _built(site_factory, root: str) -> Site:
    """Build a fixture site once (sequential, quiet) — its parsed pages are the oracle."""
    site = site_factory(root)
    site.build(BuildOptions(quiet=True, force_sequential=True))
    return site


@pytest.mark.parametrize("root", ROOTS)
def test_parse_shard_matches_in_process_parse(site_factory, root):
    """A worker re-parsing a file shard in isolation produces pages whose PageView is
    identical to the in-process parse of the same files — proving the parse leg is
    self-contained and reproduces the build's discovery+parse exactly."""
    site = _built(site_factory, root)
    content_dir = site.root_path / "content"

    files = discover_content_files(content_dir, site=site)
    reparsed = parse_shard(files, site, content_dir=content_dir)

    in_proc = {p.source_path: p for p in site.pages}

    assert reparsed, f"{root} produced no parsed pages"
    checked = 0
    for page in reparsed:
        assert page.source_path in in_proc, f"reparsed an unknown file: {page.source_path}"
        pv_reparsed = page_view_from_live_page(page, site)
        pv_in_process = page_view_from_live_page(in_proc[page.source_path], site)
        assert pv_reparsed == pv_in_process, f"reparsed page diverged for {page.source_path}"
        checked += 1
    assert checked == len(files)


@pytest.mark.parametrize("root", ROOTS)
def test_parse_shard_fills_bodies(site_factory, root):
    """The parse leg actually fills bodies (not just frontmatter): pages come back with
    html_content populated — the discriminator that this ran _parse_content, not just
    discovery construction. (Guards against silently returning unparsed pages, which
    would make the PageView excerpt/word_count parity above vacuous.)"""
    site = _built(site_factory, root)
    content_dir = site.root_path / "content"
    files = discover_content_files(content_dir, site=site)

    reparsed = parse_shard(files, site, content_dir=content_dir)

    # At least one non-empty body, and every page has output_path + a content hash.
    assert any((getattr(p, "html_content", "") or "").strip() for p in reparsed), (
        f"{root}: parse_shard returned no filled bodies — _parse_content did not run"
    )
    for p in reparsed:
        assert getattr(p, "output_path", None) is not None


def test_parse_shard_into_balanced_shards_covers_all_pages(site_factory):
    """End-to-end with S12: partitioning the files into N shards and parsing each shard
    independently yields exactly the in-process page set (a cover, no dup/loss)."""
    from bengal.orchestration.render.isolated.partition import partition_content_files

    site = _built(site_factory, "test-product")
    content_dir = site.root_path / "content"
    files = discover_content_files(content_dir, site=site)

    shards = partition_content_files(files, 3)
    parsed_paths: list = []
    for shard in shards:
        shard_files = [files[i] for i in shard]
        pages = parse_shard(shard_files, site, content_dir=content_dir)
        parsed_paths.extend(p.source_path for p in pages)

    assert sorted(parsed_paths) == sorted(f.source_path for f in files)
    assert len(parsed_paths) == len(set(parsed_paths))  # no page parsed twice


# ---------------------------------------------------------------------------
# S13.3a: the render leg (render_shard) — plumbing validated against the real site
# ---------------------------------------------------------------------------
#
# render_shard is the reusable phase-2 render core the persistent actor (S13.4) calls.
# Here we validate the plumbing (output write + accumulation + RenderChunkResult)
# against the LIVE built site: re-rendering the build's own pages must reproduce the
# exact HTML bytes the in-process build wrote. Swapping in a reconstructed WorkerSite
# as the render world is S13.3b; rendering from a SHARDED/own-heap set is S13.4.


# Scoped to snapshot-stable fixtures. This test RE-renders an already-built live site
# (the only available in-process oracle here), which perturbs build-time per-page nav
# state (next_page/prev_page, active-trail) on a double render — an artifact of the
# harness, NOT of render_shard (which reuses process_page_with_pipeline unchanged). The
# authoritative nav-heavy byte-parity (test-navigation/test-taxonomy) is validated in
# S13.3c+ against a freshly reconstructed WorkerSite rendered ONCE in a subprocess
# (the test_isolated_render_parity.py harness), where no double-render artifact exists.
@pytest.mark.parametrize("root", ["test-basic", "test-product"])
def test_render_shard_reproduces_in_process_html(site_factory, root):
    """render_shard re-rendering the build's own pages against the same site reproduces
    the exact HTML bytes the in-process build wrote — proving the render-leg renders
    every page and writes faithful output before the WorkerSite swaps the render world.

    The build_context must carry the SiteSnapshot: section listings ("In This Section"
    tiles) render from ``build_context.snapshot``, so a snapshot-less context diverges.
    This is the load-bearing requirement for S13.3b — the WorkerSite must supply
    snapshot-equivalent section data, not just the live page graph.

    NB: we deliberately do NOT assert on ``result.page_data``. That accumulation
    (per-page JSON / search-index feed) is a best-effort, output-format-gated path
    with a swallow-all except, so it is legitimately empty in some environments. It is
    not part of the render-leg's contract; the parent-merge feed is validated where it
    matters — the fork-worker parity path now, and the fresh-render S13.5 A/B later."""
    from bengal.orchestration.build_context import BuildContext
    from bengal.snapshots import create_site_snapshot

    site = _built(site_factory, root)
    out_dir = site.output_dir
    oracle = {p.relative_to(out_dir): p.read_bytes() for p in out_dir.rglob("*.html")}
    assert oracle, f"{root} build wrote no HTML"

    pages = list(site.pages)
    ctx = BuildContext(site=site, pages=pages)
    ctx.snapshot = create_site_snapshot(site)  # what the build's snapshot phase sets
    result = render_shard(pages, site, ctx)

    assert result.pages_rendered == len(pages), f"{root}: not all pages rendered"
    assert not result.errors, f"{root} render errors: {result.errors[:3]}"

    after = {p.relative_to(out_dir): p.read_bytes() for p in out_dir.rglob("*.html")}
    diffs = [str(rel) for rel, content in oracle.items() if after.get(rel) != content]
    assert not diffs, f"{root}: render_shard changed {len(diffs)} HTML file(s): {diffs[:5]}"
    assert set(after) == set(oracle), f"{root}: render_shard added/dropped HTML files"
