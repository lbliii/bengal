"""
Phase breakdown benchmarks.

Runs full builds for phase-time tracking. The build API does not support
skipping render or running phases in isolation, so we benchmark total build
time. For detailed phase breakdown (discovery, taxonomy, rendering, assets,
postprocess), use benchmark_full_build.py which extracts from BuildStats.

Run with:
    uv run pytest tests/performance/benchmark_phase_breakdown.py -v --benchmark-only
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions

PARAGRAPH = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua."
)


def create_minimal_site(num_pages: int) -> Path:
    """Create minimal test site."""
    temp_dir = Path(tempfile.mkdtemp())
    (temp_dir / "content" / "posts").mkdir(parents=True)
    (temp_dir / "public").mkdir()

    for i in range(num_pages):
        content = f"""---
title: Post {i}
date: 2025-01-15
tags: []
---

# Post {i}

{PARAGRAPH}
"""
        (temp_dir / "content" / "posts" / f"post-{i}.md").write_text(content)

    (temp_dir / "content" / "index.md").write_text("---\ntitle: Home\n---\n\n# Home\n")
    (temp_dir / "bengal.toml").write_text("""
title = "Phase Breakdown Benchmark"
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


@pytest.mark.parametrize("num_pages", [100, 500])
def test_benchmark_phase_breakdown(benchmark, num_pages: int) -> None:
    """
    Benchmark full build time.

    Phase times (discovery, taxonomy, rendering, assets, postprocess) are
    tracked internally by BuildStats. Use benchmark_full_build.py for
    detailed phase breakdown. This benchmark tracks total build time over time.
    """
    site_dir = create_minimal_site(num_pages)
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
        shutil.rmtree(site_dir, ignore_errors=True)
