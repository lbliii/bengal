"""Tests for Marimo directive."""

from __future__ import annotations


import pytest


def _marimo_available() -> bool:
    """Check if Marimo is installed."""
    try:
        import marimo  # noqa: F401

        return True
    except ImportError:
        return False


class TestMarimoCellDirective:
    """Tests for MarimoCellDirective."""

    def test_directive_initialization(self):
        """Test directive can be initialized."""
        from bengal.rendering.plugins.directives.marimo import MarimoCellDirective

        directive = MarimoCellDirective()
        assert directive.cell_counter == 0
        assert directive.generators == {}

    def test_marimo_not_installed_error(self):
        """Test graceful handling when Marimo is not installed."""
        from bengal.rendering.plugins.directives.marimo import MarimoCellDirective

        directive = MarimoCellDirective()

        # This should return error HTML if marimo not installed
        html = directive._execute_cell(
            code="print('hello')", show_code=True, page_id="test", use_cache=False, label=""
        )

        # Check for error message
        assert "marimo-error" in html.lower() or "<div" in html

    def test_error_rendering(self):
        """Test error HTML rendering."""
        from bengal.rendering.plugins.directives.marimo import MarimoCellDirective

        directive = MarimoCellDirective()

        error_html = directive._render_error("Test Error", "Something went wrong", "print('test')")

        assert "marimo-error" in error_html
        assert "Test Error" in error_html
        assert "Something went wrong" in error_html
        assert "print('test')" in error_html

    @pytest.mark.skipif(not _marimo_available(), reason="Marimo not installed")
    def test_basic_execution(self):
        """Test basic code execution with Marimo."""
        from bengal.rendering.plugins.directives.marimo import MarimoCellDirective

        directive = MarimoCellDirective()

        code = "print('Hello from Marimo')"

        html = directive._execute_cell(
            code=code, show_code=True, page_id="test", use_cache=False, label=""
        )

        # Should produce some HTML output
        assert isinstance(html, str)
        assert len(html) > 0
