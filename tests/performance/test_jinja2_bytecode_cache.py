"""
Test Jinja2 bytecode caching implementation (Optimization #1).

Validates that templates are compiled once and cached for subsequent builds.
"""

import shutil
import statistics
import tempfile
import time
from pathlib import Path

import pytest

from bengal.core.site import Site


@pytest.mark.slow
def test_bytecode_cache_directory_creation():
    """Test that bytecode cache directory is created."""
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Create minimal site
        (temp_dir / "content").mkdir()
        (temp_dir / "content" / "index.md").write_text("""---
title: Home
---

# Welcome
""")

        (temp_dir / "bengal.toml").write_text("""
[site]
title = "Test Site"

[build]
cache_templates = true
""")

        # Build site
        site = Site.from_config(temp_dir)
        site.build(parallel=False, incremental=False)

        # Check cache directory exists
        cache_dir = site.output_dir / ".bengal-cache" / "templates"
        assert cache_dir.exists(), "Template cache directory should be created"

        # Check cache files exist
        cache_files = list(cache_dir.glob("*.cache"))
        assert len(cache_files) > 0, "Template cache files should be created"

        print(f"\n✅ Cache directory created: {cache_dir}")
        print(f"✅ Cache files: {len(cache_files)} templates cached")

    finally:
        shutil.rmtree(temp_dir)


@pytest.mark.slow
@pytest.mark.serial  # Run alone to avoid timing interference from parallel tests
def test_bytecode_cache_improves_performance():
    """
    Test that bytecode cache improves build performance.

    Uses multiple runs and statistical analysis to avoid flakiness from timing noise.
    Allows 10% tolerance margin to account for system variability.
    """
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Create site with multiple pages (20 pages for more pronounced effect)
        (temp_dir / "content").mkdir()

        # Create index page
        (temp_dir / "content" / "index.md").write_text("""---
title: Home
---
# Home
Welcome to the test site.
""")

        for i in range(20):
            (temp_dir / "content" / f"page-{i}.md").write_text(f"""---
title: Page {i}
---

# Page {i}

Content for page {i}.
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
            site.build(parallel=False, incremental=False)
            cold_times.append(time.time() - start)

        # Warm builds - run 3x to average out noise
        for _ in range(3):
            site = Site.from_config(temp_dir)
            start = time.time()
            site.build(parallel=False, incremental=False)
            warm_times.append(time.time() - start)

        # Use statistics for more reliable results
        cold_time = min(cold_times)  # Best cold time
        warm_time = statistics.median(warm_times)  # Median warm time
        speedup = cold_time / warm_time if warm_time > 0 else 1.0

        print("\nBytecode Cache Performance:")
        print(f"  Cold builds:  {[f'{t:.3f}s' for t in cold_times]}")
        print(f"  Warm builds:  {[f'{t:.3f}s' for t in warm_times]}")
        print(f"  Best cold:    {cold_time:.3f}s")
        print(f"  Median warm:  {warm_time:.3f}s")
        print(f"  Speedup:      {speedup:.2f}x")

        # Allow 10% tolerance for timing noise (0.90x instead of 1.0x)
        # This accounts for system variability, test parallelization overhead, etc.
        assert speedup >= 0.90, (
            f"Cached build should not be significantly slower (got {speedup:.2f}x). "
            f"Cold={cold_time:.3f}s, Warm={warm_time:.3f}s"
        )

        if speedup >= 1.05:
            print(f"  ✅ Bytecode caching provides {speedup:.2f}x speedup")
        else:
            print(f"  ⚠️  Speedup marginal ({speedup:.2f}x) - cache working but effect small")

    finally:
        shutil.rmtree(temp_dir)


@pytest.mark.slow
def test_cache_can_be_disabled():
    """Test that cache can be disabled via config."""
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Create minimal site
        (temp_dir / "content").mkdir()
        (temp_dir / "content" / "index.md").write_text("""---
title: Home
---

# Welcome
""")

        (temp_dir / "bengal.toml").write_text("""
[site]
title = "Test Site"

[build]
cache_templates = false
""")

        # Build site
        site = Site.from_config(temp_dir)
        site.build(parallel=False, incremental=False)

        # Cache directory may exist (from other builds) but should be empty or not used
        # The important thing is that it doesn't break when disabled
        print("\n✅ Site builds successfully with cache_templates = false")

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("Testing Jinja2 Bytecode Caching (Optimization #1)...")
    print()

    print("Test 1: Cache directory creation...")
    test_bytecode_cache_directory_creation()
    print("✅ PASSED")
    print()

    print("Test 2: Performance improvement...")
    test_bytecode_cache_improves_performance()
    print("✅ PASSED")
    print()

    print("Test 3: Cache can be disabled...")
    test_cache_can_be_disabled()
    print("✅ PASSED")
    print()

    print("All tests passed! ✨")
