"""
Unit tests for traceback renderers.

Tests: CompactTracebackRenderer, MinimalTracebackRenderer display_exception,
error type and message output, trace frame formatting.
"""

from __future__ import annotations

import pytest

from bengal.errors.traceback.renderer import (
    CompactTracebackRenderer,
    MinimalTracebackRenderer,
    TracebackRenderer,
)


class TestTracebackRendererBase:
    """Test TracebackRenderer base class."""

    def test_display_exception_not_implemented(self) -> None:
        """Base renderer raises NotImplementedError."""
        renderer = TracebackRenderer(config=None)
        with pytest.raises(NotImplementedError):
            renderer.display_exception(ValueError("test"))


class TestCompactTracebackRenderer:
    """Test CompactTracebackRenderer."""

    def test_display_exception_shows_error_and_trace(self, capsys: pytest.CaptureFixture) -> None:
        """display_exception shows error type, message, and trace."""
        renderer = CompactTracebackRenderer(config=None)
        try:
            raise ValueError("test error message")
        except ValueError as e:
            renderer.display_exception(e)
        out = capsys.readouterr().out
        assert "ValueError" in out
        assert "test error message" in out


class TestMinimalTracebackRenderer:
    """Test MinimalTracebackRenderer."""

    def test_display_exception_shows_one_line(self, capsys: pytest.CaptureFixture) -> None:
        """display_exception shows error on minimal lines."""
        renderer = MinimalTracebackRenderer(config=None)
        try:
            raise RuntimeError("minimal error")
        except RuntimeError as e:
            renderer.display_exception(e)
        out = capsys.readouterr().out
        assert "RuntimeError" in out
        assert "minimal error" in out
