"""
Tests for bengal.core.utils.text module.

Tests HTML stripping and text truncation utilities.
"""

from __future__ import annotations

import pytest

from bengal.core.utils.text import (
    normalize_whitespace,
    strip_html,
    strip_html_and_normalize,
    truncate_at_sentence,
    truncate_at_word,
)


class TestStripHtml:
    """Tests for strip_html function."""

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert strip_html("") == ""

    def test_no_html(self) -> None:
        """Plain text passes through unchanged."""
        assert strip_html("Hello world") == "Hello world"

    def test_simple_tags(self) -> None:
        """Simple HTML tags are removed."""
        assert strip_html("<p>Hello</p>") == "Hello"

    def test_nested_tags(self) -> None:
        """Nested HTML tags are removed."""
        assert strip_html("<div><p>Hello <strong>world</strong>!</p></div>") == "Hello world!"

    def test_self_closing_tags(self) -> None:
        """Self-closing tags are removed."""
        assert strip_html("Hello<br/>world") == "Helloworld"
        assert strip_html("Line 1<br>Line 2") == "Line 1Line 2"

    def test_attributes_preserved_content(self) -> None:
        """Tags with attributes are removed but content preserved."""
        assert strip_html('<a href="https://example.com">Click me</a>') == "Click me"
        assert strip_html('<div class="foo" id="bar">Content</div>') == "Content"

    def test_preserves_whitespace(self) -> None:
        """Whitespace between tags is preserved."""
        assert strip_html("<p>Hello</p> <p>World</p>") == "Hello World"


class TestNormalizeWhitespace:
    """Tests for normalize_whitespace function."""

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert normalize_whitespace("") == ""

    def test_single_spaces(self) -> None:
        """Single spaces are preserved."""
        assert normalize_whitespace("Hello world") == "Hello world"

    def test_multiple_spaces(self) -> None:
        """Multiple spaces are collapsed to single space."""
        assert normalize_whitespace("Hello    world") == "Hello world"

    def test_tabs_and_newlines(self) -> None:
        """Tabs and newlines are converted to single space."""
        assert normalize_whitespace("Hello\n\nworld") == "Hello world"
        assert normalize_whitespace("Hello\t\tworld") == "Hello world"

    def test_leading_trailing_stripped(self) -> None:
        """Leading and trailing whitespace is stripped."""
        assert normalize_whitespace("  Hello world  ") == "Hello world"

    def test_mixed_whitespace(self) -> None:
        """Mixed whitespace is normalized."""
        assert normalize_whitespace("Hello  \n\t  world") == "Hello world"


class TestStripHtmlAndNormalize:
    """Tests for strip_html_and_normalize function."""

    def test_combines_both_operations(self) -> None:
        """HTML is stripped and whitespace normalized."""
        result = strip_html_and_normalize("<p>Hello</p>\n<p>World</p>")
        assert result == "Hello World"

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert strip_html_and_normalize("") == ""

    def test_complex_html(self) -> None:
        """Complex HTML is properly processed."""
        html = """
        <div class="article">
            <h1>Title</h1>
            <p>First paragraph.</p>
            <p>Second paragraph.</p>
        </div>
        """
        result = strip_html_and_normalize(html)
        assert result == "Title First paragraph. Second paragraph."


class TestTruncateAtSentence:
    """Tests for truncate_at_sentence function."""

    def test_short_text_unchanged(self) -> None:
        """Text shorter than limit is unchanged."""
        text = "Hello world."
        assert truncate_at_sentence(text, length=50) == text

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert truncate_at_sentence("") == ""

    def test_truncates_at_sentence_boundary(self) -> None:
        """Text is truncated at sentence boundary when possible."""
        text = "Hello world. This is a test. More text here that makes it longer."
        result = truncate_at_sentence(text, length=30)
        # Should truncate at "Hello world. This is a test." (29 chars) or nearby
        assert result.endswith(".") or result.endswith("...")

    def test_truncates_at_exclamation(self) -> None:
        """Text is truncated at exclamation mark."""
        text = "Hello world! This is a test that continues much longer than the limit."
        result = truncate_at_sentence(text, length=20)
        # Should truncate at "Hello world!" or use word boundary
        assert result == "Hello world!" or result.endswith("...")

    def test_truncates_at_question(self) -> None:
        """Text is truncated at question mark."""
        text = "Hello world? This is a test that continues much longer than the limit."
        result = truncate_at_sentence(text, length=20)
        # Should truncate at "Hello world?" or use word boundary
        assert result == "Hello world?" or result.endswith("...")

    def test_falls_back_to_word_boundary(self) -> None:
        """Falls back to word boundary if no sentence boundary found."""
        text = "Hello world this is a test without sentences"
        result = truncate_at_sentence(text, length=20)
        # Should truncate at word boundary with ellipsis
        assert result.endswith("...")
        assert len(result) <= 23  # 20 + "..."

    def test_respects_min_ratio(self) -> None:
        """Sentence boundary must be at least min_ratio of length."""
        text = "Hi. This is a much longer sentence that continues."
        # "Hi." is only 3 chars, less than 60% of 50, so should fall back
        result = truncate_at_sentence(text, length=50, min_ratio=0.6)
        # Should not use "Hi." as it's too short
        assert result != "Hi."


class TestTruncateAtWord:
    """Tests for truncate_at_word function."""

    def test_short_text_unchanged(self) -> None:
        """Text shorter than limit is unchanged."""
        text = "Hello world"
        assert truncate_at_word(text, length=50) == text

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert truncate_at_word("") == ""

    def test_truncates_at_word_boundary(self) -> None:
        """Text is truncated at word boundary, total length including suffix stays within limit."""
        text = "Hello world test"
        result = truncate_at_word(text, length=12)
        # length=12, suffix="..." (3 chars), so max content = 9
        # "Hello wor"[:9] -> last space at 5 -> "Hello" + "..." = "Hello..."
        assert result == "Hello..."
        assert len(result) <= 12

    def test_adds_ellipsis(self) -> None:
        """Ellipsis is added when text is truncated."""
        text = "Hello world this is a test"
        result = truncate_at_word(text, length=15)
        assert result.endswith("...")
        assert len(result) <= 15

    def test_no_space_found(self) -> None:
        """Handles text with no spaces - truncates to fit within length."""
        text = "Superlongwordwithoutspaces"
        result = truncate_at_word(text, length=10)
        # length=10, suffix="..." (3 chars), so max content = 7
        # "Superlo" + "..." = "Superlo..." (10 chars)
        assert result == "Superlo..."
        assert len(result) <= 10

    def test_exact_length(self) -> None:
        """Text at exact length is unchanged."""
        text = "Hello"
        assert truncate_at_word(text, length=5) == text
