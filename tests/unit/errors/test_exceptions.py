"""
Unit tests for Bengal exception classes.

Tests the new exception classes added in the error handling consolidation RFC:
- BengalParsingError
- BengalAutodocError
- BengalValidatorError
- BengalBuildError
- BengalTemplateFunctionError

See Also:
- plan/rfc-error-handling-consolidation.md
- bengal/errors/exceptions.py

"""

from __future__ import annotations

from pathlib import Path

from bengal.errors import (
    BengalAutodocError,
    BengalBuildError,
    BengalCacheError,
    BengalParsingError,
    BengalRenderingError,
    BengalTemplateFunctionError,
    BengalValidatorError,
    ErrorCode,
)
from bengal.errors.context import BuildPhase


class TestBengalParsingError:
    """Tests for BengalParsingError class."""

    def test_sets_parsing_build_phase(self) -> None:
        """BengalParsingError auto-sets PARSING build phase."""
        error = BengalParsingError("Invalid YAML syntax", code=ErrorCode.P001)
        assert error.build_phase == BuildPhase.PARSING

    def test_respects_explicit_build_phase(self) -> None:
        """BengalParsingError respects explicitly set build phase."""
        error = BengalParsingError(
            "Invalid YAML",
            code=ErrorCode.P001,
            build_phase=BuildPhase.INITIALIZATION,
        )
        assert error.build_phase == BuildPhase.INITIALIZATION

    def test_error_code_included_in_string(self) -> None:
        """Error code appears in string representation."""
        error = BengalParsingError("Parse failed", code=ErrorCode.P001)
        assert "P001" in str(error)

    def test_accepts_file_path_and_line(self) -> None:
        """Can include file path and line number."""
        error = BengalParsingError(
            "Invalid syntax",
            code=ErrorCode.P001,
            file_path=Path("config/site.yaml"),
            line_number=10,
        )
        assert error.file_path == Path("config/site.yaml")
        assert error.line_number == 10

    def test_get_related_test_files(self) -> None:
        """Returns appropriate test files for parsing errors."""
        error = BengalParsingError("Parse error", code=ErrorCode.P001)
        test_files = error.get_related_test_files()
        assert any("test_markdown" in f or "config" in f for f in test_files)


class TestBengalAutodocError:
    """Tests for BengalAutodocError class."""

    def test_sets_discovery_build_phase(self) -> None:
        """BengalAutodocError auto-sets DISCOVERY build phase."""
        error = BengalAutodocError("Extraction failed", code=ErrorCode.O001)
        assert error.build_phase == BuildPhase.DISCOVERY

    def test_respects_explicit_build_phase(self) -> None:
        """BengalAutodocError respects explicitly set build phase."""
        error = BengalAutodocError(
            "Extraction failed",
            code=ErrorCode.O001,
            build_phase=BuildPhase.PARSING,
        )
        assert error.build_phase == BuildPhase.PARSING

    def test_error_code_included_in_string(self) -> None:
        """Error code appears in string representation."""
        error = BengalAutodocError("Extraction failed", code=ErrorCode.O001)
        assert "O001" in str(error)

    def test_get_docs_url(self) -> None:
        """Can get documentation URL for error."""
        error = BengalAutodocError("Extraction failed", code=ErrorCode.O001)
        url = error.get_docs_url()
        assert url == "/docs/reference/errors/#o001"

    def test_get_related_test_files(self) -> None:
        """Returns appropriate test files for autodoc errors."""
        error = BengalAutodocError("Autodoc error", code=ErrorCode.O001)
        test_files = error.get_related_test_files()
        assert any("autodoc" in f for f in test_files)


class TestBengalValidatorError:
    """Tests for BengalValidatorError class."""

    def test_sets_analysis_build_phase(self) -> None:
        """BengalValidatorError auto-sets ANALYSIS build phase."""
        error = BengalValidatorError("Validator crashed", code=ErrorCode.V001)
        assert error.build_phase == BuildPhase.ANALYSIS

    def test_error_code_included_in_string(self) -> None:
        """Error code appears in string representation."""
        error = BengalValidatorError("Link check timeout", code=ErrorCode.V004)
        assert "V004" in str(error)

    def test_includes_suggestion(self) -> None:
        """Can include actionable suggestion."""
        error = BengalValidatorError(
            "Link check timeout",
            code=ErrorCode.V004,
            suggestion="Increase timeout or check network",
        )
        assert "timeout" in error.suggestion.lower() or "network" in error.suggestion.lower()

    def test_get_related_test_files(self) -> None:
        """Returns appropriate test files for validator errors."""
        error = BengalValidatorError("Validator error", code=ErrorCode.V001)
        test_files = error.get_related_test_files()
        assert any("health" in f for f in test_files)


class TestBengalBuildError:
    """Tests for BengalBuildError class."""

    def test_sets_postprocessing_build_phase(self) -> None:
        """BengalBuildError auto-sets POSTPROCESSING build phase."""
        error = BengalBuildError("Build phase failed", code=ErrorCode.B001)
        assert error.build_phase == BuildPhase.POSTPROCESSING

    def test_error_code_included_in_string(self) -> None:
        """Error code appears in string representation."""
        error = BengalBuildError("Parallel error", code=ErrorCode.B002)
        assert "B002" in str(error)

    def test_to_dict_serialization(self) -> None:
        """Can serialize to dictionary."""
        error = BengalBuildError(
            "Build failed",
            code=ErrorCode.B001,
            suggestion="Check build logs",
        )
        data = error.to_dict()
        assert data["type"] == "BengalBuildError"
        assert data["code"] == "B001"
        assert data["suggestion"] == "Check build logs"

    def test_get_related_test_files(self) -> None:
        """Returns appropriate test files for build errors."""
        error = BengalBuildError("Build error", code=ErrorCode.B001)
        test_files = error.get_related_test_files()
        assert any("orchestration" in f or "build" in f for f in test_files)


