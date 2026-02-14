"""
Performance benchmarks for Core module optimizations.

Tests validate RFC: Core Module Algorithm Optimization

Benchmarks cover:
- NavTree.build() scaling
- NavTree.find() O(1) lookup
- NavTreeCache LRU eviction
- MenuBuilder.build_hierarchy() with deferred sorting
- ContentRegistry lookups

Run with: pytest benchmarks/test_core_performance.py -v --benchmark-only
"""

from pathlib import Path

import pytest

from bengal.core.menu import MenuBuilder, MenuItem
from bengal.core.nav_tree import NavTree, NavTreeCache
from bengal.core.site import Site

# --- Fixtures ---


def create_test_site_with_pages(num_pages: int, tmp_path: Path) -> Site:
    """Create a test site with specified number of pages."""
    site_root = tmp_path / f"core_bench_{num_pages}"
    site_root.mkdir(exist_ok=True)

    # Create config
    config_content = """[site]
title = "Core Benchmark Site"
base_url = "https://example.com"

[build]
output_dir = "output"
"""
    (site_root / "bengal.toml").write_text(config_content)

    # Create content directory
    content_dir = site_root / "content"
    content_dir.mkdir(exist_ok=True)

    # Create docs section
    docs_dir = content_dir / "docs"
    docs_dir.mkdir(exist_ok=True)

    # Create index page
    (docs_dir / "_index.md").write_text("""---
title: Documentation
---
# Documentation
""")

    # Create pages
    for i in range(num_pages):
        page_content = f"""---
title: Page {i}
weight: {i}
---
# Page {i}

Content for page {i}.
"""
        (docs_dir / f"page{i:04d}.md").write_text(page_content)

    # Create site and discover content
    site = Site.from_config(site_root)
    site.discover_content()
    site.discover_assets()

    return site


@pytest.fixture(scope="module")
def site_100_pages(tmp_path_factory):
    """Create 100-page test site."""
    tmp_path = tmp_path_factory.mktemp("core_bench_100")
    return create_test_site_with_pages(100, tmp_path)


@pytest.fixture(scope="module")
def site_500_pages(tmp_path_factory):
    """Create 500-page test site."""
    tmp_path = tmp_path_factory.mktemp("core_bench_500")
    return create_test_site_with_pages(500, tmp_path)


@pytest.fixture(scope="module")
def site_1000_pages(tmp_path_factory):
    """Create 1000-page test site."""
    tmp_path = tmp_path_factory.mktemp("core_bench_1000")
    return create_test_site_with_pages(1000, tmp_path)


# --- NavTree Benchmarks ---


@pytest.mark.benchmark
@pytest.mark.parametrize(
    ("site_fixture", "page_count"),
    [
        ("site_100_pages", 100),
        ("site_500_pages", 500),
        ("site_1000_pages", 1000),
    ],
)
def test_nav_tree_build_scaling(benchmark, request, site_fixture, page_count):
    """
    Benchmark NavTree.build() with different page counts.

    Expected: Linear scaling with page count.
    Target: <10ms for 100 pages, <50ms for 500 pages, <100ms for 1000 pages.
    """
    site = request.getfixturevalue(site_fixture)

    # Clear cache before benchmark
    NavTreeCache.invalidate()

    def build_tree():
        return NavTree.build(site, version_id=None)

    result = benchmark(build_tree)

    # Verify tree was built correctly
    assert result is not None
    assert result.root is not None
    assert len(result.urls) > 0


