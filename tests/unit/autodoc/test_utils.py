"""
Tests for autodoc utility functions.
"""

from textwrap import dedent

from bengal.autodoc.utils import sanitize_text, truncate_text


class TestSanitizeText:
    """Tests for text sanitization."""

    def test_sanitize_none(self):
        """Test sanitizing None returns empty string."""
        assert sanitize_text(None) == ""

    def test_sanitize_empty_string(self):
        """Test sanitizing empty string returns empty string."""
        assert sanitize_text("") == ""

    def test_sanitize_basic_text(self):
        """Test sanitizing basic text."""
        result = sanitize_text("Hello, world!")
        assert result == "Hello, world!"

    def test_sanitize_removes_indentation(self):
        """Test that indentation is removed (prevents markdown code blocks)."""
        text = dedent("""
            This is indented text.

            More indented content here.
        """)
        result = sanitize_text(text)

        # Should not start with spaces
        assert not result.startswith(" ")
        assert "This is indented text." in result

    def test_sanitize_strips_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        result = sanitize_text("  \n\n  Some text  \n\n  ")
        assert result == "Some text"

    def test_sanitize_normalizes_line_endings(self):
        """Test that Windows line endings are normalized."""
        result = sanitize_text("Line 1\r\nLine 2\r\nLine 3")
        assert "\r" not in result
        assert result == "Line 1\nLine 2\nLine 3"

    def test_sanitize_collapses_excessive_blank_lines(self):
        """Test that excessive blank lines are collapsed."""
        text = "Paragraph 1\n\n\n\n\nParagraph 2"
        result = sanitize_text(text)

        # Should have max 2 newlines (one blank line)
        assert "\n\n\n" not in result
        assert result == "Paragraph 1\n\nParagraph 2"

    def test_sanitize_docstring_example(self):
        """Test realistic docstring from Click command."""
        docstring = """
            Build the static site.

            Generates HTML files from your content, applies templates,
            processes assets, and outputs a production-ready site.
        """
        result = sanitize_text(docstring)

        # Should not have leading indentation
        assert not result.startswith(" ")
        assert result.startswith("Build the static site.")

        # Should preserve paragraph structure
        assert "\n\n" in result

    def test_sanitize_preserves_intentional_formatting(self):
        """Test that intentional formatting within text is preserved."""
        text = dedent("""
            # Heading

            Some text with `code` and **bold**.

            - Item 1
            - Item 2
        """)
        result = sanitize_text(text)

        assert "# Heading" in result
        assert "`code`" in result
        assert "**bold**" in result
        assert "- Item 1" in result


class TestTruncateText:
    """Tests for text truncation."""

    def test_truncate_short_text(self):
        """Test that short text is not truncated."""
        text = "Short text"
        result = truncate_text(text, max_length=100)
        assert result == "Short text"

    def test_truncate_long_text(self):
        """Test that long text is truncated."""
        text = "A" * 300
        result = truncate_text(text, max_length=200)

        assert len(result) <= 203  # 200 + '...'
        assert result.endswith("...")

    def test_truncate_at_word_boundary(self):
        """Test that truncation happens at word boundaries."""
        text = "The quick brown fox jumps over the lazy dog"
        result = truncate_text(text, max_length=20)

        # Should not break in middle of word
        assert not result.endswith("fox...")
        assert result.endswith("...")

        # Should have complete words
        words = result.replace("...", "").strip().split()
        for word in words:
            assert word in text.split()

    def test_truncate_custom_suffix(self):
        """Test truncation with custom suffix."""
        text = "A" * 300
        result = truncate_text(text, max_length=200, suffix=" [more]")

        assert result.endswith(" [more]")

    def test_truncate_exactly_max_length(self):
        """Test text exactly at max length."""
        text = "A" * 200
        result = truncate_text(text, max_length=200)

        # Should not truncate if exact length
        assert result == text

    def test_truncate_handles_no_spaces(self):
        """Test truncation when there are no spaces."""
        text = "A" * 300
        result = truncate_text(text, max_length=200)

        # Should truncate anyway even without word boundary
        assert len(result) <= 203


class TestIntegration:
    """Integration tests for utils."""

    def test_sanitize_then_truncate(self):
        """Test sanitizing and truncating together."""
        text = dedent("""
            This is a very long description that needs to be
            both sanitized (remove indentation) and truncated
            to fit within a summary field. It has multiple
            paragraphs and might be too long for a preview.

            This second paragraph should probably be cut off.
        """)

        sanitized = sanitize_text(text)
        truncated = truncate_text(sanitized, max_length=100)

        assert not truncated.startswith(" ")
        assert len(truncated) <= 103
        assert "This is a very long" in truncated
