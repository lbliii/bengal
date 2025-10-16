"""
Integration tests for Phase 2c.1: Lazy loading with PageProxy.

Tests verify:
- PageProxy creation from cache during discovery
- Mixed Page + PageProxy lists in build pipeline
- Full builds vs incremental builds behavior
- Output consistency between full and lazy builds
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from bengal.cache.page_discovery_cache import PageDiscoveryCache, PageMetadata
from bengal.core.page import Page, PageProxy
from bengal.core.site import Site
from bengal.discovery.content_discovery import ContentDiscovery
from bengal.orchestration import BuildOrchestrator


@pytest.fixture
def temp_site_with_content():
    """Create a temporary site with test content."""
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

# Welcome to the site

<img src="/images/logo.png" />
"""
        )

        # Create blog directory with posts
        blog_dir = content_dir / "blog"
        blog_dir.mkdir()

        post1 = blog_dir / "post1.md"
        post1.write_text(
            """---
title: First Post
tags: [python, web]
date: 2025-01-01
---

# First Post

Content here.
<script src="/js/app.js"></script>
"""
        )

        post2 = blog_dir / "post2.md"
        post2.write_text(
            """---
title: Second Post
tags: [rust, systems]
date: 2025-01-02
---

# Second Post

More content.
"""
        )

        # Create config file
        config_file = tmpdir_path / "bengal.toml"
        config_file.write_text(
            """[site]
title = "Test Site"
baseurl = "http://localhost:8080"

[build]
output_dir = "public"
generate_sitemap = false
generate_rss = false
"""
        )

        # Create site
        site = Site.from_config(tmpdir_path, config_path=config_file)
        yield site, tmpdir_path


class TestLazyLoadingDiscovery:
    """Tests for lazy loading during content discovery."""

    def test_full_discovery_creates_full_pages(self, temp_site_with_content):
        """Verify full discovery creates Page objects."""
        site, tmpdir_path = temp_site_with_content

        discovery = ContentDiscovery(tmpdir_path / "content", site=site)
        sections, pages = discovery.discover(use_cache=False)

        # All should be full Page objects
        assert len(pages) > 0
        assert all(isinstance(p, Page) and not isinstance(p, PageProxy) for p in pages)

    def test_discovery_with_cache_creates_proxies(self, temp_site_with_content):
        """Verify discovery with cache creates PageProxy objects."""
        site, tmpdir_path = temp_site_with_content

        # First discovery - full
        discovery = ContentDiscovery(tmpdir_path / "content", site=site)
        sections, full_pages = discovery.discover(use_cache=False)

        # Build cache from discovered pages
        cache = PageDiscoveryCache(tmpdir_path / ".bengal" / "page_metadata.json")
        for page in full_pages:
            metadata = PageMetadata(
                source_path=str(page.source_path),
                title=page.title,
                date=page.date.isoformat() if page.date else None,
                tags=page.tags,
                section=str(page._section.path) if page._section else None,
                slug=page.slug,
            )
            cache.add_metadata(metadata)
        cache.save_to_disk()

        # Second discovery - with cache
        discovery2 = ContentDiscovery(tmpdir_path / "content", site=site)
        sections2, pages2 = discovery2.discover(use_cache=True, cache=cache)

        # Should have mix of Page and PageProxy
        page_count = sum(1 for p in pages2 if isinstance(p, Page) and not isinstance(p, PageProxy))
        proxy_count = sum(1 for p in pages2 if isinstance(p, PageProxy))

        # We should have proxies (unchanged pages)
        assert proxy_count > 0
        assert len(pages2) == len(full_pages)

    def test_proxy_pages_behave_like_normal_pages(self, temp_site_with_content):
        """Verify PageProxy objects work transparently in place of Page."""
        site, tmpdir_path = temp_site_with_content

        # Full discovery
        discovery = ContentDiscovery(tmpdir_path / "content", site=site)
        sections, full_pages = discovery.discover(use_cache=False)

        # Get one page
        page = full_pages[0]

        # Build cache
        cache = PageDiscoveryCache(tmpdir_path / ".bengal" / "page_metadata.json")
        for p in full_pages:
            metadata = PageMetadata(
                source_path=str(p.source_path),
                title=p.title,
                date=p.date.isoformat() if p.date else None,
                tags=p.tags,
                section=str(p._section.path) if p._section else None,
                slug=p.slug,
            )
            cache.add_metadata(metadata)
        cache.save_to_disk()

        # Second discovery with cache
        discovery2 = ContentDiscovery(tmpdir_path / "content", site=site)
        sections2, pages2 = discovery2.discover(use_cache=True, cache=cache)

        # Find corresponding proxy page
        proxy_page = next((p for p in pages2 if p.source_path == page.source_path), None)
        assert proxy_page is not None
        assert isinstance(proxy_page, PageProxy)

        # Proxy should have same metadata as original
        assert proxy_page.title == page.title
        assert proxy_page.tags == page.tags
        assert proxy_page.slug == page.slug


