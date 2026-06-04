#!/usr/bin/env python3
"""
Render-scaling ceiling probe — thread path vs. separate-heap (process) path.

Issue #350 (epic) / saga S1 — the *funding gate* for the heap-isolation render
backend. This probe measures the gap the epic is built to recover: how fast the
*same* render work goes in-thread (free-threaded ThreadPool) versus in separate
heaps (fork ProcessPool), each over a sequential baseline, on the *same* parsed
page set and the *same* machine.

What it answers
---------------
- Thread speedup  = sequential_wall / thread_wall   (the in-process plateau)
- Process speedup = sequential_wall / process_wall  (the separate-heap ceiling)
- cpu/wall ratio  = process_cpu_time / process_wall  (cores busy, not blocked)

A large process>thread gap with high cpu/wall is the signature the epic
attributes to allocator/GC/interpreter-level contention that only separate heaps
can recover (see ``benchmarks/render-scaling-attribution-findings.md`` and the
``py-spy --native`` gate in ``benchmarks/COHERENCY_PROFILING.md``).

Methodology notes
-----------------
- The site is built once normally to warm markdown parsing, so every timed
  render reads ``page.html_content`` from memory — we time *rendering*, not
  parsing (parsing is ~0% of the prize; rendering is the 68%).
- Each variant renders into its own throwaway output dir, so disk writes never
  collide and byte output can be diffed independently.
- Median-of-N (default 3) for contamination robustness. Run on an idle box.
- Fork is used for the process path because, like the production backend, it
  shares the parsed site read-only via copy-on-write with zero serialization.

Usage
-----
    PYTHONPATH=. python benchmarks/probe_render_ceiling.py <site_root> \\
        [--workers N] [--runs 3]

This script is intentionally self-contained: it does not import the production
isolated-render backend, so it can serve as an independent oracle for it.
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

# Module-global parent state shared with forked workers via copy-on-write.
# Set in the parent BEFORE the fork Pool is created; never sent through the queue.
_PROBE_STATE: dict[str, object] | None = None


def _render_indices(indices: list[int]) -> int:
    """Render a chunk of pages by index. Runs in a forked worker (or inline)."""
    from bengal.orchestration.render.pipeline_runner import process_page_with_pipeline

    assert _PROBE_STATE is not None
    site = _PROBE_STATE["site"]
    ctx = _PROBE_STATE["ctx"]
    pages = _PROBE_STATE["pages"]  # type: ignore[assignment]
    count = 0
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
        count += 1
    return count


def _balanced_chunks(n: int, k: int) -> list[list[int]]:
    """Split range(n) into k contiguous, near-equal chunks (deterministic)."""
    k = max(1, min(k, n))
    base, extra = divmod(n, k)
    chunks: list[list[int]] = []
    start = 0
    for c in range(k):
        size = base + (1 if c < extra else 0)
        chunks.append(list(range(start, start + size)))
        start += size
    return chunks


def _time_sequential(n: int) -> tuple[float, float]:
    wall0, cpu0 = time.perf_counter(), time.process_time()
    _render_indices(list(range(n)))
    return time.perf_counter() - wall0, time.process_time() - cpu0


def _time_threads(n: int, workers: int) -> tuple[float, float]:
    import concurrent.futures

    chunks = _balanced_chunks(n, workers)
    wall0, cpu0 = time.perf_counter(), time.process_time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(_render_indices, chunks))
    return time.perf_counter() - wall0, time.process_time() - cpu0


def _time_fork(n: int, workers: int) -> tuple[float, float]:
    chunks = _balanced_chunks(n, workers)
    ctx_mp = mp.get_context("fork")
    # Children CPU is only folded into os.times() once workers are reaped, so we
    # close()+join() the pool (rather than terminate() via __exit__) before
    # sampling after-times.
    before = os.times()
    wall0 = time.perf_counter()
    pool = ctx_mp.Pool(processes=len(chunks))
    try:
        list(pool.map(_render_indices, chunks))
    finally:
        pool.close()
        pool.join()
    wall = time.perf_counter() - wall0
    after = os.times()
    cpu = (after.children_user - before.children_user) + (
        after.children_system - before.children_system
    )
    return wall, cpu


def _prepare(site_root: Path) -> int:
    """Build once to warm parsing, then install probe state. Returns page count."""
    from bengal.core.site import Site
    from bengal.orchestration.build.options import BuildOptions
    from bengal.orchestration.build_context import BuildContext
    from bengal.snapshots import create_site_snapshot

    global _PROBE_STATE
    site = Site.from_config(site_root)
    warm_out = Path(tempfile.mkdtemp(prefix="probe-warm-"))
    site.output_dir = warm_out
    site.build(BuildOptions(quiet=True))

    # Pages now carry parsed html_content. Build a fresh frozen snapshot + ctx.
    snapshot = create_site_snapshot(site)
    pages = list(site.pages)
    ctx = BuildContext(site=site, pages=pages, snapshot=snapshot, parallel=True)

    _PROBE_STATE = {"site": site, "ctx": ctx, "pages": pages}
    return len(pages)


def _redirect_output(tag: str) -> None:
    """Point the shared site at a throwaway output dir for this variant."""
    assert _PROBE_STATE is not None
    site = _PROBE_STATE["site"]
    site.output_dir = Path(tempfile.mkdtemp(prefix=f"probe-{tag}-"))  # type: ignore[attr-defined]


def _median_run(fn, n: int, workers: int | None, runs: int) -> tuple[float, float]:
    walls: list[float] = []
    cpus: list[float] = []
    for _ in range(runs):
        if workers is None:
            w, c = fn(n)
        else:
            w, c = fn(n, workers)
        walls.append(w)
        cpus.append(c)
    return statistics.median(walls), statistics.median(cpus)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("site_root", type=Path)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args()

    if "fork" not in mp.get_all_start_methods():
        print("fork start method unavailable on this platform; probe needs fork.")
        return 2

    n = _prepare(args.site_root)
    if n == 0:
        print("No pages to render.")
        return 1

    print(f"Probing {n} pages, {args.workers} workers, median-of-{args.runs}\n")

    _redirect_output("seq")
    seq_wall, seq_cpu = _median_run(lambda nn: _time_sequential(nn), n, None, args.runs)

    _redirect_output("thr")
    thr_wall, thr_cpu = _median_run(_time_threads, n, args.workers, args.runs)

    _redirect_output("frk")
    frk_wall, frk_cpu = _median_run(_time_fork, n, args.workers, args.runs)

    def row(label: str, wall: float, cpu: float, base: float) -> str:
        speedup = base / wall if wall else 0.0
        cpw = cpu / wall if wall else 0.0
        return f"  {label:<22} {wall * 1000:8.0f}ms  {speedup:5.2f}x  cpu/wall={cpw:4.2f}"

    print(row("sequential (1 core)", seq_wall, seq_cpu, seq_wall))
    print(row(f"threads x{args.workers}", thr_wall, thr_cpu, seq_wall))
    print(row(f"fork procs x{args.workers}", frk_wall, frk_cpu, seq_wall))
    print()
    gap = (seq_wall / frk_wall) / (seq_wall / thr_wall) if thr_wall and frk_wall else 0.0
    print(f"  separate-heap advantage over threads: {gap:5.2f}x")
    print(
        "\n  If this gap is large (>1.3x) with high fork cpu/wall, the residual is\n"
        "  allocator/GC/interpreter contention recoverable only by separate heaps —\n"
        "  the thesis of issue #350. Confirm allocator specifically via the\n"
        "  py-spy --native gate in benchmarks/COHERENCY_PROFILING.md."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
