"""
Unit tests for template error reporting system.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import Environment, TemplateSyntaxError, UndefinedError
from jinja2.exceptions import TemplateAssertionError

from bengal.errors import BengalError, BengalRenderingError
from bengal.rendering.errors import (
    InclusionChain,
    TemplateErrorContext,
    TemplateRenderError,
    display_template_error,
)


class MockTemplateEngine:
    """Mock template engine for testing."""

    def __init__(self, template_dirs=None):
        self.template_dirs = template_dirs or [Path("/tmp/templates")]
        self.env = Environment()
        # Add some mock filters
        self.env.filters["markdown"] = lambda x: x
        self.env.filters["dateformat"] = lambda x, y: x
        self.env.filters["truncate"] = lambda x, y: x

    def _find_template_path(self, template_name):
        """Find template path (mock)."""
        for template_dir in self.template_dirs:
            template_path = template_dir / template_name
            if template_path.exists():
                return template_path
        return None


class TestTemplateErrorContext:
    """Tests for TemplateErrorContext."""

    def test_context_creation(self):
        """Test creating a template error context."""
        context = TemplateErrorContext(
            template_name="test.html",
            line_number=10,
            column=5,
            source_line="{{ page.title }}",
            surrounding_lines=[(9, "line 9"), (10, "line 10"), (11, "line 11")],
            template_path=Path("/tmp/test.html"),
        )

        assert context.template_name == "test.html"
        assert context.line_number == 10
        assert context.column == 5
        assert context.source_line == "{{ page.title }}"
        assert len(context.surrounding_lines) == 3
        assert context.template_path == Path("/tmp/test.html")


class TestInclusionChain:
    """Tests for InclusionChain."""

    def test_empty_chain(self):
        """Test empty inclusion chain."""
        chain = InclusionChain([])
        assert str(chain) == ""

    def test_single_entry(self):
        """Test inclusion chain with single entry."""
        chain = InclusionChain([("base.html", None)])
        assert "base.html" in str(chain)
        assert "└─" in str(chain)

    def test_multiple_entries(self):
        """Test inclusion chain with multiple entries."""
        chain = InclusionChain([("base.html", None), ("page.html", 20), ("partials/nav.html", 15)])

        chain_str = str(chain)
        assert "base.html" in chain_str
        assert "page.html:20" in chain_str
        assert "partials/nav.html:15" in chain_str
        assert "├─" in chain_str  # Not last
        assert "└─" in chain_str  # Last entry


class TestTemplateRenderError:
    """Tests for TemplateRenderError."""

    def test_error_classification_syntax(self):
        """Test classification of syntax errors."""
        error = TemplateSyntaxError("Unexpected end of template", 1)
        error_type = TemplateRenderError._classify_error(error)
        assert error_type == "syntax"

    def test_error_classification_filter(self):
        """Test classification of filter errors."""
        error = TemplateAssertionError("No filter named 'unknown_filter'", 1)
        error_type = TemplateRenderError._classify_error(error)
        assert error_type == "filter"

    def test_error_classification_undefined(self):
        """Test classification of undefined variable errors."""
        error = UndefinedError("'page' is undefined")
        error_type = TemplateRenderError._classify_error(error)
        assert error_type == "undefined"

    def test_from_jinja2_error_syntax(self):
        """Test creating rich error from Jinja2 syntax error."""
        # Create a Jinja2 syntax error
        try:
            env = Environment()
            env.parse("{% if test %}\n  content\n{# missing endif #}")
        except TemplateSyntaxError as e:
            mock_engine = MockTemplateEngine()
            rich_error = TemplateRenderError.from_jinja2_error(
                e, "test.html", Path("/tmp/content/page.md"), mock_engine
            )

            assert rich_error.error_type == "syntax"
            assert rich_error.message
            assert rich_error.template_context.template_name == "test.html"
            assert rich_error.page_source == Path("/tmp/content/page.md")

    def test_from_jinja2_error_filter(self):
        """Test creating rich error from unknown filter."""
        try:
            env = Environment()
            env.from_string("{{ value | unknown_filter }}")
        except TemplateAssertionError as e:
            mock_engine = MockTemplateEngine()
            rich_error = TemplateRenderError.from_jinja2_error(
                e, "test.html", Path("/tmp/content/page.md"), mock_engine
            )

            assert rich_error.error_type == "filter"
            assert "unknown_filter" in rich_error.message

    def test_suggestion_generation_filter(self):
        """Test generating suggestions for filter errors."""
        error = TemplateAssertionError("No filter named 'in_section'", 1)
        mock_engine = MockTemplateEngine()

        suggestion = TemplateRenderError._generate_suggestion(error, "filter", mock_engine)

        assert suggestion is not None
        assert "page.parent" in suggestion

    def test_find_alternatives_filter(self):
        """Test finding alternative filters."""
        error = TemplateAssertionError("No filter named 'markdwn'", 1)
        mock_engine = MockTemplateEngine()

        alternatives = TemplateRenderError._find_alternatives(error, "filter", mock_engine)

        # Should suggest 'markdown' as it's similar
        assert "markdown" in alternatives

    def test_find_alternatives_no_match(self):
        """Test finding alternatives when no close match."""
        error = TemplateAssertionError("No filter named 'xyz123'", 1)
        mock_engine = MockTemplateEngine()

        alternatives = TemplateRenderError._find_alternatives(error, "filter", mock_engine)

        # Should return empty or very poor matches
        assert len(alternatives) <= 3


class TestErrorDisplay:
    """Tests for error display function."""

    def test_display_template_error_basic(self, capsys):
        """Test basic error display."""
        error = TemplateRenderError(
            error_type="syntax",
            message="Test error message",
            template_context=TemplateErrorContext(
                template_name="test.html",
                line_number=10,
                column=None,
                source_line="{{ page.title }}",
                surrounding_lines=[],
                template_path=None,
            ),
            inclusion_chain=None,
            page_source=None,
            suggestion=None,
            available_alternatives=[],
        )

        # This should not raise an exception
        display_template_error(error, use_color=False)

        captured = capsys.readouterr()
        assert "Template Syntax Error" in captured.out
        assert "test.html" in captured.out
        assert "Test error message" in captured.out

    def test_display_with_suggestion(self, capsys):
        """Test error display with suggestion."""
        error = TemplateRenderError(
            error_type="filter",
            message="No filter named unknown_filter",
            template_context=TemplateErrorContext(
                template_name="test.html",
                line_number=10,
                column=None,
                source_line="",
                surrounding_lines=[],
                template_path=None,
            ),
            inclusion_chain=None,
            page_source=None,
            suggestion="Try using the markdown filter instead",
            available_alternatives=["markdown", "truncate"],
        )

        display_template_error(error, use_color=False)

        captured = capsys.readouterr()
        assert "Suggestion" in captured.out
        assert "Did you mean" in captured.out
        assert "markdown" in captured.out

    def test_template_render_error_extends_bengal_rendering_error(self) -> None:
        """Test that TemplateRenderError extends BengalRenderingError."""
        error = TemplateRenderError(
            error_type="syntax",
            message="Test error",
            template_context=TemplateErrorContext(
                template_name="test.html",
                line_number=10,
                column=None,
                source_line="",
                surrounding_lines=[],
                template_path=None,
            ),
            inclusion_chain=None,
            page_source=None,
            suggestion="Fix syntax",
            available_alternatives=[],
        )

        assert isinstance(error, Exception)
        assert isinstance(error, BengalRenderingError)
        assert isinstance(error, BengalError)

        # Can be raised and caught
        with pytest.raises(TemplateRenderError):
            raise error
        with pytest.raises(BengalRenderingError):
            raise error
        with pytest.raises(BengalError):
            raise error


class TestIntegration:
    """Integration tests for the error system."""

    def test_full_error_creation_workflow(self, tmp_path):
        """Test full workflow of creating and displaying an error."""
        # Create a template file with an error
        template_file = tmp_path / "broken.html"
        template_file.write_text("""
{% if condition %}
  <p>Content</p>
{# Missing endif #}
""")

        # Try to parse it
        try:
            env = Environment()
            with open(template_file) as f:
                env.parse(f.read(), str(template_file), str(template_file))
        except TemplateSyntaxError as e:
            # Create rich error
            mock_engine = MockTemplateEngine(template_dirs=[tmp_path])
            rich_error = TemplateRenderError.from_jinja2_error(
                e, "broken.html", tmp_path / "content" / "page.md", mock_engine
            )

            # Verify error properties
            assert rich_error.error_type == "syntax"
            # Template name may be full path or just filename
            assert rich_error.template_context.template_name.endswith("broken.html")
            assert rich_error.template_context.line_number is not None
            assert rich_error.page_source == tmp_path / "content" / "page.md"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