class TestLazyLoadingIntegration:
    """Integration tests for lazy loading in full build pipeline."""

    def test_full_build_creates_full_pages(self, temp_site_with_content):
        """Verify full build creates only Page objects."""
        site, tmpdir_path = temp_site_with_content

        orchestrator = BuildOrchestrator(site)
        # Simulate discovery with incremental=False (full build)
        orchestrator.content.discover(incremental=False, cache=None)

        # All pages should be full Page objects
        assert len(site.pages) > 0
        assert all(isinstance(p, Page) and not isinstance(p, PageProxy) for p in site.pages)

    def test_incremental_build_uses_cache(self, temp_site_with_content):
        """Verify incremental build uses PageProxy when cache available."""
        site, tmpdir_path = temp_site_with_content

        # First: full build to create cache
        orchestrator = BuildOrchestrator(site)
        orchestrator.content.discover(incremental=False, cache=None)
        full_page_count = len(site.pages)

        # Save discovery cache
        cache = PageDiscoveryCache(tmpdir_path / ".bengal" / "page_metadata.json")
        for page in site.pages:
            metadata = PageMetadata(
                source_path=str(page.source_path),
                title=page.title,
                date=page.date.isoformat() if page.date else None,
                tags=page.tags,
                section=str(page._section.path) if page._section else None,
                slug=page.slug,
            )
            cache.add_metadata(metadata)
        cache.save_to_disk()

        # Second: incremental build with cache
        site2 = Site.from_config(tmpdir_path)
        orchestrator2 = BuildOrchestrator(site2)
        orchestrator2.content.discover(incremental=True, cache=cache)

        # Should have PageProxy objects for unchanged pages
        proxy_count = sum(1 for p in site2.pages if isinstance(p, PageProxy))
        assert proxy_count > 0
        assert len(site2.pages) == full_page_count

    def test_mixed_page_list_works_in_pipeline(self, temp_site_with_content):
        """Verify mixed Page + PageProxy list works throughout pipeline."""
        site, tmpdir_path = temp_site_with_content

        # Full discovery
        discovery = ContentDiscovery(tmpdir_path / "content", site=site)
        sections, pages = discovery.discover(use_cache=False)

        # Create cache
        cache = PageDiscoveryCache(tmpdir_path / ".bengal" / "page_metadata.json")
        for page in pages:
            metadata = PageMetadata(
                source_path=str(page.source_path),
                title=page.title,
                date=page.date.isoformat() if page.date else None,
                tags=page.tags,
                section=str(page._section.path) if page._section else None,
                slug=page.slug,
            )
            cache.add_metadata(metadata)
        cache.save_to_disk()

        # Lazy discovery
        site2 = Site.from_config(tmpdir_path)
        discovery2 = ContentDiscovery(tmpdir_path / "content", site=site2)
        sections2, pages2 = discovery2.discover(use_cache=True, cache=cache)

        # Test that mixed list is hashable and comparable
        page_set = set(pages2)
        assert len(page_set) == len(pages2)

        # Test that pages can be used in dicts
        page_dict = {p: i for i, p in enumerate(pages2)}
        assert len(page_dict) == len(pages2)

        # Test iteration works
        for i, page in enumerate(pages2):
            assert page.source_path.exists()


class TestLazyLoadingPerformance:
    """Performance verification for lazy loading."""

    def test_metadata_access_without_loading(self, temp_site_with_content):
        """Verify accessing metadata doesn't trigger full load."""
        site, tmpdir_path = temp_site_with_content

        # Create cache
        discovery = ContentDiscovery(tmpdir_path / "content", site=site)
        sections, pages = discovery.discover(use_cache=False)

        cache = PageDiscoveryCache(tmpdir_path / ".bengal" / "page_metadata.json")
        for page in pages:
            metadata = PageMetadata(
                source_path=str(page.source_path),
                title=page.title,
                date=page.date.isoformat() if page.date else None,
                tags=page.tags,
                section=str(page._section.path) if page._section else None,
                slug=page.slug,
            )
            cache.add_metadata(metadata)
        cache.save_to_disk()

        # Lazy discovery
        discovery2 = ContentDiscovery(tmpdir_path / "content", site=site)
        sections2, pages2 = discovery2.discover(use_cache=True, cache=cache)

        # Get a proxy page
        proxy = next((p for p in pages2 if isinstance(p, PageProxy)), None)
        assert proxy is not None

        # Access metadata - should not load
        _ = proxy.title
        _ = proxy.tags
        _ = proxy.slug
        _ = proxy.date

        assert not proxy._lazy_loaded

    def test_content_access_triggers_load(self, temp_site_with_content):
        """Verify accessing content triggers lazy load."""
        site, tmpdir_path = temp_site_with_content

        # Create cache
        discovery = ContentDiscovery(tmpdir_path / "content", site=site)
        sections, pages = discovery.discover(use_cache=False)

        cache = PageDiscoveryCache(tmpdir_path / ".bengal" / "page_metadata.json")
        for page in pages:
            metadata = PageMetadata(
                source_path=str(page.source_path),
                title=page.title,
                date=page.date.isoformat() if page.date else None,
                tags=page.tags,
                section=str(page._section.path) if page._section else None,
                slug=page.slug,
            )
            cache.add_metadata(metadata)
        cache.save_to_disk()

        # Lazy discovery
        discovery2 = ContentDiscovery(tmpdir_path / "content", site=site)
        sections2, pages2 = discovery2.discover(use_cache=True, cache=cache)

        # Get a proxy page
        proxy = next((p for p in pages2 if isinstance(p, PageProxy)), None)
        assert proxy is not None
        assert not proxy._lazy_loaded

        # Access content - should load
        content = proxy.content
        assert proxy._lazy_loaded
        assert len(content) > 0
