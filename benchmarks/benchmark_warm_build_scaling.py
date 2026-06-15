#!/usr/bin/env python3
"""
Warm / incremental build scaling baseline (record-only).
========================================================

Captures the cost of a single-page *warm* rebuild (the dev-server / HMR loop:
``prepare_for_rebuild()`` + ``build(incremental=True, changed_sources={file})``)
across two or more site sizes, and commits it as a stable JSON baseline under
``benchmarks/baselines/warm_build.json``.

Why this exists (issue #331, epic #330)
---------------------------------------
``benchmark_gil_speedup.py`` only ever runs ``incremental=False`` (cold builds).
There was no committed number for the warm single-page rebuild path, so the
v0.6.0 proportional-rebuild work (#332/#333) had nothing to prove its speedup
against. This baseline is that number: a deterministic record of how the warm
single-page rebuild scales with total page count *today*. The current build
re-renders proportionally to total pages on many edits, so this baseline is
expected to show warm cost rising with site size — exactly the curve the
proportional-discovery saga must flatten.

RECORD-ONLY (not a gate)
------------------------
This is a maintainer decision: the committed baseline and the comparison
consumer MEASURE and REPORT a delta, but they never fail CI on regression.
There is no hard threshold here. The point is to hand #332/#333 a number
without introducing a flaky-red check on shared CI runners. ``--compare``
ALWAYS exits 0. A real gate, if ever wanted, must be re-captured on stable,
idle, many-core hardware first (see ``benchmark_gil_speedup.py`` --gate*).

The committed numbers in ``warm_build.json`` were captured on the maintainer's
dev machine; treat them as a directional record, not an absolute spec.

Usage
-----
    # Capture + print (does NOT write the committed baseline)
    python benchmarks/benchmark_warm_build_scaling.py

    # Capture and (re)write the committed baseline JSON
    python benchmarks/benchmark_warm_build_scaling.py --publish

    # Re-run and compare against the committed baseline, printing the delta.
    # Record-only: exits 0 even on regression.
    python benchmarks/benchmark_warm_build_scaling.py --compare

    # Custom site sizes / warm-rebuild repeats
    python benchmarks/benchmark_warm_build_scaling.py --sizes 100,1000 --warm-builds 5

Methodology
-----------
For each site size we generate a synthetic multi-section markdown site, do one
cold build to warm caches, then time ``--warm-builds`` single-leaf-page warm
rebuilds (edit a leaf page, ``prepare_for_rebuild``, incremental build with that
file as the only changed source, restore the file). We report the cold time and
the warm single-page rebuild cost (first warm, mean, median, min). Median/min
are the most stable summary on a noisy dev machine; mean is kept for continuity
with the harness.
"""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Reuse the warm-build harness (cold build + repeated single-page warm rebuilds)
# and the committed results manager (timestamped history + latest.json), exactly
# like benchmark_gil_speedup.py does.
sys.path.insert(0, str(REPO_ROOT / "tests" / "performance"))
from benchmark_warm_build_consistency import (  # noqa: E402
    create_test_site,
    run_warm_build_consistency_benchmark,
)
from results_manager import BenchmarkResults  # noqa: E402

BASELINE_DIR = REPO_ROOT / "benchmarks" / "baselines"
BASELINE_FILE = BASELINE_DIR / "warm_build.json"

DEFAULT_SIZES = (100, 1000)
DEFAULT_WARM_BUILDS = 5

METHODOLOGY = (
    "WARM (incremental) single-page rebuild, NOT a cold build. For each site "
    "size: generate a synthetic multi-section markdown site, run one cold "
    "build(incremental=False) to warm caches, then time N warm rebuilds, each = "
    "edit one leaf page + Site.prepare_for_rebuild() + "
    "build(incremental=True, changed_sources={that page}) + restore the file "
    "(matches the dev-server BuildTrigger path). In-process Site.build, "
    "BuildProfile.WRITER, quiet. We report warm single-page rebuild cost "
    "(first / mean / median / min) per size. RECORD-ONLY: this baseline is a "
    "directional record captured on the maintainer's dev machine, not a CI gate."
)


def measure_size(num_pages: int, warm_builds: int) -> dict[str, float | int]:
    """Capture warm single-page rebuild stats for one site size."""
    site_root = create_test_site(num_pages=num_pages)
    try:
        result = run_warm_build_consistency_benchmark(
            site_root,
            num_warm_builds=warm_builds,
            quiet=True,
        )
        warm_times = list(result["warm_times"])
        return {
            "pages": num_pages,
            "warm_builds": warm_builds,
            "cold_s": result["cold_s"],
            "warm_first_s": result["warm_1_s"],
            "warm_mean_s": statistics.mean(warm_times) if warm_times else 0.0,
            "warm_median_s": statistics.median(warm_times) if warm_times else 0.0,
            "warm_min_s": min(warm_times) if warm_times else 0.0,
            "warm_times_s": [round(t, 6) for t in warm_times],
        }
    finally:
        shutil.rmtree(site_root, ignore_errors=True)


def run_capture(sizes: list[int], warm_builds: int) -> dict:
    """Capture a fresh warm-build scaling result payload (data block)."""
    cells: list[dict] = []
    print("Warm-build scaling capture")
    print(f"  sizes:       {', '.join(f'{s:,}' for s in sizes)}")
    print(f"  warm builds: {warm_builds} single-page rebuilds per size")
    print()
    for size in sizes:
        print(f"  [{size:,} pages] cold build + {warm_builds} warm rebuilds...")
        cell = measure_size(size, warm_builds)
        cells.append(cell)
        print(
            f"    cold={cell['cold_s']:.3f}s  "
            f"warm_first={cell['warm_first_s']:.3f}s  "
            f"warm_median={cell['warm_median_s']:.3f}s  "
            f"warm_min={cell['warm_min_s']:.3f}s"
        )
    return {"methodology": METHODOLOGY, "cells": cells}


