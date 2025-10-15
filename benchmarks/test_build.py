import pytest
import subprocess
from pathlib import Path

SCENARIOS = ["small_site", "large_site"]

@pytest.mark.parametrize("scenario", SCENARIOS)
def test_build_performance(benchmark, scenario):
    """
    Benchmark the build process for different scenarios.
    """
    scenario_path = Path(__file__).parent / "scenarios" / scenario

    def build_site():
        subprocess.run(
            ["bengal", "build"],
            cwd=scenario_path,
            check=True,
            capture_output=True,
        )

    benchmark(build_site)