class TestBengalTemplateFunctionError:
    """Tests for BengalTemplateFunctionError class."""

    def test_inherits_from_rendering_error(self) -> None:
        """BengalTemplateFunctionError inherits from BengalRenderingError."""
        error = BengalTemplateFunctionError("Directive error", code=ErrorCode.T006)
        assert isinstance(error, BengalRenderingError)

    def test_sets_rendering_build_phase(self) -> None:
        """BengalTemplateFunctionError has RENDERING build phase (from parent)."""
        error = BengalTemplateFunctionError("Shortcode error", code=ErrorCode.T001)
        assert error.build_phase == BuildPhase.RENDERING

    def test_error_code_included_in_string(self) -> None:
        """Error code appears in string representation."""
        error = BengalTemplateFunctionError("Directive error", code=ErrorCode.T006)
        assert "T006" in str(error)

    def test_get_related_test_files(self) -> None:
        """Returns appropriate test files for template function errors."""
        error = BengalTemplateFunctionError("Template error", code=ErrorCode.T001)
        test_files = error.get_related_test_files()
        assert any("rendering" in f or "shortcode" in f for f in test_files)


class TestConvertedExceptions:
    """Tests for converted exception usage patterns (from RFC Phase 2)."""

    def test_cache_error_has_code(self) -> None:
        """Converted cache errors include error code."""
        error = BengalCacheError(
            "Cache format mismatch",
            code=ErrorCode.A001,
            suggestion="Clear cache",
        )
        assert error.code == ErrorCode.A001
        assert "A001" in str(error)
        assert error.get_docs_url() == "/docs/reference/errors/#a001"

    def test_cache_error_includes_suggestion(self) -> None:
        """Cache errors include actionable suggestions."""
        error = BengalCacheError(
            "Autodoc cache corrupted",
            code=ErrorCode.A001,
            suggestion="Clear the cache with: rm -rf .bengal/cache/",
        )
        assert "cache" in error.suggestion.lower()

    def test_rendering_error_has_original_error(self) -> None:
        """Rendering errors can chain original exception."""
        original = OSError("Disk full")
        error = BengalRenderingError(
            "Writer thread failed",
            code=ErrorCode.R010,
            original_error=original,
            suggestion="Check disk space",
        )
        assert error.original_error is original
        assert error.code == ErrorCode.R010

    def test_cache_error_with_file_path(self) -> None:
        """Cache errors can include file path context."""
        error = BengalCacheError(
            "Cache file contains invalid data type",
            code=ErrorCode.A001,
            file_path=Path(".bengal/cache/autodoc.json"),
            suggestion="Clear the cache",
        )
        assert error.file_path == Path(".bengal/cache/autodoc.json")
        assert "File:" in str(error)


class TestInvestigationHelpers:
    """Tests for investigation helper methods on new exception classes."""

    def test_parsing_error_investigation_commands(self) -> None:
        """BengalParsingError generates useful investigation commands."""
        error = BengalParsingError(
            "Invalid YAML",
            code=ErrorCode.P001,
            file_path=Path("config/site.yaml"),
        )
        commands = error.get_investigation_commands()
        # Should include grep for error code
        assert any("P001" in cmd for cmd in commands)
        # Should include view file command
        assert any("config/site.yaml" in cmd for cmd in commands)

    def test_autodoc_error_investigation_commands(self) -> None:
        """BengalAutodocError generates useful investigation commands."""
        error = BengalAutodocError("Extraction failed", code=ErrorCode.O001)
        commands = error.get_investigation_commands()
        assert any("O001" in cmd for cmd in commands)
        assert any("BengalAutodocError" in cmd for cmd in commands)

    def test_build_error_investigation_commands(self) -> None:
        """BengalBuildError generates useful investigation commands."""
        error = BengalBuildError("Build failed", code=ErrorCode.B001)
        commands = error.get_investigation_commands()
        assert any("B001" in cmd for cmd in commands)


class TestExceptionHierarchy:
    """Tests for exception class hierarchy and isinstance checks."""

    def test_all_new_exceptions_are_bengal_errors(self) -> None:
        """All new exception classes inherit from BengalError."""
        from bengal.errors import BengalError

        errors = [
            BengalParsingError("test"),
            BengalAutodocError("test"),
            BengalValidatorError("test"),
            BengalBuildError("test"),
            BengalTemplateFunctionError("test"),
        ]
        for error in errors:
            assert isinstance(error, BengalError)

    def test_template_function_error_is_rendering_error(self) -> None:
        """BengalTemplateFunctionError is also a BengalRenderingError."""
        error = BengalTemplateFunctionError("test")
        assert isinstance(error, BengalRenderingError)

    def test_can_catch_by_base_class(self) -> None:
        """Can catch all new exceptions via BengalError base class."""
        from bengal.errors import BengalError

        exceptions = [
            BengalParsingError,
            BengalAutodocError,
            BengalValidatorError,
            BengalBuildError,
            BengalTemplateFunctionError,
        ]
        for exc_class in exceptions:
            try:
                raise exc_class("test")
            except BengalError as e:
                assert e.message == "test"
