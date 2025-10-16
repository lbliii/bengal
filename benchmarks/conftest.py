"""
Benchmark fixtures and hooks for automatic history logging.
"""

import json
import subprocess
from pathlib import Path

import pytest
from benchmark_history import BenchmarkHistoryLogger


def get_git_info():
    """Get current git commit and branch."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent, text=True
        ).strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=Path(__file__).parent,
            text=True,
        ).strip()
        return commit, branch
    except Exception:
        return None, None


@pytest.fixture(scope="session")
def benchmark_history_logger():
    """Provide benchmark history logger to tests."""
    return BenchmarkHistoryLogger()


def pytest_sessionfinish(session, exitstatus):
    """Log benchmark results after test session finishes."""
    # Find the .benchmarks directory where pytest-benchmark stores results
    benchmarks_dir = Path(__file__).parent / ".benchmarks"

    if not benchmarks_dir.exists():
        return  # No benchmarks were run

    # Read the most recent benchmark result file
    benchmark_files = sorted(benchmarks_dir.glob("*-*.json"))
    if not benchmark_files:
        return

    latest_file = benchmark_files[-1]

    try:
        with open(latest_file) as f:
            results = json.load(f)

        # Get git info
        commit, branch = get_git_info()

        # Log to history
        logger = BenchmarkHistoryLogger()
        logger.log_run(
            results=results,
            git_commit=commit,
            git_branch=branch,
            metadata={
                "benchmark_file": latest_file.name,
                "exit_status": exitstatus,
            },
        )

        # Print summary
        logger.print_summary(last_n=3)

    except Exception as e:
        print(f"Warning: Could not log benchmark results: {e}")
