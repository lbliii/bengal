"""
Tests for rendering pipeline cache storage integration.

Verifies that the rendering pipeline correctly stores parsed content
and rendered output in the cache via build_cache.

These tests ensure the fix for the ._cache vs .cache bug doesn't regress,
and verify the build_cache concern separation.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bengal.cache import BuildCache
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


@pytest.fixture
def site_with_cache(tmp_path):
    """Create a site with a real BuildCache."""
    cache = BuildCache()
    site = SimpleNamespace(
        config={"markdown_engine": "mistune"},
        root_path=tmp_path,
        output_dir=tmp_path / "public",
        theme="default",
        xref_index={},
    )
    site.output_dir.mkdir(parents=True, exist_ok=True)
    return site, cache


@pytest.fixture
def mock_page(tmp_path):
    """Create a mock page for testing."""
    source_path = tmp_path / "content" / "test.md"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("# Test\n\nHello world")

    page = SimpleNamespace(
        source_path=source_path,
        output_path=None,
        _raw_content="Hello world",
        title="Test Page",
        metadata={"title": "Test Page", "type": "doc"},
        tags=[],
        toc="",
        html_content=None,
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
        Verify cache_parsed_content accesses build_cache directly.

        This test ensures the fix for the ._cache vs .cache bug and
        validates the build_cache concern separation.
        """
        site, cache = site_with_cache

        parser = DummyParser()
        engine = DummyTemplateEngine(site)
        ctx = SimpleNamespace(markdown_parser=parser, template_engine=engine)

        pipeline = RenderingPipeline(site, build_context=ctx, build_cache=cache)

        # Manually call cache_parsed_content via the cache_checker
        mock_page.html_content = "<p>Test content</p>"
        mock_page.toc = "<nav>TOC</nav>"
        mock_page.links = []

        # Before caching, parsed_content should be empty
        assert str(mock_page.source_path) not in cache.parsed_content

        # Call the method via the extracted CacheChecker
        pipeline._cache_checker.cache_parsed_content(mock_page, "default.html", "mistune-3.0-toc1")

        # After caching, parsed_content should have an entry
        assert str(mock_page.source_path) in cache.parsed_content
        assert cache.parsed_content[str(mock_page.source_path)]["html"] == "<p>Test content</p>"

    def test_cache_rendered_output_uses_correct_attribute(
        self, site_with_cache, mock_page, tmp_path
    ):
        """
        Verify cache_rendered_output accesses build_cache directly.

        This test ensures the fix for the ._cache vs .cache bug and
        validates the build_cache concern separation.
        """
        site, cache = site_with_cache

        parser = DummyParser()
        engine = DummyTemplateEngine(site)
        ctx = SimpleNamespace(markdown_parser=parser, template_engine=engine)

        pipeline = RenderingPipeline(site, build_context=ctx, build_cache=cache)

        # Update file in cache first (required for rendered output storage)
        cache.update_file(mock_page.source_path)

        # Set rendered HTML
        mock_page.rendered_html = "<html><body>Rendered</body></html>"

        # Before caching, rendered_output should be empty
        assert str(mock_page.source_path) not in cache.rendered_output

        # Call the method via the extracted CacheChecker
        pipeline._cache_checker.cache_rendered_output(mock_page, "default.html")

        # After caching, rendered_output should have an entry
        assert str(mock_page.source_path) in cache.rendered_output
        assert "Rendered" in cache.rendered_output[str(mock_page.source_path)]["html"]

    def test_build_cache_passed_directly(self, site_with_cache):
        """
        Verify build_cache can be passed directly.
        """
        site, cache = site_with_cache

        parser = DummyParser()
        engine = DummyTemplateEngine(site)
        ctx = SimpleNamespace(markdown_parser=parser, template_engine=engine)

        pipeline = RenderingPipeline(site, build_context=ctx, build_cache=cache)

        assert pipeline.build_cache is cache
        assert pipeline._cache_checker.build_cache is cache


class TestPipelineCacheIntegration:
    """Integration tests for cache storage across save/load cycles."""

    def test_parsed_content_survives_cache_save_load(self, site_with_cache, mock_page, tmp_path):
        """Verify parsed content is persisted and can be retrieved after save/load."""
        site, cache = site_with_cache

        parser = DummyParser()
        engine = DummyTemplateEngine(site)
        ctx = SimpleNamespace(markdown_parser=parser, template_engine=engine)

        pipeline = RenderingPipeline(site, build_context=ctx, build_cache=cache)

        # Store parsed content
        mock_page.html_content = "<p>Cached content for persistence test</p>"
        mock_page.toc = "<nav>TOC</nav>"
        mock_page.links = []

        cache.update_file(mock_page.source_path)
        pipeline._cache_checker.cache_parsed_content(mock_page, "default.html", "mistune-3.0-toc1")

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
        site, cache = site_with_cache

        parser = DummyParser()
        engine = DummyTemplateEngine(site)
        ctx = SimpleNamespace(markdown_parser=parser, template_engine=engine)

        pipeline = RenderingPipeline(site, build_context=ctx, build_cache=cache)

        # Update file and store rendered output
        cache.update_file(mock_page.source_path)
        mock_page.rendered_html = "<html><body>Rendered content for persistence test</body></html>"

        pipeline._cache_checker.cache_rendered_output(mock_page, "default.html")

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
