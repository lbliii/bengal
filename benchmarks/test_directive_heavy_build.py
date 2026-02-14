"""
Directive-heavy build benchmarks for real-world documentation sites.

Tracks build performance when content uses directives (admonitions, tabs, cards),
syntax highlighting, and TOC—the factors that slow real docs vs minimal benchmarks.
Docs claim "directive-heavy sites typically see 40-60% of benchmark speeds."

Prerequisite: pip install -e . from project root (bengal CLI + deps must be available).

Run with:
    pytest benchmarks/test_directive_heavy_build.py -v --benchmark-only

Related:
    - site/content/docs/about/benchmarks.md (What Slows Builds Down)
"""

import subprocess
import time
from pathlib import Path

import pytest

DIRECTIVE_TYPES = ["note", "warning", "tip", "important"]


def _directive_content(page_idx: int) -> str:
    """Generate content with multiple directives per page (deterministic)."""
    # Use page_idx to pick directives deterministically for reproducible benchmarks
    n_dirs = 2 + (page_idx % 3)
    directives = [DIRECTIVE_TYPES[(page_idx + i) % len(DIRECTIVE_TYPES)] for i in range(n_dirs)]
    admonition_blocks = "\n\n".join(
        [
            f""":::{d}
This is a {d} block on page {page_idx}. It adds parsing and rendering overhead.
:::
"""
            for d in directives
        ]
    )
    return f"""---
title: Doc Page {page_idx}
tags: [docs, directive-heavy]
---

# Page {page_idx}

Realistic documentation content with **formatting** and `inline code`.

## Section A

{admonition_blocks}

## Code Example

```python
def example_{page_idx}():
    '''Syntax highlighting adds overhead.'''
    return "page_{page_idx}"
```

## Section B

More content with *emphasis* and [links](/related).
"""


def create_directive_heavy_site(num_pages: int, tmp_path: Path) -> Path:
    """Create a site with directive-heavy content (admonitions, code blocks)."""
    site_root = tmp_path / f"directive_heavy_{num_pages}"
    site_root.mkdir(exist_ok=True)

    (site_root / "bengal.toml").write_text("""[site]
title = "Directive-Heavy Benchmark"
base_url = "https://example.com"

[build]
output_dir = "output"
parallel = true
""")

    content_dir = site_root / "content"
    content_dir.mkdir(exist_ok=True)

    for i in range(num_pages):
        (content_dir / f"page{i:04d}.md").write_text(_directive_content(i))

    (content_dir / "index.md").write_text("""---
title: Home
---

# Directive-Heavy Benchmark

This site benchmarks real-world documentation build performance.
""")

    return site_root


def _bengal_build(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    """Run bengal build (requires: pip install -e . from project root)."""
    return subprocess.run(
        ["bengal", "build", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@pytest.fixture
def directive_heavy_100(tmp_path):
    """100-page directive-heavy site (built once, reused)."""
    site = create_directive_heavy_site(100, tmp_path)
    _bengal_build(site)
    return site


@pytest.mark.benchmark
def test_directive_heavy_cold_build_100(benchmark, tmp_path):
    """Cold build of 100 pages with directives (admonitions, code blocks)."""
    site = create_directive_heavy_site(100, tmp_path)

    def build():
        _bengal_build(site)

    benchmark(build)


@pytest.mark.benchmark
def test_directive_heavy_incremental_single_page(benchmark, directive_heavy_100):
    """Incremental rebuild after editing one directive-heavy page."""
    page = directive_heavy_100 / "content" / "page0050.md"
    original = page.read_text()

    def build():
        page.write_text(original + f"\n\n<!-- edit {time.time_ns()} -->")
        _bengal_build(directive_heavy_100, "--incremental")
        page.write_text(original)

    benchmark(build)


@pytest.mark.benchmark
def test_directive_heavy_vs_minimal_ratio(tmp_path):
    """
    Compare directive-heavy vs minimal build time (informational).

    Docs claim directive-heavy sites see 40-60% of minimal benchmark speeds.
    This test reports the ratio for tracking.
    """
    # Minimal site (like large_site scenario)
    minimal = tmp_path / "minimal"
    minimal.mkdir()
    (minimal / "bengal.toml").write_text("""[site]
title = "Minimal"
base_url = "https://example.com"

[build]
output_dir = "output"
parallel = true
""")
    (minimal / "content").mkdir()
    for i in range(100):
        (minimal / "content" / f"page{i:04d}.md").write_text(
            f"---\ntitle: Page {i}\n---\n# Page {i}\nContent."
        )
    (minimal / "content" / "index.md").write_text("---\ntitle: Home\n---\n# Home")

    # Directive-heavy site
    directive_site = create_directive_heavy_site(100, tmp_path)

    def run_build(cwd: Path) -> float:
        start = time.perf_counter()
        _bengal_build(cwd)
        return time.perf_counter() - start

    # Warm run (discard)
    run_build(minimal)
    run_build(directive_site)

    # Timed runs
    minimal_time = run_build(minimal)
    directive_time = run_build(directive_site)

    ratio = directive_time / minimal_time
    pps_minimal = 100 / minimal_time
    pps_directive = 100 / directive_time

    print("\nDirective-heavy vs minimal (100 pages):")
    print(f"  Minimal:      {minimal_time:.3f}s ({pps_minimal:.0f} pps)")
    print(f"  Directive:    {directive_time:.3f}s ({pps_directive:.0f} pps)")
    print(f"  Ratio:        {ratio:.2f}x (directive-heavy / minimal)")
    print(f"  Speed factor: {1 / ratio:.2f} (docs claim ~0.4-0.6)")
