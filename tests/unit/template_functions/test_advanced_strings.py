"""Tests for advanced string template functions."""

from bengal.rendering.template_functions.advanced_strings import (
    camelize,
    contains,
    has_prefix,
    has_suffix,
    indent_text,
    regex_findall,
    regex_search,
    titleize,
    to_sentence,
    trim_prefix,
    trim_suffix,
    underscore,
    wrap_text,
)


class TestCamelize:
    """Tests for camelize filter."""

    def test_snake_case(self):
        assert camelize("hello_world") == "helloWorld"

    def test_kebab_case(self):
        assert camelize("hello-world") == "helloWorld"

    def test_spaces(self):
        assert camelize("hello world") == "helloWorld"

    def test_multiple_words(self):
        assert camelize("hello_world_test") == "helloWorldTest"

    def test_already_camel(self):
        assert camelize("helloWorld") == "helloworld"

    def test_empty_string(self):
        assert camelize("") == ""


class TestUnderscore:
    """Tests for underscore filter."""

    def test_camel_case(self):
        assert underscore("helloWorld") == "hello_world"

    def test_pascal_case(self):
        assert underscore("HelloWorld") == "hello_world"

    def test_kebab_case(self):
        assert underscore("hello-world") == "hello_world"

    def test_multiple_capitals(self):
        assert underscore("HTTPSConnection") == "https_connection"

    def test_already_snake(self):
        assert underscore("hello_world") == "hello_world"

    def test_empty_string(self):
        assert underscore("") == ""


class TestTitleize:
    """Tests for titleize filter."""

    def test_basic_title(self):
        result = titleize("hello world")
        assert result == "Hello World"

    def test_with_articles(self):
        result = titleize("the lord of the rings")
        assert result == "The Lord of the Rings"

    def test_with_and(self):
        result = titleize("harry and sally")
        assert result == "Harry and Sally"

    def test_last_word_capitalized(self):
        result = titleize("fight club the")
        assert result == "Fight Club The"  # Last word is capitalized

    def test_empty_string(self):
        assert titleize("") == ""


class TestWrapText:
    """Tests for wrap_text filter."""

    def test_wrap_long_text(self):
        text = "This is a very long piece of text that should be wrapped at the specified width"
        result = wrap_text(text, width=30)
        lines = result.split("\n")
        assert all(len(line) <= 30 for line in lines)

    def test_no_wrap_needed(self):
        text = "Short text"
        result = wrap_text(text, width=80)
        assert result == text

    def test_empty_string(self):
        assert wrap_text("") == ""

    def test_zero_width(self):
        text = "Some text"
        result = wrap_text(text, width=0)
        assert result == text


class TestIndentText:
    """Tests for indent_text filter."""

    def test_indent_single_line(self):
        result = indent_text("Hello", spaces=4)
        assert result == "    Hello"

    def test_indent_multiple_lines(self):
        text = "Line 1\nLine 2"
        result = indent_text(text, spaces=2)
        assert result == "  Line 1\n  Line 2"

    def test_indent_skip_first_line(self):
        text = "Line 1\nLine 2"
        result = indent_text(text, spaces=2, first_line=False)
        assert result == "Line 1\n  Line 2"

    def test_empty_string(self):
        assert indent_text("") == ""


class TestRegexSearch:
    """Tests for regex_search filter."""

    def test_simple_match(self):
        result = regex_search("Price: $99.99", r"\$[\d.]+")
        assert result == "$99.99"

    def test_capture_group(self):
        result = regex_search("v2.3.1", r"v(\d+)", group=1)
        assert result == "2"

    def test_no_match(self):
        result = regex_search("Hello World", r"\d+")
        assert result is None

    def test_empty_string(self):
        result = regex_search("", r"\d+")
        assert result is None

    def test_none_input(self):
        result = regex_search(None, r"\d+")
        assert result is None

    def test_invalid_group(self):
        # Should fall back to full match when group doesn't exist
        result = regex_search("test123", r"\d+", group=5)
        assert result == "123"

    def test_invalid_pattern(self):
        result = regex_search("test", r"[")
        assert result is None


