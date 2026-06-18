"""
Byte-parity + determinism guard for the isolated render backend (#350, S6).

The epic's prime invariant: a cold build's output must be byte-identical across
the in-process thread path and the separate-heap (fork) path, and across worker
counts. This complements tests/integration/test_build_snapshot.py (which locks
the thread path against a committed manifest) by asserting the isolated path
reproduces the thread path exactly.

Each build runs in its **own clean subprocess** with its **own copy of the test
root** (so neither process-level render state nor the on-disk build cache leaks
between builds). This also means the fork backend forks from a clean,
single-threaded process — never from the multithreaded pytest-xdist worker,
whose inherited-locked mutexes broke writes under Linux fork (the original CI
failure). Builds run as their own process in production, so this is also the
faithful way to test build parity.

The fork backend is confirmed to actually fire via the ``render_isolation_used``
build stat (a silent fallback to threads would otherwise make the comparison
vacuous — the lesson from #130).
"""

from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path

import pytest

pytestmark = pytest.mark.serial

# Mirrors VOLATILE_PATTERNS in test_build_snapshot.py — files with embedded
# timestamps / build-time ids that are legitimately non-reproducible.
VOLATILE_PATTERNS: tuple[str, ...] = (
    # Top-level site index + its hash.
    "index.json",
    "index.json.hash",
    # Per-page JSON output embeds a build-time `last_modified` timestamp, which
    # differs across any two build processes (not fork-specific). fnmatch `*`
    # spans `/`, so this covers all depths. NOTE: the `.graph` neighborhood block
    # *inside* index.json is reproducible (node ids are site-relative-path
    # hashes, not object identity); only the timestamp makes the whole file
    # volatile. graph.json itself carries no timestamp and IS guarded for byte
    # parity here + in tests/integration/test_graph_determinism.py.
    "*/index.json",
    "*/index.json.hash",
    "sitemap.xml",
    "agent.json",
    "changelog.json",
    "asset-manifest.json",
    ".well-known/content-signals.json",
    "**/.bengal-cache/**",
    "**/.bengal/**",
)

_ROOT = Path(__file__).parents[1] / "roots" / "test-product"

# Child program: build <root> into <out>, print one STATSJSON line. Runs in a
# clean subprocess so the isolated backend forks from a single-threaded process.
_CHILD = """
import json, sys
from pathlib import Path
from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions

root, out = Path(sys.argv[1]), Path(sys.argv[2])
site = Site.from_config(root)
site.output_dir = out
stats = site.build(BuildOptions(quiet=True))
print("STATSJSON " + json.dumps({
    "pages": int(getattr(stats, "total_pages", 0)),
    "isolation_used": bool(getattr(stats, "render_isolation_used", False)),
}))
"""


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


def _build_in_subprocess(
    src_root: Path, work: Path, tag: str, mode: str, workers: int | None
) -> tuple[dict[str, str], dict]:
    """Build a fresh copy of src_root in a clean subprocess. Returns (manifest, stats)."""
    site_root = work / f"site_{tag}"
    shutil.copytree(src_root, site_root)
    out = work / f"out_{tag}"

    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"
    if mode == "thread":
        env.pop("BENGAL_RENDER_ISOLATION", None)
    else:
        env["BENGAL_RENDER_ISOLATION"] = mode
        env["BENGAL_RENDER_ISOLATION_THRESHOLD"] = "0"
        if workers is not None:
            env["BENGAL_RENDER_ISOLATION_WORKERS"] = str(workers)

    proc = subprocess.run(
        [sys.executable, "-c", _CHILD, str(site_root), str(out)],
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    stats = None
    for line in proc.stdout.splitlines():
        if line.startswith("STATSJSON "):
            stats = json.loads(line[len("STATSJSON ") :])
    if stats is None:
        raise AssertionError(
            f"build ({tag}) produced no stats; rc={proc.returncode}\n"
            f"stderr tail:\n{proc.stderr[-2000:]}"
        )
    return _manifest(out), stats


@pytest.mark.skipif(
    "fork" not in mp.get_all_start_methods(),
    reason="isolated render backend requires the fork start method",
)
def test_isolated_render_matches_thread_path_and_is_worker_count_invariant(
    tmp_path: Path,
) -> None:
    if not _ROOT.exists():  # pragma: no cover - fixture must exist
        pytest.skip(f"missing test root {_ROOT}")

    # Thread-path baseline (isolation off).
    thread_manifest, thread_stats = _build_in_subprocess(_ROOT, tmp_path, "thread", "thread", None)
    assert thread_manifest, "baseline build produced no comparable output"
    assert thread_stats["isolation_used"] is False, "thread build should not use isolation"

    # Fork path at two worker counts — output must match the thread path AND each
    # other (worker-count invariance), and the backend must actually have fired.
    for workers in (2, 8):
        fork_manifest, fork_stats = _build_in_subprocess(
            _ROOT, tmp_path, f"fork{workers}", "fork", workers
        )
        assert fork_stats["isolation_used"] is True, (
            f"isolated backend did not fire for workers={workers} (silent fallback?)"
        )
        assert fork_stats["pages"] > 0, f"isolated backend rendered no pages: {fork_stats}"

        added = sorted(set(fork_manifest) - set(thread_manifest))
        removed = sorted(set(thread_manifest) - set(fork_manifest))
        changed = sorted(
            k
            for k in set(thread_manifest) & set(fork_manifest)
            if thread_manifest[k] != fork_manifest[k]
        )
        divergence = added or removed or changed
        assert not divergence, (
            f"fork(workers={workers}) diverged from thread path: "
            f"added={added[:5]} removed={removed[:5]} changed={changed[:5]}"
        )
