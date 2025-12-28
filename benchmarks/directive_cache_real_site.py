#!/usr/bin/env python3
"""
Benchmark: DirectiveCache impact on REAL site content.

Tests against actual content from site/ directory to measure
realistic performance impact.

Usage:
    python -m benchmarks.directive_cache_real_site
"""

from __future__ import annotations

import statistics
import time
from pathlib import Path


def collect_site_content(site_dir: Path, max_files: int = 50) -> list[tuple[str, str]]:
    """Collect markdown files from site directory.

    Returns:
        List of (filename, content) tuples
    """
    files = []

    for md_file in site_dir.rglob("*.md"):
        # Skip files in public/output directories
        if "public" in md_file.parts or "_site" in md_file.parts:
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
            # Skip very small files
            if len(content) < 100:
                continue
            files.append((str(md_file.relative_to(site_dir)), content))
        except Exception:
            continue

        if len(files) >= max_files:
            break

    return files


def count_directives(content: str) -> int:
    """Count directive blocks in content."""
    return content.count(":::{")


def render_baseline(content: str) -> tuple[str, float]:
    """Render without cache, return (html, time_ms)."""
    from bengal.directives.cache import configure_cache
    from bengal.rendering.parsers.patitas import create_markdown

    # Ensure cache is disabled for baseline
    configure_cache(enabled=False)

    md = create_markdown(plugins=["all"], highlight=False)

    start = time.perf_counter()
    html = md(content)
    elapsed = (time.perf_counter() - start) * 1000

    return html, elapsed


def render_with_cache(content: str) -> tuple[str, float]:
    """Render with directive cache, return (html, time_ms)."""
    from bengal.directives.cache import configure_cache
    from bengal.rendering.parsers.patitas import create_markdown

    # Ensure cache is enabled
    configure_cache(enabled=True)

    md = create_markdown(plugins=["all"], highlight=False)

    start = time.perf_counter()
    html = md(content)
    elapsed = (time.perf_counter() - start) * 1000

    return html, elapsed


def main():
    from bengal.directives.cache import configure_cache, get_cache

    print("=" * 70)
    print("DirectiveCache Benchmark — Real Site Content")
    print("=" * 70)

    # Find site directory
    site_dir = Path("site")
    if not site_dir.exists():
        print("Error: site/ directory not found")
        return

    # Collect files
    print("\nCollecting markdown files from site/...")
    files = collect_site_content(site_dir, max_files=100)
    print(f"Found {len(files)} markdown files")

    # Count directives
    total_directives = sum(count_directives(content) for _, content in files)
    total_chars = sum(len(content) for _, content in files)
    print(f"Total content: {total_chars:,} chars")
    print(f"Total directives: {total_directives}")

    if total_directives == 0:
        print("\n⚠️ No directives found in site content. Nothing to cache.")
        return

    # Warmup
    print("\nWarmup...")
    for _, content in files[:5]:
        render_baseline(content)

    # Benchmark 1: Baseline (no cache)
    print("\n" + "-" * 70)
    print("[1/2] Baseline (no cache) - rendering all files...")
    print("-" * 70)

    configure_cache(enabled=False)
    get_cache().clear()

    baseline_times = []
    for filename, content in files:
        _, elapsed = render_baseline(content)
        baseline_times.append(elapsed)

    baseline_total = sum(baseline_times)
    baseline_mean = statistics.mean(baseline_times)
    print(f"Total time: {baseline_total:.2f}ms")
    print(f"Mean per file: {baseline_mean:.2f}ms")

    # Benchmark 2: With cache (simulating cross-file caching)
    print("\n" + "-" * 70)
    print("[2/2] With directive cache (shared across files)...")
    print("-" * 70)

    # Enable cache and clear it
    configure_cache(enabled=True)
    cache = get_cache()
    cache.clear()
    cache.reset_stats()

    cached_times = []
    for filename, content in files:
        _, elapsed = render_with_cache(content)
        cached_times.append(elapsed)

    cached_total = sum(cached_times)
    cached_mean = statistics.mean(cached_times)
    cache_stats = cache.stats()

    print(f"Total time: {cached_total:.2f}ms")
    print(f"Mean per file: {cached_mean:.2f}ms")
    print(f"Cache hits: {cache_stats['hits']}")
    print(f"Cache misses: {cache_stats['misses']}")
    hit_rate = cache_stats["hit_rate"]
    print(f"Hit rate: {hit_rate:.1%}")

    # Summary
    speedup = baseline_total / cached_total if cached_total > 0 else 0

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\n{'Metric':<30} {'Baseline':>15} {'With Cache':>15}")
    print("-" * 60)
    print(f"{'Total render time':<30} {baseline_total:>14.2f}ms {cached_total:>14.2f}ms")
    print(f"{'Mean per file':<30} {baseline_mean:>14.2f}ms {cached_mean:>14.2f}ms")
    print(f"{'Speedup':<30} {'-':>15} {speedup:>14.2f}x")
    print(f"{'Cache hit rate':<30} {'-':>15} {hit_rate:>14.1%}")
    print(
        f"{'Directives processed':<30} {total_directives:>15} {cache_stats['hits'] + cache_stats['misses']:>15}"
    )

    # Recommendation
    print("\n" + "=" * 70)
    if speedup > 1.1:
        print("✅ Recommendation: DirectiveCache provides meaningful speedup!")
    elif speedup > 1.0:
        print("⚠️ Recommendation: Marginal speedup. Consider if complexity is worth it.")
    else:
        print("❌ Recommendation: No speedup. DirectiveCache adds overhead without benefit.")
    print("=" * 70)


if __name__ == "__main__":
    main()