class TestRegexFindall:
    """Tests for regex_findall filter."""

    def test_multiple_matches(self):
        result = regex_findall("a1 b2 c3", r"\d+")
        assert result == ["1", "2", "3"]

    def test_single_match(self):
        result = regex_findall("test123", r"\d+")
        assert result == ["123"]

    def test_no_matches(self):
        result = regex_findall("Hello World", r"\d+")
        assert result == []

    def test_empty_string(self):
        result = regex_findall("", r"\d+")
        assert result == []

    def test_none_input(self):
        result = regex_findall(None, r"\d+")
        assert result == []

    def test_invalid_pattern(self):
        result = regex_findall("test", r"[")
        assert result == []

    def test_email_pattern(self):
        text = "Contact alice@example.com or bob@test.org"
        result = regex_findall(text, r"\b\w+@\w+\.\w+\b")
        assert "alice@example.com" in result
        assert "bob@test.org" in result


class TestTrimPrefix:
    """Tests for trim_prefix filter."""

    def test_remove_prefix(self):
        assert trim_prefix("hello_world", "hello_") == "world"

    def test_no_prefix(self):
        assert trim_prefix("test", "hello_") == "test"

    def test_empty_string(self):
        assert trim_prefix("", "hello_") == ""

    def test_none_input(self):
        assert trim_prefix(None, "hello_") == ""

    def test_empty_prefix(self):
        assert trim_prefix("test", "") == "test"


class TestTrimSuffix:
    """Tests for trim_suffix filter."""

    def test_remove_suffix(self):
        assert trim_suffix("file.txt", ".txt") == "file"

    def test_no_suffix(self):
        assert trim_suffix("test", ".txt") == "test"

    def test_empty_string(self):
        assert trim_suffix("", ".txt") == ""

    def test_none_input(self):
        assert trim_suffix(None, ".txt") == ""

    def test_empty_suffix(self):
        assert trim_suffix("test", "") == "test"


class TestHasPrefix:
    """Tests for has_prefix filter."""

    def test_has_prefix_true(self):
        assert has_prefix("https://example.com", "https://") is True

    def test_has_prefix_false(self):
        assert has_prefix("http://example.com", "https://") is False

    def test_empty_string(self):
        assert has_prefix("", "https://") is False

    def test_none_input(self):
        assert has_prefix(None, "https://") is False


class TestHasSuffix:
    """Tests for has_suffix filter."""

    def test_has_suffix_true(self):
        assert has_suffix("file.md", ".md") is True

    def test_has_suffix_false(self):
        assert has_suffix("file.txt", ".md") is False

    def test_empty_string(self):
        assert has_suffix("", ".md") is False

    def test_none_input(self):
        assert has_suffix(None, ".md") is False


class TestContains:
    """Tests for contains filter."""

    def test_contains_true(self):
        assert contains("Hello World", "World") is True

    def test_contains_false(self):
        assert contains("Hello World", "Python") is False

    def test_case_sensitive(self):
        assert contains("Hello World", "world") is False

    def test_empty_string(self):
        assert contains("", "test") is False

    def test_none_input(self):
        assert contains(None, "test") is False

    def test_empty_substring(self):
        assert contains("test", "") is True


class TestToSentence:
    """Tests for to_sentence filter."""

    def test_three_items(self):
        result = to_sentence(["Alice", "Bob", "Charlie"])
        assert result == "Alice, Bob, and Charlie"

    def test_two_items(self):
        result = to_sentence(["Alice", "Bob"])
        assert result == "Alice and Bob"

    def test_one_item(self):
        result = to_sentence(["Alice"])
        assert result == "Alice"

    def test_empty_list(self):
        result = to_sentence([])
        assert result == ""

    def test_none_input(self):
        result = to_sentence(None)
        assert result == ""

    def test_custom_connector(self):
        result = to_sentence(["A", "B", "C"], connector="or")
        assert result == "A, B, or C"

    def test_no_oxford_comma(self):
        result = to_sentence(["A", "B", "C"], oxford=False)
        assert result == "A, B and C"

    def test_no_oxford_with_or(self):
        result = to_sentence(["A", "B", "C"], connector="or", oxford=False)
        assert result == "A, B or C"

    def test_integer_items(self):
        result = to_sentence([1, 2, 3])
        assert result == "1, 2, and 3"

    def test_four_items(self):
        result = to_sentence(["A", "B", "C", "D"])
        assert result == "A, B, C, and D"
