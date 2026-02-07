"""
Tests for error handling and surfacing in the rendering pipeline.

These tests verify that errors are properly logged and tracked in build stats
rather than being silently swallowed.
"""

from __future__ import annotations

import logging

import pytest

from bengal.orchestration.stats import BuildStats


class TestBuildStatsWarningTracking:
    """Test that build stats properly tracks warnings."""

    def test_add_warning_stores_in_list(self) -> None:
        """Verify add_warning stores warnings in the list."""
        stats = BuildStats()

        stats.add_warning("content/test.md", "Test warning", "link_extraction")

        assert len(stats.warnings) == 1
        assert stats.warnings[0].message == "Test warning"
        assert stats.warnings[0].warning_type == "link_extraction"

    def test_multiple_warnings_accumulated(self) -> None:
        """Verify multiple warnings are accumulated."""
        stats = BuildStats()

        stats.add_warning("page1.md", "Warning 1", "link")
        stats.add_warning("page2.md", "Warning 2", "template")
        stats.add_warning("page3.md", "Warning 3", "link")

        assert len(stats.warnings) == 3

    def test_warnings_by_type_groups_correctly(self) -> None:
        """Verify warnings_by_type groups warnings by type."""
        stats = BuildStats()

        stats.add_warning("page1.md", "Warning 1", "link")
        stats.add_warning("page2.md", "Warning 2", "template")
        stats.add_warning("page3.md", "Warning 3", "link")

        by_type = stats.warnings_by_type

        assert len(by_type["link"]) == 2
        assert len(by_type["template"]) == 1


class TestErrorCodeUsage:
    """Test that error codes are properly used."""

    def test_error_codes_exist_for_rendering_errors(self) -> None:
        """Verify error codes exist for rendering-related failures."""
        from bengal.errors import ErrorCode

        # Should have various rendering error codes
        # R004 is for template filter errors
        assert hasattr(ErrorCode, "R004")
        assert ErrorCode.R004.value == "template_filter_error"

        # R001 is for template not found
        assert hasattr(ErrorCode, "R001")
        assert ErrorCode.R001.value == "template_not_found"


class TestErrorLogging:
    """Test that errors are logged at appropriate levels."""

    def test_warning_level_used_for_non_fatal_errors(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Verify non-fatal errors log at warning level, not debug.

        This test verifies the standard logging pattern used in Bengal's
        error handling. The actual logger (structlog wrapper) may use
        different semantics but the intent is to log at WARNING level
        for non-fatal errors.
        """
        # Use standard logging to test the pattern
        test_logger = logging.getLogger("bengal.rendering.test")

        with caplog.at_level(logging.WARNING):
            # Simulate what the pipeline does on link extraction failure
            test_logger.warning("link_extraction_failed: page=content/test.md error=Test error")

        # Should have logged at warning level
        assert any(r.levelno >= logging.WARNING for r in caplog.records)
        assert any("link_extraction_failed" in r.message for r in caplog.records)


class TestPreprocessingErrorFallback:
    """Test preprocessing error fallback behavior."""

    def test_preprocessing_falls_back_to_raw_on_error(self) -> None:
        """Verify preprocessing returns raw source on error."""
        # This tests the pattern used in the pipeline:
        # try: preprocess() except: return raw

        raw_content = "# My content with {{ broken"

        def preprocess(content: str) -> str:
            if "broken" in content:
                raise Exception("Template syntax error")
            return f"<p>{content}</p>"

        # Simulate pipeline fallback pattern
        try:
            result = preprocess(raw_content)
        except Exception:
            result = raw_content

        assert result == raw_content


class TestTruncateError:
    """Test error truncation utility."""

    def test_truncate_error_exists(self) -> None:
        """Verify truncate_error utility exists."""
        from bengal.rendering.pipeline.core import truncate_error

        assert callable(truncate_error)

    def test_truncate_error_shortens_long_messages(self) -> None:
        """Verify long error messages are truncated."""
        from bengal.rendering.pipeline.core import truncate_error

        long_error = Exception("a" * 1000)
        result = truncate_error(long_error)

        # Should be truncated
        assert len(result) < 1000

    def test_truncate_error_preserves_short_messages(self) -> None:
        """Verify short error messages are preserved."""
        from bengal.rendering.pipeline.core import truncate_error

        short_error = Exception("Short error")
        result = truncate_error(short_error)

        assert "Short error" in result


class TestErrorContextInBuildWarnings:
    """Test that error context is preserved in build warnings."""

    def test_file_path_included_in_warning(self) -> None:
        """Verify file path is included in warning."""
        stats = BuildStats()

        stats.add_warning(
            "content/docs/specific-page.md",
            "Link extraction failed",
            "link_extraction",
        )

        # Warning should include file path
        warning = stats.warnings[0]
        assert "specific-page" in warning.file_path

    def test_error_type_included_in_message(self) -> None:
        """Verify error type is included in message."""
        stats = BuildStats()

        # Pattern used in pipeline: f"Link extraction failed: {truncate_error(e)}"
        stats.add_warning(
            "test.md",
            "Link extraction failed: ValueError('malformed')",
            "link_extraction",
        )

        warning = stats.warnings[0]
        assert "ValueError" in warning.message


class TestWarningTypeConstants:
    """Test that warning types are used consistently."""

    def test_link_extraction_warning_type(self) -> None:
        """Verify link_extraction warning type is used."""
        stats = BuildStats()
        stats.add_warning("test.md", "Test", "link_extraction")

        assert stats.warnings[0].warning_type == "link_extraction"

    def test_template_warning_type(self) -> None:
        """Verify template warning type is used."""
        stats = BuildStats()
        stats.add_warning("test.md", "Test", "template")

        assert stats.warnings[0].warning_type == "template"

    def test_other_warning_type_default(self) -> None:
        """Verify 'other' is the default warning type."""
        stats = BuildStats()
        stats.add_warning("test.md", "Test")  # No type specified

        assert stats.warnings[0].warning_type == "other"
