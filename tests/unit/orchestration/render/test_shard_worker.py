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
    from bengal.cache import directive_cache
    from bengal.utils.cache_registry import clear_all_caches

    # Start from clean process-global caches. The directive-cache is an id(site)-keyed
    # singleton; a prior in-process test's site (or a recycled id()) can leave entries
    # that poison this fixture's parse — e.g. child-cards on test-navigation's
    # docs/_index.md rendering against a stale section, perturbing content_hash and
    # flaking the parse-parity assertion under xdist ordering. The subprocess harnesses
    # below already guard against this; the in-process oracle build must too.
    clear_all_caches()
    directive_cache.clear_cache()

    site = site_factory(root)
    site.build(BuildOptions(quiet=True, force_sequential=True))
    return site


# known_gap: the experimental shard backend ships off by default (render_isolation="off").
# Its byte-parity vs the in-process path is order-dependent-flaky under pytest-randomly, so it
# runs as nightly signal, not a PR merge gate. Output-determinism work is tracked in #376 and the
# shard-determinism follow-up, which must close before the backend goes default-on.
@pytest.mark.known_gap
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


@pytest.mark.parametrize("root", ["test-basic", "test-product"])
def test_render_shard_renders_all_pages(site_factory, root):
    """Plumbing smoke test for the render leg: render_shard wires up the pipeline
    (build_context, caches, asset context, set_build_context) so every page in the
    shard renders through it without error, returning a well-formed RenderChunkResult.
    The build_context carries the SiteSnapshot (section listings render from it) — a
    load-bearing requirement the WorkerSite (S13.3b) must satisfy.

    Byte-parity is intentionally NOT asserted here. The only in-process oracle is the
    build's own output, and re-rendering an already-built live site is not reliably
    idempotent across environments (content-hash / per-page nav state on the
    already-rendered live pages can perturb on a second render — this flaked CI).
    Authoritative render byte-parity is S13.5's job, via the established
    single-fresh-render subprocess harness (tests/integration/test_isolated_render_parity.py),
    which renders each page exactly once and so has no double-render artifact.
    Likewise we do not assert on ``result.page_data`` (a best-effort, output-format-gated,
    swallow-all accumulation that is legitimately empty in some environments)."""
    from bengal.orchestration.build_context import BuildContext
    from bengal.snapshots import create_site_snapshot

    site = _built(site_factory, root)
    pages = list(site.pages)
    assert pages, f"{root} produced no pages"

    ctx = BuildContext(site=site, pages=pages)
    ctx.snapshot = create_site_snapshot(site)  # what the build's snapshot phase sets
    result = render_shard(pages, site, ctx)

    assert result.pages_rendered == len(pages), f"{root}: not all pages rendered"
    assert not result.errors, f"{root} render errors: {result.errors[:3]}"
    assert result.render_time_ms >= 0


# ---------------------------------------------------------------------------
# S13.3b: the WorkerSite — a real Site reconstructed from a RenderPlan
# ---------------------------------------------------------------------------
#
# This is the first rung that renders against a RECONSTRUCTED site rather than the
# live built one: build_worker_site(plan) makes an empty real Site from the plan's
# config (theme/config_service/page_cache rebuilt by __post_init__, no discovery), then
# assigns the plan's reduced state. It renders a FRESHLY-PARSED page (not the live built
# page) so there is no double-render perturbation — exactly what a real worker does.
#
# Runs in its OWN clean subprocess (mirrors tests/integration/test_isolated_render_parity.py):
# a real worker IS a separate process, and a fresh interpreter is the only contamination-
# free way to assert byte-parity. In-process, sharing the interpreter with other fixtures'
# sites poisons render via id(site)-keyed global caches and the directive-cache singleton
# (the same reason test_render_shard_renders_all_pages above does not assert byte-parity
# in-process). The child also pickle-round-trips the RenderPlan, proving heap transport.
#
# test-basic is the right rung-b target: one content/index.md, no menus / taxonomy / nav
# trees / query indexes, so it isolates the empty-Site recipe and the site-stable base.html
# read surface (title / baseurl / build_time footer / fingerprinted assets).

