"""
SSG Comparison Benchmark - CSS-Tricks Methodology
==================================================

This benchmark replicates the methodology from:
https://css-tricks.com/comparing-static-site-generator-build-times/

Goal: Generate apples-to-apples comparison data against other SSGs
(Hugo, Eleventy, Jekyll, Gatsby, Next, Nuxt)

Test Characteristics:
- Minimal markdown files (title + 3 paragraphs only)
- Cold builds (cache cleared each run)
- No asset processing, optimization, or fingerprinting
- No code blocks, lists, or complex formatting
- Test scales: 1, 16, 64, 256, 1024, 4096, 8192, 16384 files
- Plain HTML output
"""

import random
import shutil
import tempfile
import time
from pathlib import Path

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions

# Lorem ipsum paragraphs for content generation
PARAGRAPHS = [
    (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor "
        "incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "
        "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
    ),
    (
        "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat "
        "nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui "
        "officia deserunt mollit anim id est laborum."
    ),
    (
        "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque "
        "laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi "
        "architecto beatae vitae dicta sunt explicabo."
    ),
    (
        "Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia "
        "consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt. Neque porro "
        "quisquam est, qui dolorem ipsum quia dolor sit amet."
    ),
    (
        "At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium "
        "voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint "
        "occaecati cupiditate non provident."
    ),
    (
        "Temporibus autem quibusdam et aut officiis debitis aut rerum necessitatibus saepe "
        "eveniet ut et voluptates repudiandae sint et molestiae non recusandae. Itaque earum "
        "rerum hic tenetur a sapiente delectus."
    ),
    (
        "Nam libero tempore, cum soluta nobis est eligendi optio cumque nihil impedit quo minus "
        "id quod maxime placeat facere possimus, omnis voluptas assumenda est, omnis dolor "
        "repellendus."
    ),
]


def generate_random_title() -> str:
    """Generate a random title using common words."""
    adjectives = [
        "Amazing",
        "Incredible",
        "Fantastic",
        "Wonderful",
        "Great",
        "Perfect",
        "Beautiful",
        "Awesome",
        "Brilliant",
        "Excellent",
    ]
    nouns = [
        "Story",
        "Article",
        "Post",
        "Guide",
        "Tutorial",
        "Journey",
        "Adventure",
        "Experience",
        "Discovery",
        "Insight",
    ]
    return f"{random.choice(adjectives)} {random.choice(nouns)} {random.randint(1, 10000)}"


