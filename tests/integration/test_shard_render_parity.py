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


@pytest.mark.serial
@pytest.mark.parametrize("root_name", ["test-product", "test-basic"])
def test_shard_build_byte_identical_to_thread(tmp_path, root_name):
    """The shard backend renders a cold build byte-identically to the thread path (body-free
    uses). Non-vacuous: asserts the backend FIRED and that real HTML was produced + compared."""
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

    diffs = [str(rel) for rel in t if t[rel].read_bytes() != s[rel].read_bytes()]
    assert not diffs, f"{root_name}: shard render diverged from thread on {diffs}"


@pytest.mark.serial
def test_taxonomy_documents_cross_shard_content_blocker(tmp_path):
    """Pins the S14 'one true blocker': test-taxonomy's related-posts card embeds an excerpt-less
    sibling's rendered ``.content`` cross-shard, which body-free PageViews cannot supply, so the
    shard build diverges on the post pages. This test ASSERTS the divergence (so it cannot be
    silently 'fixed' into a false byte-parity claim) — when S14 ships the content preview/fallback,
    flip this to assert byte-parity and fold test-taxonomy into the parametrized test above."""
    root = _copy_root(tmp_path, "test-taxonomy")
    out_t, out_s = tmp_path / "thread", tmp_path / "shard"
    _build(root, out_t, shard=False)
    assert _build(root, out_s, shard=True), "shard backend did not fire"

    t = {p.relative_to(out_t): p for p in out_t.rglob("*.html")}
    s = {p.relative_to(out_s): p for p in out_s.rglob("*.html")}
    diffs = {str(rel) for rel in (set(t) & set(s)) if t[rel].read_bytes() != s[rel].read_bytes()}
    # The known blocker manifests on the post pages (related-posts card content fallback).
    assert any("post" in d for d in diffs), (
        "expected the cross-shard-content blocker on post pages; if this fails, S14 may have "
        "closed it — move test-taxonomy into test_shard_build_byte_identical_to_thread"
    )
