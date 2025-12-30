"""
Unit tests for the PageExplainer module.

Tests the page explanation functionality including source info extraction,
template chain resolution, dependency tracking, cache status, and diagnostics.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.debug.explainer import PageExplainer
from bengal.debug.models import (
    CacheInfo,
    DependencyInfo,
    Issue,
    OutputInfo,
    PageExplanation,
    ShortcodeUsage,
    SourceInfo,
    TemplateInfo,
)
from bengal.errors import BengalContentError


class TestSourceInfo:
    """Tests for SourceInfo model."""

    def test_size_human_bytes(self):
        """Test human-readable size for bytes."""
        info = SourceInfo(
            path=Path("test.md"),
            size_bytes=500,
            line_count=10,
            modified=None,
        )
        assert info.size_human == "500 B"

    def test_size_human_kilobytes(self):
        """Test human-readable size for kilobytes."""
        info = SourceInfo(
            path=Path("test.md"),
            size_bytes=5000,
            line_count=100,
            modified=None,
        )
        assert info.size_human == "4.9 KB"

    def test_size_human_megabytes(self):
        """Test human-readable size for megabytes."""
        info = SourceInfo(
            path=Path("test.md"),
            size_bytes=5_000_000,
            line_count=1000,
            modified=None,
        )
        assert info.size_human == "4.8 MB"


class TestCacheInfo:
    """Tests for CacheInfo model."""

    def test_status_emoji_hit(self):
        """Test cache hit emoji."""
        info = CacheInfo(status="HIT", reason=None, cache_key="test")
        assert info.status_emoji == "✅"

    def test_status_emoji_stale(self):
        """Test cache stale emoji."""
        info = CacheInfo(status="STALE", reason="File modified", cache_key="test")
        assert info.status_emoji == "⚠️"

    def test_status_emoji_miss(self):
        """Test cache miss emoji."""
        info = CacheInfo(status="MISS", reason="Not in cache", cache_key="test")
        assert info.status_emoji == "❌"


class TestIssue:
    """Tests for Issue model."""

    def test_severity_emoji_error(self):
        """Test error severity emoji."""
        issue = Issue(severity="error", issue_type="test", message="Test error")
        assert issue.severity_emoji == "❌"

    def test_severity_emoji_warning(self):
        """Test warning severity emoji."""
        issue = Issue(severity="warning", issue_type="test", message="Test warning")
        assert issue.severity_emoji == "⚠️"

    def test_severity_emoji_info(self):
        """Test info severity emoji."""
        issue = Issue(severity="info", issue_type="test", message="Test info")
        assert issue.severity_emoji == "ℹ️"


class TestPageExplainer:
    """Tests for PageExplainer class."""

    @pytest.fixture
    def mock_site(self):
        """Create a mock site with pages.

        Note: MagicMock auto-creates attributes when accessed, so we must
        explicitly set all attributes that the source code uses (e.g., _source).
        """
        site = MagicMock()
        site.root_path = Path("/test/site")
        site.output_dir = Path("/test/site/public")
        site.theme = "default"

        # Create mock pages
        page1 = MagicMock()
        page1.source_path = Path("content/docs/guide.md")
        page1.content = "# Guide\n\nSome content here.\n"
        page1._source = "# Guide\n\nSome content here.\n"  # Required: source code uses page._source
        page1.metadata = {"title": "Guide", "type": "doc", "tags": ["tutorial"]}
        page1.is_virtual = False
        page1.href = "/docs/guide/"
        page1._path = "/docs/guide/"
        page1.output_path = Path("docs/guide/index.html")
        page1._section = None
        page1.core = MagicMock()
        page1.core.type = "doc"

        page2 = MagicMock()
        page2.source_path = Path("content/posts/hello.md")
        page2.content = "# Hello\n\n:::note\nA note\n:::\n"
        page2._source = (
            "# Hello\n\n:::note\nA note\n:::\n"  # Required: source code uses page._source
        )
        page2.metadata = {"title": "Hello", "type": "post"}
        page2.is_virtual = False
        page2.href = "/posts/hello/"
        page2._path = "/posts/hello/"
        page2.output_path = Path("posts/hello/index.html")
        page2._section = None
        page2.core = MagicMock()
        page2.core.type = "post"

        site.pages = [page1, page2]
        return site

    @pytest.fixture
    def mock_cache(self):
        """Create a mock build cache."""
        cache = MagicMock()
        cache.parsed_content = {}
        cache.rendered_output = {}
        cache.dependencies = {}
        cache.is_changed = MagicMock(return_value=False)
        return cache

    def test_find_page_exact_match(self, mock_site):
        """Test finding page by exact source path."""
        explainer = PageExplainer(mock_site)
        page = explainer._find_page("content/docs/guide.md")
        assert page is not None
        assert page.source_path == Path("content/docs/guide.md")

    def test_find_page_partial_match(self, mock_site):
        """Test finding page by partial path."""
        explainer = PageExplainer(mock_site)
        page = explainer._find_page("guide.md")
        assert page is not None
        assert "guide.md" in str(page.source_path)

    def test_find_page_not_found(self, mock_site):
        """Test finding non-existent page returns None."""
        explainer = PageExplainer(mock_site)
        page = explainer._find_page("nonexistent.md")
        assert page is None

    def test_get_source_info_virtual_page(self, mock_site):
        """Test source info for virtual page."""
        mock_site.pages[0].is_virtual = True
        explainer = PageExplainer(mock_site)

        info = explainer._get_source_info(mock_site.pages[0])

        assert info.path == Path("content/docs/guide.md")
        assert info.line_count > 0
        assert info.encoding == "UTF-8"

    def test_get_shortcode_usage(self, mock_site):
        """Test extracting shortcode/directive usage."""
        explainer = PageExplainer(mock_site)

        # Page with directive
        usages = explainer._get_shortcode_usage(mock_site.pages[1])

        assert len(usages) == 1
        assert usages[0].name == "note"
        assert usages[0].count == 1

    def test_get_shortcode_usage_no_directives(self, mock_site):
        """Test shortcode extraction when no directives."""
        explainer = PageExplainer(mock_site)

        usages = explainer._get_shortcode_usage(mock_site.pages[0])

        assert len(usages) == 0

    def test_get_cache_status_no_cache(self, mock_site):
        """Test cache status when no cache available."""
        explainer = PageExplainer(mock_site, cache=None)

        status = explainer._get_cache_status(mock_site.pages[0])

        assert status.status == "UNKNOWN"
        assert "No cache" in status.reason

    def test_get_cache_status_miss(self, mock_site, mock_cache):
        """Test cache status for cache miss."""
        explainer = PageExplainer(mock_site, cache=mock_cache)

        status = explainer._get_cache_status(mock_site.pages[0])

        assert status.status == "MISS"
        assert status.content_cached is False

    def test_get_cache_status_hit(self, mock_site, mock_cache):
        """Test cache status for cache hit."""
        page_key = str(mock_site.pages[0].source_path)
        mock_cache.parsed_content[page_key] = {"html": "<p>test</p>"}
        mock_cache.rendered_output[page_key] = {"html": "<html>test</html>"}

        explainer = PageExplainer(mock_site, cache=mock_cache)
        status = explainer._get_cache_status(mock_site.pages[0])

        assert status.status == "HIT"
        assert status.content_cached is True
        assert status.rendered_cached is True

    def test_get_cache_status_stale(self, mock_site, mock_cache):
        """Test cache status for stale cache."""
        page_key = str(mock_site.pages[0].source_path)
        mock_cache.parsed_content[page_key] = {"html": "<p>test</p>"}
        mock_cache.is_changed = MagicMock(return_value=True)

        explainer = PageExplainer(mock_site, cache=mock_cache)
        status = explainer._get_cache_status(mock_site.pages[0])

        assert status.status == "STALE"
        assert "modified" in status.reason.lower()

    def test_get_template_name_from_metadata(self, mock_site):
        """Test getting template name from page metadata."""
        mock_site.pages[0].metadata["template"] = "custom.html"

        explainer = PageExplainer(mock_site)
        template = explainer._get_template_name(mock_site.pages[0])

        assert template == "custom.html"

    def test_get_template_name_from_type(self, mock_site):
        """Test getting template name from page type."""
        explainer = PageExplainer(mock_site)
        template = explainer._get_template_name(mock_site.pages[0])

        assert template == "doc.html"

    def test_extract_asset_refs(self, mock_site):
        """Test extracting asset references from content."""
        mock_site.pages[0].content = """
