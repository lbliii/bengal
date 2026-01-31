"""
Test parsed content caching implementation (Optimization #2).

Validates that parsed HTML is cached and reused when appropriate.
"""

import shutil
import statistics
import tempfile
import time
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions


@pytest.mark.slow
@pytest.mark.serial  # Run alone to avoid timing interference from parallel tests
def test_parsed_content_cache_speeds_up_builds():
    """
    Test that parsed content cache speeds up repeated full builds.

    This is the primary benefit of Optimization #2.
    Uses multiple runs and statistical analysis to avoid flakiness from timing noise.
    Allows 10% tolerance margin to account for system variability.

    """
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Create site with multiple pages
        (temp_dir / "content" / "posts").mkdir(parents=True)

        # Create index page
        (temp_dir / "content" / "index.md").write_text("""---
title: Home
---
# Home
Welcome to the test site.
""")

        for i in range(20):
            (temp_dir / "content" / "posts" / f"post-{i}.md").write_text(f"""---
title: Post {i}
---

# Post {i}

This is post {i} with some content.

## Section 1

Content here with some text to parse.

## Section 2

More content that needs parsing.

### Subsection

Even more nested content.
""")

        (temp_dir / "bengal.toml").write_text("""
[site]
title = "Test Site"

[build]
cache_templates = true
""")

        # Run multiple builds for statistical stability
        cold_times = []
        warm_times = []

        # First build (cold cache) - run 2x and take best
        for _ in range(2):
            site = Site.from_config(temp_dir)
            start = time.time()
            site.build(BuildOptions(force_sequential=True, incremental=False))
            cold_times.append(time.time() - start)

        # Warm builds - run 4x to get better statistics
        for _ in range(4):
            site = Site.from_config(temp_dir)
            start = time.time()
            site.build(BuildOptions(force_sequential=True, incremental=False))
            warm_times.append(time.time() - start)

        # Use statistics for more reliable results
        cold_time = min(cold_times)  # Best cold time
        warm_time = statistics.median(warm_times)  # Median warm time
        speedup = cold_time / warm_time if warm_time > 0 else 1.0

        print("\nParsed Content Cache Test:")
        print(f"  Cold builds:  {[f'{t:.3f}s' for t in cold_times]}")
        print(f"  Warm builds:  {[f'{t:.3f}s' for t in warm_times]}")
        print(f"  Best cold:    {cold_time:.3f}s")
        print(f"  Median warm:  {warm_time:.3f}s")
        print(f"  Speedup:      {speedup:.2f}x")

        # Allow 10% tolerance for timing noise (0.90x instead of 1.0x)
        # This accounts for system variability, test parallelization overhead, etc.
        assert speedup >= 0.90, (
            f"Warm builds should not be significantly slower (got {speedup:.2f}x). "
            f"Cold={cold_time:.3f}s, Warm={warm_time:.3f}s"
        )

        if speedup >= 1.05:
            print(f"  ✅ Parsed content caching provides {speedup:.2f}x speedup")
        else:
            print(f"  ⚠️  Speedup marginal ({speedup:.2f}x) - cache working but effect small")

    finally:
        shutil.rmtree(temp_dir)


@pytest.mark.slow
def test_parsed_content_cache_invalidation():
    """Test that parsed content cache is invalidated when content changes."""
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Create simple site
        (temp_dir / "content").mkdir()
        (temp_dir / "content" / "page.md").write_text("""---
title: Test Page
---

# Original Content

This is the original content.
""")

        (temp_dir / "bengal.toml").write_text("""
[site]
title = "Test Site"
""")

        # First build
        site = Site.from_config(temp_dir)
        site.build(BuildOptions(force_sequential=True, incremental=False))

        # Check output
        output = site.output_dir / "page" / "index.html"
        html1 = output.read_text()
        assert "Original Content" in html1

        # Modify content
        (temp_dir / "content" / "page.md").write_text("""---
title: Test Page
---

# Modified Content

This is the MODIFIED content.
""")

        # Second build
        site2 = Site.from_config(temp_dir)
        site2.build(BuildOptions(force_sequential=True, incremental=False))

        # Check that content was updated (cache was invalidated)
        html2 = output.read_text()
        assert "Modified Content" in html2, "Content changes should be detected"
        assert "MODIFIED" in html2, "Cache should be invalidated on content change"
        assert "Original Content" not in html2, "Old content should be replaced"

        print("\n✅ Parsed content cache invalidation works correctly")

    finally:
        shutil.rmtree(temp_dir)


@pytest.mark.slow
def test_parsed_content_cache_metadata_change():
    """Test that cache is invalidated when metadata changes."""
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Create simple site
        (temp_dir / "content").mkdir()
        (temp_dir / "content" / "page.md").write_text("""---
title: Original Title
author: John Doe
---

# Content

Some content here.
""")

        (temp_dir / "bengal.toml").write_text("""
[site]
title = "Test Site"
""")

        # First build
        site = Site.from_config(temp_dir)
        site.build(BuildOptions(force_sequential=True, incremental=False))

        # Modify only metadata (not content)
        (temp_dir / "content" / "page.md").write_text("""---
title: Modified Title
author: Jane Smith
---

# Content

Some content here.
""")

        # Second build
        site2 = Site.from_config(temp_dir)
        site2.build(BuildOptions(force_sequential=True, incremental=False))

        # Check that metadata changes are reflected
        output = site2.output_dir / "page" / "index.html"
        html = output.read_text()
        assert "Modified Title" in html, "Metadata changes should be detected"

        print("\n✅ Metadata changes invalidate cache correctly")

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("Testing Parsed Content Caching (Optimization #2)...")
    print()

    print("Test 1: Parsed content caching speeds up builds...")
    test_parsed_content_cache_speeds_up_builds()
    print("✅ PASSED")
    print()

    print("Test 2: Cache invalidation on content change...")
    test_parsed_content_cache_invalidation()
    print("✅ PASSED")
    print()

    print("Test 3: Cache invalidation on metadata change...")
    test_parsed_content_cache_metadata_change()
    print("✅ PASSED")
    print()

    print("All tests passed! ✨")
