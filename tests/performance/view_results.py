#!/usr/bin/env python3
"""
View and compare benchmark results.

Usage:
    # List all available results
    python view_results.py list

    # View latest results for a benchmark
    python view_results.py show incremental_scale

    # Compare latest two runs
    python view_results.py compare incremental_scale

    # Show trend for a metric
    python view_results.py trend incremental_scale "scales.0.full_build_time"

    # Generate summary report
    python view_results.py report
"""

import argparse
import json
import sys
from datetime import datetime

from results_manager import BenchmarkResults, format_comparison, format_trends


def list_all_benchmarks(manager: BenchmarkResults):
    """List all benchmarks with results."""
    print("=" * 80)
    print("AVAILABLE BENCHMARK RESULTS")
    print("=" * 80)
    print()

    if not manager.results_dir.exists():
        print("No results directory found.")
        return

    benchmarks = sorted([d.name for d in manager.results_dir.iterdir() if d.is_dir()])

    if not benchmarks:
        print("No benchmarks have saved results yet.")
        return

    for benchmark in benchmarks:
        results = manager.list_results(benchmark)
        if results:
            latest = results[0]
            print(f"{benchmark}")
            print(f"  Latest: {latest['date']} {latest['timestamp'].split('T')[1][:8]}")
            print(f"  Total runs: {len(results)}")
            print()


def show_latest(manager: BenchmarkResults, benchmark: str):
    """Show the latest result for a benchmark."""
    try:
        result = manager.load_result(benchmark, "latest.json")
    except FileNotFoundError:
        print(f"No results found for benchmark: {benchmark}")
        return

    print("=" * 80)
    print(f"LATEST RESULT: {benchmark}")
    print("=" * 80)
    print()
    print(f"Timestamp: {result['timestamp']}")
    print()
    print("Data:")
    print("-" * 80)
    print(json.dumps(result["data"], indent=2))
    print()


def compare_runs(manager: BenchmarkResults, benchmark: str, files: list[str] = None):
    """Compare two benchmark runs."""
    try:
        if files:
            comparison = manager.compare_results(benchmark, files[0], files[1])
        else:
            comparison = manager.compare_results(benchmark)

        print(format_comparison(comparison))

        # Show more detailed comparison for incremental_scale
        if benchmark == "incremental_scale":
            _show_scale_comparison(comparison)

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")


def _show_scale_comparison(comparison: dict):
    """Show detailed comparison for incremental_scale benchmark."""
    current = comparison["current"]["data"]
    previous = comparison["previous"]["data"]

    if "scales" not in current or "scales" not in previous:
        return

    print()
    print("Detailed Comparison by Scale:")
    print("-" * 80)
    print(f"{'Scale':<10} {'Metric':<30} {'Current':<12} {'Previous':<12} {'Change':<12}")
    print("-" * 80)

    for i, (curr_scale, prev_scale) in enumerate(
        zip(current["scales"], previous["scales"], strict=False)
    ):
        pages = curr_scale["pages"]

        # Compare key metrics
        metrics = [
            ("Full Build", curr_scale["full_build_time"], prev_scale["full_build_time"], "s"),
            (
                "Incr Speedup",
                curr_scale["incr_single_speedup"],
                prev_scale["incr_single_speedup"],
                "x",
            ),
            ("Cache Size", curr_scale["cache_size_mb"], prev_scale["cache_size_mb"], "MB"),
        ]

        for metric_name, curr_val, prev_val, unit in metrics:
            delta = curr_val - prev_val
            delta_pct = (delta / prev_val * 100) if prev_val != 0 else 0

            sign = "+" if delta > 0 else ""
            delta_str = f"{sign}{delta:.2f} ({sign}{delta_pct:.1f}%)"

            # Color code: green for improvements, red for regressions
            if metric_name == "Incr Speedup" and delta > 0:
                delta_str = f"✅ {delta_str}"
            elif metric_name == "Incr Speedup" and delta < -1:
                delta_str = f"❌ {delta_str}"
            elif "Build" in metric_name and delta < 0:
                delta_str = f"✅ {delta_str}"
            elif "Build" in metric_name and delta > 0.5:
                delta_str = f"⚠️  {delta_str}"

            print(
                f"{pages if metric_name == metrics[0][0] else '':<10} "
                f"{metric_name:<30} "
                f"{curr_val:>8.2f}{unit:<4} "
                f"{prev_val:>8.2f}{unit:<4} "
                f"{delta_str:<12}"
            )

        if i < len(current["scales"]) - 1:
            print()


