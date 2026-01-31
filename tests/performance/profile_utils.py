"""
Shared profiling utilities for benchmarks.

Provides consistent profiling across all performance tests.
"""

import cProfile
import pstats
from collections.abc import Callable
from pathlib import Path
from typing import Any

from bengal.utils.paths.paths import BengalPaths


class ProfileContext:
    """Context manager for profiling code blocks."""

    def __init__(self, enabled: bool = True, name: str = "profile"):
        self.enabled = enabled
        self.name = name
        self.profiler = None
        self.profile_path = None

    def __enter__(self):
        if self.enabled:
            self.profiler = cProfile.Profile()
            self.profiler.enable()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.enabled and self.profiler:
            self.profiler.disable()

    def save(self, output_dir: Path, filename: str | None = None):
        """Save profile data to file."""
        if not self.enabled or not self.profiler:
            return None

        if filename is None:
            filename = f"{self.name}.stats"

        profile_path = output_dir / filename
        profile_path.parent.mkdir(parents=True, exist_ok=True)

        self.profiler.dump_stats(str(profile_path))
        self.profile_path = profile_path

        return profile_path

    def get_stats(self) -> pstats.Stats | None:
        """Get statistics from the profile."""
        if not self.enabled or not self.profiler:
            return None

        return pstats.Stats(self.profiler)


def profile_function(
    func: Callable, *args, profile_name: str = "function", **kwargs
) -> tuple[Any, Path | None]:
    """
    Profile a function call and return result + profile path.

    Args:
        func: Function to profile
        *args: Positional arguments for func
        profile_name: Name for the profile file
        **kwargs: Keyword arguments for func (use profile=True to enable)

    Returns:
        Tuple of (function_result, profile_path)

    """
    should_profile = kwargs.pop("profile", False)

    if not should_profile:
        return func(*args, **kwargs), None

    with ProfileContext(enabled=True, name=profile_name) as ctx:
        result = func(*args, **kwargs)

    # Save to .bengal/profiles/
    from tempfile import gettempdir

    profile_dir = Path(gettempdir()) / ".bengal" / "profiles"
    profile_path = ctx.save(profile_dir)

    return result, profile_path


def save_profile_for_benchmark(
    profiler: cProfile.Profile, benchmark_name: str, site_root: Path | None = None
) -> Path:
    """
    Save profile data with consistent naming for benchmarks.

    Args:
        profiler: The profiler object
        benchmark_name: Name of the benchmark
        site_root: Site root directory (uses .bengal/profiles/)

    Returns:
        Path to saved profile

    """
    if site_root:
        profile_path = BengalPaths.get_profile_path(
            site_root, filename=f"{benchmark_name}_profile.stats"
        )
    else:
        # Use temp directory if no site root
        from tempfile import gettempdir

        profile_dir = Path(gettempdir()) / ".bengal" / "profiles"
        profile_dir.mkdir(parents=True, exist_ok=True)
        profile_path = profile_dir / f"{benchmark_name}_profile.stats"

    profiler.dump_stats(str(profile_path))

    return profile_path


def compare_profile_with_baseline(current_profile: Path, baseline_name: str = "baseline") -> bool:
    """
    Compare current profile with stored baseline.

    Args:
        current_profile: Path to current profile
        baseline_name: Name of baseline profile

    Returns:
        True if no significant regressions, False otherwise

    """
    baseline_path = current_profile.parent / f"{baseline_name}.stats"

    if not baseline_path.exists():
        print(f"ℹ️  No baseline found at {baseline_path}")
        print(f"   Save this as baseline with: cp {current_profile} {baseline_path}")
        return True

    # Use analyze_profile.py for comparison
    import subprocess
    import sys

    analyzer = Path(__file__).parent / "analyze_profile.py"

    result = subprocess.run(
        [
            sys.executable,
            str(analyzer),
            str(current_profile),
            "--compare",
            str(baseline_path),
            "--fail-on-regression",
            "15",  # 15% threshold
        ],
        capture_output=False,
    )

    return result.returncode == 0
