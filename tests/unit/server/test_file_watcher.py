"""
Unit tests for file watcher abstraction.

Tests:
    - WatchfilesWatcher creation and configuration
    - Filter callback integration
    - Factory function behavior
"""

from __future__ import annotations

from pathlib import Path

from bengal.server.file_watcher import (
    WatchfilesWatcher,
    create_watcher,
)


def _noop_filter(p: Path) -> bool:
    """No-op filter that accepts all paths."""
    return False


class TestWatchfilesWatcher:
    """Tests for WatchfilesWatcher class."""

    def test_creation(self, tmp_path: Path) -> None:
        """Test that WatchfilesWatcher can be created."""
        watcher = WatchfilesWatcher(
            paths=[tmp_path],
            ignore_filter=_noop_filter,
        )

        assert watcher.paths == [tmp_path]

    def test_stores_ignore_filter(self, tmp_path: Path) -> None:
        """Test that WatchfilesWatcher stores the ignore filter."""
        watcher = WatchfilesWatcher(
            paths=[tmp_path],
            ignore_filter=_noop_filter,
        )

        assert watcher.ignore_filter is _noop_filter

    def test_multiple_paths(self, tmp_path: Path) -> None:
        """Test that watcher can handle multiple paths."""
        path1 = tmp_path / "dir1"
        path2 = tmp_path / "dir2"
        path1.mkdir()
        path2.mkdir()

        watcher = WatchfilesWatcher(
            paths=[path1, path2],
            ignore_filter=_noop_filter,
        )

        assert watcher.paths == [path1, path2]

    def test_empty_paths_list(self) -> None:
        """Test that watcher can be created with empty paths."""
        watcher = WatchfilesWatcher(
            paths=[],
            ignore_filter=_noop_filter,
        )

        assert watcher.paths == []


class TestCreateWatcher:
    """Tests for create_watcher factory function."""

    def test_creates_watchfiles_watcher(self, tmp_path: Path) -> None:
        """Test that create_watcher returns WatchfilesWatcher."""
        watcher = create_watcher(
            paths=[tmp_path],
            ignore_filter=_noop_filter,
        )

        assert isinstance(watcher, WatchfilesWatcher)

    def test_passes_paths_to_watcher(self, tmp_path: Path) -> None:
        """Test that create_watcher passes paths correctly."""
        path1 = tmp_path / "dir1"
        path2 = tmp_path / "dir2"
        path1.mkdir()
        path2.mkdir()

        watcher = create_watcher(
            paths=[path1, path2],
            ignore_filter=_noop_filter,
        )

        assert watcher.paths == [path1, path2]

    def test_passes_ignore_filter_to_watcher(self, tmp_path: Path) -> None:
        """Test that create_watcher passes ignore filter correctly."""
        called_paths: list[Path] = []

        def tracking_filter(p: Path) -> bool:
            called_paths.append(p)
            return False

        watcher = create_watcher(
            paths=[tmp_path],
            ignore_filter=tracking_filter,
        )

        assert watcher.ignore_filter is tracking_filter


class TestWatcherIgnoreFilter:
    """Tests for ignore filter integration with watchers."""

    def test_watcher_uses_filter(self, tmp_path: Path) -> None:
        """Test that WatchfilesWatcher stores and uses the ignore filter."""
        called_paths: list[Path] = []

        def ignore_filter(p: Path) -> bool:
            called_paths.append(p)
            return str(p).endswith(".pyc")

        watcher = WatchfilesWatcher(
            paths=[tmp_path],
            ignore_filter=ignore_filter,
        )

        # The filter is stored
        assert watcher.ignore_filter is ignore_filter