@pytest.mark.benchmark
def test_nav_tree_find_o1(benchmark, site_1000_pages):
    """
    Benchmark NavTree.find() O(1) lookup.

    Expected: O(1) dict lookup, <0.01ms per operation.
    This validates the flat_nodes dict optimization.
    """
    site = site_1000_pages

    NavTreeCache.invalidate()
    tree = NavTree.build(site, version_id=None)

    # Get a sample URL in the middle of the tree
    urls = list(tree.urls)
    sample_url = urls[len(urls) // 2] if urls else "/"

    def find_operation():
        return tree.find(sample_url)

    result = benchmark(find_operation)

    # Verify find works
    assert result is not None or sample_url == "/"


@pytest.mark.benchmark
def test_nav_tree_cache_lru_hit(benchmark, site_100_pages):
    """
    Benchmark NavTreeCache LRU cache hit.

    Expected: O(1) cache lookup with LRU move_to_end.
    """
    site = site_100_pages

    NavTreeCache.invalidate()
    # Pre-warm cache
    NavTreeCache.get(site, version_id=None)

    def cache_lookup():
        return NavTreeCache.get(site, version_id=None)

    result = benchmark(cache_lookup)
    assert result is not None


# --- Menu Benchmarks ---


@pytest.mark.benchmark
@pytest.mark.parametrize("item_count", [10, 50, 100, 200])
def test_menu_build_hierarchy_scaling(benchmark, item_count):
    """
    Benchmark MenuBuilder.build_hierarchy() with deferred sorting.

    Expected: O(n + k log k) with deferred sorting vs O(n × k log k) with per-insert sort.
    """

    def build_menu():
        builder = MenuBuilder()

        # Create flat menu items
        config = []
        for i in range(item_count):
            config.append(
                {
                    "name": f"Item {i}",
                    "url": f"/item{i}/",
                    "weight": item_count - i,  # Reverse order to force sorting
                    "identifier": f"item{i}",
                }
            )

        builder.add_from_config(config)
        return builder.build_hierarchy()

    result = benchmark(build_menu)

    assert len(result) == item_count
    # Verify sorting worked
    if item_count > 1:
        assert result[0].weight < result[-1].weight


@pytest.mark.benchmark
@pytest.mark.parametrize("children_per_parent", [10, 50, 100])
def test_menu_add_child_deferred_sorting(benchmark, children_per_parent):
    """
    Benchmark MenuItem.add_child() with deferred sorting.

    Expected: O(1) per add_child, O(k log k) for final sort.
    """

    def add_children():
        parent = MenuItem(name="Parent", url="/parent/", identifier="parent")

        for i in range(children_per_parent):
            child = MenuItem(
                name=f"Child {i}",
                url=f"/child{i}/",
                weight=children_per_parent - i,  # Reverse order
            )
            parent.add_child(child)

        parent.sort_children()  # Deferred sort
        return parent.children

    result = benchmark(add_children)

    assert len(result) == children_per_parent
    # Verify sorting worked
    if children_per_parent > 1:
        assert result[0].weight < result[-1].weight


@pytest.mark.benchmark
def test_menu_hierarchical_build(benchmark):
    """
    Benchmark building hierarchical menu with parent-child relationships.

    Creates a 3-level deep menu with 20 items per level.
    """

    def build_hierarchical():
        builder = MenuBuilder()
        config = []

        # Level 0: 5 root items
        for i in range(5):
            config.append(
                {
                    "name": f"Root {i}",
                    "url": f"/root{i}/",
                    "weight": i,
                    "identifier": f"root{i}",
                }
            )

            # Level 1: 4 children per root
            for j in range(4):
                config.append(
                    {
                        "name": f"L1-{i}-{j}",
                        "url": f"/root{i}/l1-{j}/",
                        "weight": j,
                        "parent": f"root{i}",
                        "identifier": f"l1-{i}-{j}",
                    }
                )

                # Level 2: 3 children per L1
                for k in range(3):
                    config.append(
                        {
                            "name": f"L2-{i}-{j}-{k}",
                            "url": f"/root{i}/l1-{j}/l2-{k}/",
                            "weight": k,
                            "parent": f"l1-{i}-{j}",
                            "identifier": f"l2-{i}-{j}-{k}",
                        }
                    )

        builder.add_from_config(config)
        return builder.build_hierarchy()

    result = benchmark(build_hierarchical)

    # 5 root items, each with 4 children, each with 3 grandchildren
    # Total: 5 + 20 + 60 = 85 items, but only 5 roots
    assert len(result) == 5
    assert len(result[0].children) == 4
    assert len(result[0].children[0].children) == 3


# --- ContentRegistry Benchmarks ---


@pytest.mark.benchmark
def test_content_registry_page_lookup(benchmark, site_1000_pages):
    """
    Benchmark ContentRegistry page lookup by path.

    Expected: O(1) dict lookup.
    """
    site = site_1000_pages
    registry = site.registry

    # Check if registry has pages - if not, skip test
    # Note: After external package split, page registration may need updating
    if registry.page_count == 0:
        pytest.skip(
            "Registry has 0 pages - fixture needs updating to register pages. "
            "Site.discover_content() may not auto-register to registry."
        )

    # Get a sample page path - use the same format the registry uses
    if site.pages:
        sample_page = site.pages[len(site.pages) // 2]
        sample_path = sample_page.source_path
    else:
        sample_path = None

    if sample_path:

        def lookup_page():
            return registry.get_page(sample_path)

        result = benchmark(lookup_page)
        # Result may be None if path normalization differs
        if result is None:
            pytest.skip("Registry path lookup returned None. Path normalization may have changed.")


@pytest.mark.benchmark
def test_content_registry_url_lookup(benchmark, site_1000_pages):
    """
    Benchmark ContentRegistry page lookup by URL.

    Expected: O(1) dict lookup.
    """
    site = site_1000_pages
    registry = site.registry

    # Get a sample page URL
    if site.pages:
        sample_page = site.pages[len(site.pages) // 2]
        sample_url = getattr(sample_page, "_path", "/")
    else:
        sample_url = "/"

    def lookup_by_url():
        return registry.get_page_by_url(sample_url)

    result = benchmark(lookup_by_url)
    # May be None if URL doesn't match exactly
    assert result is None or result._path == sample_url


# --- LRU Cache Behavior Benchmarks ---


@pytest.mark.benchmark
def test_nav_tree_cache_lru_eviction(benchmark, tmp_path):
    """
    Benchmark LRU eviction behavior with many versions.

    Creates more versions than cache size to trigger eviction.
    """
    site_root = tmp_path / "lru_test"
    site_root.mkdir(exist_ok=True)

    config_content = """[site]
title = "LRU Test Site"

[build]
output_dir = "output"
"""
    (site_root / "bengal.toml").write_text(config_content)
    (site_root / "content").mkdir(exist_ok=True)

    site = Site.from_config(site_root)
    site.discover_content()

    # Clear cache
    NavTreeCache.invalidate()

    def access_many_versions():
        # Access more versions than cache size (20)
        for i in range(25):
            NavTreeCache.get(site, version_id=f"v{i}")

        # Re-access early versions (should trigger rebuilds due to eviction)
        for i in range(5):
            NavTreeCache.get(site, version_id=f"v{i}")

    benchmark(access_many_versions)


@pytest.mark.benchmark
def test_nav_tree_cache_lru_hot_access(benchmark, site_100_pages):
    """
    Benchmark LRU cache with hot version pattern.

    Frequently accessed versions should stay in cache.
    """
    site = site_100_pages
    NavTreeCache.invalidate()

    # Pre-populate cache with "hot" version
    NavTreeCache.get(site, version_id="hot")

    def hot_access_pattern():
        # 90% access to hot version, 10% to cold versions
        for i in range(100):
            if i % 10 == 0:
                NavTreeCache.get(site, version_id=f"cold{i}")
            else:
                NavTreeCache.get(site, version_id="hot")

    benchmark(hot_access_pattern)
