#!/usr/bin/env python
"""Process-isolation render *ceiling* probe — runnable on macOS arm64.

The free-threading question this answers
----------------------------------------
Bengal's render phase plateaus at ~1.7x in-process regardless of worker count,
with cpu/wall ~4.3 (cores busy, not lock-blocked). The diagnosed-but-unattributed
hypothesis is the free-threading **atomic-refcount / cache-coherency tax** on shared
objects every worker touches per page. The blocked question has been *which objects*
(needs Linux ``perf``/``py-spy --native``). But that is the wrong first question.

The first question is: **is the ~1.7x even fixable, or are we hardware-bound?**
That does NOT need object attribution, and it runs on macOS:

    Each OS process has its OWN heap  ->  zero cross-process refcount coherency.

So run K single-threaded render builds **concurrently as separate processes** and
compare aggregate render throughput to one single-threaded build:

  * If K processes scale ~K (up to the P-core count) while in-process threads
    plateau at ~1.7x  ->  the gap is PURE coherency tax. Owning per-page data /
    immortalizing the shared read-set can recover it. ~3.5x is on the table.
  * If K processes ALSO plateau (aggregate throughput saturates near ~1.7-2x)
    ->  the ceiling is memory-bandwidth / shared-hardware, NOT software sharing.
    Un-sharing in software cannot help; do not migrate.

Either outcome collapses the rfc-frozen-render-world decision tree with evidence,
on the hardware we actually have.

Usage
-----
    uv run python benchmarks/probe_render_ceiling.py --pages 500 --procs 5,8 --runs 2
    # worker mode is internal:
    uv run python benchmarks/probe_render_ceiling.py --worker --pages 500 [--threaded]

Discipline: measure on an IDLE machine (no other builds/agents). cpu/wall and
throughput are coherency-sensitive; a loaded run is worthless (this epic already
retracted one load-inflated number).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Reuse the authoritative fixture generator so the workload matches the committed
# gil_speedup / phase_attribution baselines exactly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from benchmarks.benchmark_gil_speedup import create_site


def _render_seconds(stats) -> float:
    """Pull the authoritative Rendering phase time (seconds) from BuildStats."""
    sd = stats.to_dict() if hasattr(stats, "to_dict") else {}
    ledger = sd.get("phase_timings_ms") or {}
    if "Rendering" in ledger:
        return float(ledger["Rendering"]) / 1000.0
    return float(sd.get("rendering_time_ms", 0)) / 1000.0


def run_worker(pages: int, threaded: bool) -> int:
    """Build ONE fixture site in-process; print {render_s, build_s, wall_s}.

    threaded=False  -> force_sequential=True  (single-threaded render: 1 core)
    threaded=True   -> force_sequential=False (in-process thread pool: the plateau)
    Fixture generation and import are OUTSIDE the reported render_s (phase ledger).
    """
    from bengal.core.site import Site
    from bengal.orchestration.build.options import BuildOptions

    tmp = Path(tempfile.mkdtemp(prefix=f"ceil_{pages}_"))
    try:
        create_site("blog", pages, tmp)
        site = Site.from_config(tmp)
        if site.output_dir.exists():
            shutil.rmtree(site.output_dir)
        site.output_dir.mkdir(parents=True)

        start = time.perf_counter()
        stats = site.build(
            BuildOptions(
                force_sequential=not threaded, incremental=False, verbose=False, quiet=True
            )
        )
        wall = time.perf_counter() - start
        sd = stats.to_dict() if hasattr(stats, "to_dict") else {}
        out = {
            "render_s": _render_seconds(stats),
            "build_s": float(sd.get("build_time_ms", wall * 1000)) / 1000.0,
            "wall_s": wall,
            "pages": int(sd.get("total_pages", pages)),
            "gil_enabled": sys._is_gil_enabled(),
            "threaded": threaded,
        }
        print(json.dumps(out))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _spawn(pages: int, threaded: bool) -> dict:
    """Launch one worker subprocess (own heap) and return its parsed JSON."""
    cmd = [sys.executable, __file__, "--worker", "--pages", str(pages)]
    if threaded:
        cmd.append("--threaded")
    proc = subprocess.run(cmd, capture_output=True, text=True, env={**os.environ})
    line = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    if not line:
        raise RuntimeError(f"worker produced no output. stderr:\n{proc.stderr[-2000:]}")
    return json.loads(line)


def _median(xs: list[float]) -> float:
    return statistics.median(xs)


def orchestrate(pages: int, proc_counts: list[int], runs: int) -> dict:

    p_cores_hint = None  # darwin: no clean public API; report cpu_count and let reader judge.
    cpu = os.cpu_count()

    # --- Baseline A: one single-threaded build, alone (honest per-core render rate) ---
    seq = [_spawn(pages, threaded=False)["render_s"] for _ in range(runs)]
    r_seq = _median(seq)

    # --- Baseline B: one in-process threaded build, alone (the ~1.7x plateau) ---
    thr = [_spawn(pages, threaded=True)["render_s"] for _ in range(runs)]
    r_thr = _median(thr)
    thread_speedup = r_seq / r_thr if r_thr else float("nan")

    # --- Probe: K single-threaded builds CONCURRENTLY (separate heaps) ---
    proc_results = {}
    for k in proc_counts:
        rounds = []
        for _ in range(runs):
            # Launch K workers truly concurrently; each reports its own internal render_s.
            with ThreadPoolExecutor(max_workers=k) as ex:
                futs = [ex.submit(_spawn, pages, False) for _ in range(k)]
                renders = [f.result()["render_s"] for f in futs]
            rounds.append(renders)
        # Per-process render time under K-way concurrency (median across all K*runs samples).
        flat = [r for rnd in rounds for r in rnd]
        r_under_k = _median(flat)
        slowdown = r_under_k / r_seq if r_seq else float("nan")
        # Aggregate speedup vs single core: K processes each rendered `pages`, concurrently.
        process_speedup = k * r_seq / r_under_k if r_under_k else float("nan")
        proc_results[k] = {
            "per_proc_render_s_median": r_under_k,
            "slowdown_vs_solo": slowdown,
            "process_speedup": process_speedup,
            "samples": flat,
        }

    return {
        "pages": pages,
        "cpu_count": cpu,
        "p_cores_hint": p_cores_hint,
        "runs": runs,
        "solo_sequential_render_s": r_seq,
        "solo_threaded_render_s": r_thr,
        "in_process_thread_speedup": thread_speedup,
        "process_isolation": proc_results,
    }


def _verdict(res: dict) -> str:
    thr = res["in_process_thread_speedup"]
    best_k = max(
        res["process_isolation"], key=lambda k: res["process_isolation"][k]["process_speedup"]
    )
    proc = res["process_isolation"][best_k]["process_speedup"]
    lines = []
    lines.append("")
    lines.append("=" * 72)
    lines.append("RENDER CEILING PROBE — verdict")
    lines.append("=" * 72)
    lines.append(f"  pages/build={res['pages']}  cpu_count={res['cpu_count']}  runs={res['runs']}")
    lines.append(
        f"  solo single-thread render : {res['solo_sequential_render_s']:.2f}s  (1 core, baseline)"
    )
    lines.append(
        f"  in-process threaded render: {res['solo_threaded_render_s']:.2f}s"
        f"  -> thread speedup {thr:.2f}x  (THE PLATEAU)"
    )
    for k, d in sorted(res["process_isolation"].items()):
        lines.append(
            f"  {k} isolated processes      : per-proc {d['per_proc_render_s_median']:.2f}s"
            f"  (slowdown {d['slowdown_vs_solo']:.2f}x)  -> aggregate {d['process_speedup']:.2f}x"
        )
    lines.append("-" * 72)
    if proc >= thr * 1.6:
        lines.append(f"  VERDICT: process isolation reaches {proc:.2f}x vs threads' {thr:.2f}x.")
        lines.append("  The plateau is the CROSS-THREAD COHERENCY TAX, not hardware.")
        lines.append("  => FIXABLE in software (owned per-page frames / immortalized read-set).")
        lines.append(
            f"  => Realistic render ceiling on this box is ~{proc:.1f}x. 3.5x is on the table."
        )
    else:
        lines.append(
            f"  VERDICT: process isolation only reaches {proc:.2f}x, near threads' {thr:.2f}x."
        )
        lines.append(
            "  The plateau is HARDWARE-bound (memory bandwidth / P-E asymmetry / shared cache)."
        )
        lines.append("  => Un-sharing in software will NOT help. Do not migrate render.")
    lines.append("=" * 72)
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--worker", action="store_true", help="internal: run one in-process build")
    ap.add_argument(
        "--threaded", action="store_true", help="worker: use the thread pool (else single-threaded)"
    )
    ap.add_argument("--pages", type=int, default=500)
    ap.add_argument(
        "--procs", type=str, default="5,8", help="comma list of process counts to probe"
    )
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--json-out", type=str, default="")
    args = ap.parse_args()

    if args.worker:
        return run_worker(args.pages, args.threaded)

    if sys._is_gil_enabled():
        print(
            "WARNING: GIL is ENABLED — run under a free-threaded interpreter (3.14t) for a valid probe.",
            file=sys.stderr,
        )

    proc_counts = [int(x) for x in args.procs.split(",") if x.strip()]
    res = orchestrate(args.pages, proc_counts, args.runs)
    print(json.dumps(res, indent=2))
    print(_verdict(res))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
