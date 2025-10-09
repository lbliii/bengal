"""
Tests for text processing utilities.
"""

import pytest
from bengal.utils.text import (
    slugify,
    strip_html,
    truncate_words,
    truncate_chars,
    truncate_middle,
    generate_excerpt,
    normalize_whitespace,
    escape_html,
    unescape_html,
    pluralize,
    humanize_bytes,
    humanize_number,
)


class TestSlugify:
    """Tests for slugify function."""
    
    def test_basic_slugify(self):
        """Test basic slugification."""
        assert slugify("Hello World!") == "hello-world"
        assert slugify("Test & Code") == "test-code"
        assert slugify("Python 3.9") == "python-39"
    
    def test_html_entity_unescaping(self):
        """Test HTML entity decoding."""
        assert slugify("Test &amp; Code", unescape_html=True) == "test-code"
        assert slugify("Test &lt; 5", unescape_html=True) == "test-5"
        assert slugify("A &amp; B &amp; C", unescape_html=True) == "a-b-c"
    
    def test_no_html_unescaping(self):
        """Test with HTML unescaping disabled."""
        # When not unescaping, &amp; becomes amp
        assert slugify("Test &amp; Code", unescape_html=False) == "test-amp-code"
    
    def test_max_length(self):
        """Test max_length parameter."""
        assert slugify("Very Long Title Here", max_length=10) == "very-long"
        assert slugify("Short", max_length=10) == "short"
        assert slugify("exactly-10", max_length=10) == "exactly-10"
    
    def test_custom_separator(self):
        """Test custom separator."""
        assert slugify("hello world", separator='_') == "hello_world"
        assert slugify("a b c", separator='.') == "a.b.c"
    
    def test_multiple_spaces_and_hyphens(self):
        """Test collapsing multiple spaces and hyphens."""
        assert slugify("hello   world") == "hello-world"
        assert slugify("a  -  b  -  c") == "a-b-c"
    
    def test_leading_trailing_hyphens(self):
        """Test removal of leading/trailing hyphens."""
        assert slugify("-hello-") == "hello"
        assert slugify("---test---") == "test"
    
    def test_unicode(self):
        """Test Unicode characters."""
        assert slugify("Café") == "café"
        assert slugify("日本語") == "日本語"
    
    def test_empty_string(self):
        """Test empty string."""
        assert slugify("") == ""
        assert slugify("   ") == ""
    
    def test_special_characters(self):
        """Test various special characters."""
        assert slugify("C++ Programming") == "c-programming"
        assert slugify("What's New?") == "whats-new"
        assert slugify("Email: test@example.com") == "email-testexamplecom"


class TestStripHtml:
    """Tests for strip_html function."""
    
    def test_basic_stripping(self):
        """Test basic HTML tag removal."""
        assert strip_html("<p>Hello</p>") == "Hello"
        assert strip_html("<strong>Bold</strong> text") == "Bold text"
    
    def test_nested_tags(self):
        """Test nested HTML tags."""
        assert strip_html("<div><p>Hello <strong>World</strong></p></div>") == "Hello World"
    
    def test_self_closing_tags(self):
        """Test self-closing tags."""
        assert strip_html("<br/>Line break") == "Line break"
        assert strip_html("Before<hr/>After") == "BeforeAfter"
    
    def test_entity_decoding(self):
        """Test HTML entity decoding."""
        assert strip_html("&lt;script&gt;", decode_entities=True) == "<script>"
        assert strip_html("&amp; &quot; &apos;", decode_entities=True) == "& \" '"
    
    def test_no_entity_decoding(self):
        """Test with entity decoding disabled."""
        assert strip_html("&lt;script&gt;", decode_entities=False) == "&lt;script&gt;"
    
    def test_empty_string(self):
        """Test empty string."""
        assert strip_html("") == ""
    
    def test_no_html(self):
        """Test plain text without HTML."""
        assert strip_html("Just plain text") == "Just plain text"


