#!/usr/bin/env python3
"""
Synthetic render-tier benchmarks for Bengal.

Establishes three performance floors by controlling *only* template complexity:

  Tier 1 — Infrastructure floor
    1 000 pages, template: {{ content | safe }}
    Measures: Bengal pipeline overhead (parsing, routing, file I/O, scheduling)
    Target: the minimum achievable pages/sec — no Kida work at all

  Tier 2 — Kida floor
    1 000 pages, template: base.html inheritance + nav loop
    Measures: typical Kida work for a simple docs-style page
    Target: how fast Kida renders a realistic-but-lean template

  Tier 3 — Production floor
    1 000 pages, theme = "default" (full docs theme)
    Measures: current production throughput on a controlled dataset
    Target: should be in the same ballpark as the live site (~90 pages/sec)

Run with:
    uv run python benchmarks/bench_render_tiers.py
    uv run python benchmarks/bench_render_tiers.py --pages 500 --runs 2
    uv run python benchmarks/bench_render_tiers.py --tier 1   # single tier
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

TIER1_PAGE_HTML = """\
{{ content | safe }}
"""

# Minimal base → child pattern so Kida's block system is exercised
TIER2_BASE_HTML = """\
<!doctype html>
<html>
<head><title>{{ page.title }}</title></head>
<body>
<nav>
{% for item in menus.main %}
<a href="{{ item.href }}">{{ item.name }}</a>
{% end %}
</nav>
<main>{% block content %}{% endblock %}</main>
</body>
</html>
"""

TIER2_PAGE_HTML = """\
{% extends "base.html" %}
{% block content %}
<h1>{{ page.title }}</h1>
{{ content | safe }}
{% endblock %}
"""

PAGE_CONTENT_TEMPLATE = """\
---
title: {title}
date: 2025-01-15
---

# {title}

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor
incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud
exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

## Section A

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu
fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident.

