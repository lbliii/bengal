#!/usr/bin/env python3
"""Benchmark Bengal build performance across scenarios.

Scenarios:
- cold_full: cache/output reset before each run, full build
- warm_incremental: warmup build, then incremental build timing

Optional:
- compare current branch against another git ref (default: main) via worktree

Outputs:
- JSON summary (always)
- CSV row dump (optional)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import statistics
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RunResult:
    scenario: str
    elapsed_ms: float
    success: bool
    return_code: int
    stderr_preview: str


def _reset_state(site_dir: Path) -> None:
    reset_paths = [
        site_dir / ".bengal" / "cache",
        site_dir / ".bengal" / "state",
        site_dir / ".bengal" / "provenance",
        site_dir / "public",
    ]
    for path in reset_paths:
        shutil.rmtree(path, ignore_errors=True)


def _run_build(
    repo_root: Path,
    site_dir: Path,
    *,
    incremental: bool,
    extra_env: dict[str, str] | None = None,
) -> RunResult:
    cmd = [
        "bengal",
        "build",
        "--quiet",
        "--incremental" if incremental else "--no-incremental",
        str(site_dir),
    ]
    env = None
    if extra_env:
        env = {**os.environ, **extra_env}

    start = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        env=env,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000
    stderr_preview = (proc.stderr or "").strip()[:300]
    scenario = "warm_incremental" if incremental else "cold_full"
    return RunResult(
        scenario=scenario,
        elapsed_ms=elapsed_ms,
        success=proc.returncode == 0,
        return_code=proc.returncode,
        stderr_preview=stderr_preview,
    )


def _scenario_cold_full(repo_root: Path, site_dir: Path, runs: int) -> list[RunResult]:
    results: list[RunResult] = []
    for _ in range(runs):
        _reset_state(site_dir)
        results.append(_run_build(repo_root, site_dir, incremental=False))
    return results


def _scenario_warm_incremental(repo_root: Path, site_dir: Path, runs: int) -> list[RunResult]:
    results: list[RunResult] = []
    for _ in range(runs):
        _reset_state(site_dir)
        # Warmup run builds cache/state.
        warmup = _run_build(repo_root, site_dir, incremental=False)
        if not warmup.success:
            results.append(
                RunResult(
                    scenario="warm_incremental",
                    elapsed_ms=0.0,
                    success=False,
                    return_code=warmup.return_code,
                    stderr_preview=warmup.stderr_preview,
                )
            )
            continue
        results.append(_run_build(repo_root, site_dir, incremental=True))
    return results


def _summarize(results: list[RunResult]) -> dict[str, object]:
    by_scenario: dict[str, list[RunResult]] = {}
    for result in results:
        by_scenario.setdefault(result.scenario, []).append(result)

    summary: dict[str, object] = {}
    for scenario, entries in by_scenario.items():
        successes = [entry.elapsed_ms for entry in entries if entry.success]
        summary[scenario] = {
            "runs": len(entries),
            "successes": sum(1 for entry in entries if entry.success),
            "mean_ms": statistics.fmean(successes) if successes else None,
            "median_ms": statistics.median(successes) if successes else None,
            "min_ms": min(successes) if successes else None,
            "max_ms": max(successes) if successes else None,
            "failures": [
                {"return_code": entry.return_code, "stderr_preview": entry.stderr_preview}
                for entry in entries
                if not entry.success
            ],
        }
    return summary


def _benchmark_repo(repo_root: Path, site_dir: Path, runs: int) -> dict[str, object]:
    cold = _scenario_cold_full(repo_root, site_dir, runs)
    warm = _scenario_warm_incremental(repo_root, site_dir, runs)
    all_results = [*cold, *warm]
    return {
        "repo_root": str(repo_root),
        "site_dir": str(site_dir),
        "results": [
            {
                "scenario": item.scenario,
                "elapsed_ms": item.elapsed_ms,
                "success": item.success,
                "return_code": item.return_code,
                "stderr_preview": item.stderr_preview,
            }
            for item in all_results
        ],
        "summary": _summarize(all_results),
    }


def _write_csv(path: Path, payloads: dict[str, dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["label", "scenario", "elapsed_ms", "success", "return_code"])
        for label, payload in payloads.items():
            rows = payload.get("results", [])
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                writer.writerow([
                    label,
                    row.get("scenario", ""),
                    row.get("elapsed_ms", ""),
                    row.get("success", ""),
                    row.get("return_code", ""),
                ])


def _benchmark_ref(repo_root: Path, site_rel: Path, ref: str, runs: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="bengal-bench-", dir=repo_root) as temp_dir:
        worktree_path = Path(temp_dir) / "repo"
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(worktree_path), ref],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        try:
            return _benchmark_repo(worktree_path, worktree_path / site_rel, runs)
        finally:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree_path)],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Bengal build matrix")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Path to Bengal repository root",
    )
    parser.add_argument(
        "--site",
        type=Path,
        default=Path("site"),
        help="Site directory relative to repo root (default: site)",
    )
    parser.add_argument("--runs", type=int, default=3, help="Runs per scenario")
    parser.add_argument(
        "--compare-ref",
        type=str,
        default=None,
        help="Optional git ref to benchmark via temporary worktree (e.g., main)",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("benchmarks/build_matrix_results.json"),
        help="Path for JSON output",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Optional path for CSV row output",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    site_dir = (repo_root / args.site).resolve()
    if not site_dir.exists():
        raise SystemExit(f"Site directory not found: {site_dir}")

    payloads: dict[str, dict[str, object]] = {
        "current": _benchmark_repo(repo_root, site_dir, args.runs),
    }
    if args.compare_ref:
        payloads[args.compare_ref] = _benchmark_ref(repo_root, args.site, args.compare_ref, args.runs)

    output = {
        "generated_at": datetime.now(UTC).isoformat(),
        "runs_per_scenario": args.runs,
        "payloads": payloads,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output, indent=2))
    if args.output_csv is not None:
        _write_csv(args.output_csv, payloads)

    print(json.dumps(output["payloads"], indent=2))
    print(f"\nSaved benchmark JSON: {args.output_json}")
    if args.output_csv is not None:
        print(f"Saved benchmark CSV:  {args.output_csv}")


if __name__ == "__main__":
    main()