def show_trend(manager: BenchmarkResults, benchmark: str, metric: str, limit: int):
    """Show trend for a metric."""
    try:
        trend_data = manager.get_trends(benchmark, metric, limit)

        if not trend_data:
            print(f"No trend data found for {benchmark} / {metric}")
            return

        print(format_trends(trend_data, f"{benchmark} - {metric}"))

        # Calculate statistics
        values = [p["value"] for p in trend_data]
        if len(values) >= 2:
            print()
            print("Statistics:")
            print(f"  Min:    {min(values):.3f}")
            print(f"  Max:    {max(values):.3f}")
            print(f"  Mean:   {sum(values) / len(values):.3f}")
            print(f"  Latest: {values[0]:.3f}")
            print(
                f"  Change: {values[0] - values[-1]:+.3f} ({((values[0] - values[-1]) / values[-1] * 100):+.1f}%)"
            )

    except Exception as e:
        print(f"Error: {e}")


def generate_report(manager: BenchmarkResults):
    """Generate summary report of all recent results."""
    print("=" * 80)
    print("BENCHMARK SUMMARY REPORT")
    print("=" * 80)
    print()
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    benchmarks = sorted([d.name for d in manager.results_dir.iterdir() if d.is_dir()])

    if not benchmarks:
        print("No results available.")
        return

    for benchmark in benchmarks:
        results = manager.list_results(benchmark)
        if not results:
            continue

        print(f"\n{benchmark}")
        print("-" * 80)

        try:
            latest = manager.load_result(benchmark, "latest.json")
            print(f"Latest run: {latest['timestamp']}")
            print(f"Total runs: {len(results)}")

            # Show key metrics based on benchmark type
            data = latest["data"]

            if benchmark == "incremental_scale":
                if "summary" in data:
                    summary = data["summary"]
                    print(
                        f"Speedup range: {summary['min_speedup']:.1f}x - {summary['max_speedup']:.1f}x"
                    )
                    print(f"Average speedup: {summary['avg_speedup']:.1f}x")
                    print(f"Largest scale: {summary['largest_scale']:,} pages")
                    print(f"Status: {'✅ PASS' if summary['all_passed'] else '❌ FAIL'}")

            elif benchmark == "stability":
                if "summary" in data:
                    summary = data["summary"]
                    print(f"Builds tested: {summary.get('num_builds', 'N/A')}")
                    print(f"Performance change: {summary.get('degradation_pct', 0):+.1f}%")
                    print(f"Memory growth: {summary.get('memory_growth_mb', 0):+.1f}MB")
                    print(f"Status: {'✅ STABLE' if summary.get('all_passed') else '⚠️  ISSUES'}")

            elif benchmark == "template_complexity" and "complexity_levels" in data:
                overheads = [
                    level["overhead_pct"]
                    for level in data["complexity_levels"]
                    if level["name"] != "baseline"
                ]
                if overheads:
                    print(f"Overhead range: {min(overheads):.1f}% - {max(overheads):.1f}%")
                    print(f"Heavy templates: {[o for o in overheads if o > 20]}")

        except Exception as e:
            print(f"Error loading result: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="View and compare benchmark results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    subparsers.add_parser("list", help="List all benchmarks with results")

    # Show command
    show_parser = subparsers.add_parser("show", help="Show latest result")
    show_parser.add_argument("benchmark", help="Benchmark name")

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two runs")
    compare_parser.add_argument("benchmark", help="Benchmark name")
    compare_parser.add_argument(
        "--files",
        nargs=2,
        help="Two result files to compare (default: latest vs previous)",
    )

    # Trend command
    trend_parser = subparsers.add_parser("trend", help="Show trend for a metric")
    trend_parser.add_argument("benchmark", help="Benchmark name")
    trend_parser.add_argument("metric", help="Metric path (e.g., 'scales.0.full_build_time')")
    trend_parser.add_argument("--limit", type=int, default=10, help="Number of results")

    # Report command
    subparsers.add_parser("report", help="Generate summary report")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    manager = BenchmarkResults()

    if args.command == "list":
        list_all_benchmarks(manager)

    elif args.command == "show":
        show_latest(manager, args.benchmark)

    elif args.command == "compare":
        compare_runs(manager, args.benchmark, args.files)

    elif args.command == "trend":
        show_trend(manager, args.benchmark, args.metric, args.limit)

    elif args.command == "report":
        generate_report(manager)

    return 0


if __name__ == "__main__":
    sys.exit(main())
