"""
Integration tests for URL ownership system.

Tests URL ownership enforcement across content, taxonomy, autodoc, redirects,
and special pages in realistic build scenarios.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.core.url_ownership import URLCollisionError


@pytest.fixture
def test_site(tmp_path: Path) -> Site:
    """Create a test site with basic structure."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    site = Site(root_path=tmp_path, config={"output_dir": "public"})
    return site


class TestContentVsTaxonomyCollision:
    """Test content vs taxonomy collision detection."""

    def test_content_can_override_taxonomy(self, test_site: Site, tmp_path: Path):
        """Test that user content (priority 100) can override taxonomy (priority 40)."""
        content_dir = tmp_path / "content"
        tags_dir = content_dir / "tags"
        tags_dir.mkdir()

        # Create user content at /tags/python/
        python_page = tags_dir / "python.md"
        python_page.write_text("---\ntitle: Python\n---\nUser content")

        # Discover content (should claim URL with priority 100)
        test_site.discover_content()

        # Verify URL was claimed
        claim = test_site.url_registry.get_claim("/tags/python/")
        assert claim is not None
        assert claim.owner == "content"
        assert claim.priority == 100

    def test_taxonomy_cannot_override_content(self, test_site: Site, tmp_path: Path):
        """Test that taxonomy cannot override existing user content."""
        content_dir = tmp_path / "content"
        tags_dir = content_dir / "tags"
        tags_dir.mkdir()

        # Create user content at /tags/python/
        python_page = tags_dir / "python.md"
        python_page.write_text("---\ntitle: Python\ntags: [python]\n---\nUser content")

        # Discover content first (claims URL)
        test_site.discover_content()

        # Try to create taxonomy page (should fail or be skipped)
        # Taxonomy orchestrator should respect existing claim
        from bengal.orchestration.taxonomy import TaxonomyOrchestrator

        taxonomy = TaxonomyOrchestrator(test_site)
        taxonomy.collect_and_generate()

        # Verify content still owns the URL
        claim = test_site.url_registry.get_claim("/tags/python/")
        assert claim is not None
        assert claim.owner == "content"
        assert claim.priority == 100


class TestRedirectVsContent:
    """Test redirect vs content priority resolution."""

    def test_redirect_cannot_override_content(self, test_site: Site, tmp_path: Path):
        """Test that redirects (priority 5) cannot override content (priority 100)."""
        content_dir = tmp_path / "content"
        about_page = content_dir / "about.md"
        about_page.write_text("---\ntitle: About\n---\nAbout page")

        # Discover content (claims /about/ with priority 100)
        test_site.discover_content()

        # Try to create redirect (should fail)
        from bengal.postprocess.redirects import RedirectGenerator

        # Create a page with alias that conflicts
        page = test_site.pages[0]
        page.aliases = ["/old-about/"]

        redirect_gen = RedirectGenerator(test_site)

        # Redirect to /about/ should fail because content already owns it
        # (This is a bit contrived - normally redirects go to different URLs)
        # But we can test that redirects respect existing claims
        redirect_gen.generate()

        # Verify content still owns /about/
        claim = test_site.url_registry.get_claim("/about/")
        assert claim is not None
        assert claim.owner == "content"