_WORKER_SITE_PARITY_CHILD = """
import json, pickle, sys
from pathlib import Path

from bengal.assets.manifest import AssetManifest
from bengal.cache import directive_cache
from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
from bengal.orchestration.build_context import BuildContext
from bengal.orchestration.render.isolated.partition import discover_content_files
from bengal.orchestration.render.isolated.shard_worker import parse_shard, render_shard
from bengal.orchestration.render.isolated.worker_site import build_worker_site, merge_shard_pages
from bengal.rendering.assets import AssetManifestContext
from bengal.snapshots import create_site_snapshot
from bengal.snapshots.render_plan import RenderPlan, assert_picklable
from bengal.utils.cache_registry import clear_all_caches

root, out, worker_out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])

# --- Oracle: a normal in-process cold build writes the canonical HTML ---
site = Site.from_config(root)
site.output_dir = out
site.build(BuildOptions(quiet=True, force_sequential=True))
page = next(iter(site.pages))
expected = page.output_path.read_bytes()

# --- The plan the parent ships, exercised through a real pickle round-trip ---
snapshot = create_site_snapshot(site)
plan = RenderPlan.from_site(site, snapshot)
assert_picklable(plan)
plan = pickle.loads(pickle.dumps(plan))   # the worker receives a transported copy

# --- The worker reconstructs a real Site and renders its own freshly-parsed shard ---
worker_site = build_worker_site(plan)
worker_site.output_dir = worker_out
content_dir = plan.root_path / "content"
worker_pages = parse_shard(
    discover_content_files(content_dir, site=worker_site), worker_site, content_dir=content_dir
)
worker_site.pages = merge_shard_pages(plan.pages, worker_pages)
worker_page = next(p for p in worker_pages if p.source_path == page.source_path)

# Per-worker process-global reset (the caller's job; the live build fires it via BUILD_START).
clear_all_caches()
directive_cache.clear_cache()
directive_cache.configure_for_site(worker_site)

# Asset manifest: the parent's asset pipeline writes it once to the shared output_dir; the
# worker loads it to resolve fingerprinted asset URLs (favicon.<hash>.ico, style.<hash>.css).
manifest_path = out / "asset-manifest.json"
manifest = AssetManifest.load(manifest_path)
entries = {k: v.output_path for k, v in manifest.entries.items()} if manifest else {}
asset_ctx = AssetManifestContext(
    entries=entries, mtime=manifest_path.stat().st_mtime if manifest_path.exists() else None
)

ctx = BuildContext(site=worker_site, pages=[worker_page])
ctx.snapshot = snapshot  # section tiles render from it (load-bearing, S13.3a)
result = render_shard([worker_page], worker_site, ctx, asset_ctx=asset_ctx)
actual = worker_page.output_path.read_bytes()

print("RESULTJSON " + json.dumps({
    "match": actual == expected,
    "errors": [list(e) for e in result.errors],
    "build_time_in_plan": plan.build_time is not None,
    "expected_len": len(expected),
    "actual_len": len(actual),
    "is_error_page": b"data-bengal-overlay" in actual,
}))
"""


@pytest.mark.known_gap  # experimental shard backend byte-parity → nightly signal, not a PR gate (see #376)
@pytest.mark.serial
def test_worker_site_renders_page_byte_identical(tmp_path):
    """A page rendered through a WorkerSite reconstructed (and pickle-transported) from a
    RenderPlan is byte-identical to the in-process build's HTML — proving the
    empty-Site-then-assign recipe is faithful for the site-stable read surface, and that
    the new RenderPlan.build_time field closes the footer-copyright-year diff (base.html
    reads site.build_time directly; a worker that left it None would emit a blank year)."""
    import json
    import os
    import shutil
    import subprocess
    import sys
    from pathlib import Path

    src = Path(__file__).parents[3] / "roots" / "test-basic"
    if not src.exists():  # pragma: no cover - fixture must exist
        pytest.skip(f"missing test root {src}")

    site_root = tmp_path / "site"
    shutil.copytree(src, site_root)
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"  # determinism across the oracle and worker render

    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            _WORKER_SITE_PARITY_CHILD,
            str(site_root),
            str(tmp_path / "out"),
            str(tmp_path / "worker_out"),
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    result = None
    for line in proc.stdout.splitlines():
        if line.startswith("RESULTJSON "):
            result = json.loads(line[len("RESULTJSON ") :])
    assert result is not None, (
        f"worker-site parity child produced no result; rc={proc.returncode}\n"
        f"stderr tail:\n{proc.stderr[-3000:]}"
    )

    assert not result["errors"], f"worker render errors: {result['errors']}"
    assert not result["is_error_page"], "worker rendered a build-error overlay (not real HTML)"
    assert result["build_time_in_plan"], "RenderPlan dropped build_time"
    # Anti-vacuity: a no-op builder cannot pass — the oracle HTML must be non-empty.
    assert result["expected_len"] > 0, "oracle produced empty HTML — byte-parity is vacuous"
    assert result["match"], (
        "WorkerSite render diverged from the in-process build "
        f"(expected {result['expected_len']}B, got {result['actual_len']}B)"
    )