class TestTruncateWords:
    """Tests for truncate_words function."""
    
    def test_basic_truncation(self):
        """Test basic word truncation."""
        assert truncate_words("The quick brown fox jumps", 3) == "The quick brown..."
        assert truncate_words("One two three four five", 3) == "One two three..."
    
    def test_no_truncation_needed(self):
        """Test when text is shorter than word_count."""
        assert truncate_words("Short text", 10) == "Short text"
        assert truncate_words("One two", 2) == "One two"
    
    def test_custom_suffix(self):
        """Test custom suffix."""
        assert truncate_words("One two three four", 2, suffix="…") == "One two…"
        assert truncate_words("A B C D", 2, suffix=" [...]") == "A B [...]"
    
    def test_empty_string(self):
        """Test empty string."""
        assert truncate_words("", 5) == ""
    
    def test_single_word(self):
        """Test single word."""
        assert truncate_words("Word", 1) == "Word"
        assert truncate_words("Word", 0) == "..."


class TestTruncateChars:
    """Tests for truncate_chars function."""
    
    def test_basic_truncation(self):
        """Test basic character truncation."""
        # Truncates at length, then rstrips, then adds suffix
        assert truncate_chars("Hello World", 8) == "Hello Wo..."
        assert truncate_chars("Testing", 4) == "Test..."
    
    def test_no_truncation_needed(self):
        """Test when text is shorter than length."""
        assert truncate_chars("Short", 10) == "Short"
        assert truncate_chars("Test", 4) == "Test"
    
    def test_custom_suffix(self):
        """Test custom suffix."""
        assert truncate_chars("Hello World", 8, suffix="…") == "Hello Wo…"
    
    def test_empty_string(self):
        """Test empty string."""
        assert truncate_chars("", 5) == ""


class TestTruncateMiddle:
    """Tests for truncate_middle function."""
    
    def test_basic_truncation(self):
        """Test basic middle truncation."""
        result = truncate_middle('/very/long/path/to/file.txt', 20)
        assert len(result) == 20
        assert result.startswith('/very')
        assert result.endswith('file.txt')
        assert '...' in result
    
    def test_no_truncation_needed(self):
        """Test when text is shorter than max_length."""
        assert truncate_middle('short.txt', 20) == 'short.txt'
    
    def test_custom_separator(self):
        """Test custom separator."""
        result = truncate_middle('abcdefghijklmnop', 10, separator='…')
        assert '…' in result
        assert len(result) == 10
    
    def test_empty_string(self):
        """Test empty string."""
        assert truncate_middle('', 10) == ''


class TestGenerateExcerpt:
    """Tests for generate_excerpt function."""
    
    def test_basic_excerpt(self):
        """Test basic excerpt generation."""
        html = "<p>Hello <strong>World</strong> from Bengal SSG</p>"
        assert generate_excerpt(html, 2) == "Hello World..."
    
    def test_with_entities(self):
        """Test excerpt with HTML entities."""
        html = "<p>Test &amp; Code &lt; 5</p>"
        assert generate_excerpt(html, 10) == "Test & Code < 5"
    
    def test_custom_word_count(self):
        """Test custom word count."""
        html = "<p>One two three four five six seven</p>"
        assert generate_excerpt(html, 3) == "One two three..."
    
    def test_custom_suffix(self):
        """Test custom suffix."""
        html = "<p>One two three four</p>"
        assert generate_excerpt(html, 2, suffix="…") == "One two…"


class TestNormalizeWhitespace:
    """Tests for normalize_whitespace function."""
    
    def test_basic_normalization(self):
        """Test basic whitespace normalization."""
        assert normalize_whitespace("  hello   world  ") == "hello world"
        assert normalize_whitespace("a  b  c") == "a b c"
    
    def test_with_newlines(self):
        """Test normalization with newlines."""
        assert normalize_whitespace("line1\n\nline2", collapse=True) == "line1 line2"
        assert normalize_whitespace("a\tb\nc", collapse=True) == "a b c"
    
    def test_no_collapse(self):
        """Test with collapse=False."""
        assert normalize_whitespace("  hello  ", collapse=False) == "hello"
    
    def test_empty_string(self):
        """Test empty string."""
        assert normalize_whitespace("") == ""