- Item one with **bold** text
- Item two with `inline code`
- Item three with a [link](https://example.com)

## Section B

```python
def hello(name: str) -> str:
    return f"Hello, {{name}}!"
```

| Column A | Column B |
|----------|----------|
| value 1  | value 2  |
| value 3  | value 4  |
"""

BENGAL_TOML_TEMPLATE = """\
title = "Bench Site"
baseurl = "https://bench.example.com"

[build]
theme = "{theme}"
parallel = true
minify_assets = false
optimize_assets = false
fingerprint_assets = false
generate_sitemap = false
generate_rss = false
"""

MENU_CONFIG = """\

[[menus.main]]
name = "Home"
url = "/"
weight = 1

[[menus.main]]
name = "Docs"
url = "/docs/"
weight = 2

[[menus.main]]
name = "About"
url = "/about/"
weight = 3
"""


# ---------------------------------------------------------------------------
# Site creation helpers
# ---------------------------------------------------------------------------


def _write_pages(content_dir: Path, num_pages: int) -> None:
    """Write num_pages markdown files to content_dir."""
    content_dir.mkdir(parents=True, exist_ok=True)
    for i in range(num_pages):
        text = PAGE_CONTENT_TEMPLATE.format(title=f"Page {i:04d}")
        (content_dir / f"page-{i:04d}.md").write_text(text)


def create_tier1_site(num_pages: int) -> Path:
    """
    Tier 1: trivial template — measures Bengal pipeline overhead.

    Theme: local 'bench-t1' with a single page.html = {{ content | safe }}.
    """
    root = Path(tempfile.mkdtemp(prefix="bengal-bench-t1-"))
    (root / "public").mkdir()

    # Content
    _write_pages(root / "content", num_pages)
    (root / "content" / "index.md").write_text("---\ntitle: Home\n---\n\n# Home\n")

    # Local theme: just a trivial page.html
    tpl_dir = root / "themes" / "bench-t1" / "templates"
    tpl_dir.mkdir(parents=True)
    (tpl_dir / "page.html").write_text(TIER1_PAGE_HTML)

    # bengal.toml (no menus for tier 1)
    (root / "bengal.toml").write_text(BENGAL_TOML_TEMPLATE.format(theme="bench-t1"))
    return root


def create_tier2_site(num_pages: int) -> Path:
    """
    Tier 2: base+child inheritance, nav loop — measures Kida for lean templates.

    Theme: local 'bench-t2' with base.html + page.html + menus config.
    """
    root = Path(tempfile.mkdtemp(prefix="bengal-bench-t2-"))
    (root / "public").mkdir()

    # Content
    _write_pages(root / "content", num_pages)
    (root / "content" / "index.md").write_text("---\ntitle: Home\n---\n\n# Home\n")

    # Local theme: base + page
    tpl_dir = root / "themes" / "bench-t2" / "templates"
    tpl_dir.mkdir(parents=True)
    (tpl_dir / "base.html").write_text(TIER2_BASE_HTML)
    (tpl_dir / "page.html").write_text(TIER2_PAGE_HTML)

    # bengal.toml with menus
    config = BENGAL_TOML_TEMPLATE.format(theme="bench-t2") + MENU_CONFIG
    (root / "bengal.toml").write_text(config)
    return root


def create_tier3_site(num_pages: int) -> Path:
    """
    Tier 3: default theme — measures production throughput on controlled data.

    Uses Bengal's full bundled 'default' theme with all partials.
    """
    root = Path(tempfile.mkdtemp(prefix="bengal-bench-t3-"))
    (root / "public").mkdir()

    # Content — plain pages so they hit page.html
    _write_pages(root / "content", num_pages)
    (root / "content" / "index.md").write_text("---\ntitle: Home\n---\n\n# Home\n")

    # bengal.toml: full default theme, with menus for realistic nav
    config = BENGAL_TOML_TEMPLATE.format(theme="default") + MENU_CONFIG
    (root / "bengal.toml").write_text(config)
    return root


# ---------------------------------------------------------------------------
# Build runner
# ---------------------------------------------------------------------------


def run_build(site_dir: Path) -> dict:
    """Run a clean (non-incremental) Bengal build and return stats."""
    from bengal.core.site import Site
    from bengal.orchestration.build.options import BuildOptions

    site = Site.from_config(site_dir)

    # Clean previous outputs and cache
    if site.output_dir.exists():
        shutil.rmtree(site.output_dir)
    cache_dir = site_dir / ".bengal"
    if cache_dir.exists():
        shutil.rmtree(cache_dir)

    start = time.perf_counter()
    build_stats = site.build(
        BuildOptions(
            force_sequential=False,
            incremental=False,
            verbose=False,
            profile_templates=False,
        )
    )
    elapsed = time.perf_counter() - start

    return {
        "elapsed_s": elapsed,
        "pages": len(site.pages),
        "pages_per_sec": len(site.pages) / elapsed,
        "ms_per_page": elapsed / max(len(site.pages), 1) * 1000,
        "rendering_ms": getattr(build_stats, "rendering_time_ms", 0),
        "discovery_ms": getattr(build_stats, "discovery_time_ms", 0),
    }


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------


TIERS = {
    1: ("Infrastructure floor (trivial template)", create_tier1_site),
    2: ("Kida floor (base+child, nav loop)", create_tier2_site),
    3: ("Production floor (default theme)", create_tier3_site),
}


def run_tier(
    tier_num: int,
    description: str,
    factory,
    num_pages: int,
    runs: int,
) -> dict:
    """Run a single tier benchmark with `runs` repetitions and return aggregate stats."""
    results = []
    site_dir = None

    try:
        for run_i in range(runs):
            # Create a fresh site for each run (avoids warm-cache skew)
            if site_dir is not None:
                shutil.rmtree(site_dir, ignore_errors=True)
            site_dir = factory(num_pages)

            stats = run_build(site_dir)
            results.append(stats)

            render_rate = (
                stats["pages"] / (stats["rendering_ms"] / 1000) if stats["rendering_ms"] > 0 else 0
            )
            run_label = f" (run {run_i + 1}/{runs})" if runs > 1 else ""
            print(
                f"    Tier {tier_num}{run_label}: "
                f"{stats['pages_per_sec']:.1f} p/s total  |  "
                f"{render_rate:.0f} p/s render-only  "
                f"({stats['rendering_ms']:.0f}ms render, "
                f"{stats['elapsed_s'] * 1000:.0f}ms total)"
            )

    finally:
        if site_dir and site_dir.exists():
            shutil.rmtree(site_dir, ignore_errors=True)

    if not results:
        return {}

    # Aggregate: drop outliers when runs >= 3, otherwise average all
    def _avg(vals: list[float]) -> float:
        if len(vals) >= 3:
            vals = sorted(vals)[1:-1]
        return sum(vals) / len(vals)

    avg_total_rate = _avg([r["pages_per_sec"] for r in results])
    avg_render_ms = _avg([r["rendering_ms"] for r in results])
    avg_render_rate = results[0]["pages"] / (avg_render_ms / 1000) if avg_render_ms > 0 else 0

    return {
        "tier": tier_num,
        "description": description,
        "pages": num_pages,
        "runs": runs,
        "pages_per_sec": avg_total_rate,
        "ms_per_page": 1000 / avg_total_rate if avg_total_rate else 0,
        "render_pages_per_sec": avg_render_rate,
        "render_ms_per_page": avg_render_ms / results[0]["pages"] if results else 0,
    }


def print_summary(tier_results: list[dict]) -> None:
    """Print the comparative summary table."""
    if not tier_results:
        return

    t1_render_rate = tier_results[0].get("render_pages_per_sec", 1.0) or 1.0

    print()
    print("=" * 80)
    print("RENDER TIER SUMMARY")
    print("=" * 80)
    print(f"{'Tier':<6} {'Description':<34} {'render p/s':>11} {'render ms':>10} {'vs T1':>7}")
    print("-" * 80)

    for r in tier_results:
        rr = r.get("render_pages_per_sec", 0) or 0
        rm = r.get("render_ms_per_page", 0) or 0
        ratio = rr / t1_render_rate if t1_render_rate and rr else 0
        ratio_str = f"{ratio:.2f}x" if r["tier"] > 1 else "   —"
        print(f"  T{r['tier']}   {r['description']:<34} {rr:>10.0f}  {rm:>8.2f}ms  {ratio_str:>7}")

    print()
    print(f"{'Tier':<6} {'Description':<34} {'total p/s':>11} {'total ms':>9}")
    print("-" * 80)
    for r in tier_results:
        print(
            f"  T{r['tier']}   {r['description']:<34} "
            f"{r['pages_per_sec']:>10.1f}  "
            f"{r['ms_per_page']:>7.1f}ms"
        )

    print("=" * 80)
    print()

    if len(tier_results) >= 2:
        t1r = tier_results[0].get("render_ms_per_page", 0)
        t2r = tier_results[1].get("render_ms_per_page", 0)
        kida_cost_ms = t2r - t1r
        print(f"  Kida simple template cost (T2 - T1):   {kida_cost_ms:+.2f} ms/page render")

    if len(tier_results) >= 3:
        t1r = tier_results[0].get("render_ms_per_page", 0)
        t3r = tier_results[2].get("render_ms_per_page", 0)
        full_cost_ms = t3r - t1r
        print(f"  Default theme template cost (T3 - T1): {full_cost_ms:+.2f} ms/page render")

    print()
    print("  Interpretation:")
    print("    T1 render p/s = minimum Kida work (pipeline floor)")
    print("    T2 render p/s = base+child inheritance + nav loop")
    print("    T3 render p/s = full default theme (all partials, css, etc.)")
    print("    Total p/s includes discovery, parsing, post-processing, health checks")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bengal synthetic render tier benchmarks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=1000,
        help="Number of pages per tier (default: 1000)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=2,
        help="Repetitions per tier — middle runs averaged when ≥3 (default: 2)",
    )
    parser.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3],
        default=None,
        help="Run only a specific tier (default: all three)",
    )
    args = parser.parse_args()

    tiers_to_run = [args.tier] if args.tier else [1, 2, 3]

    print()
    print("=" * 72)
    print("Bengal Render Tier Benchmarks")
    print(f"  pages per tier : {args.pages}")
    print(f"  runs per tier  : {args.runs}")
    print(f"  tiers          : {tiers_to_run}")
    print("=" * 72)
    print()

    tier_results = []
    for tier_num in tiers_to_run:
        description, factory = TIERS[tier_num]
        print(f"  Running Tier {tier_num}: {description} ...")
        result = run_tier(tier_num, description, factory, args.pages, args.runs)
        if result:
            tier_results.append(result)

    print_summary(tier_results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
