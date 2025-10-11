"""Tests for content transformation template functions."""

from bengal.rendering.template_functions.content import (
    safe_html,
    html_escape,
    html_unescape,
    nl2br,
    smartquotes,
    emojify,
)


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
        assert 'Hello' in result and '&' in result
    
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
        assert '\u201c' in result and '\u201d' in result
    
    def test_single_quotes(self):
        result = smartquotes("'Hello'")
        # Check for Unicode curly quotes (U+2018 and U+2019)
        assert '\u2018' in result and '\u2019' in result
    
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

