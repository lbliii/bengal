"""Tests for string template functions."""

from bengal.rendering.template_functions.strings import (
    excerpt,
    pluralize,
    reading_time,
    replace_regex,
    slugify,
    strip_html,
    strip_whitespace,
    truncate_chars,
    truncatewords,
)


class TestTruncatewords:
    """Tests for truncatewords filter."""

    def test_truncate_long_text(self):
        text = "This is a long piece of text with many words that needs truncating"
        result = truncatewords(text, 5)
        assert result == "This is a long piece..."

    def test_no_truncate_short_text(self):
        text = "Short text"
        result = truncatewords(text, 5)
        assert result == "Short text"

    def test_exact_count(self):
        text = "One two three four five"
        result = truncatewords(text, 5)
        assert result == "One two three four five"

    def test_custom_suffix(self):
        text = "This is a long piece of text"
        result = truncatewords(text, 3, " [more]")
        assert result == "This is a [more]"

    def test_empty_string(self):
        assert truncatewords("", 5) == ""

    def test_zero_count(self):
        text = "Some text here"
        result = truncatewords(text, 0)
        assert result == "..."


class TestSlugify:
    """Tests for slugify filter."""

    def test_basic_slug(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert slugify("Hello, World!") == "hello-world"

    def test_multiple_spaces(self):
        assert slugify("Hello    World") == "hello-world"

    def test_hyphens(self):
        assert slugify("Hello - World - Test") == "hello-world-test"

    def test_leading_trailing_spaces(self):
        assert slugify("  Hello World  ") == "hello-world"

    def test_numbers(self):
        assert slugify("Test 123") == "test-123"

    def test_underscores(self):
        assert slugify("hello_world") == "hello_world"

    def test_empty_string(self):
        assert slugify("") == ""

    def test_only_special_chars(self):
        assert slugify("!!!") == ""


class TestStripHtml:
    """Tests for strip_html filter."""

    def test_simple_tags(self):
        assert strip_html("<p>Hello</p>") == "Hello"

    def test_multiple_tags(self):
        html = "<div><p>Hello <strong>world</strong></p></div>"
        assert strip_html(html) == "Hello world"

    def test_no_tags(self):
        assert strip_html("Plain text") == "Plain text"

    def test_self_closing_tags(self):
        assert strip_html("Hello<br/>World") == "HelloWorld"

    def test_empty_string(self):
        assert strip_html("") == ""

    def test_html_entities(self):
        # Should decode entities
        result = strip_html("&lt;Hello&gt;")
        assert result == "<Hello>"


class TestTruncateChars:
    """Tests for truncate_chars filter."""

    def test_truncate_long_text(self):
        text = "This is a long text"
        result = truncate_chars(text, 10)
        # Total length should be exactly 10 (7 chars + "..." = 10)
        assert result == "This is..."
        assert len(result) == 10

    def test_no_truncate_short_text(self):
        text = "Short"
        result = truncate_chars(text, 10)
        assert result == "Short"

    def test_exact_length(self):
        text = "Exactly10!"
        result = truncate_chars(text, 10)
        assert result == "Exactly10!"

    def test_custom_suffix(self):
        text = "This is text"
        result = truncate_chars(text, 7, "…")
        # Total length should be exactly 7 (6 chars + "…" = 7)
        assert result == "This i…"
        assert len(result) == 7

    def test_empty_string(self):
        assert truncate_chars("", 10) == ""


class TestReplaceRegex:
    """Tests for replace_regex filter."""

    def test_simple_pattern(self):
        result = replace_regex("hello123world", r"\d+", "XXX")
        assert result == "helloXXXworld"

    def test_multiple_matches(self):
        result = replace_regex("a1b2c3", r"\d", "X")
        assert result == "aXbXcX"

    def test_no_match(self):
        result = replace_regex("hello", r"\d+", "XXX")
        assert result == "hello"

    def test_invalid_regex(self):
        # Should return original text on error
        result = replace_regex("hello", r"[", "XXX")
        assert result == "hello"

    def test_empty_string(self):
        assert replace_regex("", r"\d+", "X") == ""


class TestPluralize:
    """Tests for pluralize filter."""

    def test_singular(self):
        assert pluralize(1, "item") == "item"

    def test_plural_auto(self):
        assert pluralize(2, "item") == "items"

    def test_plural_custom(self):
        assert pluralize(2, "box", "boxes") == "boxes"

    def test_zero(self):
        assert pluralize(0, "item") == "items"

    def test_irregular(self):
        assert pluralize(3, "person", "people") == "people"


class TestReadingTime:
    """Tests for reading_time filter."""

    def test_short_text(self):
        text = " ".join(["word"] * 50)
        assert reading_time(text, wpm=200) == 1  # Minimum 1

    def test_medium_text(self):
        text = " ".join(["word"] * 600)
        assert reading_time(text, wpm=200) == 3

    def test_custom_wpm(self):
        text = " ".join(["word"] * 500)
        assert reading_time(text, wpm=250) == 2

    def test_empty_text(self):
        assert reading_time("") == 1

    def test_html_text(self):
        html = "<p>" + (" ".join(["word"] * 400)) + "</p>"
        # Should strip HTML and count words
        assert reading_time(html, wpm=200) == 2


class TestExcerpt:
    """Tests for excerpt filter."""

    def test_short_text(self):
        text = "Short text"
        assert excerpt(text, 100) == "Short text"

    def test_long_text_with_boundaries(self):
        text = "This is a long piece of text that needs to be excerpted properly"
        result = excerpt(text, 30)
        assert len(result) <= 33  # 30 + "..."
        assert result.endswith("...")
        assert not result.endswith(" ...")  # No space before ellipsis

    def test_long_text_without_boundaries(self):
        text = "This is a long piece of text"
        result = excerpt(text, 10, respect_word_boundaries=False)
        assert result == "This is a ..."

    def test_empty_text(self):
        assert excerpt("") == ""

    def test_html_text(self):
        html = "<p>This is a long piece of HTML text that should be excerpted</p>"
        result = excerpt(html, 20)
        # Should strip HTML
        assert "<p>" not in result


class TestStripWhitespace:
    """Tests for strip_whitespace filter."""

    def test_multiple_spaces(self):
        assert strip_whitespace("hello    world") == "hello world"

    def test_newlines(self):
        assert strip_whitespace("hello\n\nworld") == "hello world"

    def test_tabs(self):
        assert strip_whitespace("hello\t\tworld") == "hello world"

    def test_mixed_whitespace(self):
        assert strip_whitespace("  hello \n\t world  ") == "hello world"

    def test_empty_string(self):
        assert strip_whitespace("") == ""

    def test_already_clean(self):
        assert strip_whitespace("hello world") == "hello world"
