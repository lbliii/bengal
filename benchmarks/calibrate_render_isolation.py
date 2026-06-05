#!/usr/bin/env python3
"""
Calibrate the isolated-render crossover threshold (issue #350, saga S5).

The isolated (separate-heap) render backend wins above some page count and loses
below it (fixed per-worker startup cost). This script sweeps synthetic render
sets of increasing size and reports, for each size, the in-thread wall time vs
the fork wall time, so you can read off where fork overtakes threads — the value
to set as ``[build] render_isolation_threshold``.

It reuses the self-contained ceiling probe's machinery conceptually but drives it
against a single prepared site by *replicating* its parsed pages to hit target
sizes without needing many fixtures.

Usage
-----
    PYTHONPATH=. python benchmarks/calibrate_render_isolation.py <site_root> \\
        [--workers N] [--sizes 50,100,200,400,800,1600]

Run on an idle box; numbers on a busy laptop only show the rough crossover.
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

_STATE: dict[str, object] | None = None


def _render(indices: list[int]) -> int:
    from bengal.orchestration.render.pipeline_runner import process_page_with_pipeline

    assert _STATE is not None
    site, ctx, pages = _STATE["site"], _STATE["ctx"], _STATE["pages"]  # type: ignore[index]
    for i in indices:
        process_page_with_pipeline(
            pages[i],
            site=site,
            quiet=True,
            stats=None,
            build_context=ctx,
            changed_sources=None,
            block_cache=None,
            highlight_cache=None,
            output_collector=None,
        )
    return len(indices)


def _chunks(n: int, k: int) -> list[list[int]]:
    k = max(1, min(k, n))
    base, extra = divmod(n, k)
    out, start = [], 0
    for c in range(k):
        size = base + (1 if c < extra else 0)
        out.append(list(range(start, start + size)))
        start += size
    return out


def _thread_wall(n: int, workers: int) -> float:
    import concurrent.futures

    t = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(_render, _chunks(n, workers)))
    return time.perf_counter() - t


def _fork_wall(n: int, workers: int) -> float:
    ctx_mp = mp.get_context("fork")
    chunks = _chunks(n, workers)
    t = time.perf_counter()
    pool = ctx_mp.Pool(processes=len(chunks))
    try:
        list(pool.map(_render, chunks))
    finally:
        pool.close()
        pool.join()
    return time.perf_counter() - t


def _prepare(root: Path) -> None:
    global _STATE
    from bengal.core.site import Site
    from bengal.orchestration.build.options import BuildOptions
    from bengal.orchestration.build_context import BuildContext
    from bengal.snapshots import create_site_snapshot

    site = Site.from_config(root)
    site.output_dir = Path(tempfile.mkdtemp(prefix="calib-warm-"))
    site.build(BuildOptions(quiet=True))
    snap = create_site_snapshot(site)
    _STATE = {
        "site": site,
        "ctx": BuildContext(site=site, snapshot=snap),
        "pages": list(site.pages),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("site_root", type=Path)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--sizes", default="50,100,200,400,800,1600")
    ap.add_argument("--runs", type=int, default=2)
    args = ap.parse_args()
    if "fork" not in mp.get_all_start_methods():
        print("fork unavailable; cannot calibrate")
        return 2

    _prepare(args.site_root)
    assert _STATE is not None
    base_pages = _STATE["pages"]  # type: ignore[index]
    base_n = len(base_pages)
    if base_n == 0:
        print("no pages")
        return 1

    print(f"Calibrating from {base_n} real pages (cycled to hit sizes), {args.workers} workers\n")
    print(f"  {'pages':>6}  {'threads':>9}  {'fork':>9}  winner")
    crossover = None
    for size in (int(s) for s in args.sizes.split(",")):
        # Cycle indices to reach `size` render ops without new fixtures.
        idx = [i % base_n for i in range(size)]
        _STATE["pages"] = [base_pages[i] for i in idx]  # type: ignore[index]
        thr = statistics.median(_thread_wall(size, args.workers) for _ in range(args.runs))
        frk = statistics.median(_fork_wall(size, args.workers) for _ in range(args.runs))
        winner = "fork" if frk < thr else "threads"
        if crossover is None and frk < thr:
            crossover = size
        print(f"  {size:>6}  {thr * 1000:>7.0f}ms  {frk * 1000:>7.0f}ms  {winner}")

    print()
    if crossover:
        print(f"  Suggested [build] render_isolation_threshold ≈ {crossover}")
    else:
        print("  Fork did not overtake threads in this range; raise --sizes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
