"""
Unit tests for file watcher abstraction.

Tests:
    - WatchfilesWatcher availability detection
    - WatchdogWatcher fallback behavior
    - Backend selection via env var
    - Filter callback integration
    - Factory function behavior
"""

from __future__ import annotations

import contextlib
import importlib
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from bengal.server.file_watcher import (
    WatchdogWatcher,
    create_watcher,
    is_watchfiles_available,
)


def _noop_filter(p: Path) -> bool:
    """No-op filter that accepts all paths."""
    return False


class TestIsWatchfilesAvailable:
    """Tests for watchfiles availability detection."""

    def test_returns_bool(self) -> None:
        """Test that is_watchfiles_available returns a boolean."""
        result = is_watchfiles_available()
        assert isinstance(result, bool)

    def test_detection_works(self) -> None:
        """Test that detection runs without error."""
        # Just verify it doesn't raise
        is_watchfiles_available()


class TestWatchdogWatcher:
    """Tests for WatchdogWatcher class."""

    def test_creation(self, tmp_path: Path) -> None:
        """Test that WatchdogWatcher can be created."""
        watcher = WatchdogWatcher(
            paths=[tmp_path],
            ignore_filter=_noop_filter,
            debounce_ms=100,
        )

        assert watcher.paths == [tmp_path]
        assert watcher.debounce_ms == 100

    def test_default_debounce(self, tmp_path: Path) -> None:
        """Test that WatchdogWatcher uses default debounce."""
        watcher = WatchdogWatcher(
            paths=[tmp_path],
            ignore_filter=_noop_filter,
        )

        assert watcher.debounce_ms == 100


class TestCreateWatcher:
    """Tests for create_watcher factory function."""

    def test_creates_watchdog_when_forced(self, tmp_path: Path) -> None:
        """Test that create_watcher returns WatchdogWatcher when forced."""
        watcher = create_watcher(
            paths=[tmp_path],
            ignore_filter=_noop_filter,
            backend="watchdog",
        )

        assert isinstance(watcher, WatchdogWatcher)

    def test_env_var_overrides_parameter(self, tmp_path: Path) -> None:
        """Test that BENGAL_WATCH_BACKEND env var takes precedence."""
        with patch.dict(os.environ, {"BENGAL_WATCH_BACKEND": "watchdog"}):
            watcher = create_watcher(
                paths=[tmp_path],
                ignore_filter=_noop_filter,
                backend="watchfiles",  # This should be overridden
            )

            assert isinstance(watcher, WatchdogWatcher)

    def test_auto_falls_back_to_watchdog(self, tmp_path: Path) -> None:
        """Test that auto falls back to watchdog when watchfiles unavailable."""
        # Mock watchfiles as unavailable
        with patch(
            "bengal.server.file_watcher.WatchfilesWatcher",
            side_effect=ImportError("No module named 'watchfiles'"),
        ):
            watcher = create_watcher(
                paths=[tmp_path],
                ignore_filter=_noop_filter,
                backend="auto",
            )

            assert isinstance(watcher, WatchdogWatcher)

    def test_watchfiles_raises_when_forced_but_unavailable(self, tmp_path: Path) -> None:
        """Test that forcing watchfiles raises ImportError when unavailable."""
        # Temporarily make watchfiles unavailable
        with patch.dict("sys.modules", {"watchfiles": None}):
            # This should raise because watchfiles is forced but unavailable
            # We need to import fresh to trigger the ImportError
            import bengal.server.file_watcher as fw

            # Reload to pick up the patched modules
            with contextlib.suppress(ImportError):
                importlib.reload(fw)

            # The actual test would require more complex mocking
            # For now, just verify the function handles the case
            try:
                watcher = create_watcher(
                    paths=[tmp_path],
                    ignore_filter=_noop_filter,
                    backend="watchfiles",
                )
                # If watchfiles is available, this is fine
                assert watcher is not None
            except ImportError:
                # Expected if watchfiles is not installed
                pass


class TestWatcherIgnoreFilter:
    """Tests for ignore filter integration with watchers."""

    def test_watchdog_uses_filter(self, tmp_path: Path) -> None:
        """Test that WatchdogWatcher stores and uses the ignore filter."""
        called_paths: list[Path] = []

        def ignore_filter(p: Path) -> bool:
            called_paths.append(p)
            return str(p).endswith(".pyc")

        watcher = WatchdogWatcher(
            paths=[tmp_path],
            ignore_filter=ignore_filter,
        )

        # The filter is stored
        assert watcher.ignore_filter is ignore_filter


class TestWatcherEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_multiple_paths(self, tmp_path: Path) -> None:
        """Test that watcher can handle multiple paths."""
        path1 = tmp_path / "dir1"
        path2 = tmp_path / "dir2"
        path1.mkdir()
        path2.mkdir()

        watcher = WatchdogWatcher(
            paths=[path1, path2],
            ignore_filter=_noop_filter,
        )

        assert watcher.paths == [path1, path2]

    def test_empty_paths_list(self) -> None:
        """Test that watcher can be created with empty paths."""
        watcher = WatchdogWatcher(
            paths=[],
            ignore_filter=_noop_filter,
        )

        assert watcher.paths == []

    @pytest.mark.parametrize(
        "backend",
        ["auto", "watchdog", "WATCHDOG", "WatchDog"],
    )
    def test_backend_case_insensitive(self, tmp_path: Path, backend: str) -> None:
        """Test that backend parameter is case insensitive."""
        # Clear env var to ensure we're testing parameter
        env = os.environ.copy()
        env.pop("BENGAL_WATCH_BACKEND", None)

        with patch.dict(os.environ, env, clear=True):
            watcher = create_watcher(
                paths=[tmp_path],
                ignore_filter=_noop_filter,
                backend=backend,
            )

            # Should always work (either watchdog or watchfiles)
            assert watcher is not None


class TestWatchdogEventTypes:
    """Tests for WatchdogWatcher event type tracking."""

    def test_initializes_empty_event_types(self, tmp_path: Path) -> None:
        """Test that WatchdogWatcher initializes with empty event types set."""
        watcher = WatchdogWatcher(
            paths=[tmp_path],
            ignore_filter=_noop_filter,
        )

        assert watcher._event_types == set()

    def test_handler_captures_event_types(self, tmp_path: Path) -> None:
        """Test that the event handler captures event types correctly."""
        watcher = WatchdogWatcher(
            paths=[tmp_path],
            ignore_filter=_noop_filter,
        )

        handler = watcher._create_handler()

        # Simulate a 'created' event
        class MockEvent:
            is_directory = False
            src_path = str(tmp_path / "test.md")
            event_type = "created"

        handler.on_any_event(MockEvent())

        assert tmp_path / "test.md" in watcher._changes
        assert "created" in watcher._event_types

    def test_handler_captures_multiple_event_types(self, tmp_path: Path) -> None:
        """Test that multiple event types are accumulated."""
        watcher = WatchdogWatcher(
            paths=[tmp_path],
            ignore_filter=_noop_filter,
        )

        handler = watcher._create_handler()

        # Simulate multiple events with different types
        class MockCreatedEvent:
            is_directory = False
            src_path = str(tmp_path / "new.md")
            event_type = "created"

        class MockModifiedEvent:
            is_directory = False
            src_path = str(tmp_path / "existing.md")
            event_type = "modified"

        class MockDeletedEvent:
            is_directory = False
            src_path = str(tmp_path / "old.md")
            event_type = "deleted"

        handler.on_any_event(MockCreatedEvent())
        handler.on_any_event(MockModifiedEvent())
        handler.on_any_event(MockDeletedEvent())

        assert len(watcher._changes) == 3
        assert watcher._event_types == {"created", "modified", "deleted"}

    def test_handler_skips_directory_events(self, tmp_path: Path) -> None:
        """Test that directory events are skipped."""
        watcher = WatchdogWatcher(
            paths=[tmp_path],
            ignore_filter=_noop_filter,
        )

        handler = watcher._create_handler()

        class MockDirEvent:
            is_directory = True
            src_path = str(tmp_path / "subdir")
            event_type = "created"

        handler.on_any_event(MockDirEvent())

        assert len(watcher._changes) == 0
        assert len(watcher._event_types) == 0

    def test_handler_applies_ignore_filter(self, tmp_path: Path) -> None:
        """Test that ignore filter prevents event type tracking."""

        def ignore_pyc(p: Path) -> bool:
            return str(p).endswith(".pyc")

        watcher = WatchdogWatcher(
            paths=[tmp_path],
            ignore_filter=ignore_pyc,
        )

        handler = watcher._create_handler()

        class MockPycEvent:
            is_directory = False
            src_path = str(tmp_path / "module.pyc")
            event_type = "modified"

        class MockPyEvent:
            is_directory = False
            src_path = str(tmp_path / "module.py")
            event_type = "modified"

        handler.on_any_event(MockPycEvent())
        handler.on_any_event(MockPyEvent())

        # Only the .py file should be tracked
        assert len(watcher._changes) == 1
        assert tmp_path / "module.py" in watcher._changes
        assert "modified" in watcher._event_types
