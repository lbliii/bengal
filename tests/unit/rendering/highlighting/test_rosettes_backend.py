"""
Tests for the RosettesBackend implementation.

Validates that RosettesBackend correctly wraps the Rosettes
syntax highlighter and produces expected output.
"""

from __future__ import annotations

from bengal.rendering.highlighting.rosettes import RosettesBackend


class TestRosettesBackendBasics:
    """Test basic RosettesBackend functionality."""

    def test_name_property(self) -> None:
        """Backend name should be 'rosettes'."""
        backend = RosettesBackend()
        assert backend.name == "rosettes"

    def test_supports_language_known(self) -> None:
        """Rosettes supports common languages."""
        backend = RosettesBackend()

        # Common languages supported by Rosettes
        assert backend.supports_language("python")
        assert backend.supports_language("javascript")
        assert backend.supports_language("rust")
        assert backend.supports_language("go")
        assert backend.supports_language("typescript")

    def test_supports_language_unknown(self) -> None:
        """Unknown languages return False."""
        backend = RosettesBackend()

        # Unknown languages are not supported (fall back to plain text)
        assert not backend.supports_language("unknown-lang")
        assert not backend.supports_language("made-up-language")

    def test_highlight_produces_html(self) -> None:
        """highlight() should produce HTML with CSS classes."""
        backend = RosettesBackend()
        result = backend.highlight("print('hello')", "python")

        assert isinstance(result, str)
        assert "<" in result  # Has HTML tags
        assert "class=" in result  # Has CSS classes
        assert "highlight" in result

    def test_highlight_escapes_html(self) -> None:
        """HTML in code should be escaped."""
        backend = RosettesBackend()
        result = backend.highlight("<script>alert('xss')</script>", "html")

        # The script tag should be escaped or tokenized, not raw
        assert "<script>" not in result or "&lt;" in result


class TestRosettesBackendLineHighlighting:
    """Test line highlighting functionality."""

    def test_hl_lines_none(self) -> None:
        """No highlighting when hl_lines is None."""
        backend = RosettesBackend()
        result = backend.highlight("line1\nline2", "python", hl_lines=None)

        # Should not have .hll class
        assert "hll" not in result

    def test_hl_lines_empty_list(self) -> None:
        """No highlighting when hl_lines is empty list."""
        backend = RosettesBackend()
        result = backend.highlight("line1\nline2", "python", hl_lines=[])

        # Should not have .hll class
        assert "hll" not in result

    def test_hl_lines_single_line(self) -> None:
        """Single line should be highlighted."""
        backend = RosettesBackend()
        code = "line1\nline2\nline3"
        result = backend.highlight(code, "python", hl_lines=[2])

        # Should have .hll class for highlighted line
        assert "hll" in result

    def test_hl_lines_multiple(self) -> None:
        """Multiple lines should be highlighted."""
        backend = RosettesBackend()
        code = "line1\nline2\nline3\nline4"
        result = backend.highlight(code, "python", hl_lines=[1, 3])

        # Should have .hll class
        assert "hll" in result


class TestRosettesBackendLanguages:
    """Test language handling."""

    def test_python_highlighting(self) -> None:
        """Python code should be highlighted correctly."""
        backend = RosettesBackend()
        result = backend.highlight("def hello(): pass", "python")

        # Should have token classes
        assert "class=" in result
        # Should have highlight wrapper
        assert "highlight" in result

    def test_unknown_language_fallback(self) -> None:
        """Unknown languages should fall back to plain text."""
        backend = RosettesBackend()
        result = backend.highlight("some code here", "unknown-language-xyz")

        # Should produce output without crashing
        assert isinstance(result, str)
        assert "some code here" in result
        # Should have highlight wrapper with data-language
        assert 'data-language="unknown-language-xyz"' in result

    def test_language_aliases(self) -> None:
        """Common language aliases should work."""
        backend = RosettesBackend()

        # Python aliases
        assert backend.supports_language("py")

        # JavaScript aliases
        assert backend.supports_language("js")

        # TypeScript aliases
        assert backend.supports_language("ts")


class TestRosettesBackendCombined:
    """Test combined features."""

    def test_hl_lines_with_show_linenos(self) -> None:
        """Line highlighting should work with show_linenos."""
        backend = RosettesBackend()
        code = "line1\nline2\nline3\nline4"
        result = backend.highlight(code, "python", hl_lines=[2, 3], show_linenos=True)

        # Should have highlighting
        assert "hll" in result

    def test_empty_code(self) -> None:
        """Empty code should not raise errors."""
        backend = RosettesBackend()
        result = backend.highlight("", "python")
        assert isinstance(result, str)

    def test_whitespace_only_code(self) -> None:
        """Whitespace-only code should not raise errors."""
        backend = RosettesBackend()
        result = backend.highlight("   \n   ", "python")
        assert isinstance(result, str)
