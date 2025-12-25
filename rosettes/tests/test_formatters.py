"""Tests for Rosettes formatters."""

from rosettes import HighlightConfig, highlight, tokenize
from rosettes._config import FormatConfig
from rosettes.formatters import HtmlFormatter


class TestHtmlFormatter:
    """Tests for the HTML formatter."""

    def test_basic_output(self) -> None:
        """Generates basic HTML structure."""
        html = highlight("x = 1", "python")
        assert '<div class="highlight">' in html
        assert "<pre>" in html
        assert "<code>" in html
        assert "</code>" in html
        assert "</pre>" in html
        assert "</div>" in html

    def test_token_spans(self) -> None:
        """Generates spans for tokens with correct classes."""
        html = highlight("def foo():", "python")
        # 'def' should be keyword declaration
        assert '<span class="kd">def</span>' in html
        # 'foo' should be a name
        assert '<span class="n">foo</span>' in html

    def test_html_escaping(self) -> None:
        """Properly escapes HTML special characters."""
        html = highlight('x = "<>&\'"', "python")
        assert "&lt;" in html
        assert "&gt;" in html
        assert "&amp;" in html
        assert "&quot;" in html

    def test_custom_css_class(self) -> None:
        """Respects custom CSS class."""
        html = highlight("x = 1", "python", css_class="code-block")
        assert '<div class="code-block">' in html

    def test_line_highlighting(self) -> None:
        """Highlights specified lines."""
        code = "x = 1\ny = 2\nz = 3"
        html = highlight(code, "python", hl_lines={2})
        assert '<span class="hll">' in html

    def test_streaming_format(self) -> None:
        """format() yields string chunks."""
        tokens = iter(tokenize("x = 1", "python"))
        formatter = HtmlFormatter()
        chunks = list(formatter.format(tokens))
        assert len(chunks) > 1
        assert all(isinstance(c, str) for c in chunks)

    def test_no_wrap(self) -> None:
        """Can disable wrapping."""
        tokens = iter(tokenize("x = 1", "python"))
        formatter = HtmlFormatter()
        config = FormatConfig(wrap_code=False)
        html = "".join(formatter.format(tokens, config))
        assert "<div" not in html
        assert "<pre>" not in html

    def test_class_prefix(self) -> None:
        """Supports class prefix."""
        tokens = iter(tokenize("def foo():", "python"))
        formatter = HtmlFormatter()
        config = FormatConfig(class_prefix="hl-")
        html = "".join(formatter.format(tokens, config))
        assert '<span class="hl-kd">' in html

    def test_highlight_config(self) -> None:
        """HtmlFormatter respects HighlightConfig."""
        tokens = iter(tokenize("x = 1", "python"))
        config = HighlightConfig(css_class="custom", hl_line_class="highlighted")
        formatter = HtmlFormatter(config=config)
        # Just verify it runs without error
        html = formatter.format_string(tokens)
        assert isinstance(html, str)


class TestHighlightFunction:
    """Tests for the high-level highlight function."""

    def test_simple_code(self) -> None:
        """Highlights simple Python code."""
        html = highlight("print('hello')", "python")
        assert "highlight" in html
        assert "print" in html

    def test_multiline_code(self) -> None:
        """Handles multiline code correctly."""
        code = """
def greet(name):
    print(f"Hello, {name}!")

greet("world")
"""
        html = highlight(code, "python")
        assert "def" in html
        assert "greet" in html
        assert "print" in html

    def test_unknown_language(self) -> None:
        """Raises LookupError for unknown language."""
        import pytest

        with pytest.raises(LookupError):
            highlight("code", "nonexistent")
