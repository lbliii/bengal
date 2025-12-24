"""
Performance benchmarks for section registry lookups.

Tests that path-based section lookups remain fast (< 1ms) even
with large numbers of sections and under various conditions.
"""

import time
from pathlib import Path

import pytest

from bengal.core.section import Section
from bengal.core.site import Site


@pytest.fixture
def site_with_many_sections(tmp_path):
    """Create a site with many sections for performance testing."""
    # Create actual content directory structure
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    site = Site(root_path=tmp_path, config={})

    # Create 1000 sections with real directories
    sections = []
    for i in range(1000):
        section_dir = content_dir / f"section_{i}"
        section_dir.mkdir()

        section = Section(
            name=f"section_{i}",
            path=section_dir,
            metadata={"title": f"Section {i}"},
            pages=[],
            subsections=[],
        )
        sections.append(section)

    site.sections = sections
    return site


def test_registry_build_performance(site_with_many_sections):
    """Test that building registry is fast (< 500ms for 1000 sections)."""
    site = site_with_many_sections

    start = time.perf_counter()
    site.register_sections()
    elapsed = time.perf_counter() - start

    elapsed_ms = elapsed * 1000
    # Note: Path normalization with resolve() is filesystem-bound, so we're lenient
    assert elapsed_ms < 500, f"Registry build too slow: {elapsed_ms:.2f}ms for 1000 sections"

    # Verify registry was built correctly
    assert site.registry.section_count == 1000


def test_single_lookup_performance(site_with_many_sections):
    """Test that single lookup is fast (< 1ms with normalization)."""
    site = site_with_many_sections
    site.register_sections()

    # Get a section path for lookup
    section_path = Path("section_500")

    # Warm up
    _ = site.get_section_by_path(section_path)

    # Time single lookup (includes path normalization overhead)
    start = time.perf_counter()
    section = site.get_section_by_path(section_path)
    elapsed = time.perf_counter() - start

    elapsed_ms = elapsed * 1000
    assert section is not None
    # Path normalization adds overhead, so we test for < 1ms
    assert elapsed_ms < 1, f"Single lookup too slow: {elapsed_ms:.3f}ms"


def test_batch_lookup_performance(site_with_many_sections):
    """Test that 1000 lookups complete in reasonable time."""
    site = site_with_many_sections
    site.register_sections()

    # Time batch lookups
    start = time.perf_counter()
    for i in range(1000):
        _ = site.get_section_by_path(Path(f"section_{i}"))
    elapsed = time.perf_counter() - start

    elapsed_ms = elapsed * 1000
    avg_ms = elapsed_ms / 1000

    # Batch should complete in reasonable time (< 2s for 1000 lookups)
    assert elapsed_ms < 2000, f"Batch lookups too slow: {elapsed_ms:.2f}ms total"
    assert avg_ms < 2, f"Average lookup too slow: {avg_ms:.3f}ms"


def test_registry_memory_bounded(site_with_many_sections):
    """Test that registry memory usage is reasonable (< 50MB for 1000 sections)."""
    import sys

    site = site_with_many_sections
    site.register_sections()

    # Estimate memory usage (rough approximation)
    registry_size = sys.getsizeof(site.registry._sections_by_path)
    for key, value in site.registry._sections_by_path.items():
        registry_size += sys.getsizeof(key)
        registry_size += sys.getsizeof(value)

    size_mb = registry_size / (1024 * 1024)
    # Registry should be small - just storing references
    assert size_mb < 50, f"Registry too large: {size_mb:.2f}MB"


