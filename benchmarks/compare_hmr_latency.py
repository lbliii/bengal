#!/usr/bin/env python3
"""
Record-only HMR save-to-reload latency comparison.
===================================================

Re-measures the dev-loop save->reload latency (via ``benchmark_hmr_latency``)
and reports drift against the committed baseline at
``benchmarks/baselines/hmr_latency.json``.

This is a RECORD-ONLY consumer (the maintainer's explicit decision for #341):
it MEASURES and REPORTS but NEVER fails on a regression. Driving the async dev
server deterministically is timing-flaky; gating on it would produce flaky-red
CI. The point is to give v0.6.0's proportional-rebuild work (#332/#333) a number
to prove its speedup against, not to block merges.

It is runnable locally and from CI:

    python benchmarks/compare_hmr_latency.py            # measure + report drift
    python benchmarks/compare_hmr_latency.py --pages 50 --samples 5

Exit code is 0 unless the comparison itself could not run (e.g. no baseline
file, or measurement produced zero samples). A measured regression NEVER changes
the exit code.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "benchmarks"))

import benchmark_hmr_latency as hmr  # noqa: E402

BASELINE = REPO_ROOT / "benchmarks" / "baselines" / "hmr_latency.json"


def _baseline_cells() -> dict[int, dict]:
    if not BASELINE.exists():
        return {}
    data = json.loads(BASELINE.read_text())
    cells = data.get("data", {}).get("cells", [])
    return {c["pages"]: c for c in cells if c.get("pages") is not None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages", type=int, default=None, help="Override pages (default: baseline cells)"
    )
    parser.add_argument("--samples", type=int, default=5, help="Recorded samples per cell")
    parser.add_argument("--warmup", type=int, default=2, help="Discarded warmup edits per cell")
    parser.add_argument(
        "--timeout", type=float, default=20.0, help="Per-edit reload-signal timeout (s)"
    )
    args = parser.parse_args()

    baseline = _baseline_cells()
    if not baseline and args.pages is None:
        print(
            f"ERROR: no committed baseline at {BASELINE} and no --pages given. "
            "Capture a baseline first with: python benchmarks/benchmark_hmr_latency.py --publish",
            file=sys.stderr,
        )
        return 1

    scales = [args.pages] if args.pages is not None else sorted(baseline)

    print("HMR save->reload latency — RECORD-ONLY drift report (no gate)")
    print(f"  baseline: {BASELINE if baseline else '(none — measuring fresh)'}")
    print(f"  timer floor: {hmr.TIMER_FLOOR_MS:.0f}ms")
    print()

    any_samples = False
    print(f"  {'pages':>6} {'metric':>14} {'baseline':>11} {'measured':>11} {'delta':>9}  status")
    print("-" * 78)
    for pages in scales:
        cell = hmr.run_cell(
            pages=pages, samples=args.samples, warmup=args.warmup, timeout_s=args.timeout
        )
        if cell.median_total_ms is None:
            print(f"  {pages:>6} {'(no samples)':>14}  {cell.error}")
            continue
        any_samples = True
        base = baseline.get(pages, {})
        for metric, measured in (
            ("total_ms", cell.median_total_ms),
            ("variable_work_ms", cell.median_variable_work_ms),
        ):
            base_key = "total_ms_median" if metric == "total_ms" else "variable_work_ms_median"
            b = base.get(base_key)
            if b:
                delta = (measured - b) / b
                # RECORD ONLY: status is informational; never gates.
                status = "RECORD (faster)" if delta < 0 else "RECORD"
                print(
                    f"  {pages:>6} {metric:>14} {b:>11.1f} {measured:>11.1f} "
                    f"{delta:>+8.1%}  {status}"
                )
            else:
                print(
                    f"  {pages:>6} {metric:>14} {'(new)':>11} {measured:>11.1f} "
                    f"{'—':>9}  RECORD (no baseline)"
                )
    print()
    print("Record-only: this report never fails CI on a measured regression.")

    if not any_samples:
        print("ERROR: measurement produced zero samples; cannot report.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
