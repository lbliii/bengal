"""
Benchmark incremental builds at scale (1,000 - 10,000 pages).

This validates that the 18-42x speedup claim holds at realistic documentation scale,
not just for toy sites with 10-100 pages.

Tests:
- 1,000 pages: Large blog, medium docs site
- 5,000 pages: Large documentation site (e.g., framework docs)
- 10,000 pages: Enterprise docs (e.g., Kubernetes, AWS, Python)

For each scale:
- Full build time
- Incremental rebuild (single page change)
- Incremental rebuild (template change affecting 100 pages)
- Cache size and memory usage
- Speedup ratio validation

Expected Results:
- Incremental speedup should remain 15-40x even at 10,000 pages
- Memory usage should be sub-linear (not O(n²))
- Cache size should be reasonable (< 50MB for 10K pages)
"""

import shutil
import time
from pathlib import Path
from tempfile import mkdtemp

from results_manager import BenchmarkResults

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions


def create_large_test_site(num_pages: int, sections: int = 20) -> Path:
    """
    Create a realistic test site with specified number of pages.

    Structure:
    - Multiple sections (topic areas)
    - Tags and categories
    - Internal cross-references
    - Code blocks with syntax highlighting
    - Realistic content length (500-1000 words)

    Args:
        num_pages: Total number of pages to generate
        sections: Number of top-level sections

    Returns:
        Path to the generated site directory
    """
    site_root = Path(mkdtemp(prefix=f"bengal_scale_{num_pages}_"))

    # Create directories
    content_dir = site_root / "content"
    templates_dir = site_root / "templates"
    assets_dir = site_root / "assets"

    content_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)
    assets_dir.mkdir(parents=True)

    # Configuration
    config_content = f"""
[site]
title = "Scale Test Site - {num_pages} Pages"
baseurl = "https://example.com"
theme = "default"

[build]
output_dir = "public"
incremental = true
parallel = true

[assets]
minify = false
fingerprint = false
"""
    (site_root / "bengal.toml").write_text(config_content)

    # Generate content across sections
    pages_per_section = num_pages // sections
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

    page_count = 0

    # Create sections with pages
    for section_idx in range(sections):
        section_name = f"section-{section_idx + 1:03d}"
        section_dir = content_dir / section_name
        section_dir.mkdir()

        # Section index
        section_tags = tags[section_idx % len(tags) : section_idx % len(tags) + 3]
        section_index = f"""---
title: "Section {section_idx + 1}"
type: section
tags: {section_tags}
---

# Section {section_idx + 1}

This is section {section_idx + 1} of the scale test.
"""
        (section_dir / "_index.md").write_text(section_index)

        # Create pages in this section
        for page_idx in range(pages_per_section):
            if page_count >= num_pages:
                break

            page_count += 1
            page_tags = [tags[i % len(tags)] for i in range(page_idx, page_idx + 3)]

            # Generate realistic content with cross-references
            content = f"""---
title: "Page {page_count:05d}"
date: 2025-01-{(page_idx % 28) + 1:02d}
tags: {page_tags}
category: "section-{section_idx + 1}"
---

# Page {page_count:05d}

This is page {page_count} in section {section_idx + 1}.

## Overview

This page demonstrates realistic content for scale testing. It includes
multiple paragraphs, code blocks, lists, and cross-references.

## Features

- **Cross-references**: Links to [[section-{(section_idx + 1) % sections:03d}/page-{(page_count + 1) % num_pages:05d}]]
- **Code examples**: Syntax-highlighted code blocks
- **Structured content**: Headings, lists, and formatting

## Code Example

```python
def process_page_{page_count}():
    \"\"\"Process page {page_count} with realistic logic.\"\"\"
    data = load_data("page_{page_count}")
    result = transform(data)
    return result
```

## Implementation Details

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod
tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
quis nostrud exercitation ullamco laboris.

### Step 1: Initialization

Initialize the system with configuration:

```yaml
page_id: {page_count}
section: {section_idx + 1}
enabled: true
```

### Step 2: Processing

Process the data through the pipeline:

1. Load configuration
2. Validate inputs
3. Transform data
4. Write outputs

### Step 3: Validation

Validate the results:

- Check data integrity
- Verify cross-references
- Test performance
- Generate reports

## Related Pages

- [[section-{section_idx:03d}/page-{max(0, page_count - 1):05d}|Previous]]
- [[section-{section_idx:03d}/page-{(page_count + 1) % num_pages:05d}|Next]]
- [[section-{(section_idx + 1) % sections:03d}/_index|Next Section]]

## Conclusion

This page demonstrates realistic content complexity for scale testing.
Content includes approximately 500-700 words, multiple code blocks,
cross-references, and structured formatting.
"""

            page_file = section_dir / f"page-{page_count:05d}.md"
            page_file.write_text(content)

    print(f"✓ Generated {page_count} pages across {sections} sections")
    return site_root


