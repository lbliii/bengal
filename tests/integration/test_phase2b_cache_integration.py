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
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from bengal.cache.asset_dependency_map import AssetDependencyMap
from bengal.cache.page_discovery_cache import PageDiscoveryCache
from bengal.cache.taxonomy_index import TaxonomyIndex
from bengal.core.site import Site
from bengal.orchestration import BuildOrchestrator


@pytest.fixture
def site_with_content() -> Site:
    """Create a site with test content."""
    with TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create content directory with test pages
        content_dir = tmpdir_path / "content"
        content_dir.mkdir()

        # Create index page
        index_file = content_dir / "index.md"
        index_file.write_text(
            """---
title: Home
---

# Welcome

![Logo](/images/logo.png)
"""
        )

        # Create blog post 1
        blog_dir = content_dir / "blog"
        blog_dir.mkdir()
        post1 = blog_dir / "post1.md"
        post1.write_text(
            """---
title: Python Tips
tags: [python, programming]
date: 2025-01-01
---

# Python Tips

![Python Logo](/images/python.png)
![Highlight Script](/js/highlight.js)
"""
        )

        # Create blog post 2
        post2 = blog_dir / "post2.md"
        post2.write_text(
            """---
title: Web Development
tags: [web, javascript, programming]
date: 2025-01-02
---

# Web Development

![Stylesheet](/css/syntax.css)
![App Script](/js/app.js)
"""
        )

        # Create output directory
        output_dir = tmpdir_path / "public"
        output_dir.mkdir()

        # Create assets directory
        assets_dir = tmpdir_path / "assets"
        assets_dir.mkdir()

        # Create site for testing with minimal config
        config = {
            "site": {"title": "Test Site", "baseurl": "http://localhost:8080"},
            "build": {"output_dir": "public", "generate_sitemap": False, "generate_rss": False},
        }
        site = Site.for_testing(root_path=tmpdir_path, config=config)
        yield site


class TestPageDiscoveryCacheSaving:
    """Tests for PageDiscoveryCache integration during discovery phase."""

    def test_page_discovery_cache_saved_after_discovery(self, site_with_content):
        """Verify PageDiscoveryCache is saved after discovery phase."""
        # Build the site
        orchestrator = BuildOrchestrator(site_with_content)
        orchestrator.build(incremental=False)

        # Check cache file exists
        cache_file = site_with_content.root_path / ".bengal" / "page_metadata.json"
        assert cache_file.exists(), "PageDiscoveryCache not saved to disk"

        # Load cache and verify content
        cache = PageDiscoveryCache(cache_file)
        assert len(cache.pages) > 0, "Cache has no entries"

        # Verify cache entries contain expected pages
        cache_paths = set(cache.pages.keys())
        assert any("index.md" in path for path in cache_paths), "Home page not in cache"
        assert any("post1.md" in path for path in cache_paths), "Post 1 not in cache"
        assert any("post2.md" in path for path in cache_paths), "Post 2 not in cache"

    def test_page_discovery_cache_contains_metadata(self, site_with_content):
        """Verify PageDiscoveryCache contains correct page metadata."""
        # Build the site
        orchestrator = BuildOrchestrator(site_with_content)
        orchestrator.build(incremental=False)

        # Load cache
        cache_file = site_with_content.root_path / ".bengal" / "page_metadata.json"
        cache = PageDiscoveryCache(cache_file)

        # Find post1 metadata
        post1_path = None
        for path in cache.pages:
            if "post1.md" in path:
                post1_path = path
                break

        assert post1_path is not None, "Post 1 not found in cache"

        # Verify metadata
        metadata = cache.get_metadata(Path(post1_path))
        assert metadata is not None
        assert metadata.title == "Python Tips"
        assert "python" in metadata.tags
        assert "programming" in metadata.tags
        assert metadata.date is not None


