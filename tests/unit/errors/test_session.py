"""
Unit tests for error session tracking.

Tests: session lifecycle, error deduplication, session summary,
get_errors_for_file, get_systemic_issues, get_investigation_hints.
"""

from __future__ import annotations

from bengal.errors import BengalDiscoveryError, ErrorCode, record_error, reset_session
from bengal.errors.session import get_session


class TestErrorSessionRecord:
    """Test ErrorSession.record."""

    def setup_method(self) -> None:
        """Reset session before each test."""
        reset_session()

    def test_record_returns_pattern_info(self) -> None:
        """record returns occurrence_number, is_recurring, etc."""
        session = get_session()
        err = ValueError("test error")
        info = session.record(err, file_path="content/page.md")
        assert "occurrence_number" in info
        assert info["occurrence_number"] == 1
        assert info["is_recurring"] is False

    def test_record_same_error_deduplicates(self) -> None:
        """Same error recorded twice has is_recurring=True."""
        session = get_session()
        err = ValueError("same message")
        session.record(err, file_path="content/a.md")
        info = session.record(err, file_path="content/b.md")
        assert info["occurrence_number"] == 2
        assert info["is_recurring"] is True

    def test_record_with_error_code(self) -> None:
        """Record extracts error code from BengalError."""
        session = get_session()
        err = BengalDiscoveryError(
            "Content dir missing",
            code=ErrorCode.D001,
            file_path=None,
        )
        info = session.record(err, file_path="content")
        assert "signature" in info


class TestErrorSessionQueries:
    """Test ErrorSession query methods."""

    def setup_method(self) -> None:
        """Reset session before each test."""
        reset_session()

    def test_get_errors_for_file(self) -> None:
        """get_errors_for_file returns errors for that file."""
        session = get_session()
        session.record(ValueError("err1"), file_path="content/a.md")
        session.record(ValueError("err2"), file_path="content/a.md")
        session.record(ValueError("err3"), file_path="content/b.md")
        errors = session.get_errors_for_file("content/a.md")
        assert len(errors) == 2

    def test_get_systemic_issues(self) -> None:
        """get_systemic_issues returns patterns affecting 3+ files."""
        session = get_session()
        err = ValueError("template error")
        session.record(err, file_path="content/a.md")
        session.record(err, file_path="content/b.md")
        session.record(err, file_path="content/c.md")
        systemic = session.get_systemic_issues()
        assert len(systemic) >= 1
        assert any(p.is_systemic for p in systemic)


class TestErrorSessionSummary:
    """Test get_summary."""

    def setup_method(self) -> None:
        """Reset session before each test."""
        reset_session()

    def test_get_summary_structure(self) -> None:
        """get_summary returns expected keys."""
        session = get_session()
        session.record(ValueError("x"), file_path="a.md")
        summary = session.get_summary()
        assert "total_errors" in summary
        assert "unique_patterns" in summary
        assert "session_duration_seconds" in summary
        assert summary["total_errors"] == 1


class TestErrorSessionClear:
    """Test session clear."""

    def setup_method(self) -> None:
        """Reset session before each test."""
        reset_session()

    def test_clear_resets_session(self) -> None:
        """clear() empties all recorded errors."""
        session = get_session()
        session.record(ValueError("x"), file_path="a.md")
        session.clear()
        summary = session.get_summary()
        assert summary["total_errors"] == 0


class TestRecordErrorConvenience:
    """Test record_error convenience function."""

    def setup_method(self) -> None:
        """Reset session before each test."""
        reset_session()

    def test_record_error_delegates_to_session(self) -> None:
        """record_error records to current session."""
        info = record_error(ValueError("convenience"), file_path="x.md")
        assert "occurrence_number" in info
        session = get_session()
        assert session.get_errors_for_file("x.md")
