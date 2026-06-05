#!/usr/bin/env python3
"""
End-to-end build A/B benchmark — thread path vs. experimental render backend.

Issue #350, saga S8. The honest yardstick for "is the build faster end to end?"
that Phase-1 lacked. Builds a site root N times in each mode, reports median wall
time plus the phase attribution (rendering / related_posts / parsing-residual /
postprocess), and the end-to-end delta.

Modes:
- ``thread``  : the default in-process render path (BENGAL_RENDER_ISOLATION unset)
- ``fork``    : the separate-heap render backend (BENGAL_RENDER_ISOLATION=fork,
                threshold 0) — Phase-1's backend, kept for comparison
- (future ``shard`` once S13 lands)

Each build runs in its OWN subprocess so module state / caches never leak between
runs and the OS file cache is the only shared warmth. Use ``--runs 3`` on an idle
box; numbers on a busy laptop only show gross direction. Total wall is measured
by the harness; phase shares come from BuildStats.

Usage
-----
    PYTHONPATH=. python benchmarks/bench_build_ab.py <site_root> \\
        [--runs 3] [--modes thread,fork]
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

# Child script: build once, print a JSON line of {wall_s, pages, phases{}}.
_CHILD = r"""
import json, os, sys, time, tempfile
from pathlib import Path
from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
root = Path(sys.argv[1])
site = Site.from_config(root)
site.output_dir = Path(tempfile.mkdtemp(prefix="bench-"))
t = time.perf_counter()
stats = site.build(BuildOptions(quiet=True))
wall = time.perf_counter() - t
phases = {}
for name in ("rendering_time_ms","related_posts_time_ms","postprocess_time_ms",
             "taxonomy_time_ms","discovery_time_ms","assets_time_ms","menu_time_ms"):
    v = getattr(stats, name, None)
    if isinstance(v,(int,float)) and v>0: phases[name] = round(v/1000,2)
print("BENCHJSON " + json.dumps({"wall_s": round(wall,2),
      "pages": getattr(stats,"total_pages",0), "phases": phases}))
"""


def _run_once(site_root: Path, mode: str) -> dict | None:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"
    if mode == "thread":
        env.pop("BENGAL_RENDER_ISOLATION", None)
    else:
        env["BENGAL_RENDER_ISOLATION"] = mode
        env["BENGAL_RENDER_ISOLATION_THRESHOLD"] = "0"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(_CHILD)
        child = f.name
    try:
        out = subprocess.run(
            [sys.executable, child, str(site_root)],
            env=env,
            capture_output=True,
            text=True,
            timeout=1800,
        )
    finally:
        os.unlink(child)
    for line in out.stdout.splitlines():
        if line.startswith("BENCHJSON "):
            return json.loads(line[len("BENCHJSON ") :])
    sys.stderr.write(out.stderr[-2000:] + "\n")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("site_root", type=Path)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--modes", default="thread,fork")
    args = ap.parse_args()

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    results: dict[str, list[dict]] = {m: [] for m in modes}
    for m in modes:
        for _ in range(args.runs):
            r = _run_once(args.site_root, m)
            if r is not None:
                results[m].append(r)

    print(f"\nEnd-to-end A/B — {args.site_root}, median-of-{args.runs}\n")
    baseline = None
    for m in modes:
        runs = results[m]
        if not runs:
            print(f"  {m:8} FAILED (see stderr)")
            continue
        wall = statistics.median(r["wall_s"] for r in runs)
        pages = runs[0]["pages"]
        if baseline is None:
            baseline = wall
        speedup = baseline / wall if wall else 0.0
        # Median phase shares from the runs.
        phase_keys = sorted({k for r in runs for k in r["phases"]})
        phase_str = "  ".join(
            f"{k.replace('_time_ms', '')}={statistics.median(r['phases'].get(k, 0) for r in runs):.1f}s"
            for k in phase_keys
        )
        print(f"  {m:8} {wall:7.2f}s  ({speedup:4.2f}x)  pages={pages}")
        print(f"           {phase_str}")
    print("\n  (>1.00x = faster than the first mode listed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