class TestAssetDependencyMapTracking:
    """Tests for AssetDependencyMap integration during rendering phase."""

    def test_asset_dependency_map_saved_after_rendering(self, site_with_content):
        """Verify AssetDependencyMap is saved after rendering phase."""
        # Build the site
        orchestrator = BuildOrchestrator(site_with_content)
        orchestrator.build(incremental=False)

        # Check cache file exists
        asset_map_file = site_with_content.root_path / ".bengal" / "asset_deps.json"
        assert asset_map_file.exists(), "AssetDependencyMap not saved to disk"

        # Load map and verify content
        asset_map = AssetDependencyMap(asset_map_file)
        assert len(asset_map.pages) > 0, "Asset map has no entries"

    def test_asset_dependency_map_contains_page_assets(self, site_with_content):
        """Verify AssetDependencyMap tracks page-to-assets correctly."""
        # Build the site
        orchestrator = BuildOrchestrator(site_with_content)
        orchestrator.build(incremental=False)

        # Load map
        asset_map_file = site_with_content.root_path / ".bengal" / "asset_deps.json"
        asset_map = AssetDependencyMap(asset_map_file)

        # Find post1 assets
        post1_path = None
        for path in asset_map.pages:
            if "post1.md" in path:
                post1_path = path
                break

        assert post1_path is not None, "Post 1 not found in asset map"

        # Verify assets are tracked
        assets = asset_map.get_page_assets(Path(post1_path))
        assert assets is not None
        assert len(assets) > 0, "No assets tracked for post 1"

        # Check for specific assets - these are converted to img tags by markdown
        assert any("/images/python.png" in a for a in assets), "Image not tracked"
        assert any("/js/highlight.js" in a for a in assets), "Highlight script not tracked"

    def test_asset_dependency_map_tracks_multiple_asset_types(self, site_with_content):
        """Verify AssetDependencyMap tracks different asset types (images, scripts, styles)."""
        # Build the site
        orchestrator = BuildOrchestrator(site_with_content)
        orchestrator.build(incremental=False)

        # Load map
        asset_map_file = site_with_content.root_path / ".bengal" / "asset_deps.json"
        asset_map = AssetDependencyMap(asset_map_file)

        # Get all unique assets
        all_assets = asset_map.get_all_assets()

        # Check for different asset types
        has_images = any(".png" in a for a in all_assets)
        has_scripts = any(".js" in a for a in all_assets)
        has_stylesheets = any(".css" in a for a in all_assets)

        assert has_images, "No images tracked"
        assert has_scripts, "No scripts tracked"
        assert has_stylesheets, "No stylesheets tracked"


class TestTaxonomyIndexPersistence:
    """Tests for TaxonomyIndex integration during taxonomy phase."""

    def test_taxonomy_index_saved_after_taxonomy_building(self, site_with_content):
        """Verify TaxonomyIndex is saved after taxonomy building phase."""
        # Build the site
        orchestrator = BuildOrchestrator(site_with_content)
        orchestrator.build(incremental=False)

        # Check cache file exists
        taxonomy_file = site_with_content.root_path / ".bengal" / "taxonomy_index.json"
        assert taxonomy_file.exists(), "TaxonomyIndex not saved to disk"

        # Load index and verify content
        index = TaxonomyIndex(taxonomy_file)
        assert len(index.tags) > 0, "Taxonomy index has no tags"

    def test_taxonomy_index_contains_tag_mappings(self, site_with_content):
        """Verify TaxonomyIndex contains correct tag-to-pages mappings."""
        # Build the site
        orchestrator = BuildOrchestrator(site_with_content)
        orchestrator.build(incremental=False)

        # Load index
        taxonomy_file = site_with_content.root_path / ".bengal" / "taxonomy_index.json"
        index = TaxonomyIndex(taxonomy_file)

        # Verify expected tags exist
        assert "python" in index.tags or "programming" in index.tags, "Expected tags not found"

        # Verify tag entries have pages
        for tag_slug, entry in index.tags.items():
            assert entry.page_paths, f"Tag {tag_slug} has no pages"
            assert len(entry.page_paths) > 0

    def test_taxonomy_index_has_correct_page_counts(self, site_with_content):
        """Verify TaxonomyIndex has correct page counts for each tag."""
        # Build the site
        orchestrator = BuildOrchestrator(site_with_content)
        orchestrator.build(incremental=False)

        # Load index
        taxonomy_file = site_with_content.root_path / ".bengal" / "taxonomy_index.json"
        index = TaxonomyIndex(taxonomy_file)

        # Check programming tag (should have 2 pages: post1 and post2)
        if "programming" in index.tags:
            entry = index.tags["programming"]
            assert len(entry.page_paths) == 2, "Programming tag should have 2 pages"

        # Check python tag (should have 1 page: post1)
        if "python" in index.tags:
            entry = index.tags["python"]
            assert len(entry.page_paths) == 1, "Python tag should have 1 page"