def test_lookup_performance_with_nested_sections(tmp_path):
    """Test lookup performance with deeply nested sections."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    site = Site(root_path=tmp_path, config={})

    # Create nested structure: 3 levels deep, 10 subsections each
    def create_nested(parent_path, depth, max_depth):
        if depth >= max_depth:
            return []

        parent_path.mkdir(exist_ok=True)
        subsections = []
        for i in range(10):
            path = parent_path / f"level{depth}_sub{i}"
            path.mkdir()

            section = Section(
                name=f"level{depth}_sub{i}",
                path=path,
                metadata={},
                pages=[],
                subsections=[],
            )
            subsections.append(section)

            # Recurse
            nested = create_nested(path, depth + 1, max_depth)
            section.subsections = nested

        return subsections

    # Create 3 levels = 1,110 sections (10 + 100 + 1000)
    root_sections = create_nested(content_dir, 0, 3)
    site.sections = root_sections

    start = time.perf_counter()
    site.register_sections()
    elapsed = time.perf_counter() - start

    elapsed_ms = elapsed * 1000
    # Nested sections take longer due to recursive traversal + path operations
    assert elapsed_ms < 500, f"Registry build too slow for nested: {elapsed_ms:.2f}ms"

    # Test lookup
    lookup_path = Path("level0_sub0") / "level1_sub5" / "level2_sub3"
    lookup_start = time.perf_counter()
    section = site.get_section_by_path(lookup_path)
    lookup_elapsed = time.perf_counter() - lookup_start

    assert section is not None
    lookup_ms = lookup_elapsed * 1000
    assert lookup_ms < 1, f"Nested lookup too slow: {lookup_ms:.3f}ms"


def test_path_normalization_performance(tmp_path):
    """Test that path normalization doesn't significantly slow lookups."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    site = Site(root_path=tmp_path, config={})

    # Create 100 sections with real directories
    sections = []
    for i in range(100):
        section_dir = content_dir / f"section_{i}"
        section_dir.mkdir()

        section = Section(
            name=f"section_{i}",
            path=section_dir,
            metadata={},
            pages=[],
            subsections=[],
        )
        sections.append(section)

    site.sections = sections
    site.register_sections()

    # Test various path formats
    test_paths = [
        Path("section_50"),  # Relative Path object
        tmp_path / "content" / "section_50",  # Absolute path
    ]

    for test_path in test_paths:
        start = time.perf_counter()
        section = site.get_section_by_path(test_path)
        elapsed = time.perf_counter() - start

        assert section is not None, f"Failed to find section with path: {test_path}"

        elapsed_ms = elapsed * 1000
        # Path normalization with resolve() is filesystem-bound
        assert elapsed_ms < 10, f"Normalized lookup too slow: {elapsed_ms:.3f}ms for {test_path}"


def test_registry_rebuild_performance(site_with_many_sections):
    """Test that rebuilding registry is fast (for incremental builds)."""
    site = site_with_many_sections

    # Initial build
    site.register_sections()

    # Add 100 more sections with real directories
    content_dir = site.root_path / "content"
    for i in range(1000, 1100):
        section_dir = content_dir / f"section_{i}"
        section_dir.mkdir()

        section = Section(
            name=f"section_{i}",
            path=section_dir,
            metadata={},
            pages=[],
            subsections=[],
        )
        site.sections.append(section)

    # Rebuild
    start = time.perf_counter()
    site.register_sections()
    elapsed = time.perf_counter() - start

    elapsed_ms = elapsed * 1000
    # Rebuild should be reasonably fast
    assert elapsed_ms < 600, f"Registry rebuild too slow: {elapsed_ms:.2f}ms for 1100 sections"
    assert site.registry.section_count == 1100


def test_concurrent_lookup_performance(site_with_many_sections):
    """Test that concurrent lookups don't degrade performance."""
    import concurrent.futures

    site = site_with_many_sections
    site.register_sections()

    def lookup_sections(start_idx, count):
        results = []
        for i in range(start_idx, start_idx + count):
            section = site.get_section_by_path(Path(f"section_{i % 1000}"))
            results.append(section)
        return results

    # Concurrent lookups from 4 threads
    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(lookup_sections, i * 250, 250) for i in range(4)]
        results = [f.result() for f in futures]
    elapsed = time.perf_counter() - start

    # All lookups should succeed
    assert all(all(r is not None for r in result) for result in results)

    elapsed_sec = elapsed
    # With 4 threads doing 250 lookups each (1000 total)
    # Allow up to 5s for concurrent lookups (path operations are slow)
    assert elapsed_sec < 5, f"Concurrent lookups too slow: {elapsed_sec:.2f}s"
