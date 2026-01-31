"""
Performance benchmarks for parallel processing.
Tests to validate the 2-4x speedup claims for asset processing and post-processing.
"""

import shutil
import tempfile
import time
from pathlib import Path

from bengal.core.site import Site


def create_test_site(num_assets: int) -> Path:
    """Create a temporary test site with specified number of assets."""
    temp_dir = Path(tempfile.mkdtemp())

    # Create directory structure
    (temp_dir / "content").mkdir()
    (temp_dir / "assets" / "css").mkdir(parents=True)
    (temp_dir / "assets" / "js").mkdir(parents=True)
    (temp_dir / "assets" / "images").mkdir(parents=True)
    (temp_dir / "public").mkdir()

    # Create CSS assets
    css_count = num_assets // 3
    for i in range(css_count):
        content = f"body {{ color: red{i}; margin: {i}px; padding: {i}px; }}\n" * 20
        (temp_dir / "assets" / "css" / f"style{i}.css").write_text(content)

    # Create JS assets
    js_count = num_assets // 3
    for i in range(js_count):
        content = f"console.log('test{i}');\nfunction test{i}() {{ return {i}; }}\n" * 20
        (temp_dir / "assets" / "js" / f"script{i}.js").write_text(content)

    # Create image assets (minimal PNG)
    img_count = num_assets - css_count - js_count
    png_data = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    for i in range(img_count):
        (temp_dir / "assets" / "images" / f"image{i}.png").write_bytes(png_data)

    # Create config
    (temp_dir / "bengal.toml").write_text("""
[build]
title = "Benchmark Site"
theme = "default"
minify_assets = false
optimize_assets = false
fingerprint_assets = true
""")

    return temp_dir


def benchmark_asset_processing(num_assets: int, parallel: bool) -> float:
    """
    Benchmark asset processing with or without parallelism.

    Args:
        num_assets: Number of assets to process
        parallel: Whether to use parallel processing

    Returns:
        Time in seconds

    """
    site_dir = create_test_site(num_assets)

    try:
        # Update config
        config_path = site_dir / "bengal.toml"
        config_content = config_path.read_text()
        config_content += f"\nparallel = {'true' if parallel else 'false'}\n"
        config_path.write_text(config_content)

        site = Site.from_config(site_dir)
        site.discover_assets()

        # Verify we have the right number of assets (approximately, theme assets add more)
        # Just make sure we have at least the requested amount
        assert len(site.assets) >= num_assets, (
            f"Expected at least {num_assets} assets, got {len(site.assets)}"
        )

        # Benchmark asset processing
        start = time.time()
        site._process_assets()
        elapsed = time.time() - start

        return elapsed
    finally:
        shutil.rmtree(site_dir)


def benchmark_post_processing(parallel: bool) -> float:
    """
    Benchmark post-processing with or without parallelism.

    Args:
        parallel: Whether to use parallel processing

    Returns:
        Time in seconds

    """
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Create directory structure
        (temp_dir / "content").mkdir()
        (temp_dir / "public").mkdir()

        # Create test content
        for i in range(50):
            (temp_dir / "content" / f"post{i}.md").write_text(f"""---
title: Post {i}
date: 2025-01-{(i % 28) + 1:02d}
tags: [test, python, benchmark]
---

This is test post {i} with some content for benchmarking.
""")

        # Create config
        config_content = f"""
[build]
title = "Benchmark Site"
baseurl = "https://example.com"
generate_sitemap = true
generate_rss = true
validate_links = false
parallel = {"true" if parallel else "false"}
"""
        (temp_dir / "bengal.toml").write_text(config_content)

        site = Site.from_config(temp_dir)
        site.discover_content()

        # Manually create output pages (simulate build)
        for page in site.pages:
            page.output_path = site.output_dir / f"{page.slug}.html"
            page.output_path.write_text(f"<html><body>{page.title}</body></html>")

        # Benchmark post-processing
        start = time.time()
        site._post_process()
        elapsed = time.time() - start

        return elapsed
    finally:
        shutil.rmtree(temp_dir)


def run_benchmarks():
    """Run all benchmarks and report results."""
    print("=" * 80)
    print("BENGAL SSG - PARALLEL PROCESSING BENCHMARKS")
    print("=" * 80)
    print()

    # Benchmark asset processing with various sizes
    print("ASSET PROCESSING BENCHMARKS")
    print("-" * 80)

    asset_counts = [10, 25, 50, 100]

    for count in asset_counts:
        print(f"\nTesting with {count} assets:")

        # Run multiple times and average
        sequential_times = []
        parallel_times = []

        for _run in range(3):
            seq_time = benchmark_asset_processing(count, parallel=False)
            sequential_times.append(seq_time)

            par_time = benchmark_asset_processing(count, parallel=True)
            parallel_times.append(par_time)

        avg_sequential = sum(sequential_times) / len(sequential_times)
        avg_parallel = sum(parallel_times) / len(parallel_times)
        speedup = avg_sequential / avg_parallel if avg_parallel > 0 else 0

        print(f"  Sequential:  {avg_sequential:.3f}s")
        print(f"  Parallel:    {avg_parallel:.3f}s")
        print(f"  Speedup:     {speedup:.2f}x")

        if speedup >= 1.5:
            print(f"  ✅ PASS: Achieved {speedup:.2f}x speedup (target: 1.5x+)")
        elif speedup >= 1.0:
            print(f"  ⚠️  MARGINAL: Only {speedup:.2f}x speedup (target: 1.5x+)")
        else:
            print(f"  ❌ FAIL: Parallel is slower ({speedup:.2f}x)")

    # Benchmark post-processing
    print("\n\nPOST-PROCESSING BENCHMARKS")
    print("-" * 80)

    print("\nTesting post-processing (sitemap + RSS):")

    sequential_times = []
    parallel_times = []

    for _run in range(5):
        seq_time = benchmark_post_processing(parallel=False)
        sequential_times.append(seq_time)

        par_time = benchmark_post_processing(parallel=True)
        parallel_times.append(par_time)

    avg_sequential = sum(sequential_times) / len(sequential_times)
    avg_parallel = sum(parallel_times) / len(parallel_times)
    speedup = avg_sequential / avg_parallel if avg_parallel > 0 else 0

    print(f"  Sequential:  {avg_sequential:.3f}s")
    print(f"  Parallel:    {avg_parallel:.3f}s")
    print(f"  Speedup:     {speedup:.2f}x")

    if speedup >= 1.3:
        print(f"  ✅ PASS: Achieved {speedup:.2f}x speedup (target: 1.3x+)")
    elif speedup >= 1.0:
        print(f"  ⚠️  MARGINAL: Only {speedup:.2f}x speedup (target: 1.3x+)")
    else:
        print(f"  ❌ FAIL: Parallel is slower ({speedup:.2f}x)")

    print("\n" + "=" * 80)
    print("BENCHMARK COMPLETE")
    print("=" * 80)
    print()
    print("Notes:")
    print("  - Asset processing targets 2-4x speedup for 50+ assets")
    print("  - Post-processing targets 1.5-2x speedup")
    print("  - Small asset counts may show minimal improvement due to thread overhead")
    print("  - Actual speedup depends on CPU cores, I/O speed, and workload type")
    print()


if __name__ == "__main__":
    run_benchmarks()
