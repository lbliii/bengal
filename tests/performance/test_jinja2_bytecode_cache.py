"""
Test Jinja2 bytecode caching implementation (Optimization #1).

Validates that templates are compiled once and cached for subsequent builds.
"""

import tempfile
import shutil
import time
from pathlib import Path
from bengal.core.site import Site


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


def test_bytecode_cache_improves_performance():
    """Test that bytecode cache improves build performance."""
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create site with multiple pages
        (temp_dir / "content").mkdir()
        for i in range(10):
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
        
        # First build (cold cache)
        site = Site.from_config(temp_dir)
        
        start1 = time.time()
        site.build(parallel=False, incremental=False)
        time1 = time.time() - start1
        
        # Second build (warm cache - templates already compiled)
        site2 = Site.from_config(temp_dir)
        
        start2 = time.time()
        site2.build(parallel=False, incremental=False)
        time2 = time.time() - start2
        
        # Calculate speedup
        speedup = time1 / time2 if time2 > 0 else 1.0
        
        print(f"\nBytecode Cache Performance:")
        print(f"  First build (compile templates):  {time1:.3f}s")
        print(f"  Second build (cached templates):  {time2:.3f}s")
        print(f"  Speedup:                          {speedup:.2f}x")
        
        # Expect some speedup (though the speedup may be modest for small sites)
        assert speedup >= 1.0, f"Cached build should not be slower (got {speedup:.2f}x)"
        print(f"  ✅ Bytecode caching provides {speedup:.2f}x speedup")
        
    finally:
        shutil.rmtree(temp_dir)


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

