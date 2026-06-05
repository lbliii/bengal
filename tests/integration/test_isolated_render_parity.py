"""
Byte-parity + determinism guard for the isolated render backend (#350, S6).

The epic's prime invariant: a cold build's output must be byte-identical across
the in-process thread path and the separate-heap (fork) path, and across worker
counts. This complements tests/integration/test_build_snapshot.py (which locks
the thread path against a committed manifest) by asserting the isolated path
reproduces the thread path exactly.

Uses a deterministic multi-page root (test-product) copied into a tmp dir so
builds never touch the repo. The fork backend is forced on via env (threshold 0)
and confirmed to actually fire — a silent fallback to threads would make the
comparison vacuous.
"""

from __future__ import annotations

import hashlib
import multiprocessing as mp
import shutil
from fnmatch import fnmatch
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions

pytestmark = pytest.mark.serial

# Mirrors VOLATILE_PATTERNS in test_build_snapshot.py — files with embedded
# timestamps / build-time ids that are legitimately non-reproducible.
VOLATILE_PATTERNS: tuple[str, ...] = (
    "index.json",
    "index.json.hash",
    "sitemap.xml",
    "agent.json",
    "changelog.json",
    "asset-manifest.json",
    ".well-known/content-signals.json",
    "**/.bengal-cache/**",
    "graph.json",
    "graph/*.json",
)

_ROOT = Path(__file__).parents[1] / "roots" / "test-product"


def _is_volatile(rel: str) -> bool:
    return any(fnmatch(rel, pat) for pat in VOLATILE_PATTERNS)


def _manifest(output_dir: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(output_dir))
        if _is_volatile(rel):
            continue
        manifest[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return manifest


def _build(site_root: Path, output_dir: Path) -> None:
    site = Site.from_config(site_root)
    site.output_dir = output_dir
    site.build(BuildOptions(quiet=True))


@pytest.mark.skipif(
    "fork" not in mp.get_all_start_methods(),
    reason="isolated render backend requires the fork start method",
)
def test_isolated_render_matches_thread_path_and_is_worker_count_invariant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not _ROOT.exists():  # pragma: no cover - fixture must exist
        pytest.skip(f"missing test root {_ROOT}")

    # Work on a copy so the build never touches the repo's fixtures.
    site_root = tmp_path / "site"
    shutil.copytree(_ROOT, site_root)

    # Thread-path baseline (isolation off).
    monkeypatch.delenv("BENGAL_RENDER_ISOLATION", raising=False)
    out_thread = tmp_path / "out_thread"
    _build(site_root, out_thread)
    thread_manifest = _manifest(out_thread)
    assert thread_manifest, "baseline build produced no comparable output"

    # Spy on the backend so we can prove it actually ran (not a silent fallback).
    import bengal.orchestration.render.isolated.backend as backend_mod

    calls: list[int] = []
    original_render = backend_mod.IsolatedRenderBackend.render

    def _spy_render(self: object, *args: object, **kwargs: object) -> int:
        rendered = original_render(self, *args, **kwargs)  # type: ignore[arg-type]
        calls.append(rendered)
        return rendered

    monkeypatch.setattr(backend_mod.IsolatedRenderBackend, "render", _spy_render)

    # Fork path, two worker counts — output must match the thread path AND each
    # other (worker-count invariance).
    monkeypatch.setenv("BENGAL_RENDER_ISOLATION", "fork")
    monkeypatch.setenv("BENGAL_RENDER_ISOLATION_THRESHOLD", "0")

    fork_manifests: dict[int, dict[str, str]] = {}
    for workers in (2, 8):
        monkeypatch.setenv("BENGAL_RENDER_ISOLATION_WORKERS", str(workers))
        out_fork = tmp_path / f"out_fork_{workers}"
        _build(site_root, out_fork)
        fork_manifests[workers] = _manifest(out_fork)

    # The backend fired once per fork build and rendered pages each time.
    assert len(calls) == 2, "isolated backend did not fire (silent fallback?)"
    assert all(n > 0 for n in calls), f"isolated backend rendered no pages: {calls}"

    # Byte-parity: thread == fork(2) == fork(8).
    for workers, manifest in fork_manifests.items():
        added = sorted(set(manifest) - set(thread_manifest))
        removed = sorted(set(thread_manifest) - set(manifest))
        changed = sorted(
            k for k in set(thread_manifest) & set(manifest) if thread_manifest[k] != manifest[k]
        )
        divergence = added or removed or changed
        assert not divergence, (
            f"fork(workers={workers}) diverged from thread path: "
            f"added={added[:5]} removed={removed[:5]} changed={changed[:5]}"
        )
