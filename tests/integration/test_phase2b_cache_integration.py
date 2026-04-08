"""
Integration tests for Phase 2b cache integration.

Tests the integration of three cache components into the build pipeline:
1. PageDiscoveryCache - Page metadata caching after discovery
2. AssetDependencyMap - Asset tracking during rendering
3. TaxonomyIndex - Tag-to-pages mapping persistence

These tests verify that:
- Caches are populated correctly after their respective build phases
- Cache data is persisted to disk
- Cache data is loaded correctly on subsequent builds
- Incremental builds can leverage cached data

All tests are read-only on a single built site (built once per module).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.cache.asset_dependency_map import AssetDependencyMap
from bengal.cache.page_discovery_cache import PageDiscoveryCache
from bengal.cache.taxonomy_index import TaxonomyIndex
from bengal.core.site import Site
from bengal.orchestration import BuildOrchestrator
from bengal.orchestration.build.options import BuildOptions


@pytest.fixture(scope="module")
def built_site(tmp_path_factory) -> Site:
    """Create and build a site with test content once for all tests."""
    tmpdir_path = tmp_path_factory.mktemp("cache_integration")

    # Create content directory with test pages
    content_dir = tmpdir_path / "content"
    content_dir.mkdir()

    # Create index page
    (content_dir / "index.md").write_text(
        "---\ntitle: Home\n---\n\n# Welcome\n\n![Logo](/images/logo.png)\n"
    )

    # Create blog posts
    blog_dir = content_dir / "blog"
    blog_dir.mkdir()
    (blog_dir / "post1.md").write_text(
        "---\ntitle: Python Tips\ntags: [python, programming]\ndate: 2025-01-01\n---\n\n"
        "# Python Tips\n\n![Python Logo](/images/python.png)\n![Highlight Script](/js/highlight.js)\n"
    )
    (blog_dir / "post2.md").write_text(
        "---\ntitle: Web Development\ntags: [web, javascript, programming]\ndate: 2025-01-02\n---\n\n"
        "# Web Development\n\n![Stylesheet](/css/syntax.css)\n![App Script](/js/app.js)\n"
    )

    # Create output and assets directories
    (tmpdir_path / "public").mkdir()
    (tmpdir_path / "assets").mkdir()

    # Create and build site
    config = {
        "site": {"title": "Test Site", "baseurl": "http://localhost:8080"},
        "build": {"output_dir": "public", "generate_sitemap": False, "generate_rss": False},
    }
    site = Site.for_testing(root_path=tmpdir_path, config=config)
    orchestrator = BuildOrchestrator(site)
    orchestrator.build(BuildOptions(incremental=False, force_sequential=True))

    return site


class TestPageDiscoveryCacheSaving:
    """Tests for PageDiscoveryCache integration during discovery phase."""

    def test_page_discovery_cache_saved_after_discovery(self, built_site):
        """Verify PageDiscoveryCache is saved after discovery phase."""
        cache_dir = built_site.root_path / ".bengal"
        cache_file = cache_dir / "page_metadata.json"
        compressed_file = cache_dir / "page_metadata.json.zst"
        assert compressed_file.exists() or cache_file.exists(), (
            "PageDiscoveryCache not saved to disk"
        )

        cache = PageDiscoveryCache(cache_file)
        assert len(cache.pages) > 0, "Cache has no entries"

        cache_paths = set(cache.pages.keys())
        assert any("index.md" in path for path in cache_paths), "Home page not in cache"
        assert any("post1.md" in path for path in cache_paths), "Post 1 not in cache"
        assert any("post2.md" in path for path in cache_paths), "Post 2 not in cache"

    def test_page_discovery_cache_contains_metadata(self, built_site):
        """Verify PageDiscoveryCache contains correct page metadata."""
        cache_file = built_site.root_path / ".bengal" / "page_metadata.json"
        cache = PageDiscoveryCache(cache_file)

        post1_path = None
        for path in cache.pages:
            if "post1.md" in path:
                post1_path = path
                break

        assert post1_path is not None, "Post 1 not found in cache"

        metadata = cache.get_metadata(Path(post1_path))
        assert metadata is not None
        assert metadata.title == "Python Tips"
        assert "python" in metadata.tags
        assert "programming" in metadata.tags
        assert metadata.date is not None


class TestAssetDependencyMapTracking:
    """Tests for AssetDependencyMap integration during rendering phase."""

    def test_asset_dependency_map_saved_after_rendering(self, built_site):
        """Verify AssetDependencyMap is saved after rendering phase."""
        cache_dir = built_site.root_path / ".bengal"
        asset_map_file = cache_dir / "asset_deps.json"
        compressed_file = cache_dir / "asset_deps.json.zst"
        assert compressed_file.exists() or asset_map_file.exists(), (
            "AssetDependencyMap not saved to disk"
        )

        asset_map = AssetDependencyMap(asset_map_file)
        assert len(asset_map.pages) > 0, "Asset map has no entries"

    def test_asset_dependency_map_contains_page_assets(self, built_site):
        """Verify AssetDependencyMap tracks page-to-assets correctly.

        Note: The asset dependency map tracks template/theme-level assets
        (CSS, JS, favicons) extracted from rendered HTML output, NOT
        content-level image references in markdown. Markdown image references
        are tracked separately by the health check's broken links detector.
        """
        asset_map_file = built_site.root_path / ".bengal" / "asset_deps.json"
        asset_map = AssetDependencyMap(asset_map_file)

        post1_path = None
        for path in asset_map.pages:
            if "post1.md" in path:
                post1_path = path
                break

        assert post1_path is not None, "Post 1 not found in asset map"

        assets = asset_map.get_page_assets(Path(post1_path))
        assert assets is not None
        assert len(assets) > 0, "No assets tracked for post 1"

        assert any("css/style.css" in a for a in assets), "CSS stylesheet not tracked"
        assert any(".js" in a for a in assets), "JavaScript not tracked"

    def test_asset_dependency_map_tracks_multiple_asset_types(self, built_site):
        """Verify AssetDependencyMap tracks different asset types (images, scripts, styles)."""
        asset_map_file = built_site.root_path / ".bengal" / "asset_deps.json"
        asset_map = AssetDependencyMap(asset_map_file)

        all_assets = asset_map.get_all_assets()

        has_images = any(".png" in a for a in all_assets)
        has_scripts = any(".js" in a for a in all_assets)
        has_stylesheets = any(".css" in a for a in all_assets)

        assert has_images, "No images tracked"
        assert has_scripts, "No scripts tracked"
        assert has_stylesheets, "No stylesheets tracked"


class TestTaxonomyIndexPersistence:
    """Tests for TaxonomyIndex integration during taxonomy phase."""

    def test_taxonomy_index_saved_after_taxonomy_building(self, built_site):
        """Verify TaxonomyIndex is saved after taxonomy building phase."""
        cache_dir = built_site.root_path / ".bengal"
        taxonomy_file = cache_dir / "taxonomy_index.json"
        compressed_file = cache_dir / "taxonomy_index.json.zst"
        assert compressed_file.exists() or taxonomy_file.exists(), "TaxonomyIndex not saved to disk"

        index = TaxonomyIndex(taxonomy_file)
        assert len(index.tags) > 0, "Taxonomy index has no tags"

    def test_taxonomy_index_contains_tag_mappings(self, built_site):
        """Verify TaxonomyIndex contains correct tag-to-pages mappings."""
        taxonomy_file = built_site.root_path / ".bengal" / "taxonomy_index.json"
        index = TaxonomyIndex(taxonomy_file)

        assert "python" in index.tags or "programming" in index.tags, "Expected tags not found"

        for tag_slug, entry in index.tags.items():
            assert entry.page_paths, f"Tag {tag_slug} has no pages"
            assert len(entry.page_paths) > 0

    def test_taxonomy_index_has_correct_page_counts(self, built_site):
        """Verify TaxonomyIndex has correct page counts for each tag."""
        taxonomy_file = built_site.root_path / ".bengal" / "taxonomy_index.json"
        index = TaxonomyIndex(taxonomy_file)

        if "programming" in index.tags:
            entry = index.tags["programming"]
            assert len(entry.page_paths) == 2, "Programming tag should have 2 pages"

        if "python" in index.tags:
            entry = index.tags["python"]
            assert len(entry.page_paths) == 1, "Python tag should have 1 page"


class TestCacheIntegrationEndToEnd:
    """End-to-end tests for Phase 2b cache integration."""

    def test_all_caches_present_after_full_build(self, built_site):
        """Verify all three caches are created after a full build."""
        cache_dir = built_site.root_path / ".bengal"
        page_cache = cache_dir / "page_metadata.json.zst"
        asset_cache = cache_dir / "asset_deps.json.zst"
        taxonomy_cache = cache_dir / "taxonomy_index.json.zst"

        assert page_cache.exists() or (cache_dir / "page_metadata.json").exists(), (
            "PageDiscoveryCache missing"
        )
        assert asset_cache.exists() or (cache_dir / "asset_deps.json").exists(), (
            "AssetDependencyMap missing"
        )
        assert taxonomy_cache.exists() or (cache_dir / "taxonomy_index.json").exists(), (
            "TaxonomyIndex missing"
        )

    def test_cache_data_persistence_across_reloads(self, built_site):
        """Verify cache data persists and can be reloaded."""
        cache_file = built_site.root_path / ".bengal" / "page_metadata.json"
        asset_map_file = built_site.root_path / ".bengal" / "asset_deps.json"
        taxonomy_file = built_site.root_path / ".bengal" / "taxonomy_index.json"

        # First load
        page_cache1 = PageDiscoveryCache(cache_file)
        asset_map1 = AssetDependencyMap(asset_map_file)
        taxonomy_index1 = TaxonomyIndex(taxonomy_file)

        pages1 = len(page_cache1.pages)
        assets1 = len(asset_map1.pages)
        tags1 = len(taxonomy_index1.tags)

        # Second load (simulating cache reload)
        page_cache2 = PageDiscoveryCache(cache_file)
        asset_map2 = AssetDependencyMap(asset_map_file)
        taxonomy_index2 = TaxonomyIndex(taxonomy_file)

        assert len(page_cache2.pages) == pages1, "PageDiscoveryCache data changed"
        assert len(asset_map2.pages) == assets1, "AssetDependencyMap data changed"
        assert len(taxonomy_index2.tags) == tags1, "TaxonomyIndex data changed"

    def test_all_caches_compressed_after_build(self, built_site):
        """Verify all three auxiliary caches are compressed after a full build."""
        cache_dir = built_site.root_path / ".bengal"
        compressed_page_cache = cache_dir / "page_metadata.json.zst"
        compressed_asset_cache = cache_dir / "asset_deps.json.zst"
        compressed_taxonomy_cache = cache_dir / "taxonomy_index.json.zst"

        assert compressed_page_cache.exists(), "PageDiscoveryCache should be compressed"
        assert compressed_asset_cache.exists(), "AssetDependencyMap should be compressed"
        assert compressed_taxonomy_cache.exists(), "TaxonomyIndex should be compressed"

        page_size = compressed_page_cache.stat().st_size
        asset_size = compressed_asset_cache.stat().st_size
        taxonomy_size = compressed_taxonomy_cache.stat().st_size

        assert page_size > 0, "Page cache should have content"
        assert asset_size > 0, "Asset cache should have content"
        assert taxonomy_size > 0, "Taxonomy cache should have content"

    def test_cache_files_created(self, built_site):
        """Verify all cache files are created after build."""
        from bengal.cache.compression import load_auto

        cache_dir = built_site.root_path / ".bengal"

        page_cache_path = cache_dir / "page_metadata.json"
        compressed_page = cache_dir / "page_metadata.json.zst"
        assert compressed_page.exists() or page_cache_path.exists(), (
            "PageDiscoveryCache not created"
        )
        page_data = load_auto(page_cache_path)
        assert "pages" in page_data, "PageDiscoveryCache missing 'pages' key"

        asset_cache_path = cache_dir / "asset_deps.json"
        compressed_asset = cache_dir / "asset_deps.json.zst"
        assert compressed_asset.exists() or asset_cache_path.exists(), (
            "AssetDependencyMap not created"
        )
        asset_data = load_auto(asset_cache_path)
        assert "pages" in asset_data, "AssetDependencyMap missing 'pages' key"

        taxonomy_cache_path = cache_dir / "taxonomy_index.json"
        compressed_taxonomy = cache_dir / "taxonomy_index.json.zst"
        assert compressed_taxonomy.exists() or taxonomy_cache_path.exists(), (
            "TaxonomyIndex not created"
        )
        taxonomy_data = load_auto(taxonomy_cache_path)
        assert "tags" in taxonomy_data, "TaxonomyIndex missing 'tags' key"
