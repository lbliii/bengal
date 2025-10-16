"""
Benchmark history tracking with append-only log.

Automatically captures benchmark results with timestamps for measuring
performance across patches, commits, and releases.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class BenchmarkHistoryLogger:
    """Append-only benchmark history log with timestamps and metadata."""

    def __init__(self, log_file: Path | None = None):
        """
        Initialize history logger.

        Args:
            log_file: Path to append-only log file. Defaults to .benchmarks/history.jsonl
        """
        if log_file is None:
            log_file = Path(__file__).parent / ".benchmarks" / "history.jsonl"

        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_run(
        self,
        results: dict[str, Any],
        git_commit: str | None = None,
        git_branch: str | None = None,
        version: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Log a benchmark run with timestamp and metadata.

        Args:
            results: Dictionary of benchmark results from pytest-benchmark
            git_commit: Git commit hash (optional)
            git_branch: Git branch name (optional)
            version: Application version (optional)
            metadata: Additional metadata to track (optional)
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "results": results,
            "git_commit": git_commit,
            "git_branch": git_branch,
            "version": version,
            "metadata": metadata or {},
        }

        # Append to JSONL file (one JSON object per line)
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_history(self, limit: int | None = None) -> list[dict[str, Any]]:
        """
        Read benchmark history.

        Args:
            limit: Maximum number of recent entries to return (None = all)

        Returns:
            List of benchmark history entries, most recent last.
        """
        if not self.log_file.exists():
            return []

        entries = []
        with open(self.log_file) as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))

        if limit:
            return entries[-limit:]
        return entries

    def get_latest_results(self) -> dict[str, Any] | None:
        """Get the most recent benchmark run."""
        history = self.get_history(limit=1)
        return history[0] if history else None

    def export_csv(self, output_file: Path, metric: str = "mean") -> None:
        """
        Export benchmark history as CSV for analysis and graphing.

        Args:
            output_file: Path to write CSV file
            metric: Metric to extract (mean, min, max, stddev, etc)
        """
        import csv

        history = self.get_history()
        if not history:
            return

        # Flatten results structure for CSV
        rows = []
        for entry in history:
            timestamp = entry["timestamp"]
            git_commit = entry.get("git_commit", "")
            git_branch = entry.get("git_branch", "")

            # Extract metrics from each test result
            for test_name, test_data in entry.get("results", {}).items():
                if "stats" in test_data and metric in test_data["stats"]:
                    value = test_data["stats"][metric]
                    rows.append(
                        {
                            "timestamp": timestamp,
                            "test": test_name,
                            "metric": value,
                            "git_commit": git_commit,
                            "git_branch": git_branch,
                        }
                    )

        if rows:
            with open(output_file, "w", newline="") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["timestamp", "test", "metric", "git_commit", "git_branch"]
                )
                writer.writeheader()
                writer.writerows(rows)

    def print_summary(self, last_n: int = 5) -> None:
        """
        Print a summary of recent benchmark runs.

        Args:
            last_n: Number of recent runs to show
        """
        history = self.get_history(limit=last_n)

        if not history:
            print("No benchmark history found.")
            return

        print(f"\nBenchmark History (last {last_n} runs):")
        print("=" * 80)

        for i, entry in enumerate(history, 1):
            timestamp = entry["timestamp"]
            commit = entry.get("git_commit", "unknown")[:8]
            branch = entry.get("git_branch", "unknown")
            version = entry.get("version", "")

            print(f"\n{i}. {timestamp}")
            print(f"   Branch: {branch} | Commit: {commit} | Version: {version}")

            # Show metrics for each test
            for test_name, test_data in entry.get("results", {}).items():
                if "stats" in test_data:
                    mean = test_data["stats"].get("mean", "N/A")
                    print(f"   {test_name}: {mean}")

        print("\n" + "=" * 80)