def metadata(warm_builds: int) -> dict:
    return {
        "python_version": sys.version,
        "free_threaded": not sys._is_gil_enabled(),
        "warm_builds_per_size": warm_builds,
        "platform": sys.platform,
        "record_only": True,
    }


def publish(data: dict, meta: dict) -> Path:
    """Write the stable committed baseline + a timestamped history entry."""
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    mgr = BenchmarkResults(results_dir=BASELINE_DIR)
    mgr.save_result("warm_build", data, metadata=meta)
    BASELINE_FILE.write_text(json.dumps({"metadata": meta, "data": data}, indent=2) + "\n")
    return BASELINE_FILE


# ---------------------------------------------------------------------------
# Reusable comparison logic (so #332/#333 can assert a speedup against the
# committed baseline). compare_to_baseline() is pure: it takes a baseline
# payload + freshly-measured cells and returns per-size deltas. It NEVER decides
# pass/fail; callers (a future gate) impose their own threshold.
# ---------------------------------------------------------------------------

WARM_METRIC = "warm_median_s"


def load_baseline(path: Path = BASELINE_FILE) -> dict:
    """Load the committed baseline JSON ({'metadata':..., 'data':...})."""
    return json.loads(path.read_text())


def _cells_by_size(cells: list[dict]) -> dict[int, dict]:
    return {int(c["pages"]): c for c in cells}


def compare_to_baseline(
    baseline: dict,
    measured_cells: list[dict],
    metric: str = WARM_METRIC,
) -> list[dict]:
    """
    Compare freshly-measured cells against a committed baseline payload.

    Pure + reusable: returns one row per size that exists in BOTH, with the
    baseline value, the measured value, and the signed fractional delta
    (``(measured - baseline) / baseline``; negative = faster = improvement).
    Does NOT raise or decide pass/fail. #332/#333 can call this and assert
    ``row["delta"] <= -target_speedup`` to prove their improvement.
    """
    base_cells = _cells_by_size(baseline.get("data", {}).get("cells", []))
    meas_cells = _cells_by_size(measured_cells)
    rows: list[dict] = []
    for size in sorted(set(base_cells) & set(meas_cells)):
        b = base_cells[size].get(metric)
        m = meas_cells[size].get(metric)
        delta = ((m - b) / b) if (b and m is not None) else None
        rows.append(
            {
                "pages": size,
                "metric": metric,
                "baseline_s": b,
                "measured_s": m,
                "delta": delta,
                "speedup": (b / m) if (b and m) else None,
            }
        )
    return rows


def print_comparison(rows: list[dict]) -> None:
    print()
    print("=" * 78)
    print("WARM SINGLE-PAGE REBUILD: measured vs committed baseline (RECORD-ONLY)")
    print("=" * 78)
    print(
        f"  {'pages':>8} {'metric':>16} {'baseline':>10} {'measured':>10} {'delta':>8} {'speedup':>8}"
    )
    print("-" * 78)
    for r in rows:
        b = f"{r['baseline_s']:.3f}" if r["baseline_s"] is not None else "—"
        m = f"{r['measured_s']:.3f}" if r["measured_s"] is not None else "—"
        d = f"{r['delta']:+.1%}" if r["delta"] is not None else "—"
        sp = f"{r['speedup']:.2f}x" if r["speedup"] is not None else "—"
        print(f"  {r['pages']:>8,} {r['metric']:>16} {b:>10} {m:>10} {d:>8} {sp:>8}")
    print()
    print("RECORD-ONLY: this comparison reports the delta and ALWAYS exits 0.")
    print("It is not a gate. Negative delta = warm rebuild got faster.")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sizes",
        default=",".join(str(s) for s in DEFAULT_SIZES),
        help="Comma-separated site sizes in pages (default: 100,1000)",
    )
    parser.add_argument(
        "--warm-builds",
        type=int,
        default=DEFAULT_WARM_BUILDS,
        help="Single-page warm rebuilds to time per size (default: 5)",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Write the committed baseline (benchmarks/baselines/warm_build.json)",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Re-measure and print the delta vs the committed baseline. "
        "RECORD-ONLY: always exits 0, even on regression.",
    )
    parser.add_argument(
        "--output", "-o", default=None, help="Also write raw data JSON to this path"
    )
    args = parser.parse_args()

    sizes = [int(s) for s in args.sizes.split(",") if s.strip()]

    if args.compare:
        if not BASELINE_FILE.exists():
            print(
                f"ERROR: no committed baseline at {BASELINE_FILE}. "
                "Capture it first with --publish.",
                file=sys.stderr,
            )
            return 1
        baseline = load_baseline()
        data = run_capture(sizes, args.warm_builds)
        rows = compare_to_baseline(baseline, data["cells"])
        print_comparison(rows)
        # RECORD-ONLY: never fail on regression.
        return 0

    data = run_capture(sizes, args.warm_builds)
    meta = metadata(args.warm_builds)

    if args.output:
        Path(args.output).write_text(json.dumps({"metadata": meta, "data": data}, indent=2) + "\n")
        print(f"Raw JSON: {args.output}")

    if args.publish:
        path = publish(data, meta)
        print(f"Baseline committed: {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