class TestSpecialPagesOptOut:
    """Test special pages opt-out when user content exists."""

    def test_search_page_respects_user_content(self, test_site: Site, tmp_path: Path):
        """Test that search page generation skips when user content exists."""
        content_dir = tmp_path / "content"
        search_page = content_dir / "search.md"
        search_page.write_text("---\ntitle: Search\n---\nCustom search page")

        # Discover content (claims /search/ with priority 100)
        test_site.discover_content()

        # Try to generate special pages
        from bengal.postprocess.special_pages import SpecialPagesGenerator

        special_gen = SpecialPagesGenerator(test_site)
        special_gen.generate()

        # Verify user content owns /search/
        claim = test_site.url_registry.get_claim("/search/")
        assert claim is not None
        assert claim.owner == "content"
        assert claim.priority == 100

        # Verify special page generator didn't write (would have been rejected)
        # If user content exists, special page shouldn't be generated
        # (This depends on the generator checking registry before writing)

    def test_404_page_can_be_overridden(self, test_site: Site, tmp_path: Path):
        """Test that 404 page can be overridden by user content."""
        content_dir = tmp_path / "content"
        # Create 404.md (if pretty_urls=false, this would output to 404.html)
        # For this test, we'll check that registry allows override
        error_page = content_dir / "404.md"
        error_page.write_text("---\ntitle: 404\n---\nCustom 404")

        test_site.discover_content()

        # Generate special pages
        from bengal.postprocess.special_pages import SpecialPagesGenerator

        special_gen = SpecialPagesGenerator(test_site)
        special_gen.generate()

        # User content should win if it exists
        # (Special pages generator checks registry before writing)


class TestIncrementalBuildSafety:
    """Test incremental build safety with cached claims."""

    def test_cached_claims_prevent_shadowing(self, test_site: Site, tmp_path: Path):
        """Test that cached claims prevent new content from shadowing existing URLs."""
        from bengal.cache.build_cache.core import BuildCache

        # Simulate previous build: taxonomy claimed /tags/python/
        cache = BuildCache()
        cache.url_claims = {
            "/tags/python/": {
                "owner": "taxonomy",
                "source": "__virtual__/tags/python/page_1",
                "priority": 40,
            }
        }

        # Load cached claims into registry
        test_site.url_registry.load_from_dict(cache.url_claims)

        # Now try to create user content at /tags/python/
        content_dir = tmp_path / "content"
        tags_dir = content_dir / "tags"
        tags_dir.mkdir()
        python_page = tags_dir / "python.md"
        python_page.write_text("---\ntitle: Python\ntags: [python]\n---\nUser content")

        # Discover content (should claim with priority 100, overriding cached claim)
        test_site.discover_content()

        # User content should win (higher priority)
        claim = test_site.url_registry.get_claim("/tags/python/")
        assert claim is not None
        assert claim.owner == "content"
        assert claim.priority == 100

    def test_cached_claims_persist_across_builds(self, test_site: Site, tmp_path: Path):
        """Test that claims are saved and loaded correctly."""
        content_dir = tmp_path / "content"
        about_page = content_dir / "about.md"
        about_page.write_text("---\ntitle: About\n---\nAbout page")

        # First build: discover content
        test_site.discover_content()

        # Save claims to cache
        from bengal.cache.build_cache.core import BuildCache

        cache = BuildCache()
        cache.url_claims = test_site.url_registry.to_dict()

        # Simulate second build: load cached claims
        new_site = Site(root_path=tmp_path, config={"output_dir": "public"})
        new_site.url_registry.load_from_dict(cache.url_claims)

        # Verify claim was loaded
        claim = new_site.url_registry.get_claim("/about/")
        assert claim is not None
        assert claim.owner == "content"
        assert claim.priority == 100


class TestPriorityLevels:
    """Test priority-based conflict resolution."""

    def test_priority_hierarchy(self, test_site: Site):
        """Test that priority hierarchy is respected."""
        registry = test_site.url_registry

        # Lower priority first
        registry.claim(
            url="/test/",
            owner="redirect",
            source="alias:/old-test/",
            priority=5,
        )

        # Higher priority should override
        registry.claim(
            url="/test/",
            owner="content",
            source="content/test.md",
            priority=100,
        )

        claim = registry.get_claim("/test/")
        assert claim is not None
        assert claim.owner == "content"
        assert claim.priority == 100

    def test_same_priority_collision_raises_error(self, test_site: Site):
        """Test that same priority collisions raise URLCollisionError."""
        registry = test_site.url_registry

        registry.claim(
            url="/test/",
            owner="content",
            source="content/test1.md",
            priority=100,
        )

        # Same priority, different source should fail
        with pytest.raises(URLCollisionError):
            registry.claim(
                url="/test/",
                owner="content",
                source="content/test2.md",
                priority=100,
            )