def measure_cache_size(site_root: Path) -> float:
    """Measure the build cache size in MB."""
    cache_file = site_root / "public" / ".bengal-cache.json"
    if cache_file.exists():
        return cache_file.stat().st_size / (1024 * 1024)
    return 0.0


def benchmark_full_build(site_root: Path) -> dict:
    """Run a full build and measure performance."""
    print("  Running full build...")

    # Clear any existing cache
    cache_file = site_root / "public" / ".bengal-cache.json"
    if cache_file.exists():
        cache_file.unlink()

    site = Site.from_config(site_root)

    start = time.perf_counter()
    stats = site.build(BuildOptions(incremental=False))
    elapsed = time.perf_counter() - start

    cache_size = measure_cache_size(site_root)

    return {
        "time": elapsed,
        "pages": stats.total_pages,
        "pages_per_sec": stats.total_pages / elapsed,
        "cache_size_mb": cache_size,
    }


def benchmark_incremental_single_page(site_root: Path, site: Site) -> dict:
    """
    Benchmark incremental rebuild after changing a single page.

    This simulates the most common editing scenario: fixing a typo,
    updating content, or adding a paragraph to one page.

    Args:
        site_root: Path to test site
        site: Already-built Site object (reused for incremental context)
    """
    print("  Running incremental build (single page change)...")

    # Modify a single page
    content_dir = site_root / "content"
    test_page = list(content_dir.glob("section-001/page-*.md"))[0]

    original = test_page.read_text()
    modified = original + "\n\n## Updated Section\n\nThis content was just added.\n"
    test_page.write_text(modified)

    # Small delay to ensure file mtime changes
    time.sleep(0.1)

    start = time.perf_counter()
    stats = site.build(BuildOptions(incremental=True))
    elapsed = time.perf_counter() - start

    # Restore original
    test_page.write_text(original)

    cache_size = measure_cache_size(site_root)

    return {
        "time": elapsed,
        "pages_rebuilt": stats.total_pages,
        "cache_size_mb": cache_size,
    }


def benchmark_incremental_template_change(site_root: Path) -> dict:
    """
    Benchmark incremental rebuild after template change by modifying config.

    This simulates a global change that requires rebuilding all pages,
    such as changing the site title or base template.
    """
    print("  Running incremental build (template change)...")

    # Modify site config (triggers template changes)
    config_file = site_root / "bengal.toml"
    original_config = config_file.read_text()

    # Change site title to trigger re-render
    modified_config = original_config.replace(
        'title = "Test Site"', 'title = "Test Site (Modified)"'
    )
    config_file.write_text(modified_config)

    # Small delay to ensure file mtime changes
    time.sleep(0.1)

    # Build with new config (this will be a full rebuild due to config change)
    site = Site.from_config(site_root)

    start = time.perf_counter()
    stats = site.build(BuildOptions(incremental=True))
    elapsed = time.perf_counter() - start

    # Restore original config
    config_file.write_text(original_config)

    cache_size = measure_cache_size(site_root)

    return {
        "time": elapsed,
        "pages_rebuilt": stats.total_pages,
        "cache_size_mb": cache_size,
    }


