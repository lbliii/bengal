"""Deterministic single-build driver for NATIVE render profiling.

This is the build target for Step 0 of ``plan/rfc-frozen-render-world.md``: run it under a
native profiler on Linux to name the objects whose refcount / cache-coherency traffic dominates
the 8-worker render plateau (measured ~1.7-1.8x with cpu/wall ~4.3 → cores busy, not blocked).

macOS arm64 cannot do ``py-spy --native``, so the *profiling* is a Linux gate — but this driver
runs anywhere and prints the cpu/wall signature, so you can first confirm the plateau reproduces
on the target box, then attach the profiler. See ``benchmarks/PROFILE_RENDER_NATIVE.md``.

Usage (the build is the whole program, so a profiler wrapping the process captures the render):

    # confirm the plateau on this box (parallel vs sequential cpu/wall)
    PYTHON_GIL=0 python benchmarks/profile_render_native.py --pages 1000 --workers 8
    PYTHON_GIL=0 python benchmarks/profile_render_native.py --pages 1000 --sequential

    # reuse a pre-generated site so site-gen time is not profiled
    PYTHON_GIL=0 python benchmarks/profile_render_native.py --pages 1000 --workers 8 --reuse-dir /tmp/bengal_profile_site

The phase ledger's ``Rendering`` time and the ``cpu/wall`` ratio are printed so the profile is
self-documenting (a flat profile with cpu/wall>1 and a low-lock signature confirms the coherency
hypothesis; the native stacks then name the contended objects).
"""

from __future__ import annotations

import argparse
import os
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark_gil_speedup import create_site

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions


def _pin_workers(root: Path, workers: int) -> None:
    """Pin the render worker count via ``[build] max_workers`` (flows to the scheduler)."""
    toml = root / "bengal.toml"
    text = toml.read_text(encoding="utf-8")
    if "max_workers" not in text:
        text = text.replace("[build]\n", f"[build]\nmax_workers = {workers}\n", 1)
        toml.write_text(text, encoding="utf-8")


def _build_once(root: Path, *, sequential: bool) -> dict:
    """Run one cold build and return its cpu/wall signature + phase ledger."""
    site = Site.from_config(root)
    if site.output_dir.exists():
        shutil.rmtree(site.output_dir)
    site.output_dir.mkdir(parents=True)
    c0 = os.times()
    t0 = time.perf_counter()
    stats = site.build(
        BuildOptions(force_sequential=sequential, incremental=False, verbose=False, quiet=True)
    )
    wall = time.perf_counter() - t0
    c1 = os.times()
    cpu = (c1.user - c0.user) + (c1.system - c0.system)
    sd = stats.to_dict() if hasattr(stats, "to_dict") else {}
    ledger = sd.get("phase_timings_ms") or {}
    return {
        "wall": wall,
        "cpu": cpu,
        "cpu_per_wall": cpu / wall if wall else 0.0,
        "pages": int(sd.get("total_pages", 0)),
        "render_s": float(ledger.get("Rendering", 0)) / 1000.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, default=1000)
    parser.add_argument(
        "--workers", type=int, default=8, help="render worker count (ignored with --sequential)"
    )
    parser.add_argument("--archetype", default="blog", choices=["blog", "docs"])
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--sequential", action="store_true", help="baseline: force 1 worker")
    parser.add_argument(
        "--reuse-dir",
        default=None,
        help="generate/keep the fixture site here and reuse it if present (keeps it out of the profile)",
    )
    args = parser.parse_args(argv)

    gil_enabled = sys._is_gil_enabled() if hasattr(sys, "_is_gil_enabled") else True
    random.seed(42)

    reuse = Path(args.reuse_dir).resolve() if args.reuse_dir else None
    if reuse is not None and (reuse / "bengal.toml").exists():
        root = reuse
        owned = False
    else:
        root = reuse or Path(tempfile.mkdtemp(prefix="profile_render_"))
        if root.exists() and root == reuse:
            shutil.rmtree(root)
        create_site(args.archetype, args.pages, root)
        _pin_workers(root, args.workers)
        owned = reuse is None

    print(
        f"# profile_render_native  archetype={args.archetype} pages={args.pages} "
        f"workers={'1(seq)' if args.sequential else args.workers} "
        f"PYTHON_GIL={'1' if gil_enabled else '0'} cores={os.cpu_count()} site={root}"
    )
    try:
        for run in range(args.runs):
            r = _build_once(root, sequential=args.sequential)
            print(
                f"run={run} pages={r['pages']} wall={r['wall']:.2f}s cpu={r['cpu']:.2f}s "
                f"cpu/wall={r['cpu_per_wall']:.2f} render_phase={r['render_s']:.2f}s"
            )
    finally:
        if owned:
            shutil.rmtree(root, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
