#!/usr/bin/env python3
"""
SSG Comparison Benchmark - WITH TAGS

This variant includes tags on all pages to test the related_posts() optimization.

Compares Bengal SSG against Hugo, Eleventy, Jekyll, Gatsby, and Next.js.
Uses cold builds (cleared cache) for fair comparison.

Target: Sub-second builds for 1K pages, <10s for 4K pages.
"""

import json
import random
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

# Sample content paragraphs
PARAGRAPHS = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
]

TITLES = [
    "Understanding", "Exploring", "Deep Dive into", "Introduction to", "Guide to",
    "Advanced", "Beginner's Guide to", "Mastering", "Quick Start with", "Tutorial:"
]

NOUNS = [
    "Python Programming", "Web Development", "Data Science", "Machine Learning",
    "API Design", "Database Management", "Cloud Computing", "DevOps", "Security",
    "Performance", "Testing", "Documentation", "Architecture", "Best Practices"
]

# Realistic tag pool (like a real blog would have)
ALL_TAGS = [
    "python", "tutorial", "web-development", "api", "database",
    "performance", "testing", "documentation", "security", "devops",
    "machine-learning", "data-science", "cloud", "architecture", "best-practices",
    "django", "flask", "fastapi", "react", "vue", "javascript", "typescript"
]


def generate_random_title():
    """Generate a random title."""
    return f"{random.choice(TITLES)} {random.choice(NOUNS)}"


def create_bengal_site(temp_dir: Path, num_files: int):
    """Create a Bengal SSG test site WITH TAGS."""
    # Create directories
    (temp_dir / "content").mkdir()

    # Create index
    (temp_dir / "content" / "index.md").write_text("""---
title: Home
tags: ["python", "tutorial"]
---

Welcome to the test site.
""")

    # Create content files WITH TAGS
    # Note: num_files includes index.md, so we create num_files - 1 additional files
    for i in range(num_files - 1):
        # Give each page 2-4 random tags
        num_tags = random.randint(2, 4)
        tags = random.sample(ALL_TAGS, k=num_tags)
        tags_yaml = json.dumps(tags)  # Convert to JSON array format

        content = f"""---
title: {generate_random_title()}
tags: {tags_yaml}
---

{random.choice(PARAGRAPHS)}

{random.choice(PARAGRAPHS)}

{random.choice(PARAGRAPHS)}
"""
        (temp_dir / "content" / f"page-{i:05d}.md").write_text(content)

    # Create minimal config (all optimizations OFF)
    (temp_dir / "bengal.toml").write_text("""
title = "SSG Comparison Benchmark (Tagged)"
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


def benchmark_bengal(num_files: int, iterations: int = 3) -> dict:
    """Benchmark Bengal SSG with TAGS."""
    print(f"\n{'='*60}")
    print(f"BENGAL SSG - {num_files} files WITH TAGS")
    print(f"{'='*60}")

    times = []

    for i in range(iterations):
        # Create fresh temp directory for each iteration (cold build)
        temp_dir = Path(tempfile.mkdtemp(prefix="bengal_bench_tagged_"))

        try:
            # Create site
            create_bengal_site(temp_dir, num_files)

            # Clear cache before build
            cache_dir = temp_dir / "public" / ".bengal-cache"
            if cache_dir.exists():
                shutil.rmtree(cache_dir)

            # Time the build
            start = time.time()
            result = subprocess.run(
                ["python", "-m", "bengal.cli", "build"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            elapsed = time.time() - start

            if result.returncode != 0:
                print(f"  ❌ Build failed: {result.stderr[:200]}")
                return None

            times.append(elapsed)
            print(f"  Iteration {i+1}: {elapsed:.3f}s")

        finally:
            # Cleanup
            shutil.rmtree(temp_dir)

    # Calculate statistics
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    print(f"\n  Average: {avg_time:.3f}s")
    print(f"  Min: {min_time:.3f}s")
    print(f"  Max: {max_time:.3f}s")

    return {
        "ssg": "Bengal (Tagged)",
        "files": num_files,
        "iterations": iterations,
        "avg_time": avg_time,
        "min_time": min_time,
        "max_time": max_time,
        "times": times
    }


def main():
    """Run the tagged benchmark."""
    print("=" * 60)
    print("SSG COMPARISON BENCHMARK - WITH TAGS")
    print("=" * 60)
    print("\nThis variant includes tags on all pages to test:")
    print("  1. Related posts pre-computation")
    print("  2. site.regular_pages caching")
    print("\nExpected: 5-8x speedup over untagged benchmark at 4K+ pages")
    print("\nTest scales: 1, 16, 64, 256, 1K, 4K, 8K, 16K pages")
    print("Cold builds: 3 iterations each, cleared cache")
    print("=" * 60)

    # Test scales (powers of 2 for clean scaling analysis)
    scales = [1, 16, 64, 256, 1024, 4096, 8192, 16384]

    results = []

    for num_files in scales:
        result = benchmark_bengal(num_files, iterations=3)
        if result:
            results.append(result)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY - BENGAL WITH TAGS")
    print("=" * 60)
    print(f"\n{'Files':<10} {'Avg Time':<12} {'Min Time':<12} {'Max Time':<12} {'ms/file':<10}")
    print("-" * 60)

    for r in results:
        ms_per_file = (r['avg_time'] * 1000) / r['files']
        print(f"{r['files']:<10} {r['avg_time']:>10.3f}s  {r['min_time']:>10.3f}s  {r['max_time']:>10.3f}s  {ms_per_file:>8.2f}ms")

    # Save results
    output_file = Path(__file__).parent.parent.parent / "plan" / "benchmark_tagged_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    # Scaling analysis
    if len(results) >= 2:
        print("\n" + "=" * 60)
        print("SCALING ANALYSIS")
        print("=" * 60)

        for i in range(1, len(results)):
            prev = results[i-1]
            curr = results[i]

            file_factor = curr['files'] / prev['files']
            time_factor = curr['avg_time'] / prev['avg_time']
            efficiency = (file_factor / time_factor) * 100

            print(f"{prev['files']} → {curr['files']} files ({file_factor:.1f}x):")
            print(f"  Time: {prev['avg_time']:.3f}s → {curr['avg_time']:.3f}s ({time_factor:.2f}x)")
            print(f"  Efficiency: {efficiency:.1f}% (100% = linear scaling)")
            print()


if __name__ == "__main__":
    main()

