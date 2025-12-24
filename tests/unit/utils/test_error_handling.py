"""
Unit tests for error handling utilities.

Tests error context, enrichment, recovery patterns, and exception hierarchy.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.errors import (
    BengalCacheError,
    BengalConfigError,
    BengalContentError,
    BengalDiscoveryError,
    BengalError,
    BengalRenderingError,
    ErrorCode,
    ErrorContext,
    enrich_error,
    error_recovery_context,
    with_error_recovery,
)


class TestBengalError:
    """Tests for BengalError base class."""

    def test_basic_error(self) -> None:
        """Test basic BengalError creation."""
        error = BengalError("Test error")

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.file_path is None
        assert error.line_number is None
        assert error.suggestion is None

    def test_error_with_context(self) -> None:
        """Test BengalError with full context."""
        error = BengalError(
            "Test error",
            file_path=Path("test.md"),
            line_number=42,
            suggestion="Fix the issue",
        )

        assert error.file_path == Path("test.md")
        assert error.line_number == 42
        assert error.suggestion == "Fix the issue"
        assert "test.md" in str(error)
        assert "42" in str(error)
        assert "Fix the issue" in str(error)

    def test_error_with_original_error(self) -> None:
        """Test BengalError with original error chaining."""
        original = ValueError("Original error")
        error = BengalError(
            "Wrapped error",
            original_error=original,
        )

        assert error.original_error == original
        assert isinstance(error.original_error, ValueError)

    def test_error_to_dict(self) -> None:
        """Test BengalError serialization."""
        error = BengalError(
            "Test error",
            file_path=Path("test.md"),
            line_number=42,
            suggestion="Fix it",
        )

        result = error.to_dict()

        assert result["type"] == "BengalError"
        assert result["message"] == "Test error"
        assert result["file_path"] == "test.md"
        assert result["line_number"] == 42
        assert result["suggestion"] == "Fix it"

    def test_error_hierarchy(self) -> None:
        """Test exception hierarchy."""
        config_error = BengalConfigError("Config error")
        content_error = BengalContentError("Content error")
        rendering_error = BengalRenderingError("Rendering error")
        discovery_error = BengalDiscoveryError("Discovery error")
        cache_error = BengalCacheError("Cache error")

        # All should be BengalError instances
        assert isinstance(config_error, BengalError)
        assert isinstance(content_error, BengalError)
        assert isinstance(rendering_error, BengalError)
        assert isinstance(discovery_error, BengalError)
        assert isinstance(cache_error, BengalError)

        # Can catch as base class
        with pytest.raises(BengalError):
            raise config_error
        with pytest.raises(BengalError):
            raise content_error
        with pytest.raises(BengalError):
            raise rendering_error

    def test_error_with_code(self) -> None:
        """Test BengalError with error code."""
        error = BengalRenderingError(
            "Template not found",
            code=ErrorCode.R001,
            file_path=Path("content/post.md"),
            suggestion="Check templates directory",
        )

        assert error.code == ErrorCode.R001
        assert error.code.name == "R001"
        assert error.code.category == "rendering"
        assert "[R001]" in str(error)

    def test_error_code_docs_url(self) -> None:
        """Test error code documentation URL."""
        error = BengalConfigError(
            "Invalid config",
            code=ErrorCode.C001,
        )

        docs_url = error.get_docs_url()
        assert docs_url == "/docs/reference/errors/#c001"

    def test_error_code_in_message_format(self) -> None:
        """Test that error code appears in formatted message."""
        error = BengalContentError(
            "Invalid frontmatter",
            code=ErrorCode.N001,
            file_path=Path("test.md"),
            line_number=5,
        )

        message = str(error)
        assert "[N001]" in message
        assert "Invalid frontmatter" in message
        assert "test.md" in message
        assert "5" in message


class TestErrorContext:
    """Tests for ErrorContext dataclass."""

    def test_basic_context(self) -> None:
        """Test basic ErrorContext creation."""
        context = ErrorContext()

        assert context.file_path is None
        assert context.line_number is None
        assert context.operation is None
        assert context.suggestion is None

    def test_context_with_values(self) -> None:
        """Test ErrorContext with all values."""
        context = ErrorContext(
            file_path=Path("test.md"),
            line_number=42,
            operation="parsing file",
            suggestion="Check syntax",
        )

        assert context.file_path == Path("test.md")
        assert context.line_number == 42
        assert context.operation == "parsing file"
        assert context.suggestion == "Check syntax"


class TestEnrichError:
    """Tests for enrich_error function."""

    def test_enrich_generic_exception(self) -> None:
        """Test enriching a generic exception."""
        original = ValueError("Original error")
        context = ErrorContext(
            file_path=Path("test.md"),
            operation="parsing",
            suggestion="Fix syntax",
        )

        enriched = enrich_error(original, context, BengalContentError)

        assert isinstance(enriched, BengalContentError)
        assert isinstance(enriched, BengalError)
        assert enriched.file_path == Path("test.md")
        assert enriched.suggestion == "Fix syntax"
        assert enriched.original_error == original

    def test_enrich_already_bengal_error(self) -> None:
        """Test enriching an already-enriched error."""
        original = BengalContentError(
            "Already enriched",
            file_path=Path("original.md"),
        )
        context = ErrorContext(
            file_path=Path("new.md"),
            suggestion="New suggestion",
        )

        enriched = enrich_error(original, context, BengalContentError)

        # Should return same error, but add missing context
        assert enriched is original
        assert enriched.file_path == Path("original.md")  # Keeps original
        assert enriched.suggestion == "New suggestion"  # Adds new

    def test_enrich_with_operation(self) -> None:
        """Test enriching with operation context."""
        original = Exception("Error")
        context = ErrorContext(
            file_path=Path("test.md"),
            operation="rendering template",
            suggestion="Check template syntax",
        )

        enriched = enrich_error(original, context, BengalRenderingError)

        assert isinstance(enriched, BengalRenderingError)
        assert enriched.file_path == Path("test.md")


class TestErrorRecovery:
    """Tests for error recovery utilities."""

    def test_with_error_recovery_success(self) -> None:
        """Test with_error_recovery on successful operation."""

        def operation():
            return "success"

        result = with_error_recovery(operation)

        assert result == "success"

    def test_with_error_recovery_failure_strict(self) -> None:
        """Test with_error_recovery in strict mode."""

        def operation():
            raise ValueError("Error")

        with pytest.raises(ValueError):
            with_error_recovery(operation, strict_mode=True)

    def test_with_error_recovery_failure_recovery(self) -> None:
        """Test with_error_recovery with recovery function."""

        def operation():
            raise ValueError("Error")

        def on_error(e):
            return "recovered"

        result = with_error_recovery(
            operation,
            on_error=on_error,
            strict_mode=False,
        )

        assert result == "recovered"

    def test_error_recovery_context_success(self) -> None:
        """Test error_recovery_context on success."""
        with error_recovery_context("test operation", strict_mode=False):
            result = "success"

        assert result == "success"

    def test_error_recovery_context_failure_strict(self) -> None:
        """Test error_recovery_context in strict mode."""
        with pytest.raises(ValueError), error_recovery_context("test operation", strict_mode=True):
            raise ValueError("Error")

    def test_error_recovery_context_failure_production(self) -> None:
        """Test error_recovery_context in production mode."""
        # Should not raise, just continue
        with error_recovery_context("test operation", strict_mode=False):
            raise ValueError("Error")

        # If we get here, error was suppressed
        assert True
