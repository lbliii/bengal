"""
Results storage and comparison for performance benchmarks.

Saves benchmark results in structured JSON format with timestamps,
allowing for historical tracking and comparison across runs.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class BenchmarkResults:
    """Store and manage benchmark results."""

    def __init__(self, results_dir: Path | None = None):
        """
        Initialize results manager.

        Args:
            results_dir: Directory to store results. Defaults to ./benchmark_results/
        """
        if results_dir is None:
            results_dir = Path(__file__).parent / "benchmark_results"

        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)

    def save_result(
        self,
        benchmark_name: str,
        data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """
        Save a benchmark result with timestamp.

        Args:
            benchmark_name: Name of the benchmark (e.g., 'incremental_scale')
            data: Benchmark data to save
            metadata: Optional metadata (git commit, system info, etc.)

        Returns:
            Path to saved results file
        """
        timestamp = datetime.now()

        result = {
            "benchmark": benchmark_name,
            "timestamp": timestamp.isoformat(),
            "date": timestamp.strftime("%Y-%m-%d"),
            "time": timestamp.strftime("%H:%M:%S"),
            "data": data,
            "metadata": metadata or {},
        }

        # Create benchmark directory
        benchmark_dir = self.results_dir / benchmark_name
        benchmark_dir.mkdir(exist_ok=True)

        # Save with timestamp in filename
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = benchmark_dir / filename

        with open(filepath, "w") as f:
            json.dump(result, f, indent=2)

        # Also save as "latest.json" for easy access
        latest_path = benchmark_dir / "latest.json"
        with open(latest_path, "w") as f:
            json.dump(result, f, indent=2)

        return filepath

    def load_result(self, benchmark_name: str, filename: str = "latest.json") -> dict:
        """
        Load a specific benchmark result.

        Args:
            benchmark_name: Name of the benchmark
            filename: Filename or "latest.json" for most recent

        Returns:
            Loaded result data
        """
        filepath = self.results_dir / benchmark_name / filename

        if not filepath.exists():
            raise FileNotFoundError(f"No results found: {filepath}")

        with open(filepath) as f:
            return json.load(f)

    def list_results(self, benchmark_name: str) -> list[dict]:
        """
        List all results for a benchmark.

        Args:
            benchmark_name: Name of the benchmark

        Returns:
            List of result metadata (timestamp, filename)
        """
        benchmark_dir = self.results_dir / benchmark_name

        if not benchmark_dir.exists():
            return []

        results = []
        for filepath in sorted(benchmark_dir.glob("*.json")):
            if filepath.name == "latest.json":
                continue

            try:
                with open(filepath) as f:
                    data = json.load(f)

                results.append(
                    {
                        "filename": filepath.name,
                        "timestamp": data.get("timestamp"),
                        "date": data.get("date"),
                        "path": str(filepath),
                    }
                )
            except Exception:
                pass

        return sorted(results, key=lambda x: x["timestamp"], reverse=True)

    def compare_results(
        self,
        benchmark_name: str,
        result1_file: str = "latest.json",
        result2_file: str | None = None,
    ) -> dict:
        """
        Compare two benchmark results.

        Args:
            benchmark_name: Name of the benchmark
            result1_file: First result file (default: latest)
            result2_file: Second result file (default: second-latest)

        Returns:
            Comparison data with deltas
        """
        result1 = self.load_result(benchmark_name, result1_file)

        # If no second file specified, get second-latest
        if result2_file is None:
            all_results = self.list_results(benchmark_name)
            if len(all_results) < 2:
                raise ValueError("Need at least 2 results to compare")
            result2_file = all_results[1]["filename"]

        result2 = self.load_result(benchmark_name, result2_file)

        return {
            "benchmark": benchmark_name,
            "current": {
                "timestamp": result1["timestamp"],
                "data": result1["data"],
            },
            "previous": {
                "timestamp": result2["timestamp"],
                "data": result2["data"],
            },
            "comparison": self._compute_deltas(result1["data"], result2["data"]),
        }

    def _compute_deltas(self, current: dict, previous: dict) -> dict:
        """Compute deltas between two result sets."""
        deltas = {}

        # Handle different benchmark formats
        if "full_build" in current and "full_build" in previous:
            # Incremental scale benchmark
            deltas["full_build_time_delta"] = (
                current["full_build"]["time"] - previous["full_build"]["time"]
            )
            deltas["speedup_delta"] = current["single_speedup"] - previous["single_speedup"]

        # Add more specific delta calculations as needed

        return deltas

    def get_trends(self, benchmark_name: str, metric: str, limit: int = 10) -> list:
        """
        Get trend data for a specific metric.

        Args:
            benchmark_name: Name of the benchmark
            metric: Metric path (e.g., 'full_build.time')
            limit: Number of results to include

        Returns:
            List of (timestamp, value) tuples
        """
        all_results = self.list_results(benchmark_name)[:limit]

        trend_data = []
        for result_info in all_results:
            try:
                result = self.load_result(benchmark_name, result_info["filename"])

                # Navigate metric path
                value = result["data"]
                for key in metric.split("."):
                    value = value[key]

                trend_data.append(
                    {
                        "timestamp": result["timestamp"],
                        "value": value,
                    }
                )
            except (KeyError, TypeError):
                pass

        return trend_data


def format_comparison(comparison: dict) -> str:
    """Format comparison data as readable text."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"BENCHMARK COMPARISON: {comparison['benchmark']}")
    lines.append("=" * 80)
    lines.append("")

    lines.append(f"Current:  {comparison['current']['timestamp']}")
    lines.append(f"Previous: {comparison['previous']['timestamp']}")
    lines.append("")

    # Format deltas
    deltas = comparison["comparison"]
    if deltas:
        lines.append("Changes:")
        for key, value in deltas.items():
            if isinstance(value, float):
                sign = "+" if value > 0 else ""
                lines.append(f"  {key}: {sign}{value:.3f}")
            else:
                lines.append(f"  {key}: {value}")

    return "\n".join(lines)


