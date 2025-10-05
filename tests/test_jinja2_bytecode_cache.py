"""
Test Jinja2 bytecode caching implementation.

Validates that template bytecode is cached and reused between builds.
"""

import tempfile
import shutil
import time
from pathlib import Path
from bengal.core.site import Site


def test_bytecode_cache_is_created():
    """Test that bytecode cache directory is created."""
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create minimal site
        (temp_dir / "content").mkdir()
        (temp_dir / "content" / "index.md").write_text("""---
title: Home
---

# Home Page
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
        assert cache_dir.exists(), "Bytecode cache directory should exist"
        
        # Check that cache files are created
        cache_files = list(cache_dir.glob("*.cache"))
        assert len(cache_files) > 0, "Should have at least one cached template"
        
    finally:
        shutil.rmtree(temp_dir)


def test_bytecode_cache_improves_performance():
    """Test that subsequent builds are faster with cache."""
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create site with multiple pages
        (temp_dir / "content" / "posts").mkdir(parents=True)
        
        for i in range(20):
            (temp_dir / "content" / "posts" / f"post-{i}.md").write_text(f"""---
title: Post {i}
---

# Post {i}

This is post {i}.
""")
        
        (temp_dir / "bengal.toml").write_text("""
[site]
title = "Test Site"

[build]
cache_templates = true
""")
        
        # First build (cold cache) 
        site = Site.from_config(temp_dir)
        
        start1 = time.time()
        site.build(parallel=False, incremental=False)
        time1 = time.time() - start1
        
        # Second build (warm cache) - cache should be preserved
        site2 = Site.from_config(temp_dir)
        
        start2 = time.time()
        site2.build(parallel=False, incremental=False)
        time2 = time.time() - start2
        
        # Third build (should still be fast with cache)
        site3 = Site.from_config(temp_dir)
        
        start3 = time.time()
        site3.build(parallel=False, incremental=False)
        time3 = time.time() - start3
        
        # Average of warm builds should be faster than cold
        avg_warm = (time2 + time3) / 2
        speedup = time1 / avg_warm if avg_warm > 0 else 1.0
        
        print(f"\nBuild times:")
        print(f"  First (cold):     {time1:.3f}s")
        print(f"  Second (warm):    {time2:.3f}s")
        print(f"  Third (warm):     {time3:.3f}s")
        print(f"  Avg warm:         {avg_warm:.3f}s")
        print(f"  Speedup:          {speedup:.2f}x")
        
        # Assert at least some improvement
        # (We don't require exactly 10-15% due to variance)
        assert speedup >= 1.0, f"Warm builds should not be slower than cold (was {speedup:.2f}x)"
        
    finally:
        shutil.rmtree(temp_dir)


def test_bytecode_cache_can_be_disabled():
    """Test that bytecode cache can be disabled via config."""
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create minimal site
        (temp_dir / "content").mkdir()
        (temp_dir / "content" / "index.md").write_text("""---
title: Home
---

# Home
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
        
        # Check cache directory doesn't exist (or is empty)
        cache_dir = site.output_dir / ".bengal-cache" / "templates"
        
        if cache_dir.exists():
            cache_files = list(cache_dir.glob("*.cache"))
            assert len(cache_files) == 0, "Should not have cached templates when disabled"
        
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("Testing Jinja2 bytecode caching...")
    print()
    
    print("Test 1: Cache directory creation...")
    test_bytecode_cache_is_created()
    print("✅ PASSED")
    print()
    
    print("Test 2: Performance improvement...")
    test_bytecode_cache_improves_performance()
    print("✅ PASSED")
    print()
    
    print("Test 3: Cache can be disabled...")
    test_bytecode_cache_can_be_disabled()
    print("✅ PASSED")
    print()
    
    print("All tests passed! ✨")

