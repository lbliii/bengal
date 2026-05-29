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
from bengal.cache.parsed_output import clear_parsed_page_state
from bengal.core.records import ParsedPage, RenderedPage
from bengal.rendering.pipeline import RenderingPipeline
from bengal.rendering.pipeline.cache_checker import CacheChecker
from tests._testing.page_records import seed_parsed_page_state


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
        seed_parsed_page_state(
            mock_page,
            html_content="<p>Test content</p>",
            toc="<nav>TOC</nav>",
            links=[],
        )

        # Before caching, parsed_content should be empty
        assert str(mock_page.source_path) not in cache.parsed_content

        # Call the method via the extracted CacheChecker
        pipeline._cache_checker.cache_parsed_content(mock_page, "default.html", "mistune-3.0-toc1")

        # After caching, parsed_content should have an entry
        assert str(mock_page.source_path) in cache.parsed_content
        assert cache.parsed_content[str(mock_page.source_path)]["html"] == "<p>Test content</p>"

    def test_cache_parsed_content_persists_parsed_page_text_metrics(
        self, site_with_cache, mock_page
    ):
        """Parsed cache stores text metrics so warm hits avoid text re-extraction."""
        site, cache = site_with_cache

        parser = DummyParser()
        engine = DummyTemplateEngine(site)
        ctx = SimpleNamespace(markdown_parser=parser, template_engine=engine)
        pipeline = RenderingPipeline(site, build_context=ctx, build_cache=cache)

        parsed_page = ParsedPage(
            html_content="<p>Cached body</p>",
            toc="<nav>TOC</nav>",
            toc_items=(),
            excerpt="Cached body",
            meta_description="Cached body",
            plain_text="Cached body",
            word_count=2,
            reading_time=1,
            links=("docs/next",),
            ast_cache=None,
        )

        pipeline._cache_checker.cache_parsed_content(
            mock_page,
            "default.html",
            "patitas-test-toc1",
            parsed_page=parsed_page,
        )

        entry = cache.parsed_content[str(mock_page.source_path)]
        assert entry["plain_text"] == "Cached body"
        assert entry["word_count"] == 2
        assert entry["reading_time"] == 1

    def test_try_parsed_cache_restores_plain_text_cache_without_reextracting(
        self, site_with_cache, monkeypatch, tmp_path
    ):
        """Warm parsed-cache hits reuse cached plain text instead of parsing HTML again."""
        site, _cache = site_with_cache

        class PageWithExpensivePlainText:
            def __init__(self):
                self.source_path = tmp_path / "content" / "cached.md"
                self.output_path = tmp_path / "public" / "cached" / "index.html"
                self.metadata = {"title": "Cached"}
                self.rendered_html = ""
                clear_parsed_page_state(self)

            @property
            def plain_text(self):
                raise AssertionError("plain_text should be restored from parsed cache")

        class Cache:
            def get_parsed_content(self, *args, **kwargs):
                return {
                    "html": "<p>Cached body</p>",
                    "toc": "",
                    "toc_items": [],
                    "links": [],
                    "plain_text": "Cached body",
                    "word_count": 2,
                    "reading_time": 1,
                }

        class Renderer:
            def render_content(self, content):
                return content

            def render_page(self, page, html_content, parsed_page=None):
                return f"<html>{html_content}</html>"

        writes = []
        monkeypatch.setattr(
            "bengal.rendering.pipeline.cache_checker.format_html",
            lambda html, page, site: html,
        )
        monkeypatch.setattr(
            "bengal.rendering.pipeline.cache_checker.write_output",
            lambda *args, **kwargs: writes.append(kwargs.get("rendered_page")),
        )

        page = PageWithExpensivePlainText()
        checker = CacheChecker(site=site, renderer=Renderer(), build_cache=Cache())

        assert checker.try_parsed_cache(page, "default.html", "patitas-test-toc1") is True
        assert page._plain_text_cache == "Cached body"
        assert writes

    def test_try_rendered_cache_uses_render_record_without_mutating_page_html(
        self, site_with_cache, monkeypatch, tmp_path
    ):
        """Rendered-cache hits write the immutable record without dual-writing Page HTML."""
        site, _cache = site_with_cache

        class Cache:
            def get_rendered_output(self, *args, **kwargs):
                return "<html><body>cached html</body></html>"

        writes = []
        monkeypatch.setattr(
            "bengal.rendering.pipeline.cache_checker.write_output",
            lambda *args, **kwargs: writes.append(kwargs.get("rendered_page")),
        )

        page = SimpleNamespace(
            source_path=tmp_path / "content" / "cached.md",
            output_path=tmp_path / "public" / "cached" / "index.html",
            metadata={"title": "Cached"},
            rendered_html="<html><body>stale page html</body></html>",
        )
        checker = CacheChecker(site=site, renderer=MagicMock(), build_cache=Cache())

        assert checker.try_rendered_cache(page, "default.html") is True
        assert page.rendered_html == "<html><body>stale page html</body></html>"
        assert writes
        assert writes[0].rendered_html == "<html><body>cached html</body></html>"

    def test_try_parsed_cache_restores_empty_plain_text(
        self, site_with_cache, monkeypatch, tmp_path
    ):
        """Empty cached plain text is still a valid warm-cache value."""
        site, _cache = site_with_cache

        class PageWithEmptyPlainText:
            def __init__(self):
                self.source_path = tmp_path / "content" / "image-only.md"
                self.output_path = tmp_path / "public" / "image-only" / "index.html"
                self.metadata = {"title": "Image"}
                self.rendered_html = ""
                clear_parsed_page_state(self)

            @property
            def plain_text(self):
                raise AssertionError("empty plain_text should be restored from parsed cache")

        class Cache:
            def get_parsed_content(self, *args, **kwargs):
                return {
                    "html": "<img alt='' src='image.png'>",
                    "toc": "",
                    "toc_items": [],
                    "links": [],
                    "plain_text": "",
                    "word_count": 0,
                    "reading_time": 0,
                }

        class Renderer:
            def render_content(self, content):
                return content

            def render_page(self, page, html_content, parsed_page=None):
                return f"<html>{html_content}</html>"

        monkeypatch.setattr(
            "bengal.rendering.pipeline.cache_checker.format_html",
            lambda html, page, site: html,
        )
        monkeypatch.setattr(
            "bengal.rendering.pipeline.cache_checker.write_output", lambda *a, **k: None
        )

        page = PageWithEmptyPlainText()
        checker = CacheChecker(site=site, renderer=Renderer(), build_cache=Cache())

        assert checker.try_parsed_cache(page, "default.html", "patitas-test-toc1") is True
        assert page._plain_text_cache == ""
        assert page.rendered_html == ""

    def test_try_parsed_cache_uses_render_record_without_mutating_page_html(
        self, site_with_cache, monkeypatch, tmp_path
    ):
        """Parsed-cache hits render through records without dual-writing Page HTML."""
        site, _cache = site_with_cache

        class PageWithCachedParse:
            def __init__(self):
                self.source_path = tmp_path / "content" / "cached.md"
                self.output_path = tmp_path / "public" / "cached" / "index.html"
                self.metadata = {"title": "Cached"}
                self.rendered_html = "<html><body>stale page html</body></html>"
                clear_parsed_page_state(self)

            @property
            def plain_text(self):
                return "Cached body"

        class Cache:
            def get_parsed_content(self, *args, **kwargs):
                return {
                    "html": "<p>Cached body</p>",
                    "toc": "",
                    "toc_items": [],
                    "links": [],
                    "plain_text": "Cached body",
                    "word_count": 2,
                    "reading_time": 1,
                }

        class Renderer:
            def render_content(self, content):
                return content

            def render_page(self, page, html_content, parsed_page=None):
                return f"<html>{html_content}</html>"

        writes = []
        monkeypatch.setattr(
            "bengal.rendering.pipeline.cache_checker.format_html",
            lambda html, page, site: html,
        )
        monkeypatch.setattr(
            "bengal.rendering.pipeline.cache_checker.write_output",
            lambda *args, **kwargs: writes.append(kwargs.get("rendered_page")),
        )

        page = PageWithCachedParse()
        checker = CacheChecker(site=site, renderer=Renderer(), build_cache=Cache())

        assert checker.try_parsed_cache(page, "default.html", "patitas-test-toc1") is True
        assert page.rendered_html == "<html><body>stale page html</body></html>"
        assert writes
        assert writes[0].rendered_html == "<html><p>Cached body</p></html>"

    def test_ast_persistence_reuses_parser_last_document(
        self, site_with_cache, mock_page, monkeypatch
    ):
        """AST persistence consumes the parser's last document instead of parsing twice."""
        site, cache = site_with_cache
        site.config = {
            "markdown_engine": "patitas",
            "markdown": {"ast_cache": {"persist_tokens": True}},
            "content": {},
        }
        mock_page._source = "# Cached\n\nBody"
        mock_page.metadata = {"title": "Cached"}
        sentinel_doc = object()

        class Parser(DummyParser):
            supports_ast = True

            def __init__(self):
                super().__init__()
                self.parse_to_document_calls = 0
                self.consumed = False

            def parse_with_toc_and_context(self, content, metadata, context):
                return "<h1>Cached</h1><p>Body</p>", "<nav>Cached</nav>", "Body", "Body"

            def consume_last_document(self):
                self.consumed = True
                return sentinel_doc

            def parse_to_document(self, content, metadata):
                self.parse_to_document_calls += 1
                raise AssertionError("last document should be reused")

        parser = Parser()
        engine = DummyTemplateEngine(site)
        ctx = SimpleNamespace(markdown_parser=parser, template_engine=engine)
        pipeline = RenderingPipeline(site, build_context=ctx, build_cache=cache)
        pipeline._build_variable_context = lambda page: {
            "page": page,
            "site": site,
            "config": site.config,
        }

        monkeypatch.setattr(
            "patitas.to_dict", lambda doc: {"_type": "Document", "sentinel": doc is sentinel_doc}
        )

        parsed_page, _directive_links = pipeline._parse_with_context_aware_parser(
            mock_page, need_toc=True
        )

        assert parser.consumed is True
        assert parser.parse_to_document_calls == 0
        assert parsed_page.ast_cache == {"_type": "Document", "sentinel": True}

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

    def test_cache_rendered_output_prefers_rendered_page_record(
        self, site_with_cache, mock_page, tmp_path
    ):
        """Rendered output cache reads from RenderedPage when supplied."""
        site, cache = site_with_cache

        parser = DummyParser()
        engine = DummyTemplateEngine(site)
        ctx = SimpleNamespace(markdown_parser=parser, template_engine=engine)

        pipeline = RenderingPipeline(site, build_context=ctx, build_cache=cache)
        cache.update_file(mock_page.source_path)

        mock_page.rendered_html = "<html><body>stale mutable html</body></html>"
        rendered_page = RenderedPage(
            source_path=mock_page.source_path,
            output_path=tmp_path / "public" / "test" / "index.html",
            rendered_html="<html><body>record html</body></html>",
            render_time_ms=1.0,
        )

        pipeline._cache_checker.cache_rendered_output(mock_page, "default.html", rendered_page)

        cached = cache.rendered_output[str(mock_page.source_path)]
        assert "record html" in cached["html"]
        assert "stale mutable html" not in cached["html"]

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
        seed_parsed_page_state(
            mock_page,
            html_content="<p>Cached content for persistence test</p>",
            toc="<nav>TOC</nav>",
            links=[],
        )

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
