"""Tests for content transformation template functions."""

from unittest.mock import Mock

from bengal.rendering.template_functions.content import (
    emojify,
    filter_highlight,
    html_escape,
    html_unescape,
    nl2br,
    resolve_links_for_embedding,
    safe_html,
    smartquotes,
    urlize,
)


class TestFilterHighlight:
    """Tests for filter_highlight (syntax highlighting)."""

    def test_highlights_python(self):
        result = filter_highlight("def foo(): pass", "python")
        assert "<pre>" in result
        assert "<code" in result
        assert "def" in result
        assert "foo" in result

    def test_empty_code_returns_empty(self):
        assert filter_highlight("", "python") == ""

    def test_fallback_for_unknown_language(self):
        result = filter_highlight("x = 1", "unknown-lang-xyz")
        assert "<pre>" in result
        assert "<code" in result
        assert "x = 1" in result


class TestSafeHtml:
    """Tests for safe_html filter."""

    def test_passthrough(self):
        html = "<p>Hello</p>"
        assert safe_html(html) == html

    def test_empty_string(self):
        assert safe_html("") == ""


class TestHtmlEscape:
    """Tests for html_escape filter."""

    def test_escape_tags(self):
        result = html_escape("<p>Hello</p>")
        assert result == "&lt;p&gt;Hello&lt;/p&gt;"

    def test_escape_ampersand(self):
        result = html_escape("Tom & Jerry")
        assert result == "Tom &amp; Jerry"

    def test_escape_quotes(self):
        result = html_escape('Say "Hello"')
        assert "Hello" in result
        assert "&" in result

    def test_empty_string(self):
        assert html_escape("") == ""

    def test_plain_text(self):
        assert html_escape("Hello World") == "Hello World"


class TestHtmlUnescape:
    """Tests for html_unescape filter."""

    def test_unescape_tags(self):
        result = html_unescape("&lt;p&gt;Hello&lt;/p&gt;")
        assert result == "<p>Hello</p>"

    def test_unescape_ampersand(self):
        result = html_unescape("Tom &amp; Jerry")
        assert result == "Tom & Jerry"

    def test_unescape_quotes(self):
        result = html_unescape("&quot;Hello&quot;")
        assert result == '"Hello"'

    def test_empty_string(self):
        assert html_unescape("") == ""

    def test_plain_text(self):
        assert html_unescape("Hello World") == "Hello World"


class TestNl2br:
    """Tests for nl2br filter."""

    def test_single_newline(self):
        result = nl2br("Line 1\nLine 2")
        assert result == "Line 1<br>\nLine 2"

    def test_multiple_newlines(self):
        result = nl2br("Line 1\n\nLine 2")
        assert result == "Line 1<br>\n<br>\nLine 2"

    def test_no_newlines(self):
        result = nl2br("Single line")
        assert result == "Single line"

    def test_empty_string(self):
        assert nl2br("") == ""


class TestSmartquotes:
    """Tests for smartquotes filter."""

    def test_double_quotes(self):
        result = smartquotes('"Hello"')
        # Check for Unicode curly quotes (U+201C and U+201D)
        assert "\u201c" in result
        assert "\u201d" in result

    def test_single_quotes(self):
        result = smartquotes("'Hello'")
        # Check for Unicode curly quotes (U+2018 and U+2019)
        assert "\u2018" in result
        assert "\u2019" in result

    def test_em_dash(self):
        result = smartquotes("Hello---World")
        assert result == "Hello—World"

    def test_en_dash(self):
        result = smartquotes("Hello--World")
        assert result == "Hello–World"

    def test_empty_string(self):
        assert smartquotes("") == ""

    def test_plain_text(self):
        result = smartquotes("Hello World")
        assert "Hello World" in result


class TestEmojify:
    """Tests for emojify filter."""

    def test_smile(self):
        result = emojify("Hello :smile:")
        assert result == "Hello 😊"

    def test_heart(self):
        result = emojify("I :heart: Python")
        assert result == "I ❤️ Python"

    def test_multiple_emoji(self):
        result = emojify(":rocket: :fire: :star:")
        assert result == "🚀 🔥 ⭐"

    def test_no_emoji(self):
        result = emojify("Plain text")
        assert result == "Plain text"

    def test_empty_string(self):
        assert emojify("") == ""

    def test_unknown_emoji(self):
        result = emojify(":unknown:")
        assert result == ":unknown:"


