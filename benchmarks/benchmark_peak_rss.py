#!/usr/bin/env python3
"""
Peak-RSS Benchmark: how much resident memory does a large cold build need?
==========================================================================

The north-star claim has a memory half: "blazing fast at scale" only counts if
a 10k-page site fits in a sane RAM budget. This harness builds a large fixture
site once and samples the process RSS on a background thread while the build
runs, recording the peak. It reuses the exact fixture generators and build call
from ``benchmark_gil_speedup.py`` so the memory number is comparable to the
wall-time ladder.

The build runs on the free-threaded 3.14t interpreter (PYTHON_GIL=0 by default).
Peak RSS is sampled with ``psutil`` every ``--interval`` seconds.

Usage:
    # Default: 10000 pages x {blog, docs, autodoc}, publish committed baseline
    python benchmarks/benchmark_peak_rss.py --publish

    # Single cell
    python benchmarks/benchmark_peak_rss.py --pages 10000 --archetype docs

Methodology:
    - Cold build, fresh temp site, output wiped.
    - psutil.Process().memory_info().rss sampled on a daemon thread.
    - Peak = max RSS observed across the whole build (incl. discovery + render).
    - Reported in MB; the deliverable budget is < 2048 MB (2 GB) at 10k pages.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

import psutil

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests" / "performance"))
from results_manager import BenchmarkResults  # noqa: E402

# Reuse the fixture generators + archetype set from the GIL harness so the
# memory measurement uses identical content to the wall-time ladder.
sys.path.insert(0, str(REPO_ROOT / "benchmarks"))
from benchmark_gil_speedup import create_site  # noqa: E402

BASELINE_DIR = REPO_ROOT / "benchmarks" / "baselines"


class _RSSSampler:
    """Sample process RSS on a daemon thread; expose the peak in bytes."""

    def __init__(self, interval: float = 0.05) -> None:
        self._interval = interval
        self._proc = psutil.Process()
        self._peak = self._proc.memory_info().rss
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                rss = self._proc.memory_info().rss
            except psutil.Error:
                break
            if rss > self._peak:
                self._peak = rss
            self._stop.wait(self._interval)

    def __enter__(self) -> _RSSSampler:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join(timeout=2.0)

    @property
    def peak_bytes(self) -> int:
        # Capture a final sample so a fast build still records a real value.
        rss = self._proc.memory_info().rss
        return max(self._peak, rss)


def measure_cell(archetype: str, num_pages: int, interval: float) -> dict[str, float]:
    from bengal.core.site import Site
    from bengal.orchestration.build.options import BuildOptions

    tmp = Path(tempfile.mkdtemp(prefix=f"rss_{archetype}_"))
    try:
        create_site(archetype, num_pages, tmp)
        site = Site.from_config(tmp)
        if site.output_dir.exists():
            shutil.rmtree(site.output_dir)
        site.output_dir.mkdir(parents=True)

        with _RSSSampler(interval=interval) as sampler:
            start = time.perf_counter()
            stats = site.build(
                BuildOptions(force_sequential=False, incremental=False, verbose=False, quiet=True)
            )
            wall = time.perf_counter() - start
            peak = sampler.peak_bytes

        sd = stats.to_dict() if hasattr(stats, "to_dict") else {}
        return {
            "archetype": archetype,
            "pages": num_pages,
            "total_pages": int(sd.get("total_pages", num_pages)),
            "wall_s": wall,
            "peak_rss_bytes": peak,
            "peak_rss_mb": peak / 1024 / 1024,
            "gil_enabled": sys._is_gil_enabled(),
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def publish(cells: list[dict], budget_mb: float) -> Path:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "methodology": (
            "Cold build on free-threaded CPython 3.14t (PYTHON_GIL default off); "
            "process RSS sampled on a daemon thread (psutil); peak across the "
            f"whole build. Budget for the deliverable is < {int(budget_mb)} MB at 10k pages."
        ),
        "budget_mb": budget_mb,
        "cells": cells,
    }
    metadata = {
        "python_version": sys.version,
        "free_threaded": not sys._is_gil_enabled(),
        "platform": sys.platform,
    }
    mgr = BenchmarkResults(results_dir=BASELINE_DIR)
    mgr.save_result("peak_rss", payload, metadata=metadata)
    stable = BASELINE_DIR / "peak_rss.json"
    stable.write_text(json.dumps({"metadata": metadata, "data": payload}, indent=2) + "\n")
    return stable


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, default=None)
    parser.add_argument("--archetype", default=None)
    parser.add_argument(
        "--archetypes", default="blog,docs,autodoc", help="Comma-separated archetypes"
    )
    parser.add_argument("--scales", default="10000", help="Comma-separated page counts")
    parser.add_argument("--interval", type=float, default=0.05, help="RSS sample interval (s)")
    parser.add_argument("--budget-mb", type=float, default=2048.0)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--output", "-o", default=None)
    args = parser.parse_args()

    if args.pages and args.archetype:
        scales = [args.pages]
        archetypes = [args.archetype]
    else:
        scales = [int(s) for s in args.scales.split(",")]
        archetypes = [a.strip() for a in args.archetypes.split(",")]

    print("Peak-RSS benchmark")
    print(f"  interpreter: {sys.version.split()[0]} (GIL enabled: {sys._is_gil_enabled()})")
    print(f"  scales:      {', '.join(f'{s:,}' for s in scales)}")
    print(f"  archetypes:  {', '.join(archetypes)}")
    print(f"  budget:      {args.budget_mb:.0f} MB")
    print()

    cells: list[dict] = []
    for archetype in archetypes:
        for scale in scales:
            print(f"  [{archetype} x {scale:,}] building...", flush=True)
            cell = measure_cell(archetype, scale, args.interval)
            cells.append(cell)
            verdict = "OK" if cell["peak_rss_mb"] < args.budget_mb else "OVER BUDGET"
            print(
                f"    peak RSS: {cell['peak_rss_mb']:.0f} MB "
                f"({cell['wall_s']:.2f}s build)  [{verdict}]",
                flush=True,
            )

    print()
    print("=" * 64)
    print(f"PEAK RSS  (budget < {args.budget_mb:.0f} MB)")
    print("=" * 64)
    print(f"  {'Archetype':<10} {'Pages':>8} {'Peak RSS (MB)':>15} {'Build (s)':>11}")
    print("-" * 64)
    for c in cells:
        print(
            f"  {c['archetype']:<10} {c['pages']:>8,} "
            f"{c['peak_rss_mb']:>15.0f} {c['wall_s']:>11.2f}"
        )
    print()

    if args.output:
        Path(args.output).write_text(json.dumps(cells, indent=2))
        print(f"Raw JSON: {args.output}")

    if args.publish:
        stable = publish(cells, args.budget_mb)
        print(f"Baseline committed: {stable}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