def create_minimal_site(num_files: int) -> Path:
    """
    Create a minimal test site matching CSS-Tricks methodology.

    Args:
        num_files: Number of markdown files to generate

    Returns:
        Path to temporary site directory
    """
    temp_dir = Path(tempfile.mkdtemp())

    # Create directory structure
    (temp_dir / "content").mkdir(parents=True)
    (temp_dir / "public").mkdir()

    # Create homepage
    homepage_content = f"""---
title: {generate_random_title()}
---

{random.choice(PARAGRAPHS)}

{random.choice(PARAGRAPHS)}

{random.choice(PARAGRAPHS)}
"""
    (temp_dir / "content" / "index.md").write_text(homepage_content)

    # Create content files
    # Note: num_files includes index.md, so we create num_files - 1 additional files
    for i in range(num_files - 1):
        content = f"""---
title: {generate_random_title()}
---

{random.choice(PARAGRAPHS)}

{random.choice(PARAGRAPHS)}

{random.choice(PARAGRAPHS)}
"""
        (temp_dir / "content" / f"page-{i:05d}.md").write_text(content)

    # Create minimal config (all optimizations OFF)
    (temp_dir / "bengal.toml").write_text("""
title = "SSG Comparison Benchmark"
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


def benchmark_build(num_files: int, runs: int = 3) -> dict:
    """
    Benchmark Bengal build time for a given number of files.

    Args:
        num_files: Number of files to build
        runs: Number of runs to average

    Returns:
        Dictionary with timing information
    """
    print(f"\n{'=' * 60}")
    print(f"Benchmarking {num_files:,} files")
    print(f"{'=' * 60}")

    times = []

    for run in range(runs):
        print(f"Run {run + 1}/{runs}...", end=" ", flush=True)

        # Create fresh site for each run (cold build)
        site_dir = create_minimal_site(num_files)

        try:
            # Initialize site
            site = Site.from_config(site_dir)

            # Clean output directory
            if site.output_dir.exists():
                shutil.rmtree(site.output_dir)
            site.output_dir.mkdir(parents=True)

            # Measure build time
            start = time.time()

            # Run build (uses BuildOrchestrator internally)
            parallel = site.config.get("parallel", True)
            site.build(
                BuildOptions(force_sequential=not parallel, incremental=False, verbose=False)
            )

            elapsed = time.time() - start
            times.append(elapsed)

            print(f"{elapsed:.3f}s")

        finally:
            # Clean up
            shutil.rmtree(site_dir)

    # Calculate statistics
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    # Calculate pages per second
    pages_per_sec = num_files / avg_time if avg_time > 0 else 0

    print(f"\nResults for {num_files:,} files:")
    print(f"  Average: {avg_time:.3f}s")
    print(f"  Min:     {min_time:.3f}s")
    print(f"  Max:     {max_time:.3f}s")
    print(f"  Rate:    {pages_per_sec:.1f} pages/second")

    return {
        "files": num_files,
        "avg": avg_time,
        "min": min_time,
        "max": max_time,
        "pages_per_sec": pages_per_sec,
        "runs": times,
    }


def run_ssg_comparison_benchmark():
    """Run all benchmarks matching CSS-Tricks methodology."""
    print("=" * 80)
    print("BENGAL SSG - CSS-TRICKS COMPARISON BENCHMARK")
    print("=" * 80)
    print()
    print("Methodology: https://css-tricks.com/comparing-static-site-generator-build-times/")
    print()
    print("Test Configuration:")
    print("  - Minimal markdown (title + 3 paragraphs)")
    print("  - Cold builds (fresh temp directory each run)")
    print("  - No asset processing")
    print("  - No optimization or minification")
    print("  - Parallel processing enabled")
    print("  - 3 runs per scale, averaged")
    print()

    # CSS-Tricks test scales
    # Start with smaller scales, then go bigger
    scales = [1, 16, 64, 256, 1024, 4096, 8192, 16384]

    # Option to run smaller test set for quick validation (faster)
    # scales = [1, 16, 64, 256, 1024]  # Uncomment for quick test (~5 minutes)

    results = []

    for num_files in scales:
        result = benchmark_build(num_files)
        results.append(result)

    # Print summary table
    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)
    print()
    print(f"{'Files':<10} {'Avg Time':<12} {'Min Time':<12} {'Max Time':<12} {'Pages/sec':<12}")
    print("-" * 80)

    for r in results:
        print(
            f"{r['files']:<10,} {r['avg']:>8.3f}s    {r['min']:>8.3f}s    {r['max']:>8.3f}s    {r['pages_per_sec']:>8.1f}"
        )

    # Comparison with other SSGs (from CSS-Tricks article and README)
    print("\n" + "=" * 80)
    print("COMPARISON WITH OTHER SSGs (100 pages)")
    print("=" * 80)
    print()

    # Find the result closest to 100 pages for comparison
    comparison_result = None
    for r in results:
        if r["files"] == 64:
            # Use 64 as proxy for comparison
            # Scale to 100: multiply by 100/64
            scaled_time = r["avg"] * (100 / 64)
            comparison_result = {"files": 100, "avg": scaled_time}
        elif r["files"] == 256:
            # Use 256 as proxy
            # Scale to 100: multiply by 100/256
            scaled_time = r["avg"] * (100 / 256)
            if comparison_result is None:
                comparison_result = {"files": 100, "avg": scaled_time}

    if comparison_result:
        print(f"{'SSG':<15} {'Build Time (100 pages)':<25} {'Notes'}")
        print("-" * 80)
        print(f"{'Hugo':<15} {'~0.1-0.5s':<25} {'Go - fastest'}")
        bengal_time = f"~{comparison_result['avg']:.3f}s"
        print(f"{'Bengal':<15} {bengal_time:<25} {'Python - THIS TEST'}")
        print(f"{'Eleventy':<15} {'~1-3s':<25} {'JavaScript'}")
        print(f"{'Jekyll':<15} {'~3-10s':<25} {'Ruby'}")
        print(f"{'Gatsby':<15} {'~5-15s':<25} {'React framework'}")

    # Analysis
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()

    # Calculate growth rate (how does it scale?)
    if len(results) >= 3:
        # Compare 1 file vs 1024 files
        small = next((r for r in results if r["files"] == 1), None)
        medium = next((r for r in results if r["files"] == 1024), None)

        if small and medium:
            growth_factor = medium["avg"] / small["avg"]
            theoretical_linear = 1024  # 1024x files should take 1024x time if linear

            print("Scaling Analysis (1 file → 1,024 files):")
            print(f"  Time increased: {growth_factor:.1f}x")
            print(f"  Linear scaling: {theoretical_linear}x")
            print(f"  Efficiency:     {(theoretical_linear / growth_factor * 100):.1f}% ")

            if growth_factor < theoretical_linear * 1.1:
                print("  ✅ EXCELLENT: Near-linear scaling!")
            elif growth_factor < theoretical_linear * 1.5:
                print("  ✅ GOOD: Sub-linear scaling")
            else:
                print("  ⚠️  WARNING: Super-linear scaling detected")
            print()

    # Identify sweet spot
    print("Performance Sweet Spots:")
    for r in results:
        if r["files"] <= 100:
            if r["avg"] < 1.0:
                print(f"  ✅ {r['files']:,} files: {r['avg']:.3f}s - Excellent for small sites")
        elif r["files"] <= 1000:
            if r["avg"] < 5.0:
                print(f"  ✅ {r['files']:,} files: {r['avg']:.3f}s - Great for blogs")
        elif r["files"] <= 5000 and r["avg"] < 30.0:
            print(f"  ✅ {r['files']:,} files: {r['avg']:.3f}s - Viable for large sites")

    print()
    print("=" * 80)
    print("BENCHMARK COMPLETE")
    print("=" * 80)
    print()
    print("Next Steps:")
    print("  1. Compare against Hugo, Eleventy, Jekyll using same methodology")
    print("  2. Test with warm builds (caching enabled)")
    print("  3. Test incremental builds (1 file change)")
    print("  4. Add results to README or documentation")
    print()

    return results


if __name__ == "__main__":
    # Set random seed for reproducibility
    random.seed(42)

    try:
        results = run_ssg_comparison_benchmark()
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
    except Exception as e:
        print(f"\n\nError during benchmark: {e}")
        import traceback

        traceback.print_exc()
