"""
Comprehensive build options benchmark suite for GitHub Pages worker optimization.

This suite systematically tests ALL Bengal build option combinations under GitHub Pages
worker constraints (2-core CPU, 7GB RAM) using Python 3.14t free-threading.

Build Options Tested:
====================
- parallel: True/False (--parallel/--no-parallel)
- incremental: True/False/None (--incremental/--no-incremental/auto)
- memory_optimized: True/False (--memory-optimized)
- fast: True/False (--fast)
- profile: writer/theme-dev/dev (--profile)
- quiet: True/False (--quiet)
- strict: True/False (--strict)
- clean_output: True/False (--clean-output)

Site Sizes:
===========
- 50 pages: Small site (typical blog)
- 200 pages: Medium site (documentation)
- 500 pages: Large site (comprehensive docs)
- 1000 pages: Very large site (stress test)

Resource Constraints (GitHub Pages Worker):
===========================================
- CPU: 2 cores (emulated via CPU affinity)
- RAM: 7GB limit (emulated via resource limits)
- Python: 3.14t (free-threading, no GIL)

Total Combinations: ~100+ permutations across 4 site sizes
"""

import os
import random
import resource
import shutil
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path

import pytest

try:
    import psutil
except ImportError:
    psutil = None


# GitHub Pages worker constraints
GITHUB_PAGES_CPU_CORES = 2
GITHUB_PAGES_RAM_GB = 7
GITHUB_PAGES_RAM_BYTES = GITHUB_PAGES_RAM_GB * 1024 * 1024 * 1024


@dataclass
class BuildConfig:
    """Represents a build configuration to test."""

    parallel: bool = True
    incremental: bool | None = None  # None = auto
    memory_optimized: bool = False
    fast: bool = False
    profile: str | None = None  # writer, theme-dev, dev
    quiet: bool = False
    strict: bool = False
    clean_output: bool = False

    def to_cli_args(self) -> list[str]:
        """Convert config to CLI arguments."""
        args = []

        if not self.parallel:
            args.append("--no-parallel")
        elif self.parallel:
            args.append("--parallel")

        if self.incremental is True:
            args.append("--incremental")
        elif self.incremental is False:
            args.append("--no-incremental")
        # None = auto, no flag needed

        if self.memory_optimized:
            args.append("--memory-optimized")

        if self.fast:
            args.append("--fast")

        if self.profile:
            args.extend(["--profile", self.profile])

        if self.quiet:
            args.append("--quiet")

        if self.strict:
            args.append("--strict")

        if self.clean_output:
            args.append("--clean-output")

        return args

    def __str__(self) -> str:
        """Human-readable config name."""
        parts = []
        if not self.parallel:
            parts.append("seq")
        if self.incremental is True:
            parts.append("inc")
        elif self.incremental is False:
            parts.append("full")
        if self.memory_optimized:
            parts.append("mem")
        if self.fast:
            parts.append("fast")
        if self.profile:
            parts.append(self.profile)
        if self.quiet:
            parts.append("quiet")
        if self.strict:
            parts.append("strict")
        if self.clean_output:
            parts.append("clean")
        return "_".join(parts) if parts else "default"


def generate_test_site(num_pages: int, tmp_path: Path) -> Path:
    """
    Generate a test site with specified number of pages.

    Creates realistic content with tags, frontmatter, and markdown content.
    """
    site_root = tmp_path / f"site_{num_pages}pages"
    site_root.mkdir(exist_ok=True)

    # Create config (no fast_mode to test CLI flags)
    config_content = f"""[site]
title = "GitHub Pages Optimization Test - {num_pages} Pages"
base_url = "https://example.com"

[build]
output_dir = "output"
parallel = true
"""
    (site_root / "bengal.toml").write_text(config_content)

    # Create content directory
    content_dir = site_root / "content"
    content_dir.mkdir(exist_ok=True)

    # Generate tags pool
    tags = [
        "python",
        "javascript",
        "go",
        "rust",
        "java",
        "typescript",
        "performance",
        "security",
        "testing",
        "deployment",
        "api",
        "database",
        "frontend",
        "backend",
        "devops",
    ]

    # Create pages
    for i in range(num_pages):
        # Assign 2-4 random tags per page
        num_tags = random.randint(2, 4)
        page_tags = random.sample(tags, k=num_tags)
        tags_yaml = str(page_tags).replace("'", '"')

        # Vary content complexity
        num_code_blocks = random.randint(1, 3)
        code_blocks = "\n\n".join(
            [
                f"```python\ndef example_{i}_{j}():\n    return 'code block {i}.{j}'\n```"
                for j in range(num_code_blocks)
            ]
        )

        content = f"""---
title: Page {i}
tags: {tags_yaml}
date: 2025-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}
---

# Page {i}

This is page {i} with some content for benchmarking.

## Section 1

Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

## Section 2

Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.

{code_blocks}

More content here to make the page realistic.
"""
        (content_dir / f"page{i:04d}.md").write_text(content)

    # Create index page
    (content_dir / "index.md").write_text("""---
title: Home
---

# Welcome

This is the homepage for the GitHub Pages optimization benchmark.
""")

    return site_root


