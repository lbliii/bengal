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
from bengal.errors.display import beautify_common_exception, display_bengal_error


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
    # Jinja2 Errors
    # =========================================================================

    def test_jinja2_template_not_found(self) -> None:
        """Jinja2 TemplateNotFound shows template name."""
        jinja2 = pytest.importorskip("jinja2")

        err = jinja2.TemplateNotFound("missing_template.html")
        result = beautify_common_exception(err)

        assert result is not None
        message, suggestion = result
        assert "missing_template.html" in message
        assert "template" in suggestion.lower()

    def test_jinja2_undefined_error(self) -> None:
        """Jinja2 UndefinedError shows variable info."""
        jinja2 = pytest.importorskip("jinja2")

        err = jinja2.UndefinedError("'page' is undefined")
        result = beautify_common_exception(err)

        assert result is not None
        message, suggestion = result
        assert "undefined" in message.lower() or "page" in message
        assert suggestion is not None

    def test_jinja2_syntax_error(self) -> None:
        """Jinja2 TemplateSyntaxError shows location."""
        jinja2 = pytest.importorskip("jinja2")

        try:
            jinja2.Template("{% if unclosed")
        except jinja2.TemplateSyntaxError as err:
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

        # Check that console.print was called with error code
        calls = mock_cli.console.print.call_args_list
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

        calls = mock_cli.console.print.call_args_list
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

        calls = mock_cli.console.print.call_args_list
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
        calls = mock_cli.console.print.call_args_list
        output = " ".join(str(call) for call in calls)
        assert "Simple error" in output
