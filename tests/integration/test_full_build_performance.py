"""
Full build performance regression tests.

Validates that stable section references don't degrade build performance.
"""

import time
from pathlib import Path

import pytest

from bengal.core.site import Site


@pytest.fixture
def test_site_dir(tmp_path):
    """Create a test site with sections and pages."""
    site_dir = tmp_path / "test_site"
    site_dir.mkdir()

    # Create content structure
    content = site_dir / "content"
    content.mkdir()

    # Create blog section
    blog = content / "blog"
    blog.mkdir()
    (blog / "_index.md").write_text("""---
title: Blog
cascade:
  show_sidebar: true
  layout: post
---

Blog section.
""")

    # Create blog posts
    for i in range(5):
        (blog / f"post{i}.md").write_text(f"""---
title: Post {i}
date: 2024-01-{i + 1:02d}
---

Post {i} content.
""")

    # Create docs section
    docs = content / "docs"
    docs.mkdir()
    (docs / "_index.md").write_text("""---
title: Documentation
---

Docs section.
""")

    # Create docs pages
    for i in range(5):
        (docs / f"doc{i}.md").write_text(f"""---
title: Doc {i}
---

Doc {i} content.
""")

    # Create config
    config_content = """[site]
title = "Test Site"
base_url = "http://localhost:8000"
"""
    (site_dir / "bengal.toml").write_text(config_content)

    return site_dir


def test_full_build_baseline_performance(test_site_dir):
    """Test that full build completes in reasonable time with section registry."""
    site = Site.from_config(test_site_dir)

    start = time.perf_counter()
    site.discover_content()
    elapsed = time.perf_counter() - start

    elapsed_ms = elapsed * 1000

    # Baseline: discovery should be fast (< 500ms for small test site)
    assert elapsed_ms < 500, f"Content discovery too slow: {elapsed_ms:.2f}ms"

    # Verify sections are registered
    assert len(site._section_registry) > 0
    assert site._section_registry is not None


def test_incremental_rebuild_performance(test_site_dir):
    """Test that incremental rebuilds remain fast."""
    site = Site.from_config(test_site_dir)
    site.discover_content()

    # Initial build
    initial_page_count = len(site.pages)
    initial_section_count = len(site._section_registry)

    # Simulate incremental rebuild
    start = time.perf_counter()
    site.reset_ephemeral_state()
    site.discover_content()
    elapsed = time.perf_counter() - start

    elapsed_ms = elapsed * 1000

    # Incremental rebuild should be fast
    assert elapsed_ms < 500, f"Incremental rebuild too slow: {elapsed_ms:.2f}ms"

    # Verify state was rebuilt correctly
    assert len(site.pages) == initial_page_count
    assert len(site._section_registry) == initial_section_count


def test_section_lookup_doesnt_slow_page_processing(test_site_dir):
    """Test that page._section lookups don't significantly slow processing."""
    site = Site.from_config(test_site_dir)
    site.discover_content()

    # Time accessing all page._section properties
    start = time.perf_counter()
    for page in site.pages:
        _ = page._section
    elapsed = time.perf_counter() - start

    elapsed_ms = elapsed * 1000
    page_count = len(site.pages)
    avg_ms = elapsed_ms / page_count if page_count > 0 else 0

    # Each section lookup should be fast (< 1ms per page)
    assert avg_ms < 1, f"Average section lookup too slow: {avg_ms:.3f}ms per page"


def test_cascade_application_performance(test_site_dir):
    """Test that cascade application doesn't regress with path-based references."""
    from bengal.orchestration.content import ContentOrchestrator

    site = Site.from_config(test_site_dir)
    orchestrator = ContentOrchestrator(site)

    start = time.perf_counter()
    # discover_content() includes cascade application
    orchestrator.discover_content()
    elapsed = time.perf_counter() - start

    elapsed_ms = elapsed * 1000

    # Full discovery + cascade should be fast
    assert elapsed_ms < 1000, f"Discovery + cascade too slow: {elapsed_ms:.2f}ms"


def test_multiple_rebuild_cycles_no_degradation(test_site_dir):
    """Test that multiple rebuild cycles don't degrade performance."""
    site = Site.from_config(test_site_dir)

    timings = []
    for _i in range(5):
        start = time.perf_counter()
        site.reset_ephemeral_state()
        site.discover_content()
        elapsed = time.perf_counter() - start
        timings.append(elapsed)

    # Average should be reasonable
    avg_ms = (sum(timings) / len(timings)) * 1000
    assert avg_ms < 500, f"Average rebuild too slow: {avg_ms:.2f}ms"

    # Performance shouldn't degrade significantly over cycles
    first_timing = timings[0]
    last_timing = timings[-1]
    ratio = last_timing / first_timing

    # Last timing should be within 2x of first (allowing for variance)
    assert ratio < 2.0, f"Performance degraded: {ratio:.2f}x slower"


def test_section_registry_overhead_minimal(test_site_dir):
    """Test that section registry adds minimal overhead to discovery."""
    site = Site.from_config(test_site_dir)

    # Time multiple rebuilds to get average
    timings = []
    for _i in range(3):
        site.reset_ephemeral_state()
        start = time.perf_counter()
        site.discover_content()  # Includes registry build
        elapsed = time.perf_counter() - start
        timings.append(elapsed)

    avg_ms = (sum(timings) / len(timings)) * 1000

    # Discovery with registry should be fast (< 200ms average)
    assert avg_ms < 200, f"Discovery too slow: {avg_ms:.2f}ms average"

    # Verify registry is built
    assert len(site._section_registry) > 0


def test_large_section_tree_performance(tmp_path):
    """Test performance with a large section tree (100 sections)."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Create 100 sections with 10 pages each
    for i in range(100):
        section_dir = content_dir / f"section_{i}"
        section_dir.mkdir()

        (section_dir / "_index.md").write_text(f"""---
title: Section {i}
---

Section content.
""")

        for j in range(10):
            (section_dir / f"page_{j}.md").write_text(f"""---
title: Page {j} in Section {i}
---

Content for page {j}.
""")

    # Build site
    site = Site.from_config(tmp_path)

    start = time.perf_counter()
    site.discover_content()
    elapsed = time.perf_counter() - start

    elapsed_ms = elapsed * 1000

    # Should handle 100 sections + 1000 pages efficiently
    assert elapsed_ms < 2000, f"Large site discovery too slow: {elapsed_ms:.2f}ms"

    # Verify discovery worked
    assert len(site._section_registry) == 100
    assert len(site.pages) >= 1000  # At least 1000 regular pages

    # Test lookups are still fast
    lookup_start = time.perf_counter()
    for i in range(100):
        section = site.get_section_by_path(Path(f"section_{i}"))
        assert section is not None
    lookup_elapsed = time.perf_counter() - lookup_start

    avg_ms = (lookup_elapsed / 100) * 1000
    assert avg_ms < 1, f"Average lookup too slow: {avg_ms:.3f}ms"
