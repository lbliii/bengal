"""
Unit tests for error recovery utilities.

Tests: with_error_recovery, error_recovery_context, recover_file_processing,
fallback chains, strict mode vs production mode.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.errors.recovery import (
    error_recovery_context,
    recover_file_processing,
    with_error_recovery,
)


class TestWithErrorRecovery:
    """Test with_error_recovery."""

    def test_success_returns_result(self) -> None:
        """Successful operation returns result."""
        result = with_error_recovery(lambda: 42)
        assert result == 42

    def test_strict_mode_reraises(self) -> None:
        """Strict mode re-raises exceptions."""
        with pytest.raises(ValueError, match="fail"):
            with_error_recovery(
                lambda: (_ for _ in ()).throw(ValueError("fail")),
                strict_mode=True,
            )

    def test_production_mode_with_on_error_returns_fallback(self) -> None:
        """Production mode with on_error returns fallback value."""
        result = with_error_recovery(
            lambda: (_ for _ in ()).throw(ValueError("fail")),
            on_error=lambda e: "recovered",
            strict_mode=False,
        )
        assert result == "recovered"

    def test_production_mode_without_on_error_reraises(self) -> None:
        """Production mode without on_error re-raises."""
        with pytest.raises(ValueError, match="fail"):
            with_error_recovery(
                lambda: (_ for _ in ()).throw(ValueError("fail")),
                strict_mode=False,
            )

    def test_on_error_receives_exception(self) -> None:
        """on_error callback receives the exception."""
        captured: list[Exception] = []

        def capture(e: Exception) -> str:
            captured.append(e)
            return "ok"

        with_error_recovery(
            lambda: (_ for _ in ()).throw(ValueError("msg")),
            on_error=capture,
            strict_mode=False,
        )
        assert len(captured) == 1
        assert str(captured[0]) == "msg"

    def test_logger_called_on_recovery(self) -> None:
        """Logger receives warning when recovering."""
        logger = MagicMock()
        with_error_recovery(
            lambda: (_ for _ in ()).throw(RuntimeError("oops")),
            on_error=lambda e: None,
            strict_mode=False,
            logger=logger,
        )
        logger.warning.assert_called_once()
        call_kw = logger.warning.call_args[1]
        assert "error_recovery" in str(logger.warning.call_args)
        assert "oops" in str(call_kw.get("error", ""))


class TestErrorRecoveryContext:
    """Test error_recovery_context."""

    def test_success_yields(self) -> None:
        """Successful context yields normally."""
        with error_recovery_context("test", strict_mode=False):
            pass

    def test_strict_mode_reraises(self) -> None:
        """Strict mode re-raises from context."""
        with (
            pytest.raises(ValueError, match="in context"),
            error_recovery_context("test", strict_mode=True),
        ):
            raise ValueError("in context")

    def test_production_mode_suppresses(self) -> None:
        """Production mode suppresses exception, continues."""
        with error_recovery_context("test", strict_mode=False):
            raise ValueError("suppressed")
        # No exception propagates

    def test_production_mode_logs_warning(self) -> None:
        """Production mode logs warning when suppressing."""
        logger = MagicMock()
        with error_recovery_context("test", strict_mode=False, logger=logger):
            raise ValueError("suppressed")
        logger.warning.assert_called_once()


class TestRecoverFileProcessing:
    """Test recover_file_processing."""

    def test_success_returns_result(self, tmp_path: Path) -> None:
        """Successful file processing returns result."""
        result = recover_file_processing(
            tmp_path / "file.md",
            lambda: "processed",
        )
        assert result == "processed"

    def test_strict_mode_reraises(self, tmp_path: Path) -> None:
        """Strict mode re-raises."""
        with pytest.raises(ValueError, match="fail"):
            recover_file_processing(
                tmp_path / "file.md",
                lambda: (_ for _ in ()).throw(ValueError("fail")),
                strict_mode=True,
            )

    def test_production_mode_returns_none(self, tmp_path: Path) -> None:
        """Production mode returns None on error."""
        result = recover_file_processing(
            tmp_path / "file.md",
            lambda: (_ for _ in ()).throw(ValueError("fail")),
            strict_mode=False,
        )
        assert result is None

    def test_build_stats_add_warning_called(self, tmp_path: Path) -> None:
        """BuildStats.add_warning called when build_stats provided."""
        build_stats = MagicMock()
        recover_file_processing(
            tmp_path / "file.md",
            lambda: (_ for _ in ()).throw(ValueError("fail")),
            strict_mode=False,
            build_stats=build_stats,
        )
        build_stats.add_warning.assert_called_once()
        call_args = build_stats.add_warning.call_args[0]
        assert str(tmp_path / "file.md") in str(call_args[0])
        assert "fail" in str(call_args[1])
