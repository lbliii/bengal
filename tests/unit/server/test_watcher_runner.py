"""Tests for WatcherRunner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from bengal.server.ignore_filter import IgnoreFilter
from bengal.server.watcher_runner import WatcherRunner, create_watcher_runner


class TestWatcherRunner:
    """Tests for WatcherRunner class."""

    def test_init(self) -> None:
        """Test WatcherRunner initialization."""
        paths = [Path(".")]
        ignore_filter = IgnoreFilter()
        callback = MagicMock()

        runner = WatcherRunner(
            paths=paths,
            ignore_filter=ignore_filter,
            on_changes=callback,
            debounce_ms=100,
        )

        assert runner.paths == paths
        assert runner.ignore_filter == ignore_filter
        assert runner.on_changes == callback
        assert runner.debounce_ms == 100

    def test_start_creates_thread(self) -> None:
        """Test that start creates a background thread."""
        runner = WatcherRunner(
            paths=[Path(".")],
            ignore_filter=IgnoreFilter(),
            on_changes=MagicMock(),
        )

        assert runner._thread is None

        runner.start()
        try:
            assert runner._thread is not None
            assert runner._thread.is_alive()
        finally:
            runner.stop()

    def test_stop_cleans_up(self) -> None:
        """Test that stop cleans up the thread."""
        runner = WatcherRunner(
            paths=[Path(".")],
            ignore_filter=IgnoreFilter(),
            on_changes=MagicMock(),
        )

        runner.start()
        runner.stop()

        assert runner._thread is None

    def test_double_start_is_idempotent(self) -> None:
        """Test that calling start twice doesn't create two threads."""
        runner = WatcherRunner(
            paths=[Path(".")],
            ignore_filter=IgnoreFilter(),
            on_changes=MagicMock(),
        )

        try:
            runner.start()
            first_thread = runner._thread

            runner.start()
            second_thread = runner._thread

            assert first_thread is second_thread
        finally:
            runner.stop()

    def test_double_stop_is_idempotent(self) -> None:
        """Test that calling stop twice doesn't error."""
        runner = WatcherRunner(
            paths=[Path(".")],
            ignore_filter=IgnoreFilter(),
            on_changes=MagicMock(),
        )

        runner.start()
        runner.stop()
        runner.stop()  # Should not error

        assert runner._thread is None


class TestCreateWatcherRunner:
    """Tests for create_watcher_runner factory function."""

    def test_creates_runner_with_site_config(self) -> None:
        """Test that factory creates runner with site config."""
        mock_site = MagicMock()
        mock_site.config = {
            "dev_server": {
                "exclude_patterns": ["*.pyc"],
                "exclude_regex": [r"\.tmp$"],
            }
        }
        mock_site.output_dir = Path("public")

        runner = create_watcher_runner(
            site=mock_site,
            watch_dirs=[Path("content")],
            on_changes=MagicMock(),
            debounce_ms=200,
        )

        assert isinstance(runner, WatcherRunner)
        assert runner.debounce_ms == 200
        assert Path("content") in runner.paths

    def test_creates_runner_with_empty_config(self) -> None:
        """Test that factory handles empty config."""
        mock_site = MagicMock()
        mock_site.config = {}
        mock_site.output_dir = Path("public")

        runner = create_watcher_runner(
            site=mock_site,
            watch_dirs=[Path(".")],
            on_changes=MagicMock(),
        )

        assert isinstance(runner, WatcherRunner)
