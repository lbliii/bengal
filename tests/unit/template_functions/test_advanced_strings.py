"""Tests for advanced string template functions."""

from bengal.rendering.template_functions.advanced_strings import (
    camelize,
    indent_text,
    titleize,
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
