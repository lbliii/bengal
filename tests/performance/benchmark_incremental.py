"""
Performance benchmarks for incremental builds.
Tests to validate the 50-900x speedup claims for incremental builds vs full rebuilds.
"""

import shutil
import tempfile
import time
from pathlib import Path

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions


def create_test_site(num_pages: int, num_assets: int = 20) -> Path:
    """Create a temporary test site with specified number of pages and assets."""
    temp_dir = Path(tempfile.mkdtemp())

    # Create directory structure
    (temp_dir / "content" / "posts").mkdir(parents=True)
    (temp_dir / "assets" / "css").mkdir(parents=True)
    (temp_dir / "assets" / "js").mkdir(parents=True)
    (temp_dir / "public").mkdir()

    # Create pages
    for i in range(num_pages):
        content = f"""---
title: Post {i}
date: 2025-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}
tags: [test, python, benchmark]
---

# Post {i}

This is test post {i} with some content for benchmarking.

## Section 1

Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

## Section 2

Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.

```python
def example():
    return "code block"
```

More content here to make the page realistic.
"""
        (temp_dir / "content" / "posts" / f"post-{i}.md").write_text(content)

    # Create homepage
    (temp_dir / "content" / "index.md").write_text("""---
title: Home
---

# Welcome

This is the homepage.
""")

    # Create assets
    css_count = num_assets // 2
    for i in range(css_count):
        content = f"body {{ color: red{i}; margin: {i}px; }}\n" * 10
        (temp_dir / "assets" / "css" / f"style{i}.css").write_text(content)

    js_count = num_assets - css_count
    for i in range(js_count):
        content = f"console.log('test{i}');\n" * 10
        (temp_dir / "assets" / "js" / f"script{i}.js").write_text(content)

    # Create config
    (temp_dir / "bengal.toml").write_text("""
[build]
title = "Benchmark Site"
theme = "default"
minify_assets = false
optimize_assets = false
fingerprint_assets = false
parallel = true
""")

    return temp_dir


def benchmark_full_build(site_dir: Path) -> float:
    """
    Benchmark a full build (no cache).

    Args:
        site_dir: Site directory

    Returns:
        Time in seconds
    """
    site = Site.from_config(site_dir)

    # Clean output directory
    if site.output_dir.exists():
        shutil.rmtree(site.output_dir)

    start = time.time()
    site.build(BuildOptions(incremental=False))
    elapsed = time.time() - start

    return elapsed


def benchmark_incremental_build(site_dir: Path, change_type: str = "content") -> float:
    """
    Benchmark an incremental build after making a small change.

    Args:
        site_dir: Site directory
        change_type: Type of change ('content', 'template', 'asset')

    Returns:
        Time in seconds
    """
    site = Site.from_config(site_dir)

    # Make a small change based on type
    if change_type == "content":
        # Modify one content file
        post_file = site_dir / "content" / "posts" / "post-0.md"
        content = post_file.read_text()
        modified_content = content.replace("This is test post 0", "This is MODIFIED test post 0")
        post_file.write_text(modified_content)

    elif change_type == "template":
        # Modify a template (this should trigger more rebuilds)
        theme_dir = site_dir / "themes" / "default" / "templates"
        if not theme_dir.exists():
            # Use bundled theme
            import bengal

            bengal_dir = Path(bengal.__file__).parent
            theme_dir = bengal_dir / "themes" / "default" / "templates"

        # We can't modify bundled templates, so create a local theme override
        local_theme_dir = site_dir / "themes" / "default" / "templates"
        local_theme_dir.mkdir(parents=True, exist_ok=True)

        # Copy and modify base template
        template_file = local_theme_dir / "base.html"
        template_file.write_text("""
<!DOCTYPE html>
<html>
<head>
    <title>{{ page.title }}</title>
</head>
<body>
    {% block content %}{% endblock %}
    <!-- Modified comment -->
</body>
</html>
""")

    elif change_type == "asset":
        # Modify one asset file
        asset_file = site_dir / "assets" / "css" / "style0.css"
        if asset_file.exists():
            content = asset_file.read_text()
            asset_file.write_text(content + "\n/* Modified */\n")

    # Small delay to ensure file modification time changes
    time.sleep(0.1)

    start = time.time()
    site.build(BuildOptions(incremental=True))
    elapsed = time.time() - start

    return elapsed


