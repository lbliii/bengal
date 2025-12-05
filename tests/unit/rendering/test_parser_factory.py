"""
Tests for ParserFactory - HTML parser for build-time validation.

These tests verify that:
1. ParserFactory returns working native parser
2. Native parser correctly extracts text from HTML
3. Native parser excludes code/script/style blocks
4. Parser handles malformed HTML gracefully
"""

from __future__ import annotations


from bengal.rendering.parsers.factory import ParserBackend, ParserFactory


class TestParserFactory:
    """Test ParserFactory behavior."""

    def test_default_parser_returns_native(self):
        """Test that default parser returns native parser."""
        parser = ParserFactory.get_html_parser()
        assert parser is not None

        # Should be able to parse HTML
        html_content = "<div>Test</div>"
        result = parser(html_content)
        assert result is not None
        assert hasattr(result, "get_text")

    def test_explicit_native_backend(self):
        """Test explicitly requesting native backend."""
        parser = ParserFactory.get_html_parser("native")
        assert parser is not None

        html_content = "<p>Test paragraph</p>"
        result = parser(html_content)
        assert result is not None

    def test_unsupported_backend_falls_back_to_native(self):
        """Test that unsupported backends fall back to native."""
        # Should not raise error, just return native parser
        parser = ParserFactory.get_html_parser("unsupported")
        assert parser is not None

        # Verify it works
        html_content = "<p>Test</p>"
        result = parser(html_content)
        assert result is not None
        assert "Test" in result.get_text()


class TestNativeHTMLParser:
    """Test the native HTML parser functionality."""

    def test_native_parser_basic_html(self):
        """Test native parser with basic HTML."""
        parser = ParserFactory.get_html_parser("native")
        html_content = "<html><body><p>Test paragraph</p></body></html>"
        result = parser(html_content)

        # Native parser returns the parser instance
        assert hasattr(result, "get_text")
        text = result.get_text()
        assert "Test paragraph" in text

    def test_native_parser_strips_code_blocks(self):
        """Test that native parser strips code blocks from text."""
        parser = ParserFactory.get_html_parser("native")
        html_content = """
        <html>
            <body>
                <p>Normal text</p>
                <code>{{ page.title }}</code>
                <p>More text</p>
            </body>
        </html>
        """
        result = parser(html_content)
        text = result.get_text()

        assert "Normal text" in text
        assert "More text" in text
        # Code block content should be stripped
        assert "{{ page.title }}" not in text

    def test_native_parser_strips_pre_blocks(self):
        """Test that native parser strips pre blocks."""
        parser = ParserFactory.get_html_parser("native")
        html_content = """
        <html>
            <body>
                <p>Visible</p>
                <pre>{{ hidden }}</pre>
                <p>Also visible</p>
            </body>
        </html>
        """
        result = parser(html_content)
        text = result.get_text()

        assert "Visible" in text
        assert "Also visible" in text
        assert "{{ hidden }}" not in text

    def test_native_parser_strips_script_tags(self):
        """Test that native parser strips script tags."""
        parser = ParserFactory.get_html_parser("native")
        html_content = """
        <html>
            <body>
                <p>Visible text</p>
                <script>console.log("hidden");</script>
            </body>
        </html>
        """
        result = parser(html_content)
        text = result.get_text()

        assert "Visible text" in text
        assert "console.log" not in text

    def test_native_parser_strips_style_tags(self):
        """Test that native parser strips style tags."""
        parser = ParserFactory.get_html_parser("native")
        html_content = """
        <html>
            <head><style>body { color: red; }</style></head>
            <body><p>Text</p></body>
        </html>
        """
        result = parser(html_content)
        text = result.get_text()

        assert "Text" in text
        assert "color: red" not in text

    def test_native_parser_handles_malformed_html(self):
        """Test that native parser handles malformed HTML gracefully."""
        parser = ParserFactory.get_html_parser("native")

        # Unclosed tags
        html_content = "<p>Unclosed paragraph<div>Other content"
        result = parser(html_content)

        # Should not raise error
        assert result is not None
        text = result.get_text()
        assert "Unclosed paragraph" in text

    def test_native_parser_normalizes_whitespace(self):
        """Test that native parser normalizes whitespace in extracted text."""
        parser = ParserFactory.get_html_parser("native")
        html_content = """
        <p>Multiple    spaces</p>
        <p>
            Newlines
            and
            spaces
        </p>
        """
        result = parser(html_content)
        text = result.get_text()

        # Should normalize multiple spaces to single space
        assert "Multiple spaces" in text
        assert "    " not in text  # No multiple spaces


class TestParserFeatures:
    """Test parser feature metadata."""

    def test_native_features(self):
        """Test native parser feature metadata."""
        features = ParserFactory.get_parser_features("native")
        assert features["tolerant"] is True
        assert features["speed"] == "fast"
        assert features["xpath"] is False
        assert features["dependencies"] is None

    def test_unknown_backend_returns_empty_dict(self):
        """Test that unknown backend returns empty feature dict."""
        features = ParserFactory.get_parser_features("unknown")
        assert features == {}


class TestParserBackendConstants:
    """Test ParserBackend constants."""

    def test_backend_constants_defined(self):
        """Test that NATIVE constant is defined."""
        assert hasattr(ParserBackend, "NATIVE")

    def test_backend_constant_values(self):
        """Test that backend constant has expected value."""
        assert ParserBackend.NATIVE == "native"