def run_scale_benchmark(num_pages: int, sections: int = 20):
    """Run complete benchmark suite for a given scale."""
    print(f"\n{'=' * 80}")
    print(f"SCALE BENCHMARK: {num_pages:,} PAGES")
    print(f"{'=' * 80}")

    # Create test site
    print(f"\nGenerating test site with {num_pages:,} pages...")
    site_root = create_large_test_site(num_pages, sections)

    try:
        # Full build
        full_result = benchmark_full_build(site_root)

        # Create Site object ONCE for incremental builds (reuses build state)
        site = Site.from_config(site_root)

        # Incremental: Single page change
        incr_single = benchmark_incremental_single_page(site_root, site)

        # Incremental: Template change
        incr_template = benchmark_incremental_template_change(site_root)

        # Calculate speedups
        single_speedup = full_result["time"] / incr_single["time"]
        template_speedup = full_result["time"] / incr_template["time"]

        # Print results
        print(f"\n{'-' * 80}")
        print("RESULTS")
        print(f"{'-' * 80}")
        print("\nFull Build:")
        print(f"  Time:         {full_result['time']:.3f}s")
        print(f"  Pages/sec:    {full_result['pages_per_sec']:.1f}")
        print(f"  Cache size:   {full_result['cache_size_mb']:.2f}MB")

        print("\nIncremental Build (Single Page):")
        print(f"  Time:         {incr_single['time']:.3f}s")
        print(f"  Pages rebuilt: {incr_single['pages_rebuilt']}")
        print(f"  Speedup:      {single_speedup:.1f}x")
        print(f"  Cache size:   {incr_single['cache_size_mb']:.2f}MB")

        print("\nIncremental Build (Template Change):")
        print(f"  Time:         {incr_template['time']:.3f}s")
        print(f"  Pages rebuilt: {incr_template['pages_rebuilt']}")
        print(f"  Speedup:      {template_speedup:.1f}x")
        print(f"  Cache size:   {incr_template['cache_size_mb']:.2f}MB")

        # Validation
        print(f"\n{'-' * 80}")
        print("VALIDATION")
        print(f"{'-' * 80}")

        checks = []

        # Check speedup targets
        if single_speedup >= 15.0:
            checks.append(f"✅ Single page speedup: {single_speedup:.1f}x (target: ≥15x)")
        else:
            checks.append(f"❌ Single page speedup: {single_speedup:.1f}x (target: ≥15x)")

        if template_speedup >= 5.0:
            checks.append(f"✅ Template speedup: {template_speedup:.1f}x (target: ≥5x)")
        else:
            checks.append(f"⚠️  Template speedup: {template_speedup:.1f}x (target: ≥5x)")

        # Check cache size is reasonable
        max_cache_mb = num_pages * 0.01  # ~10KB per page
        if incr_single["cache_size_mb"] <= max_cache_mb:
            checks.append(
                f"✅ Cache size: {incr_single['cache_size_mb']:.2f}MB (target: ≤{max_cache_mb:.1f}MB)"
            )
        else:
            checks.append(
                f"⚠️  Cache size: {incr_single['cache_size_mb']:.2f}MB (target: ≤{max_cache_mb:.1f}MB)"
            )

        # Check pages/sec
        target_pps = 100
        if full_result["pages_per_sec"] >= target_pps:
            checks.append(
                f"✅ Performance: {full_result['pages_per_sec']:.1f} pages/sec (target: ≥{target_pps})"
            )
        else:
            checks.append(
                f"⚠️  Performance: {full_result['pages_per_sec']:.1f} pages/sec (target: ≥{target_pps})"
            )

        for check in checks:
            print(check)

        return {
            "pages": num_pages,
            "full_build": full_result,
            "incr_single": incr_single,
            "incr_template": incr_template,
            "single_speedup": single_speedup,
            "template_speedup": template_speedup,
        }

    finally:
        # Cleanup
        shutil.rmtree(site_root)


