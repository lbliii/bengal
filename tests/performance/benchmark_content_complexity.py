"""
Parameterized content-complexity benchmarks.

Measures build performance across content complexity dimensions inspired by
Hugo's site_benchmark_test.go (tags_per_page, shortcodes, root_sections).

Dimensions:
- Directives per page: 0, 2, 5, 10 (admonition parsing overhead)
- Code blocks per page: 0, 3, 10 (syntax highlighting cost)
- Taxonomy terms per page: 0, 5, 20 (taxonomy index cost)

Uses cached scenarios from benchmarks/scenarios/ when available (run
scripts/generate_benchmark_scenarios.py to create them).

Run with:
    uv run pytest tests/performance/benchmark_content_complexity.py -v --benchmark-only
    uv run poe benchmark
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions

# Path to benchmarks/scenarios (from project root)
BENCHMARKS_ROOT = Path(__file__).resolve().parent.parent.parent / "benchmarks"
SCENARIOS_DIR = BENCHMARKS_ROOT / "scenarios"

PARAGRAPH = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam."
)

DIRECTIVE_BLOCK = """
:::note
This is an admonition block with some content for benchmarking.
:::
"""

CODE_BLOCK = """
```python
def example():
    return "syntax highlighted code"
```
"""


def create_content_complexity_site(
    num_pages: int,
    directives_per_page: int,
    code_blocks_per_page: int,
    taxonomy_terms_per_page: int,
) -> Path:
    """
    Create a test site with configurable content complexity.

    Args:
        num_pages: Number of pages to create
        directives_per_page: Number of :::note directives per page
        code_blocks_per_page: Number of fenced code blocks per page
        taxonomy_terms_per_page: Number of tags per page in frontmatter

    Returns:
        Path to temporary site directory
    """
    temp_dir = Path(tempfile.mkdtemp())

    (temp_dir / "content" / "posts").mkdir(parents=True)
    (temp_dir / "public").mkdir()

    tags = [f"tag{i}" for i in range(max(taxonomy_terms_per_page, 1))]
    tags_str = str(tags[:taxonomy_terms_per_page]) if taxonomy_terms_per_page else "[]"

    for i in range(num_pages):
        body_parts = [PARAGRAPH]

        body_parts.extend([DIRECTIVE_BLOCK] * directives_per_page)
        body_parts.extend([CODE_BLOCK] * code_blocks_per_page)

        content = f"""---
title: Post {i}
date: 2025-01-15
tags: {tags_str}
---

# Post {i}

{"".join(body_parts)}
"""
        (temp_dir / "content" / "posts" / f"post-{i}.md").write_text(content)

    (temp_dir / "content" / "index.md").write_text("""---
title: Home
---

# Home

Welcome.
""")

    (temp_dir / "bengal.toml").write_text("""
title = "Content Complexity Benchmark"
baseurl = "https://example.com"

[build]
theme = "default"
parallel = true
minify_assets = false
optimize_assets = false
fingerprint_assets = false
generate_sitemap = false
generate_rss = false
""")

    return temp_dir


def get_or_create_site(
    num_pages: int,
    directives_per_page: int,
    code_blocks_per_page: int,
    taxonomy_terms_per_page: int,
) -> tuple[Path, bool]:
    """
    Get site from cache or create temp. Returns (path, use_cache).

    When use_cache is True, caller must NOT delete the directory.
    """
    scenario_name = (
        f"content_complexity_{num_pages}_d{directives_per_page}"
        f"_c{code_blocks_per_page}_t{taxonomy_terms_per_page}"
    )
    cached = SCENARIOS_DIR / scenario_name
    if cached.exists() and (cached / "bengal.toml").exists():
        return cached, True
    return create_content_complexity_site(
        num_pages, directives_per_page, code_blocks_per_page, taxonomy_terms_per_page
    ), False


@pytest.mark.parametrize("directives_per_page", [0, 2, 5, 10])
def test_benchmark_directives(benchmark, directives_per_page: int) -> None:
    """Benchmark build time vs directives per page (0, 2, 5, 10)."""
    site_dir, use_cache = get_or_create_site(50, directives_per_page, 0, 0)
    try:

        def run_build() -> None:
            site = Site.from_config(site_dir)
            if site.output_dir.exists():
                shutil.rmtree(site.output_dir)
            site.build(
                BuildOptions(
                    force_sequential=False,
                    incremental=False,
                    verbose=False,
                )
            )

        benchmark(run_build)
    finally:
        if not use_cache:
            shutil.rmtree(site_dir, ignore_errors=True)


@pytest.mark.parametrize("code_blocks_per_page", [0, 3, 10])
def test_benchmark_code_blocks(benchmark, code_blocks_per_page: int) -> None:
    """Benchmark build time vs code blocks per page (0, 3, 10)."""
    site_dir, use_cache = get_or_create_site(50, 0, code_blocks_per_page, 0)
    try:

        def run_build() -> None:
            site = Site.from_config(site_dir)
            if site.output_dir.exists():
                shutil.rmtree(site.output_dir)
            site.build(
                BuildOptions(
                    force_sequential=False,
                    incremental=False,
                    verbose=False,
                )
            )

        benchmark(run_build)
    finally:
        if not use_cache:
            shutil.rmtree(site_dir, ignore_errors=True)


@pytest.mark.parametrize("taxonomy_terms_per_page", [0, 5, 20])
def test_benchmark_taxonomy(benchmark, taxonomy_terms_per_page: int) -> None:
    """Benchmark build time vs taxonomy terms per page (0, 5, 20)."""
    site_dir, use_cache = get_or_create_site(50, 0, 0, taxonomy_terms_per_page)
    try:

        def run_build() -> None:
            site = Site.from_config(site_dir)
            if site.output_dir.exists():
                shutil.rmtree(site.output_dir)
            site.build(
                BuildOptions(
                    force_sequential=False,
                    incremental=False,
                    verbose=False,
                )
            )

        benchmark(run_build)
    finally:
        if not use_cache:
            shutil.rmtree(site_dir, ignore_errors=True)