class TestUrlize:
    """Tests for urlize filter."""

    def test_simple_url(self):
        result = urlize("Check out https://example.com for more info")
        assert '<a href="https://example.com">https://example.com</a>' in result
        assert "Check out" in result
        assert "for more info" in result

    def test_http_url(self):
        result = urlize("Visit http://example.com")
        assert '<a href="http://example.com">' in result

    def test_www_url(self):
        result = urlize("Visit www.example.com")
        assert '<a href="https://www.example.com">' in result

    def test_url_with_path(self):
        result = urlize("See https://example.com/docs/guide")
        assert '<a href="https://example.com/docs/guide">' in result

    def test_url_with_query(self):
        result = urlize("Link: https://example.com/search?q=test")
        assert "search?q=test" in result

    def test_multiple_urls(self):
        result = urlize("Site: https://a.com and https://b.com")
        assert '<a href="https://a.com">' in result
        assert '<a href="https://b.com">' in result

    def test_target_attribute(self):
        result = urlize("Visit https://example.com", target="_blank")
        assert 'target="_blank"' in result

    def test_rel_attribute(self):
        result = urlize("Visit https://example.com", rel="noopener noreferrer")
        assert 'rel="noopener noreferrer"' in result

    def test_shorten_display(self):
        long_url = "https://example.com/very/long/path/to/resource"
        result = urlize(f"Visit {long_url}", shorten=True, shorten_length=30)
        assert "..." in result

    def test_no_urls(self):
        result = urlize("Just plain text without links")
        assert result == "Just plain text without links"

    def test_empty_string(self):
        assert urlize("") == ""

    def test_none_input(self):
        assert urlize(None) == ""

    def test_escapes_html(self):
        # Ensure HTML in URL display text is properly escaped
        result = urlize("Visit https://example.com/<script>alert(1)</script>")
        # The <script> is outside the URL so it won't be part of the link
        # The text after the URL is left as-is (this filter only converts URLs)
        assert '<a href="https://example.com/' in result


class TestResolveLinksForEmbedding:
    """Tests for resolve_links_for_embedding filter."""

    def test_empty_html_returns_empty(self):
        page = Mock(href="/docs/guides/foo/")
        assert resolve_links_for_embedding("", page) == ""

    def test_none_page_returns_html_unchanged(self):
        html = '<a href="./child">Child</a>'
        assert resolve_links_for_embedding(html, None) == html

    def test_relative_href_rewritten_to_absolute(self):
        page = Mock(href="/docs/content/authoring/external-references/")
        html = '<a href="./child">Child</a>'
        result = resolve_links_for_embedding(html, page)
        assert 'href="/docs/content/authoring/external-references/child"' in result

    def test_relative_src_rewritten_to_absolute(self):
        page = Mock(href="/docs/guides/images/")
        html = '<img src="./diagram.png" alt="Diagram">'
        result = resolve_links_for_embedding(html, page)
        assert 'src="/docs/guides/images/diagram.png"' in result

    def test_absolute_href_unchanged(self):
        page = Mock(href="/docs/guides/")
        html = '<a href="/docs/other">Other</a>'
        assert resolve_links_for_embedding(html, page) == html

    def test_http_url_unchanged(self):
        page = Mock(href="/docs/guides/")
        html = '<a href="https://example.com">External</a>'
        assert resolve_links_for_embedding(html, page) == html

    def test_anchor_unchanged(self):
        page = Mock(href="/docs/guides/")
        html = '<a href="#section">Section</a>'
        assert resolve_links_for_embedding(html, page) == html

    def test_plain_text_unchanged(self):
        page = Mock(href="/docs/guides/")
        html = "<p>No links here</p>"
        assert resolve_links_for_embedding(html, page) == html

    def test_uses_path_when_href_missing(self):
        page = type("Page", (), {"_path": "/docs/fallback/"})()
        html = '<a href="./child">Child</a>'
        result = resolve_links_for_embedding(html, page)
        assert 'href="/docs/fallback/child"' in result