def format_trends(trend_data: list, metric_name: str) -> str:
    """Format trend data as readable text."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"TREND: {metric_name}")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"{'Timestamp':<25} {'Value':<15}")
    lines.append("-" * 80)

    for point in trend_data:
        ts = datetime.fromisoformat(point["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        value = point["value"]

        if isinstance(value, float):
            lines.append(f"{ts:<25} {value:>12.3f}")
        else:
            lines.append(f"{ts:<25} {value:>12}")

    return "\n".join(lines)


if __name__ == "__main__":
    # Example usage
    import argparse

    parser = argparse.ArgumentParser(description="Manage benchmark results")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    list_parser = subparsers.add_parser("list", help="List results for a benchmark")
    list_parser.add_argument("benchmark", help="Benchmark name")

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two results")
    compare_parser.add_argument("benchmark", help="Benchmark name")
    compare_parser.add_argument(
        "--files",
        nargs=2,
        help="Two result files to compare (default: latest vs previous)",
    )

    # Trend command
    trend_parser = subparsers.add_parser("trend", help="Show trend for a metric")
    trend_parser.add_argument("benchmark", help="Benchmark name")
    trend_parser.add_argument("metric", help="Metric path (e.g., 'full_build.time')")
    trend_parser.add_argument("--limit", type=int, default=10, help="Number of results")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        exit(1)

    manager = BenchmarkResults()

    if args.command == "list":
        results = manager.list_results(args.benchmark)
        print(f"\nResults for {args.benchmark}:")
        print("-" * 80)
        for r in results:
            print(f"{r['date']} {r['timestamp'].split('T')[1][:8]} - {r['filename']}")
        print(f"\nTotal: {len(results)} results")

    elif args.command == "compare":
        if args.files:
            comparison = manager.compare_results(args.benchmark, args.files[0], args.files[1])
        else:
            comparison = manager.compare_results(args.benchmark)

        print(format_comparison(comparison))

    elif args.command == "trend":
        trend_data = manager.get_trends(args.benchmark, args.metric, args.limit)
        print(format_trends(trend_data, args.metric))
