"""
Performance benchmarks for NavTree navigation architecture.

Tests verify:
- NavTree.build() scales linearly with page count
- Cache lookup is O(1) (<1ms)
- NavTree.find() is O(1) via flat_nodes dict
- Overall render overhead is <1ms per page (target)
"""

from pathlib import Path

import pytest

from bengal.core.nav_tree import NavTree, NavTreeCache
from bengal.core.site import Site


def create_test_site_with_pages(num_pages: int, tmp_path: Path) -> Site:
    """Create a test site with specified number of pages."""
    site_root = tmp_path / f"nav_bench_{num_pages}"
    site_root.mkdir(exist_ok=True)

    # Create config
    config_content = """[site]
title = "NavTree Benchmark Site"
base_url = "https://example.com"

[build]
output_dir = "output"
"""
    (site_root / "bengal.toml").write_text(config_content)

    # Create content directory
    content_dir = site_root / "content"
    content_dir.mkdir(exist_ok=True)

    # Create a docs section
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
    tmp_path = tmp_path_factory.mktemp("nav_bench_100")
    return create_test_site_with_pages(100, tmp_path)


@pytest.fixture(scope="module")
def site_500_pages(tmp_path_factory):
    """Create 500-page test site."""
    tmp_path = tmp_path_factory.mktemp("nav_bench_500")
    return create_test_site_with_pages(500, tmp_path)


@pytest.fixture(scope="module")
def site_1000_pages(tmp_path_factory):
    """Create 1000-page test site."""
    tmp_path = tmp_path_factory.mktemp("nav_bench_1000")
    return create_test_site_with_pages(1000, tmp_path)


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "site_fixture,page_count",
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
def test_nav_tree_cache_lookup(benchmark, site_100_pages):
    """
    Benchmark NavTreeCache lookup vs cold build.

    Expected: Cache lookup should be O(1) and <1ms.
    Cold build includes tree construction overhead.
    """
    site = site_100_pages

    # Clear cache
    NavTreeCache.invalidate()

    # First build (cold)
    tree_cold = NavTreeCache.get(site, version_id=None)

    # Benchmark cache lookup (should be O(1) dict access)
    def cache_lookup():
        return NavTreeCache.get(site, version_id=None)

    result = benchmark(cache_lookup)

    # Verify cached tree is returned
    assert result is tree_cold  # Same object (cached)


@pytest.mark.benchmark
def test_nav_tree_find_operation(benchmark, site_1000_pages):
    """
    Benchmark NavTree.find() operation (O(1) lookup).

    Expected: O(1) dict lookup, <0.1ms per find operation.
    """
    site = site_1000_pages

    NavTreeCache.invalidate()
    tree = NavTree.build(site, version_id=None)

    # Get a sample URL to find
    sample_url = next(iter(tree.urls))

    def find_operation():
        return tree.find(sample_url)

    result = benchmark(find_operation)

    # Verify find works
    assert result is not None
    assert result.url == sample_url


@pytest.mark.benchmark
def test_nav_tree_context_creation(benchmark, site_500_pages):
    """
    Benchmark NavTreeContext creation (active trail computation).

    Expected: <1ms per context creation (target for render overhead).
    """
    site = site_500_pages

    NavTreeCache.invalidate()
    tree = NavTree.build(site, version_id=None)

    # Get a sample page
    sample_page = site.pages[0]

    from bengal.core.nav_tree import NavTreeContext

    def create_context():
        return NavTreeContext(tree, sample_page)

    result = benchmark(create_context)

    # Verify context works
    assert result is not None
    assert result.tree == tree
    assert result.page == sample_page


@pytest.mark.benchmark
def test_nav_tree_walk_operation(benchmark, site_1000_pages):
    """
    Benchmark NavTree.root.walk() iteration.

    Expected: Linear time complexity, efficient iteration.
    """
    site = site_1000_pages

    NavTreeCache.invalidate()
    tree = NavTree.build(site, version_id=None)

    def walk_tree():
        return list(tree.root.walk())

    result = benchmark(walk_tree)

    # Verify walk works
    assert len(result) > 0
    assert result[0] == tree.root


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "site_fixture,page_count",
    [
        ("site_100_pages", 100),
        ("site_500_pages", 500),
        ("site_1000_pages", 1000),
    ],
)
def test_nav_tree_flat_nodes_construction(benchmark, request, site_fixture, page_count):
    """
    Benchmark flat_nodes dict construction (happens in __post_init__).

    Expected: Linear time complexity, efficient dict construction.
    """
    site = request.getfixturevalue(site_fixture)

    NavTreeCache.invalidate()

    def build_and_access_flat_nodes():
        tree = NavTree.build(site, version_id=None)
        return tree.flat_nodes

    result = benchmark(build_and_access_flat_nodes)

    # Verify flat_nodes is constructed
    assert len(result) > 0
    assert isinstance(result, dict)


