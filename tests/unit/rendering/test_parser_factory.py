"""
Tests for ParserFactory - HTML parser selection and optional dependency handling.

These tests verify that:
1. Native parser works without any optional dependencies
2. BS4 parser requires beautifulsoup4 to be installed
3. LXML parser requires lxml to be installed
4. Parser factory falls back gracefully when dependencies are missing
"""

import builtins
import sys

import pytest

from bengal.rendering.parsers.factory import ParserBackend, ParserFactory


class TestParserFactoryWithoutOptionalDeps:
    """Test ParserFactory behavior when optional dependencies are not installed."""

    def test_native_parser_works_without_bs4(self, monkeypatch):
        """Test that native parser works even without bs4 installed."""
        # Simulate bs4 not being installed
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "bs4" or name.startswith("bs4."):
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        # Force reimport of factory module to trigger the ImportError
        if "bengal.rendering.parsers.factory" in sys.modules:
            monkeypatch.delitem(sys.modules, "bengal.rendering.parsers.factory")

        # This should work - native parser doesn't need bs4
        from bengal.rendering.parsers.factory import ParserFactory

        parser = ParserFactory.get_html_parser("native")
        assert parser is not None

        # Test parsing some HTML
        html_content = "<html><body><p>Test</p></body></html>"
        result = parser(html_content)
        assert result is not None

    def test_bs4_parser_raises_error_when_not_installed(self, monkeypatch):
        """Test that requesting bs4 parser explicitly raises clear error when not installed."""
        # Mock BS4_AVAILABLE to False
        from bengal.rendering.parsers import factory

        original_bs4_available = factory.BS4_AVAILABLE
        monkeypatch.setattr(factory, "BS4_AVAILABLE", False)

        with pytest.raises(
            ImportError, match="beautifulsoup4 is not installed.*pip install beautifulsoup4"
        ):
            ParserFactory.get_html_parser("bs4")

        # Restore
        monkeypatch.setattr(factory, "BS4_AVAILABLE", original_bs4_available)

    def test_default_parser_falls_back_to_native(self):
        """Test that default parser selection falls back to native."""
        # Don't specify a backend - should get native with warning
        parser = ParserFactory.get_html_parser(None)
        assert parser is not None

        # Should be able to parse HTML
        html_content = "<div>Test</div>"
        result = parser(html_content)
        assert result is not None


class TestParserFactoryWithBS4:
    """Test ParserFactory when beautifulsoup4 is available."""

    def test_bs4_parser_available(self):
        """Test that bs4 parser can be created when installed."""
        try:
            import bs4  # noqa: F401

            parser = ParserFactory.get_html_parser("bs4")
            assert parser is not None

            # Test parsing
            html_content = "<html><body><p>Test <strong>bold</strong></p></body></html>"
            result = parser(html_content)
            assert result is not None
            # BS4 should return a BeautifulSoup object
            assert hasattr(result, "find")  # BS4 soup has find method
        except ImportError:
            pytest.skip("beautifulsoup4 not installed")

    def test_bs4_parser_extracts_text(self):
        """Test that bs4 parser can extract text content."""
        try:
            import bs4  # noqa: F401

            parser = ParserFactory.get_html_parser("bs4")
            html_content = """
            <html>
                <body>
                    <p>Paragraph text</p>
                    <code>{{ page.title }}</code>
                </body>
            </html>
            """
            result = parser(html_content)
            text = result.get_text()
            assert "Paragraph text" in text
            assert "{{ page.title }}" in text
        except ImportError:
            pytest.skip("beautifulsoup4 not installed")


class TestParserFactoryWithLXML:
    """Test ParserFactory when lxml is available."""

    def test_lxml_parser_available(self):
        """Test that lxml parser can be created when installed."""
        try:
            import lxml.etree  # noqa: F401

            parser = ParserFactory.get_html_parser("lxml")
            assert parser is not None

            # Test parsing
            html_content = "<html><body><p>Test</p></body></html>"
            result = parser(html_content)
            assert result is not None
        except ImportError:
            pytest.skip("lxml not installed")


class TestParserFeatures:
    """Test parser feature metadata."""

    def test_bs4_features(self):
        """Test bs4 parser feature metadata."""
        features = ParserFactory.get_parser_features("bs4")
        assert features["tolerant"] is True
        assert features["speed"] == "medium"
        assert features["xpath"] is False

    def test_lxml_features(self):
        """Test lxml parser feature metadata."""
        features = ParserFactory.get_parser_features("lxml")
        assert features["tolerant"] is False
        assert features["speed"] == "fast"
        assert features["xpath"] is True

    def test_native_features(self):
        """Test native parser feature metadata."""
        features = ParserFactory.get_parser_features("native")
        assert features["tolerant"] is True
        assert features["speed"] == "slow"
        assert features["xpath"] is False

    def test_unknown_backend_returns_empty_dict(self):
        """Test that unknown backend returns empty feature dict."""
        features = ParserFactory.get_parser_features("unknown")
        assert features == {}


class TestNativeHTMLParser:
    """Test the native HTML parser fallback."""

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


class TestParserBackendConstants:
    """Test ParserBackend constants."""

    def test_backend_constants_defined(self):
        """Test that all backend constants are defined."""
        assert hasattr(ParserBackend, "BS4")
        assert hasattr(ParserBackend, "LXML")
        assert hasattr(ParserBackend, "NATIVE")

    def test_backend_constant_values(self):
        """Test that backend constants have expected values."""
        assert ParserBackend.BS4 == "bs4"
        assert ParserBackend.LXML == "lxml"
        assert ParserBackend.NATIVE == "native"
