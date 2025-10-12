#!/usr/bin/env python3
"""
Profile rendering phase to identify bottlenecks.

Usage:
    python tests/performance/profile_rendering.py

This will:
1. Create a test site with 1,024 pages
2. Profile the entire build
3. Output detailed timing statistics
"""

import cProfile
import io
import pstats
import random
import shutil
import tempfile
from pathlib import Path

from bengal.core.site import Site

# Sample content paragraphs
PARAGRAPHS = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
]

TITLES = [
    "Understanding",
    "Exploring",
    "Deep Dive into",
    "Introduction to",
    "Guide to",
    "Advanced",
    "Beginner's Guide to",
    "Mastering",
    "Quick Start with",
    "Tutorial:",
]

NOUNS = [
    "Python Programming",
    "Web Development",
    "Data Science",
    "Machine Learning",
    "API Design",
    "Database Management",
    "Cloud Computing",
    "DevOps",
    "Security",
    "Performance",
    "Testing",
    "Documentation",
    "Architecture",
    "Best Practices",
]


def generate_random_title():
    """Generate a random title."""
    return f"{random.choice(TITLES)} {random.choice(NOUNS)}"


def create_test_site(num_files: int = 1024):
    """Create a temporary test site with the specified number of files."""
    temp_dir = Path(tempfile.mkdtemp(prefix="bengal_profile_"))

    # Create directories
    (temp_dir / "content").mkdir()

    # Create index
    (temp_dir / "content" / "index.md").write_text("""---
title: Home
---

Welcome to the test site.
""")

    # Create content files WITHOUT tags (to isolate site.regular_pages issue)
    for i in range(num_files - 1):
        content = f"""---
title: {generate_random_title()}
---

{random.choice(PARAGRAPHS)}

{random.choice(PARAGRAPHS)}

{random.choice(PARAGRAPHS)}
"""
        (temp_dir / "content" / f"page-{i:05d}.md").write_text(content)

    # Create minimal config
    (temp_dir / "bengal.toml").write_text("""
title = "Profile Test Site"
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


def profile_build(site_path: Path):
    """Profile the build process."""
    print(f"Profiling site at: {site_path}")
    print("=" * 60)

    # Create profiler
    profiler = cProfile.Profile()

    # Profile the build
    profiler.enable()

    # Build the site
    site = Site.from_config(site_path)
    site.build()

    profiler.disable()

    # Print statistics
    print("\n" + "=" * 60)
    print("TOP 30 FUNCTIONS BY CUMULATIVE TIME")
    print("=" * 60)

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.sort_stats("cumulative")
    ps.print_stats(30)
    print(s.getvalue())

    print("\n" + "=" * 60)
    print("TOP 30 FUNCTIONS BY TOTAL TIME")
    print("=" * 60)

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.sort_stats("tottime")
    ps.print_stats(30)
    print(s.getvalue())

    print("\n" + "=" * 60)
    print("FUNCTIONS MATCHING 'regular_pages'")
    print("=" * 60)

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.print_stats("regular_pages")
    print(s.getvalue())

    print("\n" + "=" * 60)
    print("FUNCTIONS MATCHING 'sample'")
    print("=" * 60)

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.print_stats("sample")
    print(s.getvalue())

    # Save full profile for detailed analysis
    profile_path = Path(__file__).parent.parent.parent / "plan" / "profile_stats.prof"
    profiler.dump_stats(str(profile_path))
    print(f"\nFull profile saved to: {profile_path}")
    print("Analyze with: python -m pstats {profile_path}")


def main():
    """Main profiling function."""
    print("Creating test site with 1,024 pages...")
    site_path = create_test_site(1024)

    try:
        profile_build(site_path)
    finally:
        # Cleanup
        print(f"\nCleaning up: {site_path}")
        shutil.rmtree(site_path)

    print("\nProfiling complete!")


if __name__ == "__main__":
    main()
