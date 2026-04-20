"""
Unit tests for error display module.

Tests beautify_common_exception and display_bengal_error functions
with various edge cases and exception types.

See Also:
- bengal/errors/display.py
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.errors import BengalRenderingError, ErrorCode
from bengal.errors.display import (
    beautify_common_exception,
    display_bengal_error,
    display_template_render_error,
)


class TestBeautifyCommonException:
    """Tests for beautify_common_exception function."""

    # =========================================================================
    # FileNotFoundError
    # =========================================================================

    def test_file_not_found_with_filename(self) -> None:
        """FileNotFoundError with filename attribute shows the filename."""
        err = FileNotFoundError(2, "No such file", "config.yaml")
        result = beautify_common_exception(err)

        assert result is not None
        message, suggestion = result
        assert "config.yaml" in message
        assert suggestion is not None

    def test_file_not_found_without_filename(self) -> None:
        """FileNotFoundError without filename shows error message, not 'None'."""
        err = FileNotFoundError("File does not exist")
        result = beautify_common_exception(err)

        assert result is not None
        message, _ = result
        # Should NOT show "File not found: None"
        assert "None" not in message
        assert "File does not exist" in message

    def test_file_not_found_with_none_filename(self) -> None:
        """FileNotFoundError with explicit None filename handled gracefully."""
        err = FileNotFoundError(2, "No such file", None)
        result = beautify_common_exception(err)

        assert result is not None
        message, _ = result
        # Should show the errno message, not "None"
        assert "None" not in message or "No such file" in message

    # =========================================================================
    # PermissionError
    # =========================================================================

    def test_permission_error_with_filename(self) -> None:
        """PermissionError with filename shows the path."""
        err = PermissionError(13, "Permission denied", "/etc/passwd")
        result = beautify_common_exception(err)

        assert result is not None
        message, suggestion = result
        assert "/etc/passwd" in message
        assert "permission" in suggestion.lower()

    def test_permission_error_without_filename(self) -> None:
        """PermissionError without filename shows error message."""
        err = PermissionError("Access denied")
        result = beautify_common_exception(err)

        assert result is not None
        message, _ = result
        assert "Access denied" in message or "Permission denied" in message

    # =========================================================================
    # YAML Errors
    # =========================================================================

    def test_yaml_error_with_mark(self) -> None:
        """YAML error with problem_mark shows line and column."""
        pytest.importorskip("yaml")
        import yaml

        # Create YAML error with mark
        try:
            yaml.safe_load("key: [unclosed")
        except yaml.YAMLError as err:
            result = beautify_common_exception(err)
            assert result is not None
            message, suggestion = result
            assert "line" in message.lower() or "yaml" in message.lower()
            assert suggestion is not None

    def test_yaml_error_without_mark(self) -> None:
        """YAML error without mark still returns useful message."""
        pytest.importorskip("yaml")
        import yaml

        # YAMLError base class without mark
        err = yaml.YAMLError("Generic YAML error")
        result = beautify_common_exception(err)

        assert result is not None
        message, _ = result
        assert "yaml" in message.lower()

    # =========================================================================
    # JSON Errors
    # =========================================================================

    def test_json_decode_error(self) -> None:
        """JSON decode error shows line and column."""
        try:
            json.loads('{"key": invalid}')
        except json.JSONDecodeError as err:
            result = beautify_common_exception(err)
            assert result is not None
            message, suggestion = result
            assert "line" in message.lower()
            assert suggestion is not None

    # =========================================================================
    # Kida Template Errors
    # =========================================================================

    def test_kida_template_not_found(self) -> None:
        """Kida TemplateNotFoundError shows template name."""
        from kida import TemplateNotFoundError

        err = TemplateNotFoundError("missing_template.html")
        result = beautify_common_exception(err)

        assert result is not None
        message, suggestion = result
        assert "missing_template.html" in message
        assert "template" in suggestion.lower()

    def test_kida_undefined_error(self) -> None:
        """Kida UndefinedError shows variable info."""
        from kida import UndefinedError

        err = UndefinedError("page")
        result = beautify_common_exception(err)

        assert result is not None
        message, suggestion = result
        assert "undefined" in message.lower() or "page" in message
        assert suggestion is not None

    def test_kida_syntax_error(self) -> None:
        """Kida TemplateSyntaxError shows location."""
        from kida import TemplateSyntaxError

        err = TemplateSyntaxError("unexpected end of template", lineno=1, filename="test.html")
        result = beautify_common_exception(err)

        assert result is not None
        message, suggestion = result
        assert "syntax" in message.lower()
        assert suggestion is not None

    # =========================================================================
    # Encoding Errors
    # =========================================================================

    def test_unicode_decode_error(self) -> None:
        """UnicodeDecodeError shows encoding issue."""
        err = UnicodeDecodeError("utf-8", b"\xff\xfe", 0, 1, "invalid start byte")
        result = beautify_common_exception(err)

        assert result is not None
        message, suggestion = result
        assert "encoding" in message.lower()
        assert "utf-8" in suggestion.lower()

    # =========================================================================
    # Unknown Errors
    # =========================================================================

    def test_unknown_exception_returns_none(self) -> None:
        """Unknown exception types return None."""

        class CustomError(Exception):
            pass

        result = beautify_common_exception(CustomError("something"))
        assert result is None

    def test_standard_exception_returns_none(self) -> None:
        """Standard exceptions without special handling return None."""
        assert beautify_common_exception(ValueError("bad value")) is None
        assert beautify_common_exception(TypeError("wrong type")) is None
        assert beautify_common_exception(KeyError("missing")) is None


class TestDisplayBengalError:
    """Tests for display_bengal_error function."""

    def test_displays_error_code(self) -> None:
        """Error code is displayed in output."""
        error = BengalRenderingError(
            "Template not found",
            code=ErrorCode.R001,
        )

        mock_cli = MagicMock()
        mock_cli.icons = MagicMock()
        mock_cli.icons.error = "✖"
        mock_cli.use_rich = False

        display_bengal_error(error, mock_cli)

        # Check that error() was called with error code
        calls = mock_cli.error.call_args_list
        output = " ".join(str(call) for call in calls)
        assert "R001" in output

    def test_displays_file_path(self) -> None:
        """File path is displayed when available."""
        error = BengalRenderingError(
            "Template error",
            code=ErrorCode.R001,
            file_path=Path("content/post.md"),
            line_number=42,
        )

        mock_cli = MagicMock()
        mock_cli.icons = MagicMock()
        mock_cli.icons.error = "✖"
        mock_cli.use_rich = False

        display_bengal_error(error, mock_cli)

        calls = mock_cli.info.call_args_list
        output = " ".join(str(call) for call in calls)
        assert "content/post.md" in output
        assert "42" in output

    def test_displays_suggestion(self) -> None:
        """Suggestion is displayed when available."""
        error = BengalRenderingError(
            "Template error",
            suggestion="Check templates/ directory",
        )

        mock_cli = MagicMock()
        mock_cli.icons = MagicMock()
        mock_cli.icons.error = "✖"
        mock_cli.use_rich = False

        display_bengal_error(error, mock_cli)

        calls = mock_cli.info.call_args_list
        output = " ".join(str(call) for call in calls)
        assert "Check templates/" in output

    def test_handles_error_without_code(self) -> None:
        """Errors without code are displayed gracefully."""
        error = BengalRenderingError("Simple error")

        mock_cli = MagicMock()
        mock_cli.icons = MagicMock()
        mock_cli.icons.error = "✖"
        mock_cli.use_rich = False

        # Should not raise
        display_bengal_error(error, mock_cli)

        # Should still display the message
        calls = mock_cli.info.call_args_list
        output = " ".join(str(call) for call in calls)
        assert "Simple error" in output


class TestDisplayTemplateRenderError:
    """Tests for the canonical CLIOutput-aware template-error renderer (Sprint A2.2)."""

    def _make_error(
        self,
        *,
        error_type: str = "syntax",
        code: ErrorCode | None = ErrorCode.R002,
        suggestion: str | None = None,
        alternatives: list[str] | None = None,
    ):
        from bengal.rendering.errors import TemplateErrorContext, TemplateRenderError

        return TemplateRenderError(
            error_type=error_type,
            message="boom",
            template_context=TemplateErrorContext(
                template_name="page.html",
                line_number=3,
                column=None,
                source_line="{{ x }}",
                surrounding_lines=[(2, "before"), (3, "{{ x }}"), (4, "after")],
                template_path=Path("/tmp/page.html"),
            ),
            inclusion_chain=None,
            page_source=None,
            suggestion=suggestion,
            available_alternatives=alternatives or [],
            code=code,
        )

    def _capture(self, mock_cli: MagicMock) -> str:
        """Concatenate every cli.info / cli.error call into a flat string."""
        parts: list[str] = []
        for call in mock_cli.info.call_args_list:
            parts.extend(str(arg) for arg in call.args)
        for call in mock_cli.error.call_args_list:
            parts.extend(str(arg) for arg in call.args)
        return "\n".join(parts)

    def test_emits_error_code_prefix_in_header(self) -> None:
        """A2.2 acceptance: every rendered template error contains the [R0XX] prefix."""
        mock_cli = MagicMock()
        mock_cli.icons = MagicMock()

        display_template_render_error(self._make_error(), mock_cli)

        output = self._capture(mock_cli)
        assert "[R002]" in output
        assert "Template Syntax Error" in output

    def test_renders_code_window_with_caret(self) -> None:
        mock_cli = MagicMock()
        mock_cli.icons = MagicMock()

        display_template_render_error(self._make_error(), mock_cli)

        output = self._capture(mock_cli)
        assert "  Code:" in output
        # Error line should be marked with `>`.
        assert ">    3 |" in output
        # Caret underline appears under the offending line.
        assert "^" in output

    def test_includes_suggestion_and_alternatives(self) -> None:
        mock_cli = MagicMock()
        mock_cli.icons = MagicMock()

        err = self._make_error(
            error_type="filter",
            code=ErrorCode.R004,
            suggestion="Use `format_date` instead",
            alternatives=["format_date", "dateformat", "fmt_date"],
        )
        display_template_render_error(err, mock_cli)

        output = self._capture(mock_cli)
        assert "Suggestion: Use `format_date` instead" in output
        # Top match is promoted onto its own line.
        assert "Did you mean: 'format_date'?" in output
        # Remaining matches go on a secondary line, top excluded.
        assert "Other matches: 'dateformat', 'fmt_date'" in output

    def test_omits_other_matches_line_when_only_one_alternative(self) -> None:
        mock_cli = MagicMock()
        mock_cli.icons = MagicMock()

        err = self._make_error(
            error_type="filter",
            code=ErrorCode.R004,
            alternatives=["format_date"],
        )
        display_template_render_error(err, mock_cli)

        output = self._capture(mock_cli)
        assert "Did you mean: 'format_date'?" in output
        assert "Other matches" not in output

    def test_includes_docs_url_when_code_present(self) -> None:
        mock_cli = MagicMock()
        mock_cli.icons = MagicMock()

        display_template_render_error(self._make_error(), mock_cli)

        output = self._capture(mock_cli)
        assert "Docs: https://lbliii.github.io/bengal" in output

    def test_falls_back_when_code_missing(self) -> None:
        mock_cli = MagicMock()
        mock_cli.icons = MagicMock()

        err = self._make_error(code=None)
        display_template_render_error(err, mock_cli)

        output = self._capture(mock_cli)
        # No prefix, but header still emitted; no docs URL.
        assert "Template Syntax Error" in output
        assert "[R" not in output
        assert "Docs:" not in output
