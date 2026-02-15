"""Tests for string template functions."""

from bengal.rendering.template_functions.strings import (
    base64_decode,
    base64_encode,
    card_excerpt,
    excerpt,
    excerpt_for_card,
    filesize,
    pluralize,
    reading_time,
    replace_regex,
    slugify,
    strip_html,
    strip_whitespace,
    truncate_chars,
    truncatewords,
    truncatewords_html,
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


class TestTruncatewordsHtml:
    """Tests for truncatewords_html filter - preserves HTML structure."""

    def test_preserves_simple_tags(self):
        html = "<p>Hello <strong>world</strong> how are you today</p>"
        result = truncatewords_html(html, 3)
        assert "<strong>" in result
        assert "</strong>" in result
        assert "</p>" in result

    def test_closes_unclosed_tags(self):
        html = "<div><p>One two three four five</p></div>"
        result = truncatewords_html(html, 3)
        assert result.count("<div>") == result.count("</div>")
        assert result.count("<p>") == result.count("</p>")

    def test_handles_void_elements(self):
        html = "<p>Hello<br>world<img src='x'>test</p>"
        result = truncatewords_html(html, 2)
        # br and img are void elements, should not try to close them
        assert "</br>" not in result
        assert "</img>" not in result

    def test_short_content_unchanged(self):
        html = "<p>Short</p>"
        result = truncatewords_html(html, 10)
        assert result == html

    def test_empty_input(self):
        assert truncatewords_html("", 5) == ""

    def test_nested_tags(self):
        html = "<div><ul><li>One</li><li>Two</li><li>Three</li></ul></div>"
        result = truncatewords_html(html, 2)
        # Should close all open tags
        assert result.count("<") == result.count(">")

    def test_adds_suffix(self):
        html = "<p>One two three four five</p>"
        result = truncatewords_html(html, 3)
        assert "..." in result

    def test_custom_suffix(self):
        html = "<p>One two three four five</p>"
        result = truncatewords_html(html, 3, " [more]")
        assert "[more]" in result

    def test_preserves_tag_attributes(self):
        html = '<p class="test">Hello <a href="/link">world</a> today</p>'
        result = truncatewords_html(html, 2)
        assert 'class="test"' in result

    def test_self_closing_tags(self):
        html = "<p>Hello<br/>world today</p>"
        result = truncatewords_html(html, 2)
        # Self-closing br should not cause issues
        assert "</br>" not in result


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


class TestExcerptForCard:
    """Tests for excerpt_for_card filter."""

    def test_strips_leading_title(self):
        content = "My Post Title. This is the actual excerpt content."
        result = excerpt_for_card(content, title="My Post Title")
        assert result == "This is the actual excerpt content."

    def test_strips_leading_title_case_insensitive(self):
        content = "my post title. This is the actual content."
        result = excerpt_for_card(content, title="My Post Title")
        assert result == "This is the actual content."

    def test_strips_title_then_description(self):
        content = "Title. Description text. Real content here."
        result = excerpt_for_card(content, title="Title", description="Description text")
        assert result == "Real content here."

    def test_no_strip_when_title_not_at_start(self):
        content = "This mentions Title in the middle."
        result = excerpt_for_card(content, title="Title")
        assert result == "This mentions Title in the middle."

    def test_strips_html_first(self):
        html = "<p>Title.</p><p>Real content here.</p>"
        result = excerpt_for_card(html, title="Title")
        assert "Title" not in result
        assert "Real content" in result

    def test_empty_content(self):
        assert excerpt_for_card("", title="Title") == ""
        assert excerpt_for_card("", title="", description="") == ""

    def test_empty_title_and_description(self):
        content = "Some content here."
        assert excerpt_for_card(content) == "Some content here."
        assert excerpt_for_card(content, title="", description="") == "Some content here."

    def test_autodoc_docstring_strips_element_name(self):
        """Autodoc: description often starts with element name."""
        content = "process_data converts input to output."
        result = excerpt_for_card(content, title="process_data")
        assert result == "converts input to output."

    def test_changelog_summary_strips_version(self):
        """Changelog: summary may start with version."""
        content = "0.1.8 - Bug fixes. Fixed crash on startup."
        result = excerpt_for_card(content, title="0.1.8")
        assert result == "Bug fixes. Fixed crash on startup."

    def test_tutorial_description_strips_title(self):
        """Tutorial: description from content may start with title."""
        content = "Getting Started. Learn the basics in 10 minutes."
        result = excerpt_for_card(content, title="Getting Started")
        assert result == "Learn the basics in 10 minutes."


class TestCardExcerpt:
    """Tests for card_excerpt filter."""

    def test_strips_title_and_truncates(self):
        content = "My Post. This is a long excerpt that should be truncated."
        result = card_excerpt(content, words=5, title="My Post")
        assert result == "This is a long excerpt..."

    def test_default_word_count(self):
        content = "Title. " + " ".join(["word"] * 50)
        result = card_excerpt(content, title="Title")
        assert result.endswith("...")
        assert len(result.split()) <= 31  # 30 words + suffix

    def test_empty_content(self):
        assert card_excerpt("") == ""
        assert card_excerpt("", words=10, title="Title") == ""

    def test_short_content_unchanged(self):
        content = "Title. Short."
        result = card_excerpt(content, words=10, title="Title")
        assert result == "Short."

    def test_custom_suffix(self):
        content = "Title. One two three four five six."
        result = card_excerpt(content, words=3, title="Title", suffix=" [more]")
        assert result == "One two three [more]"

    def test_changelog_summary_truncates(self):
        """Changelog: long summary truncated at 160 chars equivalent (words)."""
        content = "0.1.8. " + " ".join(["word"] * 50)
        result = card_excerpt(content, words=25, title="0.1.8")
        assert result.endswith("...")
        assert "0.1.8" not in result


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


class TestFilesize:
    """Tests for filesize filter."""

    def test_bytes(self):
        result = filesize(500)
        assert "B" in result

    def test_kilobytes(self):
        result = filesize(2048)  # 2 KB
        assert "KB" in result

    def test_megabytes(self):
        result = filesize(1536 * 1024)  # 1.5 MB
        assert "MB" in result

    def test_gigabytes(self):
        result = filesize(2 * 1024 * 1024 * 1024)  # 2 GB
        assert "GB" in result

    def test_zero_bytes(self):
        result = filesize(0)
        assert "0" in result


class TestBase64Encode:
    """Tests for base64_encode filter."""

    def test_simple_string(self):
        result = base64_encode("hello")
        assert result == "aGVsbG8="

    def test_with_spaces(self):
        result = base64_encode("hello world")
        assert result == "aGVsbG8gd29ybGQ="

    def test_unicode(self):
        result = base64_encode("héllo")
        assert result != ""  # Should encode unicode properly

    def test_empty_string(self):
        assert base64_encode("") == ""

    def test_none_input(self):
        assert base64_encode(None) == ""


class TestBase64Decode:
    """Tests for base64_decode filter."""

    def test_simple_string(self):
        result = base64_decode("aGVsbG8=")
        assert result == "hello"

    def test_with_spaces(self):
        result = base64_decode("aGVsbG8gd29ybGQ=")
        assert result == "hello world"

    def test_roundtrip(self):
        original = "Test string 123!"
        encoded = base64_encode(original)
        decoded = base64_decode(encoded)
        assert decoded == original

    def test_empty_string(self):
        assert base64_decode("") == ""

    def test_none_input(self):
        assert base64_decode(None) == ""

    def test_invalid_base64(self):
        # Should return empty string on invalid input
        result = base64_decode("not_valid_base64!!!")
        assert result == ""


class TestPlainify:
    """Tests for plainify filter (alias for strip_html)."""

    def test_plainify_is_strip_html(self):
        # The plainify filter is an alias for strip_html
        html = "<p>Hello <strong>world</strong></p>"
        assert strip_html(html) == "Hello world"
