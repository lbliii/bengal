"""
Full build performance regression tests.

Validates that stable section references don't degrade build performance.

These tests provide progress feedback when run with pytest -v.
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
    assert site.registry.section_count > 0


def test_incremental_rebuild_performance(test_site_dir):
    """Test that incremental rebuilds remain fast."""
    site = Site.from_config(test_site_dir)
    site.discover_content()

    # Initial build
    initial_page_count = len(site.pages)
    initial_section_count = site.registry.section_count

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
    assert site.registry.section_count == initial_section_count


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


def test_multiple_rebuild_cycles_no_degradation(test_site_dir, test_progress):
    """Test that multiple rebuild cycles don't degrade performance."""
    site = Site.from_config(test_site_dir)

    timings = []
    num_cycles = 5

    with test_progress.phase("Running rebuild cycles", total=num_cycles) as update:
        for i in range(num_cycles):
            start = time.perf_counter()
            site.reset_ephemeral_state()
            site.discover_content()
            elapsed = time.perf_counter() - start
            timings.append(elapsed)
            update(i + 1, f"cycle {i + 1}: {elapsed * 1000:.1f}ms")

    # Average should be reasonable
    avg_ms = (sum(timings) / len(timings)) * 1000
    test_progress.status(f"Average: {avg_ms:.2f}ms")
    assert avg_ms < 500, f"Average rebuild too slow: {avg_ms:.2f}ms"

    # Performance shouldn't degrade significantly over cycles
    first_timing = timings[0]
    last_timing = timings[-1]
    ratio = last_timing / first_timing

    # Last timing should be within 2x of first (allowing for variance)
    assert ratio < 2.0, f"Performance degraded: {ratio:.2f}x slower"


def test_content_registry_overhead_minimal(test_site_dir, test_progress):
    """Test that section registry adds minimal overhead to discovery."""
    site = Site.from_config(test_site_dir)

    # Time multiple rebuilds to get average
    timings = []
    num_runs = 3

    with test_progress.phase("Measuring registry overhead", total=num_runs) as update:
        for i in range(num_runs):
            site.reset_ephemeral_state()
            start = time.perf_counter()
            site.discover_content()  # Includes registry build
            elapsed = time.perf_counter() - start
            timings.append(elapsed)
            update(i + 1, f"run {i + 1}: {elapsed * 1000:.1f}ms")

    avg_ms = (sum(timings) / len(timings)) * 1000
    test_progress.status(f"Average: {avg_ms:.2f}ms")

    # Discovery with registry should be fast (< 200ms average)
    assert avg_ms < 200, f"Discovery too slow: {avg_ms:.2f}ms average"

    # Verify registry is built
    assert site.registry.section_count > 0


def test_large_section_tree_performance(tmp_path, test_progress):
    """Test performance with a large section tree (100 sections)."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    num_sections = 100
    pages_per_section = 10

    # Create 100 sections with 10 pages each
    with test_progress.phase(f"Creating {num_sections} sections", total=num_sections) as update:
        for i in range(num_sections):
            section_dir = content_dir / f"section_{i}"
            section_dir.mkdir()

            (section_dir / "_index.md").write_text(f"""---
title: Section {i}
---

Section content.
""")

            for j in range(pages_per_section):
                (section_dir / f"page_{j}.md").write_text(f"""---
title: Page {j} in Section {i}
---

Content for page {j}.
""")

            if i % 20 == 0:  # Update every 20 sections
                update(i + 1, f"section_{i}")

    # Build site
    site = Site.from_config(tmp_path)

    with test_progress.timed(f"Discovering {num_sections * pages_per_section} pages"):
        start = time.perf_counter()
        site.discover_content()
        elapsed = time.perf_counter() - start

    elapsed_ms = elapsed * 1000
    test_progress.status(f"Discovery: {elapsed_ms:.2f}ms")

    # Should handle 100 sections + 1000 pages efficiently
    assert elapsed_ms < 2000, f"Large site discovery too slow: {elapsed_ms:.2f}ms"

    # Verify discovery worked
    assert site.registry.section_count == num_sections
    assert len(site.pages) >= num_sections * pages_per_section

    # Test lookups are still fast
    with test_progress.timed(f"Testing {num_sections} section lookups"):
        lookup_start = time.perf_counter()
        for i in range(num_sections):
            section = site.get_section_by_path(Path(f"section_{i}"))
            assert section is not None
        lookup_elapsed = time.perf_counter() - lookup_start

    avg_ms = (lookup_elapsed / num_sections) * 1000
    test_progress.status(f"Avg lookup: {avg_ms:.3f}ms")
    assert avg_ms < 1, f"Average lookup too slow: {avg_ms:.3f}ms"
