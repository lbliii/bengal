"""
Unit tests for template validation system.

Tests the TemplateValidator class which delegates to template engine's validate() method.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from bengal.health.validators.templates import TemplateValidator, validate_templates


@dataclass
class MockTemplateError:
    """Mock template error returned by engine.validate()."""

    template: str
    message: str
    line: int | None = None
    error_type: str | None = "syntax"


class MockTemplateEngine:
    """Mock template engine for testing."""

    def __init__(
        self, template_dirs: list[Path] | None = None, errors: list[MockTemplateError] | None = None
    ):
        self.template_dirs = template_dirs or []
        self._errors = errors or []

    def validate(self) -> list[MockTemplateError]:
        """Return configured errors for testing."""
        return self._errors

    def get_template_path(self, template_name: str) -> Path | None:
        """Find template path."""
        for template_dir in self.template_dirs:
            template_path = template_dir / template_name
            if template_path.exists():
                return template_path
        return None


class TestTemplateValidator:
    """Tests for TemplateValidator."""

    def test_validator_initialization(self):
        """Test validator initialization."""
        mock_engine = MockTemplateEngine()
        validator = TemplateValidator(mock_engine)

        assert validator.template_engine == mock_engine

    def test_validate_all_no_errors(self):
        """Test validation with no errors."""
        mock_engine = MockTemplateEngine(errors=[])
        validator = TemplateValidator(mock_engine)

        errors = validator.validate_all()
        assert errors == []

    def test_validate_all_with_syntax_error(self, tmp_path):
        """Test validation with syntax error."""
        template_file = tmp_path / "invalid.html"
        template_file.write_text("{% if x %}missing endif")

        mock_engine = MockTemplateEngine(
            template_dirs=[tmp_path],
            errors=[
                MockTemplateError(
                    template="invalid.html",
                    message="Unexpected end of template. Missing endif.",
                    line=1,
                    error_type="syntax",
                )
            ],
        )
        validator = TemplateValidator(mock_engine)

        errors = validator.validate_all()
        assert len(errors) == 1
        assert errors[0].error_type == "syntax"
        assert "endif" in errors[0].message

    def test_validate_all_with_missing_include(self, tmp_path):
        """Test validation with missing include."""
        template_file = tmp_path / "page.html"
        template_file.write_text('{% include "nonexistent.html" %}')

        mock_engine = MockTemplateEngine(
            template_dirs=[tmp_path],
            errors=[
                MockTemplateError(
                    template="page.html",
                    message="Template 'nonexistent.html' not found",
                    line=1,
                    error_type="include",
                )
            ],
        )
        validator = TemplateValidator(mock_engine)

        errors = validator.validate_all()
        assert len(errors) == 1
        assert "nonexistent.html" in errors[0].message

    def test_validate_all_multiple_errors(self, tmp_path):
        """Test validation with multiple errors."""
        mock_engine = MockTemplateEngine(
            template_dirs=[tmp_path],
            errors=[
                MockTemplateError(template="a.html", message="Error in a", line=1),
                MockTemplateError(template="b.html", message="Error in b", line=2),
                MockTemplateError(template="c.html", message="Error in c", line=3),
            ],
        )
        validator = TemplateValidator(mock_engine)

        errors = validator.validate_all()
        assert len(errors) == 3

    def test_validate_all_returns_template_render_errors(self, tmp_path):
        """Test that validate_all returns TemplateRenderError objects."""
        from bengal.rendering.errors import TemplateRenderError

        mock_engine = MockTemplateEngine(
            template_dirs=[tmp_path],
            errors=[
                MockTemplateError(
                    template="test.html",
                    message="Test error",
                    line=5,
                    error_type="syntax",
                )
            ],
        )
        validator = TemplateValidator(mock_engine)

        errors = validator.validate_all()
        assert len(errors) == 1
        assert isinstance(errors[0], TemplateRenderError)
        assert errors[0].error_type == "syntax"
        assert errors[0].message == "Test error"
        assert errors[0].template_context.template_name == "test.html"
        assert errors[0].template_context.line_number == 5


class TestValidateTemplatesFunction:
    """Tests for validate_templates helper function."""

    def test_validate_templates_no_errors(self, tmp_path, capsys):
        """Test validate_templates with valid templates."""
        mock_engine = MockTemplateEngine(template_dirs=[tmp_path], errors=[])

        error_count = validate_templates(mock_engine)

        assert error_count == 0

        captured = capsys.readouterr()
        assert "Validating templates" in captured.out
        assert "All templates valid" in captured.out

    def test_validate_templates_with_errors(self, tmp_path, capsys):
        """Test validate_templates with invalid templates."""
        mock_engine = MockTemplateEngine(
            template_dirs=[tmp_path],
            errors=[
                MockTemplateError(
                    template="invalid.html",
                    message="Syntax error",
                    line=1,
                    error_type="syntax",
                )
            ],
        )

        error_count = validate_templates(mock_engine)

        assert error_count == 1

        captured = capsys.readouterr()
        assert "Validating templates" in captured.out
        assert "Found" in captured.out
        assert "error" in captured.out


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_error_list(self):
        """Test validation with empty error list."""
        mock_engine = MockTemplateEngine(errors=[])
        validator = TemplateValidator(mock_engine)

        errors = validator.validate_all()
        assert errors == []

    def test_error_without_line_number(self, tmp_path):
        """Test handling errors without line numbers."""
        mock_engine = MockTemplateEngine(
            template_dirs=[tmp_path],
            errors=[
                MockTemplateError(
                    template="test.html",
                    message="General error",
                    line=None,  # No line number
                    error_type="syntax",
                )
            ],
        )
        validator = TemplateValidator(mock_engine)

        errors = validator.validate_all()
        assert len(errors) == 1
        assert errors[0].template_context.line_number is None

    def test_error_without_error_type(self, tmp_path):
        """Test handling errors without explicit error type."""
        mock_engine = MockTemplateEngine(
            template_dirs=[tmp_path],
            errors=[
                MockTemplateError(
                    template="test.html",
                    message="Unknown error",
                    line=1,
                    error_type=None,  # No error type
                )
            ],
        )
        validator = TemplateValidator(mock_engine)

        errors = validator.validate_all()
        assert len(errors) == 1
        # Should default to "syntax"
        assert errors[0].error_type == "syntax"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
