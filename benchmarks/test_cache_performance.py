"""
Performance benchmarks for cache algorithm operations.

Tests bottleneck operations:
1. TaxonomyIndex.get_tags_for_page() - O(t×p) linear scan
2. TaxonomyIndex.remove_page_from_all_tags() - O(t×p) linear scan
3. QueryIndex._remove_page_from_key() - O(p) list.remove()
4. FileTrackingMixin.get_affected_pages() - O(n) iteration

Run with:
    pytest benchmarks/test_cache_performance.py -v --benchmark-only
    pytest benchmarks/test_cache_performance.py -v  # Without benchmark plugin

This establishes baseline measurements before optimization.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Synthetic Data Generators
# ---------------------------------------------------------------------------


def generate_taxonomy_data(
    num_pages: int = 1000,
    num_tags: int = 100,
    tags_per_page: int = 5,
) -> tuple[dict[str, list[str]], dict[str, set[str]]]:
    """
    Generate synthetic tag-to-pages and page-to-tags mappings.

    Args:
        num_pages: Total number of pages
        num_tags: Total number of unique tags
        tags_per_page: Average tags per page

    Returns:
        Tuple of (tag_to_pages dict, page_to_tags dict for verification)
    """
    tag_to_pages: dict[str, list[str]] = {f"tag-{i}": [] for i in range(num_tags)}
    page_to_tags: dict[str, set[str]] = {}

    for p in range(num_pages):
        page_path = f"content/blog/post-{p:05d}.md"
        page_to_tags[page_path] = set()

        # Assign tags in round-robin fashion with some variance
        for t in range(tags_per_page):
            tag_idx = (p * tags_per_page + t) % num_tags
            tag_slug = f"tag-{tag_idx}"
            tag_to_pages[tag_slug].append(page_path)
            page_to_tags[page_path].add(tag_slug)

    return tag_to_pages, page_to_tags


def generate_query_index_data(
    num_pages: int = 1000,
    num_keys: int = 50,
) -> dict[str, set[str]]:
    """
    Generate synthetic query index data (key → page_paths).

    Args:
        num_pages: Total number of pages
        num_keys: Number of index keys (e.g., sections, authors)

    Returns:
        Dict mapping index key to set of page paths
    """
    entries: dict[str, set[str]] = {f"section-{i}": set() for i in range(num_keys)}

    for p in range(num_pages):
        page_path = f"content/section-{p % num_keys}/post-{p:05d}.md"
        key = f"section-{p % num_keys}"
        entries[key].add(page_path)

    return entries


def generate_dependency_data(
    num_pages: int = 1000,
    deps_per_page: int = 10,
    num_shared_deps: int = 20,
) -> dict[str, set[str]]:
    """
    Generate synthetic dependency data (source → dependencies).

    Args:
        num_pages: Total number of pages
        deps_per_page: Average dependencies per page
        num_shared_deps: Number of shared dependencies (templates, partials)

    Returns:
        Dict mapping source path to set of dependency paths
    """
    # Shared dependencies (templates, partials)
    shared_deps = [f"templates/layouts/layout-{i}.html" for i in range(num_shared_deps)]

    dependencies: dict[str, set[str]] = {}

    for p in range(num_pages):
        page_path = f"content/blog/post-{p:05d}.md"
        deps = set()

        # Add some shared dependencies
        for i in range(min(deps_per_page // 2, num_shared_deps)):
            deps.add(shared_deps[(p + i) % num_shared_deps])

        # Add some unique dependencies
        for i in range(deps_per_page - len(deps)):
            deps.add(f"content/data/file-{(p * deps_per_page + i) % (num_pages * 2)}.yaml")

        dependencies[page_path] = deps

    return dependencies


# ---------------------------------------------------------------------------
# Fixtures for TaxonomyIndex Benchmarks
# ---------------------------------------------------------------------------


def create_taxonomy_index(tag_to_pages: dict[str, list[str]]) -> Any:
    """Create TaxonomyIndex from tag_to_pages mapping."""
    from bengal.cache.taxonomy_index import TagEntry, TaxonomyIndex

    index = TaxonomyIndex.__new__(TaxonomyIndex)
    index.cache_path = Path("/dev/null")
    index.tags = {}
    index._page_to_tags = {}  # Initialize reverse index

    for tag_slug, page_paths in tag_to_pages.items():
        # Use update_tag to properly maintain reverse index
        index.tags[tag_slug] = TagEntry(
            tag_slug=tag_slug,
            tag_name=tag_slug.replace("-", " ").title(),
            page_paths=page_paths,
            updated_at=datetime.now().isoformat(),
            is_valid=True,
        )
        # Manually build reverse index (since we bypassed update_tag)
        for page in page_paths:
            if page not in index._page_to_tags:
                index._page_to_tags[page] = set()
            index._page_to_tags[page].add(tag_slug)

    return index


@pytest.fixture
def taxonomy_index_100():
    """TaxonomyIndex-like data: 100 pages, 20 tags."""
    tag_to_pages, _ = generate_taxonomy_data(num_pages=100, num_tags=20, tags_per_page=3)
    return create_taxonomy_index(tag_to_pages)


@pytest.fixture
def taxonomy_index_1k():
    """TaxonomyIndex-like data: 1K pages, 100 tags."""
    tag_to_pages, _ = generate_taxonomy_data(num_pages=1000, num_tags=100, tags_per_page=5)
    return create_taxonomy_index(tag_to_pages)


@pytest.fixture
def taxonomy_index_5k():
    """TaxonomyIndex-like data: 5K pages, 300 tags."""
    tag_to_pages, _ = generate_taxonomy_data(num_pages=5000, num_tags=300, tags_per_page=10)
    return create_taxonomy_index(tag_to_pages)


@pytest.fixture
def taxonomy_index_10k():
    """TaxonomyIndex-like data: 10K pages, 500 tags."""
    tag_to_pages, _ = generate_taxonomy_data(num_pages=10000, num_tags=500, tags_per_page=15)
    return create_taxonomy_index(tag_to_pages)


# ---------------------------------------------------------------------------
# Fixtures for QueryIndex Benchmarks
# ---------------------------------------------------------------------------


@dataclass
class MockIndexEntry:
    """Minimal IndexEntry for benchmarking page_paths operations."""

    key: str
    page_paths: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@pytest.fixture
def query_index_entries_1k():
    """QueryIndex entries: 1K pages across 50 keys (~20 pages/key)."""
    entries_data = generate_query_index_data(num_pages=1000, num_keys=50)
    return {key: MockIndexEntry(key=key, page_paths=paths) for key, paths in entries_data.items()}


@pytest.fixture
def query_index_entries_5k():
    """QueryIndex entries: 5K pages across 100 keys (~50 pages/key)."""
    entries_data = generate_query_index_data(num_pages=5000, num_keys=100)
    return {key: MockIndexEntry(key=key, page_paths=paths) for key, paths in entries_data.items()}


@pytest.fixture
def query_index_entries_10k():
    """QueryIndex entries: 10K pages across 100 keys (~100 pages/key)."""
    entries_data = generate_query_index_data(num_pages=10000, num_keys=100)
    return {key: MockIndexEntry(key=key, page_paths=paths) for key, paths in entries_data.items()}


# ---------------------------------------------------------------------------
# Fixtures for FileTrackingMixin Benchmarks
# ---------------------------------------------------------------------------


@pytest.fixture
def file_tracking_deps_1k():
    """Dependency data: 1K pages, 10 deps/page."""
    return generate_dependency_data(num_pages=1000, deps_per_page=10, num_shared_deps=20)


@pytest.fixture
def file_tracking_deps_5k():
    """Dependency data: 5K pages, 15 deps/page."""
    return generate_dependency_data(num_pages=5000, deps_per_page=15, num_shared_deps=50)


@pytest.fixture
def file_tracking_deps_10k():
    """Dependency data: 10K pages, 20 deps/page."""
    return generate_dependency_data(num_pages=10000, deps_per_page=20, num_shared_deps=100)


# ---------------------------------------------------------------------------
# Benchmark: TaxonomyIndex.get_tags_for_page()
# Current complexity: O(t×p) where t=tags, p=pages/tag
# Target complexity: O(1) with reverse index
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
class TestTaxonomyGetTagsForPage:
    """Benchmark get_tags_for_page() - reverse lookup from page to tags."""

    def test_100_pages(self, taxonomy_index_100):
        """Baseline: 100 pages, 20 tags."""
        page_path = Path("content/blog/post-00050.md")

        # Warm up
        taxonomy_index_100.get_tags_for_page(page_path)

        # Measure
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            result = taxonomy_index_100.get_tags_for_page(page_path)
        duration = time.perf_counter() - start

        avg_ms = (duration / iterations) * 1000
        print(f"\n📊 get_tags_for_page (100 pages, 20 tags): {avg_ms:.4f}ms avg")
        assert isinstance(result, set)

    def test_1k_pages(self, taxonomy_index_1k):
        """Baseline: 1K pages, 100 tags."""
        page_path = Path("content/blog/post-00500.md")

        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            result = taxonomy_index_1k.get_tags_for_page(page_path)
        duration = time.perf_counter() - start

        avg_ms = (duration / iterations) * 1000
        print(f"\n📊 get_tags_for_page (1K pages, 100 tags): {avg_ms:.4f}ms avg")
        assert isinstance(result, set)

    def test_5k_pages(self, taxonomy_index_5k):
        """Baseline: 5K pages, 300 tags."""
        page_path = Path("content/blog/post-02500.md")

        iterations = 50
        start = time.perf_counter()
        for _ in range(iterations):
            result = taxonomy_index_5k.get_tags_for_page(page_path)
        duration = time.perf_counter() - start

        avg_ms = (duration / iterations) * 1000
        print(f"\n📊 get_tags_for_page (5K pages, 300 tags): {avg_ms:.4f}ms avg")
        assert isinstance(result, set)

    @pytest.mark.slow
    @pytest.mark.memory_intensive(limit_gb=1.0)
    def test_10k_pages(self, taxonomy_index_10k):
        """Baseline: 10K pages, 500 tags. Expected bottleneck."""
        page_path = Path("content/blog/post-05000.md")

        iterations = 20
        start = time.perf_counter()
        for _ in range(iterations):
            result = taxonomy_index_10k.get_tags_for_page(page_path)
        duration = time.perf_counter() - start

        avg_ms = (duration / iterations) * 1000
        print(f"\n📊 get_tags_for_page (10K pages, 500 tags): {avg_ms:.4f}ms avg")
        print("   ⚠️ Target after optimization: <5ms")
        assert isinstance(result, set)


# ---------------------------------------------------------------------------
# Benchmark: TaxonomyIndex.remove_page_from_all_tags()
# Current complexity: O(t×p)
# Target complexity: O(t') where t' = tags for this specific page
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
class TestTaxonomyRemovePageFromAllTags:
    """Benchmark remove_page_from_all_tags() - remove page from all its tags."""

    def test_1k_pages(self, taxonomy_index_1k):
        """Optimized: 1K pages, 100 tags with reverse index."""
        page_path = Path("content/blog/post-00500.md")

        iterations = 50
        timings = []

        for _i in range(iterations):
            # Create fresh copy for each iteration (since removal modifies state)
            tag_to_pages, _ = generate_taxonomy_data(num_pages=1000, num_tags=100, tags_per_page=5)
            index = create_taxonomy_index(tag_to_pages)

            start = time.perf_counter()
            result = index.remove_page_from_all_tags(page_path)
            timings.append(time.perf_counter() - start)

        avg_ms = (sum(timings) / len(timings)) * 1000
        print(f"\n📊 remove_page_from_all_tags (1K pages, 100 tags): {avg_ms:.4f}ms avg")
        assert isinstance(result, set)

    @pytest.mark.slow
    @pytest.mark.memory_intensive(limit_gb=1.0)
    def test_10k_pages(self):
        """Optimized: 10K pages, 500 tags with reverse index."""
        page_path = Path("content/blog/post-05000.md")
        iterations = 5
        timings = []

        for _ in range(iterations):
            tag_to_pages, _ = generate_taxonomy_data(
                num_pages=10000, num_tags=500, tags_per_page=15
            )
            index = create_taxonomy_index(tag_to_pages)

            start = time.perf_counter()
            result = index.remove_page_from_all_tags(page_path)
            timings.append(time.perf_counter() - start)

        avg_ms = (sum(timings) / len(timings)) * 1000
        print(f"\n📊 remove_page_from_all_tags (10K pages, 500 tags): {avg_ms:.4f}ms avg")
        print("   ✅ Target after optimization: <20ms")
        assert isinstance(result, set)


# ---------------------------------------------------------------------------
# Benchmark: QueryIndex._remove_page_from_key()
# Current complexity: O(p) due to list.remove()
# Target complexity: O(1) with set-based storage
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
class TestQueryIndexRemovePageFromKey:
    """Benchmark _remove_page_from_key() - list.remove() is O(p)."""

    def test_set_discard_1k(self, query_index_entries_1k):
        """Benchmark: set.discard() on 1K pages across 50 keys."""
        # Pick a key with many pages
        key = "section-0"
        entry = query_index_entries_1k[key]
        page_to_remove = next(iter(entry.page_paths))

        iterations = 1000
        timings = []

        for _ in range(iterations):
            # Create fresh set each time
            test_set = entry.page_paths.copy()
            start = time.perf_counter()
            test_set.discard(page_to_remove)
            timings.append(time.perf_counter() - start)

        avg_us = (sum(timings) / len(timings)) * 1_000_000
        print(f"\n📊 set.discard() (1K pages, 50 keys, ~20 pages/key): {avg_us:.2f}μs avg")

    def test_set_discard_10k(self, query_index_entries_10k):
        """Benchmark: set.discard() on 10K pages across 100 keys (~100 pages/key)."""
        key = "section-0"
        entry = query_index_entries_10k[key]
        page_to_remove = next(iter(entry.page_paths))

        iterations = 500
        timings = []

        for _ in range(iterations):
            test_set = entry.page_paths.copy()
            start = time.perf_counter()
            test_set.discard(page_to_remove)
            timings.append(time.perf_counter() - start)

        avg_us = (sum(timings) / len(timings)) * 1_000_000
        print(f"\n📊 set.discard() (10K pages, 100 keys, ~100 pages/key): {avg_us:.2f}μs avg")
        print("   ✅ O(1) set operations achieved")

    def test_set_vs_list_comparison(self, query_index_entries_10k):
        """Compare old list.remove() vs new set.discard() for same data."""
        key = "section-0"
        entry = query_index_entries_10k[key]
        pages_list = list(entry.page_paths)  # Convert to list for comparison
        page_to_remove = pages_list[len(pages_list) // 2]

        iterations = 500

        # Benchmark list.remove() (old approach)
        list_timings = []
        for _ in range(iterations):
            test_list = pages_list.copy()
            start = time.perf_counter()
            if page_to_remove in test_list:
                test_list.remove(page_to_remove)
            list_timings.append(time.perf_counter() - start)

        # Benchmark set.discard() (new approach)
        set_timings = []
        for _ in range(iterations):
            test_set = entry.page_paths.copy()
            start = time.perf_counter()
            test_set.discard(page_to_remove)
            set_timings.append(time.perf_counter() - start)

        list_avg_us = (sum(list_timings) / len(list_timings)) * 1_000_000
        set_avg_us = (sum(set_timings) / len(set_timings)) * 1_000_000
        speedup = list_avg_us / set_avg_us if set_avg_us > 0 else float("inf")

        print("\n📊 list.remove() vs set.discard() (~100 pages/key):")
        print(f"   list.remove() (old): {list_avg_us:.2f}μs")
        print(f"   set.discard() (new): {set_avg_us:.2f}μs")
        print(f"   Speedup: {speedup:.1f}x ✅")


# ---------------------------------------------------------------------------
# Benchmark: FileTrackingMixin.get_affected_pages()
# Current complexity: O(n) iteration over all pages
# Target complexity: O(1) with reverse dependency graph
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
class TestFileTrackingGetAffectedPages:
    """Benchmark get_affected_pages() - find pages depending on changed file."""

    def test_1k_pages(self, file_tracking_deps_1k):
        """Baseline: 1K pages, 10 deps/page, 20 shared deps."""
        dependencies = file_tracking_deps_1k

        # Pick a shared dependency (template) that many pages depend on
        shared_dep = "templates/layouts/layout-0.html"

        # Simulate get_affected_pages: O(n) iteration
        def get_affected_pages_current(changed_file: str) -> set[str]:
            affected = set()
            for source, deps in dependencies.items():
                if changed_file in deps:
                    affected.add(source)
            return affected

        iterations = 500
        start = time.perf_counter()
        for _ in range(iterations):
            result = get_affected_pages_current(shared_dep)
        duration = time.perf_counter() - start

        avg_ms = (duration / iterations) * 1000
        print(f"\n📊 get_affected_pages (1K pages, 10 deps/page): {avg_ms:.4f}ms avg")
        print(f"   Found {len(result)} affected pages")

    @pytest.mark.slow
    @pytest.mark.memory_intensive(limit_gb=1.0)
    def test_10k_pages(self, file_tracking_deps_10k):
        """Baseline: 10K pages, 20 deps/page. Expected bottleneck."""
        dependencies = file_tracking_deps_10k

        shared_dep = "templates/layouts/layout-0.html"

        def get_affected_pages_current(changed_file: str) -> set[str]:
            affected = set()
            for source, deps in dependencies.items():
                if changed_file in deps:
                    affected.add(source)
            return affected

        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            result = get_affected_pages_current(shared_dep)
        duration = time.perf_counter() - start

        avg_ms = (duration / iterations) * 1000
        print(f"\n📊 get_affected_pages (10K pages, 20 deps/page): {avg_ms:.4f}ms avg")
        print(f"   Found {len(result)} affected pages")
        print("   ⚠️ Target after optimization: <5ms")

    def test_reverse_index_comparison(self, file_tracking_deps_10k):
        """Compare O(n) iteration vs O(1) reverse lookup."""
        dependencies = file_tracking_deps_10k

        # Build reverse index (what optimization will do)
        reverse_deps: dict[str, set[str]] = {}
        for source, deps in dependencies.items():
            for dep in deps:
                if dep not in reverse_deps:
                    reverse_deps[dep] = set()
                reverse_deps[dep].add(source)

        shared_dep = "templates/layouts/layout-0.html"

        # Current: O(n) iteration
        def get_affected_current(changed_file: str) -> set[str]:
            affected = set()
            for source, deps in dependencies.items():
                if changed_file in deps:
                    affected.add(source)
            return affected

        # Optimized: O(1) lookup
        def get_affected_optimized(changed_file: str) -> set[str]:
            return reverse_deps.get(changed_file, set()).copy()

        iterations = 100

        # Benchmark current
        start = time.perf_counter()
        for _ in range(iterations):
            result_current = get_affected_current(shared_dep)
        current_duration = time.perf_counter() - start

        # Benchmark optimized
        start = time.perf_counter()
        for _ in range(iterations):
            result_optimized = get_affected_optimized(shared_dep)
        optimized_duration = time.perf_counter() - start

        current_ms = (current_duration / iterations) * 1000
        optimized_ms = (optimized_duration / iterations) * 1000
        speedup = current_ms / optimized_ms if optimized_ms > 0 else float("inf")

        print("\n📊 get_affected_pages O(n) vs O(1) (10K pages):")
        print(f"   Current (O(n)):   {current_ms:.4f}ms")
        print(f"   Optimized (O(1)): {optimized_ms:.4f}ms")
        print(f"   Speedup: {speedup:.1f}x")

        # Verify correctness
        assert result_current == result_optimized, "Results should be identical"


# ---------------------------------------------------------------------------
# Summary Report
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_baseline_summary():
    """Generate summary report of all baselines."""
    print("\n" + "=" * 70)
    print("📊 CACHE ALGORITHM BASELINE SUMMARY")
    print("=" * 70)
    print("""
Operations benchmarked:

1. TaxonomyIndex.get_tags_for_page()
   Current: O(t×p) linear scan of all tags
   Target:  O(1) with reverse index

2. TaxonomyIndex.remove_page_from_all_tags()
   Current: O(t×p) linear scan + list.remove() per tag
   Target:  O(t') where t' = tags for this specific page

3. QueryIndex._remove_page_from_key()
   Current: O(p) list.remove()
   Target:  O(1) set.discard()

4. FileTrackingMixin.get_affected_pages()
   Current: O(n) iteration over all pages
   Target:  O(1) reverse dependency lookup

Run individual benchmark classes for detailed timings:
    pytest benchmarks/test_cache_performance.py::TestTaxonomyGetTagsForPage -v
    pytest benchmarks/test_cache_performance.py::TestTaxonomyRemovePageFromAllTags -v
    pytest benchmarks/test_cache_performance.py::TestQueryIndexRemovePageFromKey -v
    pytest benchmarks/test_cache_performance.py::TestFileTrackingGetAffectedPages -v
""")
    print("=" * 70)
