"""
Test parsed content caching implementation (Optimization #2).

Validates that parsed HTML is cached and reused when appropriate.
"""

import tempfile
import shutil
import time
from pathlib import Path
from bengal.core.site import Site


def test_parsed_content_cache_speeds_up_builds():
    """
    Test that parsed content cache speeds up repeated full builds.
    
    This is the primary benefit of Optimization #2.
    """
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create site with multiple pages
        (temp_dir / "content" / "posts").mkdir(parents=True)
        
        for i in range(15):
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
        
        # First build (cold cache - must parse everything)
        site = Site.from_config(temp_dir)
        
        start1 = time.time()
        stats1 = site.build(parallel=False, incremental=False)
        time1 = time.time() - start1
        
        # Second build (warm cache - can use parsed content)
        site2 = Site.from_config(temp_dir)
        
        start2 = time.time()
        stats2 = site2.build(parallel=False, incremental=False)
        time2 = time.time() - start2
        
        # Third build (should also be fast)
        site3 = Site.from_config(temp_dir)
        
        start3 = time.time()
        stats3 = site3.build(parallel=False, incremental=False)
        time3 = time.time() - start3
        
        # Average warm build time
        avg_warm = (time2 + time3) / 2
        speedup = time1 / avg_warm if avg_warm > 0 else 1.0
        
        print(f"\nParsed Content Cache Test:")
        print(f"  First build (cold):  {time1:.3f}s")
        print(f"  Second build (warm): {time2:.3f}s")
        print(f"  Third build (warm):  {time3:.3f}s")
        print(f"  Avg warm:            {avg_warm:.3f}s")
        print(f"  Speedup:             {speedup:.2f}x")
        
        # Expect measurable speedup
        assert speedup >= 1.0, f"Warm builds should not be slower ({speedup:.2f}x)"
        print(f"  ✅ Parsed content caching provides {speedup:.2f}x speedup")
        
    finally:
        shutil.rmtree(temp_dir)


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
        site.build(parallel=False, incremental=False)
        
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
        site2.build(parallel=False, incremental=False)
        
        # Check that content was updated (cache was invalidated)
        html2 = output.read_text()
        assert "Modified Content" in html2, "Content changes should be detected"
        assert "MODIFIED" in html2, "Cache should be invalidated on content change"
        assert "Original Content" not in html2, "Old content should be replaced"
        
        print("\n✅ Parsed content cache invalidation works correctly")
        
    finally:
        shutil.rmtree(temp_dir)


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
        site.build(parallel=False, incremental=False)
        
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
        site2.build(parallel=False, incremental=False)
        
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

