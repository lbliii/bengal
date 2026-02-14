#!/usr/bin/env python3
"""
Analyze benchmark results from GitHub Pages optimization suite.

This script processes pytest-benchmark JSON output and generates:
- Best configuration per site size
- Performance comparison tables
- Recommendations for GitHub Pages builds
- Resource usage analysis

Usage:
    pytest benchmarks/test_github_pages_optimization.py --benchmark-json=results.json
    python benchmarks/analyze_github_pages_results.py results.json
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_benchmark_results(json_path: Path) -> dict[str, Any]:
    """Load benchmark results from pytest-benchmark JSON output."""
    with open(json_path) as f:
        return json.load(f)


def parse_test_name(
    test_name: str, bench_data: dict[str, Any] | None = None
) -> tuple[str, int, str]:
    """
    Parse test name to extract site size and config.

    Format: test_build_configuration[default-site_50_pages-50]
    Or from params: {"site_fixture": "site_50_pages", "page_count": 50, "build_config": "..."}
    """
    # Try to get from params first (more reliable)
    if bench_data and "params" in bench_data:
        params = bench_data["params"]
        page_count = params.get("page_count", 0)
        site_fixture = params.get("site_fixture", "unknown")
        # Extract config from param string
        param_str = bench_data.get("param", "")
        config_str = param_str.split("-")[0] if "-" in param_str else "default"
        return site_fixture, page_count, config_str

    # Fallback: parse from test name
    if "[" in test_name:
        params = test_name.split("[")[1].rstrip("]")
        parts = params.split("-")
        if len(parts) >= 3:
            config_str = parts[0]
            site_fixture = parts[1]
            try:
                page_count = int(parts[2])
                return site_fixture, page_count, config_str
            except ValueError:
                pass

    # Fallback for other test names
    return "unknown", 0, "unknown"


def analyze_results(results: dict[str, Any]) -> dict[str, Any]:
    """Analyze benchmark results and generate insights."""
    benchmarks = results.get("benchmarks", [])

    # Group by site size
    by_size: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for bench in benchmarks:
        test_name = bench.get("name", "")
        _site_fixture, page_count, config_str = parse_test_name(test_name, bench)

        if page_count > 0:
            bench_data = {
                "test_name": test_name,
                "config": config_str,
                "mean": bench.get("stats", {}).get("mean", 0),
                "median": bench.get("stats", {}).get("median", 0),
                "min": bench.get("stats", {}).get("min", 0),
                "max": bench.get("stats", {}).get("max", 0),
                "stddev": bench.get("stats", {}).get("stddev", 0),
            }
            by_size[page_count].append(bench_data)

    # Find best configuration per size
    best_configs: dict[int, dict[str, Any]] = {}
    for page_count, configs in by_size.items():
        if configs:
            best = min(configs, key=lambda x: x["mean"])
            best_configs[page_count] = best

    # Calculate speedups vs baseline
    speedups: dict[int, dict[str, float]] = {}
    for page_count, configs in by_size.items():
        baseline = next((c for c in configs if "default" in c["config"] or c["config"] == ""), None)
        if baseline:
            baseline_time = baseline["mean"]
            speedups[page_count] = {c["config"]: baseline_time / c["mean"] for c in configs}

    return {
        "by_size": by_size,
        "best_configs": best_configs,
        "speedups": speedups,
    }


def print_analysis(analysis: dict[str, Any]) -> None:
    """Print formatted analysis results."""
    print("=" * 80)
    print("GitHub Pages Build Optimization Analysis")
    print("=" * 80)
    print()

    best_configs = analysis["best_configs"]
    speedups = analysis["speedups"]
    by_size = analysis["by_size"]

    # Best configurations per size
    print("🏆 Best Configuration per Site Size")
    print("-" * 80)
    for page_count in sorted(best_configs.keys()):
        best = best_configs[page_count]
        print(f"\n{page_count} pages:")
        print(f"  Config: {best['config']}")
        print(f"  Time: {best['mean']:.2f}s (mean)")
        print(f"  Pages/sec: {page_count / best['mean']:.1f}")

        # Show speedup vs baseline
        if page_count in speedups:
            config_speedup = speedups[page_count].get(best["config"], 1.0)
            if config_speedup > 1.0:
                print(f"  Speedup vs baseline: {config_speedup:.2f}x")

    print("\n" + "=" * 80)
    print("📊 Top 5 Configurations per Size")
    print("-" * 80)

    for page_count in sorted(by_size.keys()):
        configs = sorted(by_size[page_count], key=lambda x: x["mean"])
        top5 = configs[:5]

        print(f"\n{page_count} pages (top 5):")
        for i, config in enumerate(top5, 1):
            print(
                f"  {i}. {config['config']:<30} "
                f"{config['mean']:.2f}s "
                f"({page_count / config['mean']:.1f} pages/sec)"
            )

    print("\n" + "=" * 80)
    print("💡 Recommendations for GitHub Pages")
    print("-" * 80)

    # Generate recommendations
    recommendations = []

    # Check if fast mode helps
    fast_benefits = []
    for page_count in sorted(by_size.keys()):
        configs = by_size[page_count]
        default = next((c for c in configs if "default" in c["config"]), None)
        fast = next((c for c in configs if "fast" in c["config"]), None)

        if default and fast:
            speedup = default["mean"] / fast["mean"]
            if speedup > 1.05:  # >5% improvement
                fast_benefits.append((page_count, speedup))

    if fast_benefits:
        avg_speedup = sum(s[1] for s in fast_benefits) / len(fast_benefits)
        recommendations.append(
            f"✅ Use --fast flag: {avg_speedup:.2f}x average speedup (reduces logging overhead)"
        )

    # Check memory-optimized for large sites
    mem_benefits = []
    for page_count in sorted(by_size.keys()):
        if page_count >= 500:
            configs = by_size[page_count]
            default = next((c for c in configs if "default" in c["config"]), None)
            mem_opt = next((c for c in configs if "mem" in c["config"]), None)

            if default and mem_opt:
                # Memory-optimized might be slightly slower but uses less memory
                time_diff = (mem_opt["mean"] - default["mean"]) / default["mean"]
                if time_diff < 0.1:  # <10% slower
                    mem_benefits.append((page_count, time_diff))

    if mem_benefits:
        recommendations.append(
            "✅ Use --memory-optimized for sites with 500+ pages "
            "(prevents OOM on constrained workers)"
        )

    # Check parallel vs sequential
    parallel_benefits = []
    for page_count in sorted(by_size.keys()):
        configs = by_size[page_count]
        parallel = next((c for c in configs if "seq" not in c["config"]), None)
        sequential = next((c for c in configs if "seq" in c["config"]), None)

        if parallel and sequential:
            speedup = sequential["mean"] / parallel["mean"]
            parallel_benefits.append((page_count, speedup))

    if parallel_benefits:
        avg_speedup = sum(s[1] for s in parallel_benefits) / len(parallel_benefits)
        recommendations.append(
            f"✅ Parallel processing helps: {avg_speedup:.2f}x average speedup "
            f"on 2-core system (Python 3.14t free-threading)"
        )

    # Check CI-specific recommendations
    ci_configs = []
    for page_count in sorted(by_size.keys()):
        configs = by_size[page_count]
        ci = next(
            (
                c
                for c in configs
                if "fast" in c["config"] and "strict" in c["config"] and "clean" in c["config"]
            ),
            None,
        )
        if ci:
            ci_configs.append((page_count, ci))

    if ci_configs:
        recommendations.append(
            "✅ For CI/CD: Use --fast --strict --clean-output (optimal for GitHub Actions)"
        )

    for rec in recommendations:
        print(f"  {rec}")

    if not recommendations:
        print("  Run benchmarks to generate recommendations")

    print()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_github_pages_results.py <benchmark_json_file>")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    if not json_path.exists():
        print(f"Error: File not found: {json_path}")
        sys.exit(1)

    print(f"Loading results from: {json_path}")
    results = load_benchmark_results(json_path)

    print("Analyzing results...")
    analysis = analyze_results(results)

    print_analysis(analysis)


if __name__ == "__main__":
    main()