def run_incremental_benchmarks():
    """Run all incremental build benchmarks and report results."""
    print("=" * 80)
    print("BENGAL SSG - INCREMENTAL BUILD BENCHMARKS")
    print("=" * 80)
    print()
    print("Testing claim: 50-900x speedup for incremental builds")
    print()

    site_sizes = [
        (10, 10, "Small"),
        (50, 20, "Medium"),
        (100, 50, "Large"),
    ]

    for num_pages, num_assets, size_label in site_sizes:
        print(f"\n{size_label.upper()} SITE ({num_pages} pages, {num_assets} assets)")
        print("-" * 80)

        site_dir = create_test_site(num_pages, num_assets)

        try:
            # Run full build first (creates cache)
            print("Running full build...")
            full_build_times = []
            for _run in range(3):
                full_time = benchmark_full_build(site_dir)
                full_build_times.append(full_time)

            avg_full = sum(full_build_times) / len(full_build_times)
            print(f"  Full build:        {avg_full:.3f}s")

            # Test incremental build with content change
            print("\nTesting incremental build (single content change)...")
            incremental_times = []
            for run in range(3):
                # Restore original state
                if run > 0:
                    post_file = site_dir / "content" / "posts" / "post-0.md"
                    content = post_file.read_text()
                    if "MODIFIED" in content:
                        content = content.replace("MODIFIED ", "")
                        post_file.write_text(content)
                    time.sleep(0.1)

                inc_time = benchmark_incremental_build(site_dir, change_type="content")
                incremental_times.append(inc_time)

            avg_incremental = sum(incremental_times) / len(incremental_times)
            speedup = avg_full / avg_incremental if avg_incremental > 0 else 0

            print(f"  Incremental build: {avg_incremental:.3f}s")
            print(f"  Speedup:           {speedup:.1f}x")

            if speedup >= 50:
                print(f"  ✅ EXCELLENT: Achieved {speedup:.1f}x speedup (target: 50x+)")
            elif speedup >= 10:
                print(f"  ✅ GOOD: Achieved {speedup:.1f}x speedup (target: 50x+)")
            elif speedup >= 2:
                print(f"  ⚠️  MARGINAL: Only {speedup:.1f}x speedup (target: 50x+)")
            else:
                print(f"  ❌ FAIL: Only {speedup:.1f}x speedup (target: 50x+)")

            # Test asset change
            print("\nTesting incremental build (single asset change)...")
            asset_times = []
            for _run in range(3):
                asset_time = benchmark_incremental_build(site_dir, change_type="asset")
                asset_times.append(asset_time)

            avg_asset = sum(asset_times) / len(asset_times)
            asset_speedup = avg_full / avg_asset if avg_asset > 0 else 0

            print(f"  Incremental build: {avg_asset:.3f}s")
            print(f"  Speedup:           {asset_speedup:.1f}x")

            if asset_speedup >= 50:
                print(f"  ✅ EXCELLENT: Achieved {asset_speedup:.1f}x speedup")
            elif asset_speedup >= 10:
                print(f"  ✅ GOOD: Achieved {asset_speedup:.1f}x speedup")
            else:
                print(f"  ⚠️  MARGINAL: Only {asset_speedup:.1f}x speedup")

        finally:
            shutil.rmtree(site_dir)

    print("\n" + "=" * 80)
    print("BENCHMARK COMPLETE")
    print("=" * 80)
    print()
    print("Summary:")
    print("  - Incremental builds should be 50-900x faster than full builds")
    print("  - Content changes: Only rebuild affected pages")
    print("  - Asset changes: Only reprocess changed assets")
    print("  - Template changes: Rebuild all pages using that template")
    print()
    print("Notes:")
    print("  - Actual speedup depends on site size and change type")
    print("  - Larger sites show better speedup ratios")
    print("  - First build is always slower (no cache)")
    print("  - Cache is stored in output_dir/.bengal-cache.json")
    print()


if __name__ == "__main__":
    run_incremental_benchmarks()