class TestEscapeHtml:
    """Tests for escape_html function."""
    
    def test_basic_escaping(self):
        """Test basic HTML escaping."""
        assert escape_html("<script>") == "&lt;script&gt;"
        assert escape_html("a < b > c") == "a &lt; b &gt; c"
    
    def test_quotes(self):
        """Test quote escaping."""
        assert escape_html('"quotes"') == "&quot;quotes&quot;"
    
    def test_ampersand(self):
        """Test ampersand escaping."""
        assert escape_html("A & B") == "A &amp; B"
    
    def test_empty_string(self):
        """Test empty string."""
        assert escape_html("") == ""


class TestUnescapeHtml:
    """Tests for unescape_html function."""
    
    def test_basic_unescaping(self):
        """Test basic HTML unescaping."""
        assert unescape_html("&lt;script&gt;") == "<script>"
        assert unescape_html("&amp; &quot; &apos;") == "& \" '"
    
    def test_empty_string(self):
        """Test empty string."""
        assert unescape_html("") == ""


class TestPluralize:
    """Tests for pluralize function."""
    
    def test_singular(self):
        """Test singular form."""
        assert pluralize(1, 'page') == 'page'
        assert pluralize(1, 'item') == 'item'
    
    def test_plural_default(self):
        """Test default plural form (singular + 's')."""
        assert pluralize(0, 'page') == 'pages'
        assert pluralize(2, 'item') == 'items'
        assert pluralize(100, 'file') == 'files'
    
    def test_plural_custom(self):
        """Test custom plural form."""
        assert pluralize(2, 'box', 'boxes') == 'boxes'
        assert pluralize(0, 'child', 'children') == 'children'
    
    def test_edge_cases(self):
        """Test edge cases."""
        assert pluralize(-1, 'item') == 'items'  # Negative counts are plural


class TestHumanizeBytes:
    """Tests for humanize_bytes function."""
    
    def test_bytes(self):
        """Test byte formatting."""
        assert humanize_bytes(0) == "0 B"
        assert humanize_bytes(500) == "500 B"
        assert humanize_bytes(1023) == "1023 B"
    
    def test_kilobytes(self):
        """Test kilobyte formatting."""
        assert humanize_bytes(1024) == "1.0 KB"
        assert humanize_bytes(1536) == "1.5 KB"
        assert humanize_bytes(10240) == "10.0 KB"
    
    def test_megabytes(self):
        """Test megabyte formatting."""
        assert humanize_bytes(1048576) == "1.0 MB"
        assert humanize_bytes(1572864) == "1.5 MB"
    
    def test_gigabytes(self):
        """Test gigabyte formatting."""
        assert humanize_bytes(1073741824) == "1.0 GB"
    
    def test_terabytes(self):
        """Test terabyte formatting."""
        assert humanize_bytes(1099511627776) == "1.0 TB"


class TestHumanizeNumber:
    """Tests for humanize_number function."""
    
    def test_small_numbers(self):
        """Test small numbers (no separators needed)."""
        assert humanize_number(0) == "0"
        assert humanize_number(100) == "100"
        assert humanize_number(999) == "999"
    
    def test_thousands(self):
        """Test thousands."""
        assert humanize_number(1000) == "1,000"
        assert humanize_number(1234) == "1,234"
    
    def test_millions(self):
        """Test millions."""
        assert humanize_number(1000000) == "1,000,000"
        assert humanize_number(1234567) == "1,234,567"
    
    def test_negative(self):
        """Test negative numbers."""
        assert humanize_number(-1000) == "-1,000"

