"""
Unit tests for CLI error display functionality.

Tests the beautiful error display for BengalError instances and
common exception beautification.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from bengal.cli.helpers.error_display import (
    beautify_common_exception,
    display_bengal_error,
)
from bengal.errors import (
    BengalConfigError,
    BengalContentError,
    BengalRenderingError,
    ErrorCode,
)


class TestDisplayBengalError:
    """Tests for display_bengal_error function."""

    def test_display_error_with_code(self) -> None:
        """Test displaying error with error code."""
        error = BengalRenderingError(
            "Template not found: single.html",
            code=ErrorCode.R001,
            file_path=Path("content/post.md"),
            suggestion="Check templates/ directory",
        )

        # Mock CLIOutput
        cli = MagicMock()
        cli.icons = MagicMock()
        cli.icons.error = "x"
        cli.use_rich = False
        cli.console = MagicMock()

        display_bengal_error(error, cli)

        # Should have printed code, message, file path, suggestion, and docs URL
        assert cli.console.print.called
        calls = [str(call) for call in cli.console.print.call_args_list]
        call_str = " ".join(calls)
        assert "R001" in call_str
        assert "Rendering" in call_str

    def test_display_error_without_code(self) -> None:
        """Test displaying error without error code."""
        error = BengalContentError(
            "Content parsing failed",
            file_path=Path("content/test.md"),
        )

        cli = MagicMock()
        cli.icons = MagicMock()
        cli.icons.error = "x"
        cli.use_rich = False
        cli.console = MagicMock()

        display_bengal_error(error, cli)

        # Should still display but without code
        assert cli.console.print.called

    def test_display_error_with_related_files(self) -> None:
        """Test displaying error with related files."""
        error = BengalRenderingError(
            "Template error",
            code=ErrorCode.R002,
        )
        # Add related files
        error.related_files = [
            MagicMock(__str__=lambda self: "templates/base.html"),
            MagicMock(__str__=lambda self: "templates/page.html"),
        ]

        cli = MagicMock()
        cli.icons = MagicMock()
        cli.icons.error = "x"
        cli.use_rich = False
        cli.console = MagicMock()

        display_bengal_error(error, cli)

        calls = [str(call) for call in cli.console.print.call_args_list]
        call_str = " ".join(calls)
        assert "Related" in call_str

    def test_display_error_with_line_number(self) -> None:
        """Test displaying error with file path and line number."""
        error = BengalContentError(
            "Invalid frontmatter",
            code=ErrorCode.N001,
            file_path=Path("content/post.md"),
            line_number=5,
        )

        cli = MagicMock()
        cli.icons = MagicMock()
        cli.icons.error = "x"
        cli.use_rich = False
        cli.console = MagicMock()

        display_bengal_error(error, cli)

        calls = [str(call) for call in cli.console.print.call_args_list]
        call_str = " ".join(calls)
        assert "content/post.md:5" in call_str


class TestBeautifyCommonException:
    """Tests for beautify_common_exception function."""

    def test_file_not_found_error(self) -> None:
        """Test beautifying FileNotFoundError."""
        error = FileNotFoundError("config.yaml")
        error.filename = "config.yaml"

        result = beautify_common_exception(error)

        assert result is not None
        message, suggestion = result
        assert "File not found" in message
        assert "config.yaml" in message
        assert suggestion is not None

    def test_permission_error(self) -> None:
        """Test beautifying PermissionError."""
        error = PermissionError("Permission denied")
        error.filename = "/etc/passwd"

        result = beautify_common_exception(error)

        assert result is not None
        message, suggestion = result
        assert "Permission denied" in message
        assert suggestion is not None

    def test_unicode_decode_error(self) -> None:
        """Test beautifying UnicodeDecodeError."""
        error = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

        result = beautify_common_exception(error)

        assert result is not None
        message, suggestion = result
        assert "encoding" in message.lower()
        assert "UTF-8" in suggestion

    def test_yaml_error(self) -> None:
        """Test beautifying YAML errors."""
        import yaml

        error = yaml.scanner.ScannerError(
            problem="mapping values are not allowed here",
            problem_mark=yaml.Mark("test.yaml", 0, 10, 5, None, None),
        )

        result = beautify_common_exception(error)

        assert result is not None
        message, suggestion = result
        assert "YAML" in message
        assert "line 11" in message  # 10 + 1 (0-indexed)

    def test_json_decode_error(self) -> None:
        """Test beautifying JSON decode errors."""
        import json

        try:
            json.loads('{"key": value}')  # Missing quotes around value
        except json.JSONDecodeError as e:
            result = beautify_common_exception(e)

            assert result is not None
            message, suggestion = result
            assert "JSON" in message
            assert suggestion is not None

    def test_jinja2_template_syntax_error(self) -> None:
        """Test beautifying Jinja2 template syntax errors."""
        import jinja2

        error = jinja2.TemplateSyntaxError(
            message="unexpected 'end of print statement'",
            lineno=15,
            name="base.html",
            filename="/templates/base.html",
        )

        result = beautify_common_exception(error)

        assert result is not None
        message, suggestion = result
        assert "syntax error" in message.lower()
        assert "line 15" in message

    def test_jinja2_undefined_error(self) -> None:
        """Test beautifying Jinja2 undefined variable errors."""
        import jinja2

        error = jinja2.UndefinedError("'page' is undefined")

        result = beautify_common_exception(error)

        assert result is not None
        message, suggestion = result
        assert "Undefined" in message
        assert "context" in suggestion.lower()

    def test_jinja2_template_not_found(self) -> None:
        """Test beautifying Jinja2 template not found errors."""
        import jinja2

        error = jinja2.TemplateNotFound("custom.html")

        result = beautify_common_exception(error)

        assert result is not None
        message, suggestion = result
        assert "Template not found" in message
        assert "custom.html" in message

    def test_unknown_exception_returns_none(self) -> None:
        """Test that unknown exceptions return None."""
        error = RuntimeError("Some random error")

        result = beautify_common_exception(error)

        assert result is None

    def test_value_error_returns_none(self) -> None:
        """Test that ValueError returns None (not specially handled)."""
        error = ValueError("Invalid value")

        result = beautify_common_exception(error)

        assert result is None


class TestErrorCodeIntegration:
    """Tests for error code integration with display."""

    def test_error_code_docs_url(self) -> None:
        """Test that error codes generate correct docs URLs."""
        error = BengalConfigError(
            "Invalid config",
            code=ErrorCode.C001,
        )

        assert error.code is not None
        assert error.code.docs_url == "/docs/reference/errors/#c001"

    def test_error_code_category(self) -> None:
        """Test that error codes have correct categories."""
        config_error = BengalConfigError("Test", code=ErrorCode.C001)
        content_error = BengalContentError("Test", code=ErrorCode.N001)
        render_error = BengalRenderingError("Test", code=ErrorCode.R001)

        assert config_error.code.category == "config"
        assert content_error.code.category == "content"
        assert render_error.code.category == "rendering"

    def test_all_error_codes_have_categories(self) -> None:
        """Test that all error codes have valid categories."""
        valid_categories = {
            "config",
            "content",
            "rendering",
            "discovery",
            "cache",
            "server",
            "template_function",
            "parsing",
            "asset",
            "graph",
            "autodoc",
        }

        for code in ErrorCode:
            assert code.category in valid_categories, (
                f"ErrorCode {code.name} has invalid category: {code.category}"
            )

    def test_all_error_codes_have_docs_urls(self) -> None:
        """Test that all error codes generate valid docs URLs."""
        for code in ErrorCode:
            url = code.docs_url
            assert url.startswith("/docs/reference/errors/#")
            assert code.name.lower() in url
