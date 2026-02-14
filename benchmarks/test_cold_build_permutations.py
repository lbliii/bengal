"""
Comprehensive cold build permutation benchmarks.

Compares all build mode combinations across multiple site sizes (100, 500, 1000 pages).
Tests cold builds (no cache) to measure true build performance.

Build Modes Tested:
===================
1. Standard (default parallel)
2. Fast mode (--fast)
3. Memory-optimized (--memory-optimized)
4. Sequential (--no-parallel)
5. Fast + Memory-optimized (--fast --memory-optimized)

Site Sizes:
===========
- 100 pages: Small-medium site
- 500 pages: Medium-large site
- 1000 pages: Large site

Expected Insights:
==================
- Fast mode impact (logging overhead reduction)
- Memory-optimized tradeoffs (speed vs memory)
- Parallel vs sequential speedup (2-4x expected)
- Scaling characteristics across site sizes
"""

import random
import shutil
import subprocess
from pathlib import Path

import pytest


def generate_test_site(num_pages: int, tmp_path: Path) -> Path:
    """
    Generate a test site with specified number of pages.

    Creates realistic content with tags, frontmatter, and markdown content.
    """
    site_root = tmp_path / f"site_{num_pages}pages"
    site_root.mkdir(exist_ok=True)

    # Create config (no fast_mode to test CLI flags)
    config_content = f"""[site]
title = "Cold Build Test - {num_pages} Pages"
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
    ]

    # Create pages
    for i in range(num_pages):
        # Assign 2-4 random tags per page
        num_tags = random.randint(2, 4)
        page_tags = random.sample(tags, k=num_tags)
        tags_yaml = str(page_tags).replace("'", '"')

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

```python
def example_{i}():
    return "code block {i}"
```

More content here to make the page realistic.
"""
        (content_dir / f"page{i:04d}.md").write_text(content)

    # Create index page
    (content_dir / "index.md").write_text("""---
title: Home
---

# Welcome

This is the homepage for the cold build benchmark.
""")

    return site_root


@pytest.fixture(scope="module")
def site_100_pages(tmp_path_factory):
    """Generate 100-page test site."""
    tmp_path = tmp_path_factory.mktemp("cold_build_100")
    site_path = generate_test_site(100, tmp_path)
    yield site_path
    shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.fixture(scope="module")
def site_500_pages(tmp_path_factory):
    """Generate 500-page test site."""
    tmp_path = tmp_path_factory.mktemp("cold_build_500")
    site_path = generate_test_site(500, tmp_path)
    yield site_path
    shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.fixture(scope="module")
def site_1000_pages(tmp_path_factory):
    """Generate 1000-page test site."""
    tmp_path = tmp_path_factory.mktemp("cold_build_1000")
    site_path = generate_test_site(1000, tmp_path)
    yield site_path
    shutil.rmtree(tmp_path, ignore_errors=True)


# Standard build benchmarks
@pytest.mark.benchmark
@pytest.mark.parametrize(
    ("site_fixture", "page_count"),
    [
        ("site_100_pages", 100),
        ("site_500_pages", 500),
        ("site_1000_pages", 1000),
    ],
)
def test_standard_build(benchmark, request, site_fixture, page_count):
    """Standard build (default parallel, no flags)."""
    site_path = request.getfixturevalue(site_fixture)

    def build():
        # Clean output to ensure cold build
        output_dir = site_path / "output"
        if output_dir.exists():
            shutil.rmtree(output_dir)

        subprocess.run(
            ["bengal", "build"],
            cwd=site_path,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    benchmark(build)


@pytest.mark.benchmark
@pytest.mark.parametrize(
    ("site_fixture", "page_count"),
    [
        ("site_100_pages", 100),
        ("site_500_pages", 500),
        ("site_1000_pages", 1000),
    ],
)
def test_fast_mode(benchmark, request, site_fixture, page_count):
    """Fast mode build (--fast: quiet output + guaranteed parallel)."""
    site_path = request.getfixturevalue(site_fixture)

    def build():
        output_dir = site_path / "output"
        if output_dir.exists():
            shutil.rmtree(output_dir)

        subprocess.run(
            ["bengal", "build", "--fast"],
            cwd=site_path,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    benchmark(build)


@pytest.mark.benchmark
@pytest.mark.parametrize(
    ("site_fixture", "page_count"),
    [
        ("site_100_pages", 100),
        ("site_500_pages", 500),
        ("site_1000_pages", 1000),
    ],
)
def test_memory_optimized(benchmark, request, site_fixture, page_count):
    """Memory-optimized build (--memory-optimized: streaming for large sites)."""
    site_path = request.getfixturevalue(site_fixture)

    def build():
        output_dir = site_path / "output"
        if output_dir.exists():
            shutil.rmtree(output_dir)

        subprocess.run(
            ["bengal", "build", "--memory-optimized"],
            cwd=site_path,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    benchmark(build)


@pytest.mark.benchmark
@pytest.mark.parametrize(
    ("site_fixture", "page_count"),
    [
        ("site_100_pages", 100),
        ("site_500_pages", 500),
        ("site_1000_pages", 1000),
    ],
)
def test_sequential_build(benchmark, request, site_fixture, page_count):
    """Sequential build (--no-parallel: baseline for parallel speedup)."""
    site_path = request.getfixturevalue(site_fixture)

    def build():
        output_dir = site_path / "output"
        if output_dir.exists():
            shutil.rmtree(output_dir)

        subprocess.run(
            ["bengal", "build", "--no-parallel"],
            cwd=site_path,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    benchmark(build)


@pytest.mark.benchmark
@pytest.mark.parametrize(
    ("site_fixture", "page_count"),
    [
        ("site_500_pages", 500),
        ("site_1000_pages", 1000),
    ],
)
def test_fast_memory_optimized(benchmark, request, site_fixture, page_count):
    """Fast mode + Memory-optimized (--fast --memory-optimized: for large sites)."""
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
        )

    benchmark(build)
