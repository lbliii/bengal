"""
End-to-end performance benchmarks for full site builds.
Tests realistic site sizes and provides build time breakdown by phase.
"""

import shutil
import tempfile
import time
from pathlib import Path

from bengal.core.site import Site


def create_realistic_site(num_pages: int, num_assets: int, num_tags: int = 10) -> Path:
    """
    Create a temporary test site with realistic content.

    Args:
        num_pages: Number of pages/posts to create
        num_assets: Number of assets (CSS, JS, images)
        num_tags: Number of unique tags to distribute across posts

    Returns:
        Path to temporary site directory
    """
    temp_dir = Path(tempfile.mkdtemp())

    # Create directory structure
    (temp_dir / "content" / "posts").mkdir(parents=True)
    (temp_dir / "content" / "pages").mkdir(parents=True)
    (temp_dir / "assets" / "css").mkdir(parents=True)
    (temp_dir / "assets" / "js").mkdir(parents=True)
    (temp_dir / "assets" / "images").mkdir(parents=True)
    (temp_dir / "public").mkdir()

    # Generate tag pool
    tags = [f"tag{i}" for i in range(num_tags)]

    # Create blog posts (80% of content)
    num_posts = int(num_pages * 0.8)
    for i in range(num_posts):
        # Assign 2-4 random tags per post
        import random

        post_tags = random.sample(tags, min(random.randint(2, 4), len(tags)))

        content = f"""---
title: Blog Post {i}
date: 2025-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}
author: Test Author
tags: {post_tags}
excerpt: This is the excerpt for post {i}
---

# Blog Post {i}

This is a realistic blog post with multiple sections and content.

## Introduction

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod
tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

## Main Content

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore
eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident.

### Subsection 1

Here's a code example:

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Calculate first 10 numbers
for i in range(10):
    print(f"F({i}) = {{fibonacci(i)}}")
```

### Subsection 2

More content with a list:

- Item 1 with **bold text**
- Item 2 with *italic text*
- Item 3 with `inline code`

## Conclusion

Final thoughts and summary of post {i}. This demonstrates realistic
content structure with headings, code blocks, lists, and formatting.

[Read more about this topic](/related-post)
"""
        (temp_dir / "content" / "posts" / f"post-{i}.md").write_text(content)

    # Create static pages (20% of content)
    num_static = num_pages - num_posts
    for i in range(num_static):
        content = f"""---
title: Page {i}
---

# {["About", "Contact", "Services", "Portfolio", "Team"][i % 5]}

This is a static page with content.

## Section

Regular content for static pages.
"""
        (temp_dir / "content" / "pages" / f"page-{i}.md").write_text(content)

    # Create homepage
    (temp_dir / "content" / "index.md").write_text("""---
title: Home
---

# Welcome to the Test Site

This is a realistic homepage with content.
""")

    # Create CSS assets
    css_count = num_assets // 3
    for i in range(css_count):
        content = (
            f"""
/* Stylesheet {i} */
.component-{i} {{
    display: flex;
    flex-direction: column;
    padding: {i}rem;
    margin: {i}rem;
    color: #333;
    background: #fff;
}}

.component-{i}:hover {{
    background: #f5f5f5;
}}

@media (max-width: 768px) {{
    .component-{i} {{
        padding: {i * 0.5}rem;
    }}
}}
"""
            * 5
        )
        (temp_dir / "assets" / "css" / f"component-{i}.css").write_text(content)

    # Create JS assets
    js_count = num_assets // 3
    for i in range(js_count):
        content = (
            f"""
// Module {i}
(function() {{
    'use strict';

    function init{i}() {{
        console.log('Initializing module {i}');

        const elements = document.querySelectorAll('.component-{i}');
        elements.forEach(el => {{
            el.addEventListener('click', function() {{
                console.log('Clicked component {i}');
            }});
        }});
    }}

    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', init{i});
    }} else {{
        init{i}();
    }}
}})();
"""
            * 3
        )
        (temp_dir / "assets" / "js" / f"module-{i}.js").write_text(content)

    # Create image assets (minimal PNGs)
    img_count = num_assets - css_count - js_count
    png_data = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    for i in range(img_count):
        (temp_dir / "assets" / "images" / f"image-{i}.png").write_bytes(png_data)

    # Create config
    (temp_dir / "bengal.toml").write_text("""
title = "Benchmark Site"
baseurl = "https://example.com"

[build]
theme = "default"
parallel = true
minify_assets = false
optimize_assets = false
fingerprint_assets = true
generate_sitemap = true
generate_rss = true

[pagination]
per_page = 10
""")

    return temp_dir