# Test

![Image](images/test.png)

<img src="/assets/logo.svg" alt="Logo">

![External](https://example.com/image.png)
"""
        explainer = PageExplainer(mock_site)
        refs = explainer._extract_asset_refs(mock_site.pages[0].content)

        # Should include local refs, exclude external
        assert "images/test.png" in refs
        assert "/assets/logo.svg" in refs
        assert "https://example.com/image.png" not in refs

    def test_extract_extends(self):
        """Test extracting extends directive from template."""
        explainer = PageExplainer(MagicMock())

        content = '{% extends "base.html" %}\n{% block content %}...'
        result = explainer._extract_extends(content)

        assert result == "base.html"

    def test_extract_extends_none(self):
        """Test extracting extends when not present."""
        explainer = PageExplainer(MagicMock())

        content = "{% block content %}...{% endblock %}"
        result = explainer._extract_extends(content)

        assert result is None

    def test_extract_includes(self):
        """Test extracting include directives from template."""
        explainer = PageExplainer(MagicMock())

        content = """
{% include "header.html" %}
{% include 'footer.html' %}
{% include "sidebar.html" %}
"""
        result = explainer._extract_includes(content)

        assert len(result) == 3
        assert "header.html" in result
        assert "footer.html" in result
        assert "sidebar.html" in result

    def test_explain_raises_for_missing_page(self, mock_site):
        """Test that explain raises BengalContentError for missing page."""
        explainer = PageExplainer(mock_site)

        with pytest.raises(BengalContentError, match="Page not found"):
            explainer.explain("nonexistent.md")

    def test_diagnose_issues_broken_link(self, mock_site):
        """Test diagnosing broken internal links."""
        content = """
# Test

[Valid Link](/posts/hello/)
[Broken Link](/docs/missing/)
"""
        mock_site.pages[0].content = content
        mock_site.pages[0]._source = content  # Required: source code uses page._source
        explainer = PageExplainer(mock_site)
        issues = explainer._diagnose_issues(mock_site.pages[0])

        # Should find broken link
        broken_link_issues = [i for i in issues if i.issue_type == "broken_link"]
        assert len(broken_link_issues) == 1
        assert "/docs/missing/" in broken_link_issues[0].message


class TestPageExplanation:
    """Tests for PageExplanation model."""

    def test_create_explanation(self):
        """Test creating a full page explanation."""
        explanation = PageExplanation(
            source=SourceInfo(
                path=Path("test.md"),
                size_bytes=1000,
                line_count=50,
                modified=datetime.now(),
            ),
            frontmatter={"title": "Test", "type": "doc"},
            template_chain=[
                TemplateInfo(
                    name="doc.html",
                    source_path=Path("templates/doc.html"),
                    theme="default",
                )
            ],
            dependencies=DependencyInfo(
                templates=["doc.html", "base.html"],
                assets=["image.png"],
            ),
            shortcodes=[ShortcodeUsage(name="note", count=2, lines=[10, 20])],
            cache=CacheInfo(status="HIT", reason=None, cache_key="test"),
            output=OutputInfo(path=Path("test/index.html"), url="/test/"),
        )

        assert explanation.source.size_bytes == 1000
        assert explanation.frontmatter["title"] == "Test"
        assert len(explanation.template_chain) == 1
        assert len(explanation.dependencies.templates) == 2
        assert len(explanation.shortcodes) == 1
        assert explanation.cache.status == "HIT"
        assert explanation.output.url == "/test/"
