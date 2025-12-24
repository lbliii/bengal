"""
Benchmark suite for Bengal configuration loading performance.

This suite validates the RFC-config-algorithm-optimization claims and tracks
improvements from batch deep merge optimization.

Benchmark Categories:
====================

1. Real-World Config Loading
   - test_bengal_docs_config_load: Load actual Bengal docs site config (~12 files)

2. Batch Merge Optimization
   - test_batch_merge_vs_sequential: Compare batch_deep_merge vs sequential deep_merge
   - test_batch_merge_scaling: Test performance across 5, 15, 30 config files

3. Stress Tests
   - test_config_load_30_files: Large directory structure stress test
   - test_config_1000_keys: Large config (1000+ keys) stress test

Expected Performance:
=====================
- Bengal docs config: <30ms for 12 files, ~130 keys
- 30 config files: <100ms with batch merge
- Batch merge: 5-12x fewer dict copy operations than sequential

RFC Reference: plan/drafted/rfc-config-algorithm-optimization.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def bengal_site_root() -> Path:
    """Return path to Bengal docs site root."""
    return Path(__file__).parent.parent / "site"


@pytest.fixture
def synthetic_config_5_files(tmp_path: Path) -> Path:
    """Create synthetic config directory with 5 files."""
    return _create_synthetic_config(tmp_path / "config_5", num_files=5, keys_per_file=20)


@pytest.fixture
def synthetic_config_15_files(tmp_path: Path) -> Path:
    """Create synthetic config directory with 15 files."""
    return _create_synthetic_config(tmp_path / "config_15", num_files=15, keys_per_file=20)


@pytest.fixture
def synthetic_config_30_files(tmp_path: Path) -> Path:
    """Create synthetic config directory with 30 files."""
    return _create_synthetic_config(tmp_path / "config_30", num_files=30, keys_per_file=20)


@pytest.fixture
def large_config_1000_keys(tmp_path: Path) -> Path:
    """Create config with 1000+ keys for stress testing."""
    return _create_synthetic_config(tmp_path / "config_1000", num_files=10, keys_per_file=100)


def _create_synthetic_config(
    config_dir: Path,
    num_files: int,
    keys_per_file: int,
    nesting_depth: int = 3,
) -> Path:
    """
    Create a synthetic config directory for benchmarking.

    Args:
        config_dir: Directory to create
        num_files: Number of YAML files to create
        keys_per_file: Number of top-level keys per file
        nesting_depth: Maximum nesting depth for nested dicts

    Returns:
        Path to the _default directory (where ConfigDirectoryLoader looks)
    """
    default_dir = config_dir / "_default"
    default_dir.mkdir(parents=True, exist_ok=True)

    for i in range(num_files):
        config: dict[str, Any] = {}
        for j in range(keys_per_file):
            key = f"section_{i}_{j}"
            config[key] = _create_nested_value(f"value_{i}_{j}", nesting_depth)

        yaml_path = default_dir / f"config_{i:02d}.yaml"
        with yaml_path.open("w") as f:
            yaml.safe_dump(config, f)

    return config_dir


def _create_nested_value(base_value: str, depth: int) -> dict[str, Any] | str:
    """Create a nested dict structure for testing deep merge."""
    if depth <= 1:
        return base_value

    return {
        "name": base_value,
        "enabled": True,
        "nested": _create_nested_value(f"{base_value}_nested", depth - 1),
    }


# -----------------------------------------------------------------------------
# Real-World Config Loading Benchmarks
# -----------------------------------------------------------------------------


@pytest.mark.benchmark
def test_bengal_docs_config_load(benchmark, bengal_site_root: Path) -> None:
    """
    Benchmark: Load Bengal docs site configuration.

    Real-world test using the actual site/config/ directory structure:
    - 10 files in _default/ (~130 total keys)
    - 2 files in environments/

    Expected: <30ms for full load
    """
    from bengal.config.directory_loader import ConfigDirectoryLoader

    config_dir = bengal_site_root / "config"

    if not config_dir.exists():
        pytest.skip("Bengal site config not found")

    loader = ConfigDirectoryLoader()

    result = benchmark(loader.load, config_dir)

    # Verify config was loaded
    assert result is not None
    assert isinstance(result, dict)
    # Should have content from site.yaml
    assert "title" in result or "site" in result


# -----------------------------------------------------------------------------
# Batch Merge Optimization Benchmarks
# -----------------------------------------------------------------------------


@pytest.mark.benchmark
def test_batch_merge_vs_sequential_10_configs(benchmark) -> None:
    """
    Benchmark: Compare batch_deep_merge vs sequential deep_merge.

    Creates 10 configs with 20 keys each (200 total keys, depth 3).
    Measures batch merge performance.

    Expected: batch_deep_merge should be significantly faster than
    sequential deep_merge for 10+ configs.
    """
    from bengal.config.merge import batch_deep_merge

    # Create 10 configs with overlapping keys
    configs = []
    for i in range(10):
        config: dict[str, Any] = {}
        for j in range(20):
            config[f"section_{j}"] = {
                "name": f"config_{i}_section_{j}",
                "enabled": True,
                "options": {"level": i, "index": j},
            }
        configs.append(config)

    result = benchmark(batch_deep_merge, configs)

    # Verify merge correctness
    assert result is not None
    assert "section_0" in result
    # Last config wins for overlapping keys
    assert result["section_0"]["name"] == "config_9_section_0"


@pytest.mark.benchmark
def test_sequential_merge_10_configs(benchmark) -> None:
    """
    Benchmark: Sequential deep_merge for comparison.

    Same data as test_batch_merge_vs_sequential_10_configs but using
    sequential deep_merge calls.
    """
    from bengal.config.merge import deep_merge

    # Create 10 configs with overlapping keys
    configs = []
    for i in range(10):
        config: dict[str, Any] = {}
        for j in range(20):
            config[f"section_{j}"] = {
                "name": f"config_{i}_section_{j}",
                "enabled": True,
                "options": {"level": i, "index": j},
            }
        configs.append(config)

    def sequential_merge(configs: list[dict[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for config in configs:
            result = deep_merge(result, config)
        return result

    result = benchmark(sequential_merge, configs)

    # Verify merge correctness
    assert result is not None
    assert "section_0" in result
    assert result["section_0"]["name"] == "config_9_section_0"


# -----------------------------------------------------------------------------
# Scaling Benchmarks
# -----------------------------------------------------------------------------


@pytest.mark.benchmark
def test_config_load_5_files(benchmark, synthetic_config_5_files: Path) -> None:
    """Benchmark: Load 5 config files."""
    from bengal.config.directory_loader import ConfigDirectoryLoader

    loader = ConfigDirectoryLoader()
    result = benchmark(loader.load, synthetic_config_5_files)

    assert result is not None


@pytest.mark.benchmark
def test_config_load_15_files(benchmark, synthetic_config_15_files: Path) -> None:
    """Benchmark: Load 15 config files."""
    from bengal.config.directory_loader import ConfigDirectoryLoader

    loader = ConfigDirectoryLoader()
    result = benchmark(loader.load, synthetic_config_15_files)

    assert result is not None


@pytest.mark.benchmark
def test_config_load_30_files(benchmark, synthetic_config_30_files: Path) -> None:
    """
    Benchmark: Load 30 config files (stress test).

    This is the primary benchmark for validating batch merge optimization.
    RFC claims: 80ms → 30ms (63% reduction) for 30 files.

    Expected: <100ms with batch merge optimization
    """
    from bengal.config.directory_loader import ConfigDirectoryLoader

    loader = ConfigDirectoryLoader()
    result = benchmark(loader.load, synthetic_config_30_files)

    assert result is not None
    # Should have sections from all 30 files
    assert len([k for k in result if k.startswith("section_")]) > 0


@pytest.mark.benchmark
def test_config_load_1000_keys(benchmark, large_config_1000_keys: Path) -> None:
    """
    Benchmark: Load config with 1000+ keys (stress test).

    Tests performance with many keys rather than many files.
    Expected: <50ms for 1000 keys
    """
    from bengal.config.directory_loader import ConfigDirectoryLoader

    loader = ConfigDirectoryLoader()
    result = benchmark(loader.load, large_config_1000_keys)

    assert result is not None


# -----------------------------------------------------------------------------
# Correctness Tests (not benchmarked, but critical)
# -----------------------------------------------------------------------------


def test_batch_merge_produces_identical_results() -> None:
    """
    Verify batch_deep_merge produces identical results to sequential deep_merge.

    This is a correctness test, not a benchmark.
    """
    from bengal.config.merge import batch_deep_merge, deep_merge

    # Create configs with overlapping nested keys
    configs = [
        {"site": {"title": "Base", "nested": {"a": 1}}},
        {"site": {"baseurl": "/", "nested": {"b": 2}}},
        {"build": {"parallel": True}},
        {"site": {"nested": {"c": 3}}, "build": {"incremental": True}},
    ]

    # Sequential merge
    sequential_result: dict[str, Any] = {}
    for config in configs:
        sequential_result = deep_merge(sequential_result, config)

    # Batch merge
    batch_result = batch_deep_merge(configs)

    # Results must be identical
    assert batch_result == sequential_result


def test_batch_merge_empty_list() -> None:
    """Verify batch_deep_merge handles empty list."""
    from bengal.config.merge import batch_deep_merge

    result = batch_deep_merge([])
    assert result == {}


def test_batch_merge_single_config() -> None:
    """Verify batch_deep_merge handles single config."""
    from bengal.config.merge import batch_deep_merge

    config = {"site": {"title": "Test"}}
    result = batch_deep_merge([config])
    assert result == config


def test_batch_merge_does_not_mutate_inputs() -> None:
    """Verify batch_deep_merge does not mutate input configs."""
    import copy

    from bengal.config.merge import batch_deep_merge

    configs = [
        {"site": {"title": "Base"}},
        {"site": {"baseurl": "/"}},
    ]
    original = copy.deepcopy(configs)

    batch_deep_merge(configs)

    assert configs == original
