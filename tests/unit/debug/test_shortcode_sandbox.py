"""
Unit tests for the ShortcodeSandbox module.

Tests the shortcode/directive sandbox functionality including validation,
rendering in isolation, typo detection, and batch testing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip(
    "bengal.debug.shortcode_sandbox",
    reason="ShortcodeSandbox module not yet implemented",
)

from bengal.debug.shortcode_sandbox import (
    RenderResult,
    ShortcodeSandbox,
    ValidationResult,
)


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self):
        """Test creating a valid result."""
        result = ValidationResult(
            content="```{note}\nTest\n```",
            valid=True,
            directive_name="note",
        )
        assert result.valid is True
        assert result.directive_name == "note"
        assert len(result.errors) == 0

    def test_invalid_result_with_errors(self):
        """Test creating an invalid result with errors."""
        result = ValidationResult(
            content="```{unknowndirective}\nTest\n```",
            valid=False,
            directive_name="unknowndirective",
            errors=["Unknown directive: unknowndirective"],
            suggestions=["Did you mean: note, tip, warning?"],
        )
        assert result.valid is False
        assert len(result.errors) == 1
        assert len(result.suggestions) == 1


class TestRenderResult:
    """Tests for RenderResult dataclass."""

    def test_successful_render(self):
        """Test creating a successful render result."""
        result = RenderResult(
            input_content="```{note}\nTest\n```",
            html="<div class='admonition note'>Test</div>",
            success=True,
            directive_name="note",
            parse_time_ms=1.5,
            render_time_ms=2.5,
        )
        assert result.success is True
        assert result.html != ""
        assert result.parse_time_ms == 1.5

    def test_failed_render(self):
        """Test creating a failed render result."""
        result = RenderResult(
            input_content="```{invalid",
            html="",
            success=False,
            errors=["Syntax error: unclosed directive"],
        )
        assert result.success is False
        assert len(result.errors) == 1

    def test_format_summary_success(self):
        """Test format_summary for successful render."""
        result = RenderResult(
            input_content="test",
            html="<p>test</p>",
            success=True,
            directive_name="note",
            parse_time_ms=1.0,
            render_time_ms=2.0,
        )
        summary = result.format_summary()
        assert "Success" in summary
        assert "note" in summary
        assert "1.00ms" in summary or "1.0" in summary

    def test_format_summary_failure(self):
        """Test format_summary for failed render."""
        result = RenderResult(
            input_content="test",
            html="",
            success=False,
            errors=["Test error"],
            warnings=["Test warning"],
        )
        summary = result.format_summary()
        assert "Failed" in summary
        assert "Test error" in summary
        assert "Test warning" in summary


class TestShortcodeSandbox:
    """Tests for ShortcodeSandbox class."""

    @pytest.fixture
    def sandbox(self):
        """Create a sandbox instance."""
        return ShortcodeSandbox()

    def test_create_default_context(self, sandbox):
        """Test that default context is created."""
        context = sandbox._mock_context
        assert "page" in context
        assert "site" in context
        assert context["page"]["title"] == "Test Page"
        assert context["site"]["title"] == "Test Site"

    def test_get_known_directives(self, sandbox):
        """Test getting known directive names."""
        directives = sandbox._get_known_directives()
        # Should have standard directives
        assert "note" in directives
        assert "tip" in directives
        assert "warning" in directives
        assert "tabs" in directives

    def test_validate_known_directive(self, sandbox):
        """Test validating a known directive."""
        content = "```{note}\nThis is a note.\n```"
        result = sandbox.validate(content)

        assert result.valid is True
        assert result.directive_name == "note"
        assert len(result.errors) == 0

    def test_validate_unknown_directive(self, sandbox):
        """Test validating an unknown directive."""
        content = "```{unknowndirective}\nContent\n```"
        result = sandbox.validate(content)

        assert result.valid is False
        assert result.directive_name == "unknowndirective"
        assert any("Unknown directive" in e for e in result.errors)

    def test_validate_missing_closing_fence(self, sandbox):
        """Test validating directive without closing fence."""
        content = "```{note}\nThis has no closing fence"
        result = sandbox.validate(content)

        assert result.valid is False
        assert any("closing fence" in e.lower() for e in result.errors)

    def test_validate_no_directive_pattern(self, sandbox):
        """Test validating content without directive pattern."""
        content = "Just regular markdown content"
        result = sandbox.validate(content)

        # Should be valid but with suggestions
        assert result.directive_name is None
        assert len(result.suggestions) > 0

    def test_find_similar_directives_typo(self, sandbox):
        """Test typo detection for directive names via utility function."""
        from bengal.debug.utils import find_similar_strings

        known = frozenset(["note", "tip", "warning", "tabs"])

        # Close typo should find similar
        similar = find_similar_strings("nots", known)
        assert "note" in similar

        similar = find_similar_strings("warningg", known)
        assert "warning" in similar

    def test_find_similar_directives_no_match(self, sandbox):
        """Test typo detection with no close matches via utility function."""
        from bengal.debug.utils import find_similar_strings

        known = frozenset(["note", "tip", "warning"])
        similar = find_similar_strings("xyzabc", known)
        assert len(similar) == 0

    def test_levenshtein_distance(self):
        """Test Levenshtein distance calculation via utility function."""
        from bengal.debug.utils import levenshtein_distance

        # Identical strings
        assert levenshtein_distance("abc", "abc") == 0

        # One character difference
        assert levenshtein_distance("abc", "abd") == 1
        assert levenshtein_distance("abc", "abcd") == 1

        # Two character difference
        assert levenshtein_distance("abc", "xyz") == 3

    def test_list_directives(self, sandbox):
        """Test listing available directives."""
        directives = sandbox.list_directives()

        assert len(directives) > 0

        # Each directive should have names and description
        for directive in directives:
            assert "names" in directive
            assert "description" in directive
            assert "class" in directive

    def test_get_directive_help_existing(self, sandbox):
        """Test getting help for existing directive."""
        help_text = sandbox.get_directive_help("note")
        assert help_text is not None
        assert len(help_text) > 0

    def test_get_directive_help_nonexistent(self, sandbox):
        """Test getting help for non-existent directive."""
        help_text = sandbox.get_directive_help("nonexistent_directive")
        assert help_text is None

    def test_run_with_content(self, sandbox):
        """Test run method with direct content."""
        content = "```{note}\nTest content\n```"
        report = sandbox.run(content=content)

        assert report.tool_name == "sandbox"
        # Should have at least one finding
        assert len(report.findings) > 0

    def test_run_validate_only(self, sandbox):
        """Test run method with validate_only flag."""
        from bengal.debug.base import Severity

        content = "```{note}\nTest content\n```"
        report = sandbox.run(content=content, validate_only=True)

        # Should have info finding about valid syntax
        info_findings = [f for f in report.findings if f.severity == Severity.INFO]
        assert len(info_findings) > 0

    def test_run_with_invalid_content(self, sandbox):
        """Test run method with invalid content."""
        from bengal.debug.base import Severity

        content = "```{unknowndirective}\nTest\n```"
        report = sandbox.run(content=content)

        # Should have error findings
        error_findings = [f for f in report.findings if f.severity == Severity.ERROR]
        assert len(error_findings) > 0

    def test_run_with_file_path(self, sandbox, tmp_path):
        """Test run method with file path."""
        file_path = tmp_path / "test.md"
        file_path.write_text("```{tip}\nA tip!\n```")

        report = sandbox.run(file_path=file_path)
        assert len(report.findings) > 0

    def test_run_with_nonexistent_file(self, sandbox):
        """Test run method with non-existent file."""
        from bengal.debug.base import Severity

        report = sandbox.run(file_path=Path("/nonexistent/file.md"))

        error_findings = [f for f in report.findings if f.severity == Severity.ERROR]
        assert len(error_findings) > 0
        assert any(
            "not found" in f.description.lower() or "not found" in f.title.lower()
            for f in error_findings
        )

    def test_run_with_no_content(self, sandbox):
        """Test run method with no content provided."""
        from bengal.debug.base import Severity

        report = sandbox.run()

        warning_findings = [f for f in report.findings if f.severity == Severity.WARNING]
        assert len(warning_findings) > 0

    def test_batch_test(self, sandbox):
        """Test batch testing multiple shortcodes."""
        test_cases = [
            {"content": "```{note}\nNote 1\n```"},
            {"content": "```{tip}\nTip here\n```"},
            {"content": "```{warning}\nWarning!\n```"},
        ]

        results = sandbox.batch_test(test_cases)

        assert len(results) == 3
        # All should be RenderResult objects
        for result in results:
            assert isinstance(result, RenderResult)

    def test_batch_test_with_expected(self, sandbox):
        """Test batch testing with expected output."""
        test_cases = [
            {
                "content": "```{note}\nTest note\n```",
                "expected": "admonition",  # Should contain this class
            },
        ]

        results = sandbox.batch_test(test_cases)

        assert len(results) == 1


class TestShortcodeSandboxRendering:
    """Tests for actual rendering functionality."""

    @pytest.fixture
    def sandbox(self):
        """Create a sandbox instance."""
        return ShortcodeSandbox()

    def test_render_note_directive(self, sandbox):
        """Test rendering a note directive."""
        content = "```{note}\nThis is a note.\n```"
        result = sandbox.render(content)

        assert result.success is True
        assert result.directive_name == "note"
        assert "admonition" in result.html.lower() or "note" in result.html.lower()

    def test_render_tip_directive(self, sandbox):
        """Test rendering a tip directive."""
        content = "```{tip}\nThis is a tip.\n```"
        result = sandbox.render(content)

        assert result.success is True
        assert result.directive_name == "tip"

    def test_render_warning_directive(self, sandbox):
        """Test rendering a warning directive."""
        content = "```{warning}\nThis is a warning.\n```"
        result = sandbox.render(content)

        assert result.success is True
        assert result.directive_name == "warning"

    def test_render_with_timing(self, sandbox):
        """Test that render timing is captured."""
        content = "```{note}\nTest\n```"
        result = sandbox.render(content)

        assert result.parse_time_ms >= 0
        assert result.render_time_ms >= 0

    def test_render_invalid_syntax(self, sandbox):
        """Test rendering with invalid syntax."""
        content = "```{unknowndirective}\nTest\n```"
        result = sandbox.render(content)

        assert result.success is False
        assert len(result.errors) > 0


class TestShortcodeSandboxCustomContext:
    """Tests for sandbox with custom context."""

    def test_custom_mock_context(self):
        """Test creating sandbox with custom context."""
        custom_context = {
            "page": {
                "title": "Custom Page",
                "metadata": {"author": "Test Author"},
            },
            "site": {
                "title": "Custom Site",
            },
        }

        sandbox = ShortcodeSandbox(mock_context=custom_context)
        assert sandbox._mock_context["page"]["title"] == "Custom Page"
        assert sandbox._mock_context["site"]["title"] == "Custom Site"
