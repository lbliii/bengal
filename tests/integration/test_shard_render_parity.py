"""Byte-parity gate for the COW-free shard render backend — issue #350, S16 (in the small).

A full cold build with ``BENGAL_RENDER_ISOLATION=shard`` must produce byte-identical HTML to
the thread path (the non-negotiable invariant), or fall back. Each build runs in its OWN clean
subprocess (no module-state leak; a real worker IS a separate process). Asserts the shard
backend actually FIRED (non-vacuous), and that output is byte-identical for the body-free uses
(title/url/excerpt/metadata listing+linking).

KNOWN LIMITATION (documented, NOT yet gated): cross-shard rendered-CONTENT access diverges —
the default theme's related-posts card falls back to a sibling's ``.content`` for excerpt-less
posts, which body-free PageViews cannot supply (see ``test_taxonomy_documents_cross_shard_content_blocker``).
That is the S14 "one true blocker"; render_isolation stays OFF by default until S14 ships a
body-free content preview or a fallback. This test pins the boundary of what is byte-correct today.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_CHILD = r"""
import sys
from pathlib import Path
from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
root, out = Path(sys.argv[1]), Path(sys.argv[2])
site = Site.from_config(root)
site.output_dir = out
stats = site.build(BuildOptions(quiet=True))
print("USED_ISOLATION", bool(getattr(stats, "render_isolation_used", False)))
"""

_ROOTS = Path(__file__).parents[1] / "roots"


def _build(root: Path, out: Path, *, shard: bool) -> bool:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"
    if shard:
        env["BENGAL_RENDER_ISOLATION"] = "shard"
        env["BENGAL_RENDER_ISOLATION_THRESHOLD"] = "0"
    else:
        env.pop("BENGAL_RENDER_ISOLATION", None)
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD, str(root), str(out)],
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert proc.returncode == 0, f"build failed (shard={shard})\n{proc.stderr[-3000:]}"
    used = any(ln.strip() == "USED_ISOLATION True" for ln in proc.stdout.splitlines())
    return used


def _copy_root(tmp_path: Path, name: str) -> Path:
    src = _ROOTS / name
    if not src.exists():  # pragma: no cover
        pytest.skip(f"missing test root {src}")
    dst = tmp_path / name
    shutil.copytree(src, dst)
    return dst


# Per-fixture pages excluded from the byte compare: the default theme has an UNSEEDED
# random-posts widget (sample(3) on the page pool) that is non-deterministic even thread-vs-
# thread, so it can never be byte-stable and is overlay-checked, not byte-checked (mirrors
# tests/integration/test_isolated_render_parity.py). Everything else MUST be byte-identical.
_PARITY_FIXTURES = [
    ("test-product", frozenset()),
    ("test-basic", frozenset()),
    ("test-taxonomy", frozenset()),  # related-posts cross-shard content resolves via S14
    ("test-navigation", frozenset({"docs/reference/api/index.html"})),  # random-posts widget
]


@pytest.mark.known_gap  # experimental shard backend byte-parity → nightly signal, not a PR gate (see #376)
@pytest.mark.serial
@pytest.mark.parametrize(("root_name", "exclude"), _PARITY_FIXTURES)
def test_shard_build_byte_identical_to_thread(tmp_path, root_name, exclude):
    """The shard backend renders a cold build byte-identically to the thread path — including
    nested sections (product), generated pages + related-posts cross-shard CONTENT (taxonomy,
    via the S14 fork content registry), and menus/nav (navigation). Non-vacuous: asserts the
    backend FIRED and that real HTML was produced + compared; excludes only the unseeded
    random-posts widget page (non-deterministic thread-vs-thread)."""
    root = _copy_root(tmp_path, root_name)
    out_t, out_s = tmp_path / "thread", tmp_path / "shard"

    used_thread = _build(root, out_t, shard=False)
    used_shard = _build(root, out_s, shard=True)
    assert not used_thread, "thread build must NOT use isolation"
    assert used_shard, "shard build did not fire the isolation backend (gate/threshold?)"

    t = {p.relative_to(out_t): p for p in out_t.rglob("*.html")}
    s = {p.relative_to(out_s): p for p in out_s.rglob("*.html")}
    assert t, "thread build produced no HTML — byte-parity would be vacuous (#130)"
    assert set(t) == set(s), (
        f"page set differs: only-thread={set(t) - set(s)}, only-shard={set(s) - set(t)}"
    )

    diffs = [
        str(rel)
        for rel in t
        if str(rel) not in exclude and t[rel].read_bytes() != s[rel].read_bytes()
    ]
    assert not diffs, f"{root_name}: shard render diverged from thread on {diffs}"


@pytest.mark.serial
def test_shard_resolves_cross_shard_related_content(tmp_path):
    """Non-vacuous guard for the S14 fix: test-taxonomy's related-posts card embeds an
    excerpt-less sibling's rendered ``.content`` cross-shard. Assert the related-posts content
    is actually PRESENT in the shard output (not just absent-in-both) — so a regression that
    drops the content registry fails here, not silently passes a vacuous byte compare."""
    root = _copy_root(tmp_path, "test-taxonomy")
    out_s = tmp_path / "shard"
    assert _build(root, out_s, shard=True), "shard backend did not fire"

    post1 = out_s / "post1" / "index.html"
    assert post1.exists(), "expected post1/index.html in the shard build"
    html = post1.read_text()
    assert 'class="related-posts"' in html, "related-posts section missing entirely"
    # The card embeds a sibling post's rendered content body — present only if the cross-shard
    # content registry resolved it (S14). An excerpt-less sibling would otherwise render blank.
    assert "blog-card-excerpt" in html, (
        "related-post card body missing — cross-shard content registry (S14) did not resolve"
    )


def _walk_files(out: Path) -> dict[str, Path]:
    """Every output file (not just HTML), keyed by output-relative POSIX path."""
    return {str(p.relative_to(out)): p for p in out.rglob("*") if p.is_file()}


# Per-fixture sentinel outputs that MUST be present in the shard build, deterministic
# thread-vs-thread, and therefore in the byte-compared set — so each fixture's compare
# actually exercises the artifacts it was added to guard (non-vacuous, #130):
#   - test-taxonomy: the generated tag pages sharded into workers by S13.4e.
#   - test-blog-paginated: the per-page JSON for a SECTIONED content page + the section index
#     (#418, dropped under shard when the worker's JSON accumulation crashed on a snapshot
#     section's nav) AND the enriched authored ``type: blog`` ``_index.md`` HTML + its per-page
#     JSON (#419, whose archive-card ``<time>`` dates diverged thread-vs-shard).
_FULL_OUTPUT_FIXTURES = [
    ("test-taxonomy", ("tags/index.html", "tags/python/index.html", "tags/testing/index.html")),
    (
        "test-blog-paginated",
        (
            "posts/index.html",
            "posts/index.json",
            "posts/post-01/index.json",
            "posts/post-13/index.json",
        ),
    ),
]


@pytest.mark.known_gap  # experimental shard backend byte-parity → nightly signal, not a PR gate (see #376)
@pytest.mark.serial
@pytest.mark.parametrize(("root_name", "sentinels"), _FULL_OUTPUT_FIXTURES)
def test_shard_full_output_byte_identical_excluding_nondeterminism(tmp_path, root_name, sentinels):
    """S13.4e + S16-v2: a shard build must be byte-identical to the thread path across the WHOLE
    output tree — not just ``*.html`` — including per-page JSON, the search index, sitemap, RSS,
    and the markdown output format. Covers the generated pages S13.4e sharded into workers
    (test-taxonomy) and the two pre-existing content-shard parity gaps closed alongside this:
    per-page JSON for SECTIONED pages (#418) and the enriched authored blog-list ``_index.md``
    (#419), both on test-blog-paginated.

    Non-determinism (timestamped JSON sidecars, ``*.hash``, the unseeded random-posts widget) is
    excluded *self-calibratingly*: any file that already differs thread-vs-thread is dropped from
    the compare, so the assertion can only fail on a genuine shard divergence. Non-vacuous: the
    shard backend must FIRE, the per-fixture ``sentinels`` must be PRESENT and in the compared
    set, and a real set of deterministic files must be compared (#130)."""
    root = _copy_root(tmp_path, root_name)
    out_t1, out_t2, out_s = tmp_path / "t1", tmp_path / "t2", tmp_path / "shard"

    # Two thread builds calibrate which files are non-deterministic run-to-run; one shard build
    # is the comparand. Same source root → identical source paths in any reprs.
    assert not _build(root, out_t1, shard=False)
    assert not _build(root, out_t2, shard=False)
    assert _build(root, out_s, shard=True), "shard backend did not fire (gate/threshold?)"

    t1, t2, s = _walk_files(out_t1), _walk_files(out_t2), _walk_files(out_s)
    assert t1, "thread build produced no files — parity would be vacuous (#130)"
    assert set(t1) == set(s), (
        f"file set differs: only-thread={sorted(set(t1) - set(s))}, "
        f"only-shard={sorted(set(s) - set(t1))}"
    )

    nondeterministic = {
        rel for rel in t1 if rel in t2 and t1[rel].read_bytes() != t2[rel].read_bytes()
    }
    compared = [rel for rel in t1 if rel not in nondeterministic]
    assert len(compared) > 10, f"too few deterministic files compared ({len(compared)}) — vacuous?"

    # Each sentinel must be present in the shard output AND deterministic, so the byte check
    # below actually exercises it (not a vacuous absence/exclusion).
    for rel in sentinels:
        assert rel in s, f"{root_name}: expected output {rel} missing from shard build"
        assert rel not in nondeterministic, (
            f"{root_name}: sentinel {rel} unexpectedly non-deterministic"
        )

    diffs = [rel for rel in compared if t1[rel].read_bytes() != s[rel].read_bytes()]
    assert not diffs, (
        f"{root_name}: shard diverged from thread on deterministic files: {sorted(diffs)}"
    )
