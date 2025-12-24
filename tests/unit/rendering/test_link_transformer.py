"""Tests for the link transformer module."""

from bengal.rendering.link_transformer import (
    get_baseurl,
    should_transform_links,
    transform_internal_links,
)


class TestTransformInternalLinks:
    """Tests for transform_internal_links function."""

    def test_transforms_internal_href(self):
        """Test that internal hrefs are transformed."""
        html = '<a href="/docs/guide/">Guide</a>'
        result = transform_internal_links(html, "/bengal")
        assert result == '<a href="/bengal/docs/guide/">Guide</a>'

    def test_transforms_internal_src(self):
        """Test that internal src attributes are transformed."""
        html = '<img src="/images/logo.png" alt="Logo">'
        result = transform_internal_links(html, "/bengal")
        assert result == '<img src="/bengal/images/logo.png" alt="Logo">'

    def test_preserves_external_links(self):
        """Test that external links are not transformed."""
        html = '<a href="https://example.com/page/">External</a>'
        result = transform_internal_links(html, "/bengal")
        assert result == html

    def test_preserves_relative_links(self):
        """Test that relative links (without leading /) are not transformed."""
        html = '<a href="sibling/page/">Relative</a>'
        result = transform_internal_links(html, "/bengal")
        assert result == html

    def test_preserves_anchor_links(self):
        """Test that anchor links are not transformed."""
        html = '<a href="#section">Section</a>'
        result = transform_internal_links(html, "/bengal")
        assert result == html

    def test_preserves_already_prefixed_links(self):
        """Test that links already having baseurl are not double-prefixed."""
        html = '<a href="/bengal/docs/guide/">Guide</a>'
        result = transform_internal_links(html, "/bengal")
        assert result == html

    def test_handles_single_quotes(self):
        """Test that single-quoted attributes are handled."""
        html = "<a href='/docs/guide/'>Guide</a>"
        result = transform_internal_links(html, "/bengal")
        assert result == "<a href='/bengal/docs/guide/'>Guide</a>"

    def test_handles_root_path(self):
        """Test that root path / is transformed correctly."""
        html = '<a href="/">Home</a>'
        result = transform_internal_links(html, "/bengal")
        assert result == '<a href="/bengal/">Home</a>'

    def test_handles_multiple_links(self):
        """Test that multiple links in same HTML are all transformed."""
        html = """
        <a href="/docs/">Docs</a>
        <a href="/blog/">Blog</a>
        <a href="https://external.com/">External</a>
        """
        result = transform_internal_links(html, "/bengal")
        assert "/bengal/docs/" in result
        assert "/bengal/blog/" in result
        assert "https://external.com/" in result  # Unchanged

    def test_empty_baseurl_returns_unchanged(self):
        """Test that empty baseurl returns HTML unchanged."""
        html = '<a href="/docs/guide/">Guide</a>'
        result = transform_internal_links(html, "")
        assert result == html

    def test_empty_html_returns_empty(self):
        """Test that empty HTML returns empty."""
        result = transform_internal_links("", "/bengal")
        assert result == ""

    def test_none_html_returns_empty(self):
        """Test that None HTML is handled."""
        result = transform_internal_links(None, "/bengal")
        assert result is None

    def test_absolute_baseurl(self):
        """Test with absolute baseurl (like production domain)."""
        html = '<a href="/docs/guide/">Guide</a>'
        result = transform_internal_links(html, "https://example.com/bengal")
        assert result == '<a href="https://example.com/bengal/docs/guide/">Guide</a>'

    def test_baseurl_without_leading_slash(self):
        """Test that baseurl without leading slash is normalized."""
        html = '<a href="/docs/guide/">Guide</a>'
        result = transform_internal_links(html, "bengal")
        assert result == '<a href="/bengal/docs/guide/">Guide</a>'

    def test_preserves_query_strings(self):
        """Test that links with query strings are transformed correctly."""
        html = '<a href="/search/?q=test">Search</a>'
        result = transform_internal_links(html, "/bengal")
        assert result == '<a href="/bengal/search/?q=test">Search</a>'


class TestShouldTransformLinks:
    """Tests for should_transform_links function."""

    def test_returns_true_when_baseurl_set(self):
        """Test that function returns True when baseurl is configured."""
        config = {"baseurl": "/bengal"}
        assert should_transform_links(config) is True

    def test_returns_false_when_no_baseurl(self):
        """Test that function returns False when no baseurl."""
        config = {}
        assert should_transform_links(config) is False

    def test_returns_false_when_empty_baseurl(self):
        """Test that function returns False when baseurl is empty string."""
        config = {"baseurl": ""}
        assert should_transform_links(config) is False

    def test_respects_explicit_disable(self):
        """Test that transform_links: false disables transformation."""
        config = {"baseurl": "/bengal", "build": {"transform_links": False}}
        assert should_transform_links(config) is False

    def test_explicit_enable(self):
        """Test that transform_links: true enables transformation."""
        config = {"baseurl": "/bengal", "build": {"transform_links": True}}
        assert should_transform_links(config) is True


class TestGetBaseurl:
    """Tests for get_baseurl function."""

    def test_returns_baseurl(self):
        """Test that baseurl is returned."""
        config = {"baseurl": "/bengal"}
        assert get_baseurl(config) == "/bengal"

    def test_strips_trailing_slash(self):
        """Test that trailing slash is stripped."""
        config = {"baseurl": "/bengal/"}
        assert get_baseurl(config) == "/bengal"

    def test_returns_empty_for_missing(self):
        """Test that empty string is returned for missing baseurl."""
        config = {}
        assert get_baseurl(config) == ""

    def test_returns_empty_for_none(self):
        """Test that empty string is returned for None baseurl."""
        config = {"baseurl": None}
        assert get_baseurl(config) == ""