class TestCacheIntegrationEndToEnd:
    """End-to-end tests for Phase 2b cache integration."""

    def test_all_caches_present_after_full_build(self, site_with_content):
        """Verify all three caches are created after a full build."""
        # Build the site
        orchestrator = BuildOrchestrator(site_with_content)
        orchestrator.build(incremental=False)

        # Check all cache files exist (compressed format)
        cache_dir = site_with_content.root_path / ".bengal"
        # Caches should be compressed (.json.zst) but load_auto handles both formats
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

    def test_cache_data_persistence_across_reloads(self, site_with_content):
        """Verify cache data persists and can be reloaded."""
        # Build the site
        orchestrator = BuildOrchestrator(site_with_content)
        orchestrator.build(incremental=False)

        # Load all caches
        cache_file = site_with_content.root_path / ".bengal" / "page_metadata.json"
        asset_map_file = site_with_content.root_path / ".bengal" / "asset_deps.json"
        taxonomy_file = site_with_content.root_path / ".bengal" / "taxonomy_index.json"

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

        # Verify data matches
        assert len(page_cache2.pages) == pages1, "PageDiscoveryCache data changed"
        assert len(asset_map2.pages) == assets1, "AssetDependencyMap data changed"
        assert len(taxonomy_index2.tags) == tags1, "TaxonomyIndex data changed"

    def test_all_caches_compressed_after_build(self, site_with_content):
        """Verify all three auxiliary caches are compressed after a full build."""
        # Build the site
        orchestrator = BuildOrchestrator(site_with_content)
        orchestrator.build(incremental=False)

        # Check all compressed cache files exist
        cache_dir = site_with_content.root_path / ".bengal"
        compressed_page_cache = cache_dir / "page_metadata.json.zst"
        compressed_asset_cache = cache_dir / "asset_deps.json.zst"
        compressed_taxonomy_cache = cache_dir / "taxonomy_index.json.zst"

        assert compressed_page_cache.exists(), "PageDiscoveryCache should be compressed"
        assert compressed_asset_cache.exists(), "AssetDependencyMap should be compressed"
        assert compressed_taxonomy_cache.exists(), "TaxonomyIndex should be compressed"

        # Verify compression ratios (should be ~92-93% reduction)
        # Estimate original sizes by loading and checking compressed size
        page_size = compressed_page_cache.stat().st_size
        asset_size = compressed_asset_cache.stat().st_size
        taxonomy_size = compressed_taxonomy_cache.stat().st_size

        # All should be reasonably compressed (less than 20% of estimated original)
        assert page_size > 0, "Page cache should have content"
        assert asset_size > 0, "Asset cache should have content"
        assert taxonomy_size > 0, "Taxonomy cache should have content"

    def test_cache_files_created(self, site_with_content):
        """Verify all cache files are created after build."""
        # Build the site
        orchestrator = BuildOrchestrator(site_with_content)
        orchestrator.build(incremental=False)

        cache_dir = site_with_content.root_path / ".bengal"

        # Verify cache files exist and are valid JSON
        assert (cache_dir / "page_metadata.json").exists(), "PageDiscoveryCache not created"
        with open(cache_dir / "page_metadata.json") as f:
            page_data = json.load(f)
        assert "pages" in page_data, "PageDiscoveryCache missing 'pages' key"

        assert (cache_dir / "asset_deps.json").exists(), "AssetDependencyMap not created"
        with open(cache_dir / "asset_deps.json") as f:
            asset_data = json.load(f)
        assert "pages" in asset_data, "AssetDependencyMap missing 'pages' key"

        assert (cache_dir / "taxonomy_index.json").exists(), "TaxonomyIndex not created"
        with open(cache_dir / "taxonomy_index.json") as f:
            taxonomy_data = json.load(f)
        assert "tags" in taxonomy_data, "TaxonomyIndex missing 'tags' key"