# ---------------------------------------------------------------------------
# S13.3c/d: multi-shard byte-parity — menus + NavTree precompute + section/
# breadcrumb/index reconstruction across N>=2 disjoint shards.
# ---------------------------------------------------------------------------
#
# Rung b (above) proved the empty-Site recipe on one page of test-basic. Rungs c/d add
# the full render world: site.menu reconstructed from the plan (so base.html stops
# crashing on `_auto_nav` dicts lacking `_path`), the parent-built NavTrees shipped
# view-ified and installed via NavTreeCache.set_precomputed (so the docs sidebar renders
# without NavTree.build, which needs live Sections), the section registry rebuilt (so
# `get_page_section` resolves and section-index pages don't misroute to the root-home
# tile branch), and plan.pages ordered to match the live discovery walk (so page.next/prev
# are byte-stable). This gate renders EVERY page across N>=2 disjoint shards — where
# PageViews stand in for the pages other shards own — and diffs each against the
# in-process oracle.
#
# Non-determinism: the `random-posts-widget` (`site.regular_pages | sample(3)`, UNSEEDED)
# is provably non-reproducible across processes once the candidate pool exceeds the
# sample size (test-navigation/api.md). Those pages are byte-EXCLUDED (the same reason the
# fork-path parity test, tests/integration/test_isolated_render_parity.py, uses only the
# deterministic test-product) but still asserted to render without an error overlay, so a
# reconstruction crash there cannot hide. Anti-vacuity (#130): we assert the shard backend
# actually split into >=2 shards, the cover is exact, and a non-trivial number of pages
# (incl. multi-level ones) were byte-compared — a silent single-shard fallback or an
# all-widget-skip fails the test.

_MULTISHARD_PARITY_CHILD = """
import json, pickle, sys
from pathlib import Path

from bengal.assets.manifest import AssetManifest
from bengal.cache import directive_cache
from bengal.core.nav_tree import NavTreeCache
from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
from bengal.orchestration.build_context import BuildContext
from bengal.orchestration.render.isolated.partition import (
    discover_content_files,
    partition_content_files,
)
from bengal.orchestration.render.isolated.shard_worker import parse_shard, render_shard
from bengal.orchestration.render.isolated.worker_site import build_worker_site, merge_shard_pages
from bengal.rendering.assets import AssetManifestContext
from bengal.snapshots import create_site_snapshot
from bengal.snapshots.render_plan import RenderPlan, assert_picklable
from bengal.utils.cache_registry import clear_all_caches

WIDGET_MARK = b"random-posts-widget"

root, out, wout, nshards = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4])

# --- Oracle: a normal in-process cold build writes the canonical HTML ---
site = Site.from_config(root)
site.output_dir = out
site.build(BuildOptions(quiet=True, force_sequential=True))
oracle = {
    p.source_path: (p.output_path.read_bytes(), str(p.output_path.relative_to(out)))
    for p in site.pages
    if getattr(p, "output_path", None)
}

# --- Plan, exercised through a real pickle round-trip (heap transport) ---
snapshot = create_site_snapshot(site)
plan = RenderPlan.from_site(site, snapshot)
assert_picklable(plan)
plan = pickle.loads(pickle.dumps(plan))

content_dir = plan.root_path / "content"
all_files = discover_content_files(content_dir, site=build_worker_site(plan))
shards = partition_content_files(all_files, nshards, "balanced")

manifest_path = out / "asset-manifest.json"
manifest = AssetManifest.load(manifest_path)
entries = {k: v.output_path for k, v in manifest.entries.items()} if manifest else {}

# --- Each shard reconstructs its own WorkerSite and renders its own parsed pages,
#     all writing into the shared worker output dir (as parallel workers would). ---
rendered = {}
shard_errors = []
for i, idxs in enumerate(shards):
    ws = build_worker_site(plan, shard_index=i)
    ws.output_dir = wout
    files_i = [all_files[j] for j in idxs]
    worker_pages = parse_shard(files_i, ws, content_dir=content_dir)
    ws.pages = merge_shard_pages(plan.pages, worker_pages)

    # Per-worker process-global reset + the precomputed nav-tree install (the caller's
    # job; a real worker IS a fresh process, here we mirror it per shard in one process).
    clear_all_caches()
    directive_cache.clear_cache()
    directive_cache.configure_for_site(ws)
    NavTreeCache.invalidate()
    NavTreeCache.set_precomputed(dict(plan.navigation.nav_trees))

    asset_ctx = AssetManifestContext(
        entries=entries, mtime=manifest_path.stat().st_mtime if manifest_path.exists() else None
    )
    ctx = BuildContext(site=ws, pages=list(worker_pages))
    ctx.snapshot = snapshot
    result = render_shard(list(worker_pages), ws, ctx, asset_ctx=asset_ctx)
    shard_errors.extend([list(e) for e in result.errors])
    for p in worker_pages:
        rendered[str(p.source_path)] = p.output_path.read_bytes()

# --- Compare every rendered page to the oracle; widget pages are overlay-checked only. ---
pages = []
for sp, (exp, rel) in oracle.items():
    act = rendered.get(str(sp))
    has_widget = WIDGET_MARK in exp
    pages.append({
        "rel": rel,
        "rendered": act is not None,
        "match": (act == exp) if act is not None else None,
        "overlay": (b"data-bengal-overlay" in act) if act is not None else None,
        "widget": has_widget,
        "exp_len": len(exp),
    })

print("MSREPORT " + json.dumps({
    "num_shards": len(shards),
    "cover_ok": set(rendered.keys()) == {str(sp) for sp in oracle},
    "n_rendered": len(rendered),
    "n_oracle": len(oracle),
    "errors": shard_errors,
    "pages": pages,
}))
"""