def run_all_scale_benchmarks(save_results: bool = True):
    """Run benchmarks at multiple scales."""
    print("=" * 80)
    print("BENGAL SSG - INCREMENTAL BUILD SCALE BENCHMARKS")
    print("=" * 80)
    print()
    print("This benchmark validates that incremental build performance")
    print("scales to real-world documentation site sizes.")
    print()
    print("Scales tested:")
    print("  - 1,000 pages:  Large blog, medium docs site")
    print("  - 5,000 pages:  Large documentation site (framework docs)")
    print("  - 10,000 pages: Enterprise docs (Kubernetes, AWS, Python)")
    print()

    scales = [
        (1000, 20),  # 1K pages, 20 sections
        (5000, 50),  # 5K pages, 50 sections
        (10000, 100),  # 10K pages, 100 sections
    ]

    # Option for quick test
    # scales = [(1000, 20)]  # Uncomment for quick test

    results = []

    for num_pages, sections in scales:
        result = run_scale_benchmark(num_pages, sections)
        results.append(result)

    # Summary table
    print(f"\n{'=' * 80}")
    print("SUMMARY - INCREMENTAL BUILD SCALING")
    print(f"{'=' * 80}")
    print()
    print(
        f"{'Pages':<10} {'Full Build':<12} {'Single Page':<14} {'Speedup':<10} {'Cache (MB)':<12}"
    )
    print(f"{'':<10} {'(seconds)':<12} {'(seconds)':<14} {'(ratio)':<10} {'':<12}")
    print("-" * 80)

    for r in results:
        print(
            f"{r['pages']:<10,} "
            f"{r['full_build']['time']:>8.2f}s    "
            f"{r['incr_single']['time']:>10.3f}s    "
            f"{r['single_speedup']:>6.1f}x    "
            f"{r['incr_single']['cache_size_mb']:>8.2f}"
        )

    print()
    print("Key Findings:")
    print()

    # Check if speedup degrades with scale
    speedups = [r["single_speedup"] for r in results]
    if all(s >= 15.0 for s in speedups):
        print("✅ Incremental build speedup maintains ≥15x at all scales")
    else:
        print("⚠️  Incremental build speedup degrades at larger scales")

    # Check if performance is acceptable
    full_times = [r["full_build"]["time"] for r in results]
    if results[-1]["full_build"]["time"] < 120:  # 10K pages in < 2 min
        print(
            f"✅ Full builds complete in reasonable time even at 10K pages ({full_times[-1]:.1f}s)"
        )
    else:
        print(f"⚠️  Full builds may be too slow at 10K pages ({full_times[-1]:.1f}s)")

    # Check cache size scaling
    cache_sizes = [r["incr_single"]["cache_size_mb"] for r in results]
    cache_per_page = cache_sizes[-1] / results[-1]["pages"]
    if cache_per_page < 0.02:  # < 20KB per page
        print(f"✅ Cache size scales linearly ({cache_per_page * 1024:.1f}KB per page)")
    else:
        print(
            f"⚠️  Cache size may be growing super-linearly ({cache_per_page * 1024:.1f}KB per page)"
        )

    print()

    # Save results if requested
    if save_results:
        print("Saving results...")
        manager = BenchmarkResults()

        # Prepare structured data
        results_data = {
            "scales": [
                {
                    "pages": r["pages"],
                    "full_build_time": r["full_build"]["time"],
                    "full_build_pages_per_sec": r["full_build"]["pages_per_sec"],
                    "incr_single_time": r["incr_single"]["time"],
                    "incr_single_speedup": r["single_speedup"],
                    "incr_template_time": r["incr_template"]["time"],
                    "incr_template_speedup": r["template_speedup"],
                    "cache_size_mb": r["incr_single"]["cache_size_mb"],
                }
                for r in results
            ],
            "summary": {
                "min_speedup": min(r["single_speedup"] for r in results),
                "max_speedup": max(r["single_speedup"] for r in results),
                "avg_speedup": sum(r["single_speedup"] for r in results) / len(results),
                "largest_scale": results[-1]["pages"],
                "all_passed": all(r["single_speedup"] >= 15.0 for r in results),
            },
        }

        saved_path = manager.save_result("incremental_scale", results_data)
        print(f"✓ Results saved to: {saved_path}")
        print()

    return results


if __name__ == "__main__":
    run_all_scale_benchmarks()