@contextmanager
def limit_cpu_cores(cores: int) -> Iterator[None]:
    """
    Limit process to use only specified number of CPU cores.

    Uses CPU affinity on platforms that support it (Linux, macOS, Windows).
    """
    if psutil is None:
        # psutil not available, skip CPU limiting
        yield
        return

    try:
        process = psutil.Process()
        original_affinity = process.cpu_affinity()

        # Get available CPU cores
        available_cores = list(range(os.cpu_count() or cores))
        limited_cores = available_cores[:cores]

        # Set CPU affinity
        process.cpu_affinity(limited_cores)

        yield

    except (AttributeError, psutil.AccessDenied, OSError):
        # CPU affinity not supported or permission denied
        # This is OK, we'll proceed without limiting
        yield
    finally:
        # Restore original affinity
        if psutil and "original_affinity" in locals():
            with suppress(Exception):
                process.cpu_affinity(original_affinity)


@contextmanager
def limit_memory(max_bytes: int) -> Iterator[None]:
    """
    Limit process memory usage (soft limit).

    Uses resource.setrlimit on Unix systems.
    """
    if sys.platform == "win32":
        # Windows doesn't support resource limits easily
        yield
        return

    try:
        # Get current limits
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)

        # Set new soft limit (hard limit stays the same)
        resource.setrlimit(resource.RLIMIT_AS, (max_bytes, hard))

        yield

    except (ValueError, OSError):
        # Limit setting failed, proceed anyway
        yield
    finally:
        # Restore original limits
        with suppress(Exception):
            resource.setrlimit(resource.RLIMIT_AS, (soft, hard))


@pytest.fixture(scope="session")
def github_pages_constraints():
    """
    Apply GitHub Pages worker constraints to benchmark runs.

    This fixture applies CPU and memory limits before each test.
    """
    with limit_cpu_cores(GITHUB_PAGES_CPU_CORES), limit_memory(GITHUB_PAGES_RAM_BYTES):
        yield


# Site fixtures
@pytest.fixture(scope="module")
def site_50_pages(tmp_path_factory):
    """Generate 50-page test site."""
    tmp_path = tmp_path_factory.mktemp("gh_pages_50")
    site_path = generate_test_site(50, tmp_path)
    yield site_path
    shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.fixture(scope="module")
def site_200_pages(tmp_path_factory):
    """Generate 200-page test site."""
    tmp_path = tmp_path_factory.mktemp("gh_pages_200")
    site_path = generate_test_site(200, tmp_path)
    yield site_path
    shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.fixture(scope="module")
def site_500_pages(tmp_path_factory):
    """Generate 500-page test site."""
    tmp_path = tmp_path_factory.mktemp("gh_pages_500")
    site_path = generate_test_site(500, tmp_path)
    yield site_path
    shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.fixture(scope="module")
def site_1000_pages(tmp_path_factory):
    """Generate 1000-page test site."""
    tmp_path = tmp_path_factory.mktemp("gh_pages_1000")
    site_path = generate_test_site(1000, tmp_path)
    yield site_path
    shutil.rmtree(tmp_path, ignore_errors=True)


# Build configuration combinations
# We test key combinations rather than all permutations (which would be 1000+)

