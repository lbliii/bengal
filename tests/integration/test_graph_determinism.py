"""
Live byte-parity gate for the knowledge graph's emitted ``graph.json``.

Determinism is load-bearing: the graph viz bakes node ids, force-layout
coordinates and (from #-graph-showcase P1) PageRank scores + Louvain community
ids straight into ``graph.json`` and each page's ``index.json`` ``.graph``
block, and Bengal guards warm==cold byte parity.

Before this gate existed there was **no live check**: ``graph.json`` was only in
the skipped/stale build-snapshot fixture and was explicitly listed in
``test_isolated_render_parity.py``'s ``VOLATILE_PATTERNS`` (i.e. treated as
non-reproducible). ``test_graph_layout.py`` only exercises ``compute_force_layout``
in isolation, never the real emitted file with communities/pagerank.

This builds a link-dense root **twice, in two clean subprocesses with different
``PYTHONHASHSEED`` values**, and asserts the emitted ``graph.json`` is
byte-identical. Different hash seeds is the harshest test of any latent
dict/set-iteration-order dependence (e.g. an unsorted page list, or a Louvain
shuffle on the global ``random`` module): if anything in the bake rode on
process-local hashing or RNG state, the two files would diverge.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.serial

# Link-dense enough to form real Louvain communities and a non-uniform PageRank
# distribution (28 nodes / 117 edges), so the byte-parity assertion meaningfully
# exercises the community + pagerank bake — not just a trivial 3-node graph.
_ROOT = Path(__file__).parents[1] / "roots" / "test-blog-paginated"

_CHILD = """
import sys
from pathlib import Path
from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions

root, out = Path(sys.argv[1]), Path(sys.argv[2])
site = Site.from_config(root)
site.output_dir = out
site.build(BuildOptions(quiet=True))
"""


def _build_graph_json(work: Path, tag: str, hashseed: str) -> Path:
    """Build a fresh copy of the root in a clean subprocess; return graph.json."""
    site_root = work / f"site_{tag}"
    shutil.copytree(_ROOT, site_root)
    out = work / f"out_{tag}"

    env = dict(os.environ)
    env["PYTHONHASHSEED"] = hashseed

    proc = subprocess.run(
        [sys.executable, "-c", _CHILD, str(site_root), str(out)],
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    graph_json = out / "graph" / "graph.json"
    if proc.returncode != 0 or not graph_json.exists():
        raise AssertionError(
            f"build ({tag}) failed or produced no graph.json; rc={proc.returncode}\n"
            f"stderr tail:\n{proc.stderr[-2000:]}"
        )
    return graph_json


def test_graph_json_is_byte_identical_across_builds(tmp_path: Path) -> None:
    a = _build_graph_json(tmp_path, "a", "0")
    b = _build_graph_json(tmp_path, "b", "1")  # different hash seed on purpose

    bytes_a, bytes_b = a.read_bytes(), b.read_bytes()

    # Guard against a vacuous pass: the graph must be non-trivial, or "identical"
    # would prove nothing (the #130 manifest-count lesson).
    data = json.loads(bytes_a)
    assert len(data["nodes"]) >= 10, "root too small to exercise the bake meaningfully"
    assert len(data["edges"]) >= 10

    if bytes_a != bytes_b:
        # Surface the first structural divergence to make failures debuggable.
        da, db = json.loads(bytes_a), json.loads(bytes_b)
        ids_a = [n["id"] for n in da["nodes"]]
        ids_b = [n["id"] for n in db["nodes"]]
        first = next(
            (i for i, (x, y) in enumerate(zip(ids_a, ids_b, strict=False)) if x != y),
            None,
        )
        raise AssertionError(
            "graph.json differs across two cold builds (different PYTHONHASHSEED) — "
            "a determinism regression in the graph bake.\n"
            f"node count a={len(ids_a)} b={len(ids_b)}; first id divergence at index {first}"
        )