def benchmark_site_build(num_pages: int, num_assets: int, label: str) -> dict:
    """
    Benchmark a full site build and return timing breakdown.

    Args:
        num_pages: Number of pages to generate
        num_assets: Number of assets to generate
        label: Label for this benchmark

    Returns:
        Dictionary with timing information
    """
    print(f"\n{label.upper()} ({num_pages} pages, {num_assets} assets)")
    print("-" * 80)

    site_dir = create_realistic_site(num_pages, num_assets)

    try:
        # Run build 3 times and average
        times = []

        for _run in range(3):
            # Clean output directory
            site = Site.from_config(site_dir)
            if site.output_dir.exists():
                shutil.rmtree(site.output_dir)

            # Measure total build time
            start_total = time.time()

            # Run full build (BuildOrchestrator handles all phases)
            parallel = site.config.get("parallel", True)
            build_stats = site.build(parallel=parallel, incremental=False, verbose=False)

            total_time = time.time() - start_total

            # Extract phase times from build stats
            discovery_time = build_stats.discovery_time_ms / 1000
            taxonomy_time = build_stats.taxonomy_time_ms / 1000
            rendering_time = build_stats.rendering_time_ms / 1000
            assets_time = build_stats.assets_time_ms / 1000
            postprocess_time = build_stats.postprocess_time_ms / 1000

            times.append(
                {
                    "total": total_time,
                    "discovery": discovery_time,
                    "taxonomy": taxonomy_time,
                    "rendering": rendering_time,
                    "assets": assets_time,
                    "postprocess": postprocess_time,
                }
            )

        # Calculate averages
        avg_times = {
            "total": sum(t["total"] for t in times) / len(times),
            "discovery": sum(t["discovery"] for t in times) / len(times),
            "taxonomy": sum(t["taxonomy"] for t in times) / len(times),
            "rendering": sum(t["rendering"] for t in times) / len(times),
            "assets": sum(t["assets"] for t in times) / len(times),
            "postprocess": sum(t["postprocess"] for t in times) / len(times),
        }

        # Print results
        print(f"  Total build time:     {avg_times['total']:.3f}s")
        print("  Breakdown:")
        print(
            f"    Discovery:          {avg_times['discovery']:.3f}s ({avg_times['discovery'] / avg_times['total'] * 100:.1f}%)"
        )
        print(
            f"    Taxonomy:           {avg_times['taxonomy']:.3f}s ({avg_times['taxonomy'] / avg_times['total'] * 100:.1f}%)"
        )
        print(
            f"    Rendering:          {avg_times['rendering']:.3f}s ({avg_times['rendering'] / avg_times['total'] * 100:.1f}%)"
        )
        print(
            f"    Assets:             {avg_times['assets']:.3f}s ({avg_times['assets'] / avg_times['total'] * 100:.1f}%)"
        )
        print(
            f"    Post-processing:    {avg_times['postprocess']:.3f}s ({avg_times['postprocess'] / avg_times['total'] * 100:.1f}%)"
        )

        # Calculate pages per second
        pages_per_second = num_pages / avg_times["total"]
        print(f"  Throughput:           {pages_per_second:.1f} pages/second")

        return avg_times

    finally:
        shutil.rmtree(site_dir)


def run_full_build_benchmarks():
    """Run all full build benchmarks and report results."""
    print("=" * 80)
    print("BENGAL SSG - FULL BUILD BENCHMARKS")
    print("=" * 80)
    print()
    print("Testing realistic site builds with various sizes")
    print()

    results = []

    # Small site
    small_times = benchmark_site_build(10, 15, "Small Site")
    results.append(("Small", 10, 15, small_times))

    # Medium site
    medium_times = benchmark_site_build(100, 75, "Medium Site")
    results.append(("Medium", 100, 75, medium_times))

    # Large site
    large_times = benchmark_site_build(500, 200, "Large Site")
    results.append(("Large", 500, 200, large_times))

    # Very large site (optional - can take a while)
    # very_large_times = benchmark_site_build(1000, 500, "Very Large Site")
    # results.append(('Very Large', 1000, 500, very_large_times))

    # Summary table
    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)
    print()
    print(f"{'Site':<12} {'Pages':<8} {'Assets':<8} {'Build Time':<12} {'Pages/sec':<12}")
    print("-" * 80)

    for label, pages, assets, times in results:
        pages_per_sec = pages / times["total"]
        print(
            f"{label:<12} {pages:<8} {assets:<8} {times['total']:>8.3f}s    {pages_per_sec:>8.1f}"
        )

    print()
    print("Performance Targets:")
    print("  ✅ Small sites (<100 pages):    < 1 second")
    print("  ✅ Medium sites (100-500 pages): 1-5 seconds")
    print("  ✅ Large sites (500-1000 pages): 5-15 seconds")
    print()
    print("Notes:")
    print("  - Times include all phases: discovery, rendering, assets, post-processing")
    print("  - Parallel processing enabled (default)")
    print("  - Asset minification disabled for faster benchmarking")
    print("  - Actual times depend on CPU, disk speed, and content complexity")
    print()


if __name__ == "__main__":
    run_full_build_benchmarks()