BUILD_CONFIGS = [
    # Baseline configurations
    BuildConfig(),  # Default (parallel=True, incremental=None)
    BuildConfig(parallel=False),  # Sequential baseline
    BuildConfig(incremental=False),  # Force full build
    BuildConfig(incremental=True),  # Force incremental
    # Fast mode combinations
    BuildConfig(fast=True),
    BuildConfig(fast=True, incremental=False),
    BuildConfig(fast=True, incremental=True),
    # Memory-optimized combinations
    BuildConfig(memory_optimized=True),
    BuildConfig(memory_optimized=True, fast=True),
    BuildConfig(memory_optimized=True, incremental=False),
    # Profile combinations
    BuildConfig(profile="writer"),
    BuildConfig(profile="theme-dev"),
    BuildConfig(profile="dev"),
    # Quiet mode (often used with fast)
    BuildConfig(quiet=True),
    BuildConfig(quiet=True, fast=True),
    # Strict mode (CI/CD)
    BuildConfig(strict=True),
    BuildConfig(strict=True, fast=True),
    # Clean output (CI cache-busting)
    BuildConfig(clean_output=True),
    BuildConfig(clean_output=True, fast=True),
    # Common CI combinations
    BuildConfig(fast=True, strict=True, clean_output=True),
    BuildConfig(fast=True, memory_optimized=True, strict=True),
    # Edge cases
    BuildConfig(parallel=False, incremental=True),  # Sequential incremental
    BuildConfig(parallel=False, memory_optimized=True),  # Sequential memory-opt
]


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "site_fixture,page_count",
    [
        ("site_50_pages", 50),
        ("site_200_pages", 200),
        ("site_500_pages", 500),
        ("site_1000_pages", 1000),
    ],
)
@pytest.mark.parametrize("build_config", BUILD_CONFIGS, ids=str)
def test_build_configuration(
    benchmark,
    request,
    github_pages_constraints,
    site_fixture: str,
    page_count: int,
    build_config: BuildConfig,
):
    """
    Benchmark a specific build configuration under GitHub Pages constraints.

    Tests all combinations of build options across multiple site sizes.
    """
    site_path = request.getfixturevalue(site_fixture)

    def build():
        # Clean output to ensure cold build
        output_dir = site_path / "output"
        if output_dir.exists():
            shutil.rmtree(output_dir)

        # Build command with configuration
        cmd = ["bengal", "build"] + build_config.to_cli_args()

        subprocess.run(
            cmd,
            cwd=site_path,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "PYTHON_GIL": "0"},  # Ensure free-threading
        )

    benchmark(build)


# Specific focused tests for common scenarios


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "site_fixture,page_count",
    [
        ("site_50_pages", 50),
        ("site_200_pages", 200),
        ("site_500_pages", 500),
    ],
)
def test_optimal_ci_build(benchmark, request, github_pages_constraints, site_fixture, page_count):
    """
    Test optimal CI/CD build configuration.

    Expected: --fast --strict --clean-output
    """
    site_path = request.getfixturevalue(site_fixture)

    def build():
        output_dir = site_path / "output"
        if output_dir.exists():
            shutil.rmtree(output_dir)

        subprocess.run(
            ["bengal", "build", "--fast", "--strict", "--clean-output"],
            cwd=site_path,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "PYTHON_GIL": "0"},
        )

    benchmark(build)


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "site_fixture,page_count",
    [
        ("site_500_pages", 500),
        ("site_1000_pages", 1000),
    ],
)
def test_large_site_optimal(benchmark, request, github_pages_constraints, site_fixture, page_count):
    """
    Test optimal configuration for large sites (500+ pages).

    Expected: --fast --memory-optimized
    """
    site_path = request.getfixturevalue(site_fixture)

    def build():
        output_dir = site_path / "output"
        if output_dir.exists():
            shutil.rmtree(output_dir)

        subprocess.run(
            ["bengal", "build", "--fast", "--memory-optimized"],
            cwd=site_path,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "PYTHON_GIL": "0"},
        )

    benchmark(build)


@pytest.mark.benchmark
def test_parallel_vs_sequential_2core(benchmark, request, github_pages_constraints, site_200_pages):
    """
    Compare parallel vs sequential on 2-core system (GitHub Pages constraint).

    Expected: Parallel should be ~1.5-2x faster on 2 cores.
    """
    site_path = site_200_pages

    def build_parallel():
        output_dir = site_path / "output"
        if output_dir.exists():
            shutil.rmtree(output_dir)

        subprocess.run(
            ["bengal", "build", "--parallel"],
            cwd=site_path,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "PYTHON_GIL": "0"},
        )

    def build_sequential():
        output_dir = site_path / "output"
        if output_dir.exists():
            shutil.rmtree(output_dir)

        subprocess.run(
            ["bengal", "build", "--no-parallel"],
            cwd=site_path,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "PYTHON_GIL": "0"},
        )

    parallel_time = benchmark(build_parallel)
    sequential_time = benchmark(build_sequential)

    # Calculate speedup
    speedup = sequential_time.stats.mean / parallel_time.stats.mean
    print(f"\nParallel speedup on 2-core: {speedup:.2f}x")
    print(f"Parallel: {parallel_time.stats.mean:.2f}s")
    print(f"Sequential: {sequential_time.stats.mean:.2f}s")
