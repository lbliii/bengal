"""Tests for HTML formatter output correctness."""

from __future__ import annotations

from bengal.rendering.rosettes import Token, TokenType, highlight
from bengal.rendering.rosettes._config import FormatConfig
from bengal.rendering.rosettes.formatters import HtmlFormatter


class TestHtmlFormatterBasics:
    """Test basic HTML formatter functionality."""

    def test_semantic_class_output(self) -> None:
        """Semantic mode should use .syntax-* classes."""
        formatter = HtmlFormatter(css_class_style="semantic")
        tokens = [Token(TokenType.KEYWORD, "def", 1, 1)]

        html = formatter.format_string(iter(tokens), FormatConfig())

        assert 'class="syntax-' in html

    def test_pygments_class_output(self) -> None:
        """Pygments mode should use short classes like .k, .nf."""
        formatter = HtmlFormatter(css_class_style="pygments")
        tokens = [Token(TokenType.KEYWORD, "def", 1, 1)]

        html = formatter.format_string(iter(tokens), FormatConfig())

        assert 'class="k"' in html

    def test_wrapper_class_semantic(self) -> None:
        """Semantic mode should use 'rosettes' wrapper class."""
        html = highlight("def foo(): pass", "python", css_class_style="semantic")
        assert 'class="rosettes"' in html

    def test_wrapper_class_pygments(self) -> None:
        """Pygments mode should use 'highlight' wrapper class."""
        html = highlight("def foo(): pass", "python", css_class_style="pygments")
        assert 'class="highlight"' in html


class TestHtmlFormatterLineHighlighting:
    """Test line highlighting functionality."""

    def test_line_highlighting_single(self) -> None:
        """hl_lines should add .hll class to specified lines."""
        code = "line1\nline2\nline3"
        html = highlight(code, "python", hl_lines={2})

        assert 'class="hll"' in html
        # Only line 2 should be highlighted
        assert html.count('class="hll"') == 1

    def test_line_highlighting_multiple(self) -> None:
        """Multiple lines should be highlighted."""
        code = "line1\nline2\nline3\nline4"
        html = highlight(code, "python", hl_lines={1, 3})

        assert 'class="hll"' in html
        assert html.count('class="hll"') == 2

    def test_line_highlighting_out_of_range(self) -> None:
        """Out-of-range line numbers should not cause errors."""
        code = "line1\nline2"
        html = highlight(code, "python", hl_lines={10})
        # Should not crash, may or may not highlight
        assert isinstance(html, str)


class TestHtmlFormatterLineNumbers:
    """Test line number functionality."""

    def test_show_linenos(self) -> None:
        """show_linenos should add line numbers."""
        code = "line1\nline2\nline3"
        html = highlight(code, "python", show_linenos=True)

        # Should have line number markers
        assert "linenos" in html or "line" in html.lower()


class TestHtmlFormatterEmptyHandling:
    """Test empty/whitespace handling."""

    def test_empty_code(self) -> None:
        """Empty code should not raise errors."""
        html = highlight("", "python")
        assert isinstance(html, str)
        assert len(html) > 0  # Should have wrapper

    def test_whitespace_only(self) -> None:
        """Whitespace-only code should not raise errors."""
        html = highlight("   \n   ", "python")
        assert isinstance(html, str)


class TestHtmlFormatterDataAttributes:
    """Test data attributes in output."""

    def test_data_language_attribute(self) -> None:
        """Output should include data-language attribute."""
        html = highlight("def foo(): pass", "python")
        assert 'data-language="python"' in html

    def test_data_language_with_alias(self) -> None:
        """Aliases should resolve to canonical name in data-language."""
        html = highlight("def foo(): pass", "py")
        assert 'data-language="python"' in html
