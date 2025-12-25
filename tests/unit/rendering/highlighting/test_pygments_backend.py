"""
Tests for the PygmentsBackend implementation.

Validates that PygmentsBackend correctly wraps Pygments and
produces expected output.
"""

from __future__ import annotations

from bengal.rendering.highlighting.pygments import PygmentsBackend


class TestPygmentsBackendBasics:
    """Test basic PygmentsBackend functionality."""

    def test_name_property(self) -> None:
        """Backend name should be 'pygments'."""
        backend = PygmentsBackend()
        assert backend.name == "pygments"

    def test_supports_language_always_true(self) -> None:
        """Pygments supports nearly all languages via fallback."""
        backend = PygmentsBackend()

        # Common languages
        assert backend.supports_language("python")
        assert backend.supports_language("javascript")
        assert backend.supports_language("rust")

        # Unknown languages (fall back to text)
        assert backend.supports_language("unknown-lang")
        assert backend.supports_language("made-up-language")

    def test_highlight_produces_html(self) -> None:
        """highlight() should produce HTML with CSS classes."""
        backend = PygmentsBackend()
        result = backend.highlight("print('hello')", "python")

        assert isinstance(result, str)
        assert "<" in result  # Has HTML tags
        assert "class=" in result  # Has CSS classes
        assert "highlight" in result.lower()

    def test_highlight_escapes_html(self) -> None:
        """HTML in code should be escaped."""
        backend = PygmentsBackend()
        result = backend.highlight("<script>alert('xss')</script>", "html")

        # The script tag should be escaped or tokenized, not raw
        assert "<script>" not in result or "&lt;" in result


class TestPygmentsBackendLineNumbers:
    """Test line number functionality."""

    def test_show_linenos_false(self) -> None:
        """Line numbers should not appear when show_linenos=False."""
        backend = PygmentsBackend()
        code = "line1\nline2\nline3"
        result = backend.highlight(code, "python", show_linenos=False)

        # Should not have line number table structure
        assert "linenos" not in result.lower() or 'class="linenos"' not in result

    def test_show_linenos_true(self) -> None:
        """Line numbers should appear when show_linenos=True."""
        backend = PygmentsBackend()
        code = "line1\nline2\nline3"
        result = backend.highlight(code, "python", show_linenos=True)

        # Should have table structure for line numbers
        assert "table" in result.lower()


class TestPygmentsBackendLineHighlighting:
    """Test line highlighting functionality."""

    def test_hl_lines_none(self) -> None:
        """No highlighting when hl_lines is None."""
        backend = PygmentsBackend()
        result = backend.highlight("line1\nline2", "python", hl_lines=None)

        # Should not have .hll class
        assert "hll" not in result

    def test_hl_lines_empty_list(self) -> None:
        """No highlighting when hl_lines is empty list."""
        backend = PygmentsBackend()
        result = backend.highlight("line1\nline2", "python", hl_lines=[])

        # Should not have .hll class
        assert "hll" not in result

    def test_hl_lines_single_line(self) -> None:
        """Single line should be highlighted."""
        backend = PygmentsBackend()
        code = "line1\nline2\nline3"
        result = backend.highlight(code, "python", hl_lines=[2])

        # Should have .hll class for highlighted line
        assert "hll" in result

    def test_hl_lines_multiple(self) -> None:
        """Multiple lines should be highlighted."""
        backend = PygmentsBackend()
        code = "line1\nline2\nline3\nline4"
        result = backend.highlight(code, "python", hl_lines=[1, 3])

        # Should have .hll class
        assert "hll" in result

    def test_hl_lines_newline_fix(self) -> None:
        """The Pygments .hll newline fix should be applied."""
        backend = PygmentsBackend()
        code = "line1\nline2\nline3"
        result = backend.highlight(code, "python", hl_lines=[1, 2])

        # Should not have "\n</span>" pattern (the fix removes it)
        # The pattern is specifically for .hll spans
        assert "\n</span>" not in result or "hll" not in result


class TestPygmentsBackendLanguages:
    """Test language handling."""

    def test_python_highlighting(self) -> None:
        """Python code should be highlighted correctly."""
        backend = PygmentsBackend()
        result = backend.highlight("def hello(): pass", "python")

        # Should have keyword class for 'def'
        assert "class=" in result

    def test_unknown_language_fallback(self) -> None:
        """Unknown languages should fall back gracefully."""
        backend = PygmentsBackend()
        result = backend.highlight("some code here", "unknown-language-xyz")

        # Should still produce output without crashing
        assert isinstance(result, str)
        assert "some code here" in result

    def test_mermaid_not_highlighted(self) -> None:
        """Mermaid should be treated as plain text."""
        backend = PygmentsBackend()
        result = backend.highlight("graph TD\n  A --> B", "mermaid")

        # Should still produce output (falls back to text)
        assert isinstance(result, str)


class TestPygmentsBackendCombined:
    """Test combined features."""

    def test_linenos_with_hl_lines(self) -> None:
        """Line numbers and highlighting should work together."""
        backend = PygmentsBackend()
        code = "line1\nline2\nline3\nline4"
        result = backend.highlight(code, "python", hl_lines=[2, 3], show_linenos=True)

        # Should have both features
        assert "table" in result.lower()  # Line numbers
        assert "hll" in result  # Highlighting

    def test_fallback_on_error(self) -> None:
        """Errors should result in fallback rendering."""
        backend = PygmentsBackend()

        # Even with weird input, should not raise
        result = backend.highlight("", "python")
        assert isinstance(result, str)

        result = backend.highlight("code", "")
        assert isinstance(result, str)
