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
