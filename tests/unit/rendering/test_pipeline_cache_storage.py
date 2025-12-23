"""
Tests for rendering pipeline cache storage integration.

Verifies that the rendering pipeline correctly stores parsed content
and rendered output in the cache via dependency_tracker.cache.

These tests ensure the fix for the ._cache vs .cache bug doesn't regress.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bengal.cache import BuildCache, DependencyTracker
from bengal.rendering.pipeline import RenderingPipeline


class DummyParser:
    """Minimal parser for testing cache storage."""

    def __init__(self):
        self.enabled = {}

    def enable_cross_references(self, *args, **kwargs):
        self.enabled["xref"] = True

    def parse(self, content, metadata):
        return f"<p>{content}</p>"

    def parse_with_toc(self, content, metadata):
        return f"<p>{content}</p>", "<nav>TOC</nav>"

    def parse_with_toc_and_context(self, content, metadata, context):
        return f"<p>{content}</p>", "<nav>TOC</nav>"

    def parse_with_context(self, content, metadata, context):
        return f"<p>{content}</p>"


class DummyTemplateEngine:
    """Minimal template engine for testing."""

    def __init__(self, site):
        self.site = site
        self.env = SimpleNamespace(
            get_template=lambda name: MagicMock(render=lambda **kw: "<html></html>")
        )
        self._dependency_tracker = None


@pytest.fixture
def site_with_cache(tmp_path):
    """Create a site with a real BuildCache and DependencyTracker."""
    cache = BuildCache()
    site = SimpleNamespace(
        config={"markdown_engine": "mistune"},
        root_path=tmp_path,
        output_dir=tmp_path / "public",
        theme="default",
        xref_index={},
    )
    site.output_dir.mkdir(parents=True, exist_ok=True)
    tracker = DependencyTracker(cache, site)
    return site, cache, tracker


@pytest.fixture
def mock_page(tmp_path):
    """Create a mock page for testing."""
    source_path = tmp_path / "content" / "test.md"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("# Test\n\nHello world")

    page = SimpleNamespace(
        source_path=source_path,
        output_path=None,
        content="Hello world",
        title="Test Page",
        metadata={"title": "Test Page", "type": "doc"},
        tags=[],
        toc="",
        parsed_ast=None,
        rendered_html=None,
        _prerendered_html=None,
        _virtual=False,
        is_virtual=False,
        _toc_items_cache=[],
        links=[],
    )
    return page


class TestPipelineCacheStorage:
    """Test that the rendering pipeline correctly stores content in cache."""

    def test_cache_parsed_content_uses_correct_attribute(
        self, site_with_cache, mock_page, tmp_path
    ):
        """
        Verify _cache_parsed_content accesses dependency_tracker.cache (not ._cache).

        This test ensures the fix for the ._cache vs .cache bug.
        """
        site, cache, tracker = site_with_cache

        parser = DummyParser()
        engine = DummyTemplateEngine(site)
        ctx = SimpleNamespace(markdown_parser=parser, template_engine=engine)

        pipeline = RenderingPipeline(site, dependency_tracker=tracker, build_context=ctx)

        # Manually call _cache_parsed_content
        mock_page.parsed_ast = "<p>Test content</p>"
        mock_page.toc = "<nav>TOC</nav>"
        mock_page.links = []

        # Before caching, parsed_content should be empty
        assert str(mock_page.source_path) not in cache.parsed_content

        # Call the method
        pipeline._cache_parsed_content(mock_page, "default.html", "mistune-3.0-toc1")

        # After caching, parsed_content should have an entry
        assert str(mock_page.source_path) in cache.parsed_content
        assert cache.parsed_content[str(mock_page.source_path)]["html"] == "<p>Test content</p>"

    def test_cache_rendered_output_uses_correct_attribute(
        self, site_with_cache, mock_page, tmp_path
    ):
        """
        Verify _cache_rendered_output accesses dependency_tracker.cache (not ._cache).

        This test ensures the fix for the ._cache vs .cache bug.
        """
        site, cache, tracker = site_with_cache

        parser = DummyParser()
        engine = DummyTemplateEngine(site)
        ctx = SimpleNamespace(markdown_parser=parser, template_engine=engine)

        pipeline = RenderingPipeline(site, dependency_tracker=tracker, build_context=ctx)

        # Update file in cache first (required for rendered output storage)
        cache.update_file(mock_page.source_path)

        # Set rendered HTML
        mock_page.rendered_html = "<html><body>Rendered</body></html>"

        # Before caching, rendered_output should be empty
        assert str(mock_page.source_path) not in cache.rendered_output

        # Call the method
        pipeline._cache_rendered_output(mock_page, "default.html")

        # After caching, rendered_output should have an entry
        assert str(mock_page.source_path) in cache.rendered_output
        assert "Rendered" in cache.rendered_output[str(mock_page.source_path)]["html"]

    def test_dependency_tracker_has_cache_attribute(self, site_with_cache):
        """
        Verify DependencyTracker exposes cache as public attribute.

        This ensures the rendering pipeline can access it correctly.
        """
        site, cache, tracker = site_with_cache

        # Must have .cache (public), not ._cache (private)
        assert hasattr(tracker, "cache")
        assert tracker.cache is cache

        # Should NOT have ._cache
        # (Note: Python allows accessing private attrs, so we just verify the public one works)
        assert tracker.cache.file_fingerprints is not None


class TestPipelineCacheIntegration:
    """Integration tests for cache storage across save/load cycles."""

    def test_parsed_content_survives_cache_save_load(self, site_with_cache, mock_page, tmp_path):
        """Verify parsed content is persisted and can be retrieved after save/load."""
        site, cache, tracker = site_with_cache

        parser = DummyParser()
        engine = DummyTemplateEngine(site)
        ctx = SimpleNamespace(markdown_parser=parser, template_engine=engine)

        pipeline = RenderingPipeline(site, dependency_tracker=tracker, build_context=ctx)

        # Store parsed content
        mock_page.parsed_ast = "<p>Cached content for persistence test</p>"
        mock_page.toc = "<nav>TOC</nav>"
        mock_page.links = []

        cache.update_file(mock_page.source_path)
        pipeline._cache_parsed_content(mock_page, "default.html", "mistune-3.0-toc1")

        # Save cache to disk
        cache_path = tmp_path / ".bengal" / "cache.json"
        cache.save(cache_path)

        # Load into fresh cache
        loaded_cache = BuildCache.load(cache_path)

        # Verify parsed content was persisted
        assert str(mock_page.source_path) in loaded_cache.parsed_content
        assert (
            "Cached content for persistence test"
            in loaded_cache.parsed_content[str(mock_page.source_path)]["html"]
        )

    def test_rendered_output_survives_cache_save_load(self, site_with_cache, mock_page, tmp_path):
        """Verify rendered output is persisted and can be retrieved after save/load."""
        site, cache, tracker = site_with_cache

        parser = DummyParser()
        engine = DummyTemplateEngine(site)
        ctx = SimpleNamespace(markdown_parser=parser, template_engine=engine)

        pipeline = RenderingPipeline(site, dependency_tracker=tracker, build_context=ctx)

        # Update file and store rendered output
        cache.update_file(mock_page.source_path)
        mock_page.rendered_html = "<html><body>Rendered content for persistence test</body></html>"

        pipeline._cache_rendered_output(mock_page, "default.html")

        # Save cache to disk
        cache_path = tmp_path / ".bengal" / "cache.json"
        cache.save(cache_path)

        # Load into fresh cache
        loaded_cache = BuildCache.load(cache_path)

        # Verify rendered output was persisted
        assert str(mock_page.source_path) in loaded_cache.rendered_output
        assert (
            "Rendered content for persistence test"
            in loaded_cache.rendered_output[str(mock_page.source_path)]["html"]
        )