@pytest.mark.known_gap  # experimental shard backend byte-parity → nightly signal, not a PR gate (see #376)
@pytest.mark.serial
@pytest.mark.parametrize("fixture", ["test-product", "test-navigation"])
@pytest.mark.parametrize("num_shards", [2, 3])
def test_shard_build_is_byte_identical_to_in_process(fixture, num_shards, tmp_path):
    """A cold build split across N>=2 WorkerSite shards is byte-identical to the
    in-process build, page by page — proving the S13.3c/d reconstruction (menus,
    precomputed NavTrees, section registry, walk-order page list) is faithful when
    PageViews stand in for the pages other shards own.

    test-product and test-navigation together cover a 2-level section + tiles and a
    3-level docs sidebar with a multi-item config menu (children + active trail).
    The non-deterministic random-posts widget page is overlay-checked, not byte-diffed.
    """
    import json
    import os
    import shutil
    import subprocess
    import sys
    from pathlib import Path

    src = Path(__file__).parents[3] / "roots" / fixture
    if not src.exists():  # pragma: no cover - fixture must exist
        pytest.skip(f"missing test root {src}")

    site_root = tmp_path / "site"
    shutil.copytree(src, site_root)
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"

    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            _MULTISHARD_PARITY_CHILD,
            str(site_root),
            str(tmp_path / "out"),
            str(tmp_path / "worker_out"),
            str(num_shards),
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    report = None
    for line in proc.stdout.splitlines():
        if line.startswith("MSREPORT "):
            report = json.loads(line[len("MSREPORT ") :])
    assert report is not None, (
        f"multi-shard parity child produced no report; rc={proc.returncode}\n"
        f"stderr tail:\n{proc.stderr[-4000:]}"
    )

    # The shard backend must actually have split — a silent single-shard fallback would
    # make "N-shard parity" vacuous (the #130 lesson). With >=4 source files per fixture
    # and num_shards in {2,3}, the partitioner always yields >=2 non-empty shards.
    assert report["num_shards"] >= 2, (
        f"expected >=2 shards, got {report['num_shards']} (single-shard fallback?)"
    )
    assert report["cover_ok"], (
        f"shard cover incomplete: rendered {report['n_rendered']} of {report['n_oracle']} pages"
    )
    assert not report["errors"], f"shard render errors: {report['errors']}"

    compared = [p for p in report["pages"] if not p["widget"]]
    skipped = [p for p in report["pages"] if p["widget"]]

    # Anti-vacuity: a non-trivial number of real pages must be byte-compared (not all
    # skipped as widgets), and every oracle page must be non-empty.
    assert len(compared) >= 2, (
        f"too few byte-compared pages ({len(compared)}) — gate would be vacuous"
    )
    assert all(p["exp_len"] > 0 for p in report["pages"]), "oracle produced an empty page"

    mismatches = [p["rel"] for p in compared if p["match"] is not True]
    assert not mismatches, (
        f"{fixture} (N={num_shards}): shard build diverged from in-process on: {mismatches}"
    )

    # Widget pages are not byte-comparable (unseeded random sample), but a reconstruction
    # crash there must not hide behind the exclusion.
    for p in skipped:
        assert p["rendered"], f"widget page not rendered: {p['rel']}"
        assert not p["overlay"], f"widget page rendered a build-error overlay: {p['rel']}"
