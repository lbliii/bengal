"""Tests for WatcherRunner."""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from bengal.server.ignore_filter import IgnoreFilter
from bengal.server.watcher_runner import WatcherRunner, _WatcherState, create_watcher_runner

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class _FakeWatcher:
    def __init__(self, stop_event: asyncio.Event | None) -> None:
        self.stop_event = stop_event

    async def watch(self) -> AsyncIterator[tuple[set[Path], set[str]]]:
        while self.stop_event is not None and not self.stop_event.is_set():
            await asyncio.sleep(0.01)
        if False:
            yield set(), set()


@pytest.fixture
def fake_watcher(monkeypatch: pytest.MonkeyPatch) -> None:
    def create_fake_watcher(
        paths: list[Path],
        ignore_filter: IgnoreFilter,
        stop_event: asyncio.Event | None,
        force_polling: bool | None = None,
    ) -> _FakeWatcher:
        _ = paths, ignore_filter, force_polling
        return _FakeWatcher(stop_event)

    monkeypatch.setattr("bengal.server.watcher_runner.create_watcher", create_fake_watcher)


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
        assert runner._state is _WatcherState.NEW

    def test_start_creates_thread(self, fake_watcher: None) -> None:
        """Test that start creates a background thread."""
        runner = WatcherRunner(
            paths=[Path(".")],
            ignore_filter=IgnoreFilter(),
            on_changes=MagicMock(),
        )

        assert runner._thread is None

        runner.start()
        try:
            assert runner._ready_event.wait(timeout=5.0)
            assert runner._thread is not None
            assert runner._thread.is_alive()
            assert runner._state is _WatcherState.RUNNING
        finally:
            runner.stop()

    def test_stop_cleans_up(self, fake_watcher: None) -> None:
        """Test that stop cleans up the thread."""
        runner = WatcherRunner(
            paths=[Path(".")],
            ignore_filter=IgnoreFilter(),
            on_changes=MagicMock(),
        )

        runner.start()
        runner.stop()

        assert runner._thread is None
        assert runner._state is _WatcherState.STOPPED

    def test_double_start_is_idempotent(self, fake_watcher: None) -> None:
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

    def test_double_stop_is_idempotent(self, fake_watcher: None) -> None:
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

    def test_stop_handles_closed_loop_race(self) -> None:
        """Test stop tolerates the watcher thread closing its loop first."""
        runner = WatcherRunner(
            paths=[Path(".")],
            ignore_filter=IgnoreFilter(),
            on_changes=MagicMock(),
        )
        loop = asyncio.new_event_loop()
        loop.close()
        thread = MagicMock()
        thread.is_alive.return_value = False

        runner._thread = thread
        runner._loop = loop
        runner._async_stop_event = MagicMock()
        runner._state = _WatcherState.RUNNING

        runner.stop()

        assert runner._thread is None
        assert runner._state is _WatcherState.STOPPED

    def test_stop_before_loop_is_published(self) -> None:
        """Test stop can complete before the watcher thread publishes its loop."""
        runner = WatcherRunner(
            paths=[Path(".")],
            ignore_filter=IgnoreFilter(),
            on_changes=MagicMock(),
        )
        thread = MagicMock()
        thread.is_alive.return_value = False

        runner._thread = thread
        runner._state = _WatcherState.STARTING
        runner._READY_TIMEOUT_SECONDS = 0.01

        runner.stop()

        assert runner._thread is None
        assert runner._loop is None
        assert runner._async_stop_event is None
        assert runner._state is _WatcherState.STOPPED

    def test_double_stop_during_stopping_is_idempotent(self) -> None:
        """Test a second stop call during shutdown joins and cleans up."""
        runner = WatcherRunner(
            paths=[Path(".")],
            ignore_filter=IgnoreFilter(),
            on_changes=MagicMock(),
        )
        thread = MagicMock()
        thread.is_alive.return_value = False

        runner._thread = thread
        runner._state = _WatcherState.STOPPING
        runner._JOIN_TIMEOUT_SECONDS = 0.01

        runner.stop()

        thread.join.assert_called_once_with(timeout=0.01)
        assert runner._thread is None
        assert runner._state is _WatcherState.STOPPED

    def test_start_while_starting_is_idempotent(self) -> None:
        """Test start does not create a second thread while startup is in progress."""
        runner = WatcherRunner(
            paths=[Path(".")],
            ignore_filter=IgnoreFilter(),
            on_changes=MagicMock(),
        )
        thread = MagicMock()

        runner._thread = thread
        runner._state = _WatcherState.STARTING

        runner.start()

        assert runner._thread is thread

    def test_concurrent_stop_during_thread_start_does_not_join_unstarted_thread(
        self, fake_watcher: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test stop cannot join the watcher thread before start() starts it."""
        runner = WatcherRunner(
            paths=[Path(".")],
            ignore_filter=IgnoreFilter(),
            on_changes=MagicMock(),
        )
        real_thread_class = threading.Thread
        thread_start_entered = threading.Event()
        stop_attempt_started = threading.Event()
        stop_errors: list[BaseException] = []

        class SlowStartThread:
            def __init__(self, target, daemon=False):
                self._thread = real_thread_class(target=target, daemon=daemon)
                self._started = False

            def start(self) -> None:
                thread_start_entered.set()
                stop_attempt_started.wait(timeout=1.0)
                time.sleep(0.01)
                self._thread.start()
                self._started = True

            def join(self, timeout=None) -> None:
                if not self._started:
                    msg = "cannot join thread before it is started"
                    raise RuntimeError(msg)
                self._thread.join(timeout=timeout)

            def is_alive(self) -> bool:
                return self._started and self._thread.is_alive()

        def stop_runner() -> None:
            stop_attempt_started.set()
            try:
                runner.stop()
            except BaseException as e:
                stop_errors.append(e)

        monkeypatch.setattr("bengal.server.watcher_runner.threading.Thread", SlowStartThread)

        starter = real_thread_class(target=runner.start)
        stopper = real_thread_class(target=stop_runner)

        starter.start()
        assert thread_start_entered.wait(timeout=1.0)
        stopper.start()
        starter.join(timeout=2.0)
        stopper.join(timeout=2.0)

        try:
            assert not starter.is_alive()
            assert not stopper.is_alive()
            assert stop_errors == []
        finally:
            runner.stop()

    def test_run_failure_before_ready_marks_failed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test thread startup failures unblock waiters and record failure state."""
        runner = WatcherRunner(
            paths=[Path(".")],
            ignore_filter=IgnoreFilter(),
            on_changes=MagicMock(),
        )

        def fail_new_event_loop():
            msg = "loop unavailable"
            raise RuntimeError(msg)

        monkeypatch.setattr(asyncio, "new_event_loop", fail_new_event_loop)

        runner._run()

        assert runner._ready_event.is_set()
        assert runner._stopped_event.is_set()
        assert runner._state is _WatcherState.FAILED
        assert isinstance(runner._failure, RuntimeError)

    def test_force_stop_timeout_marks_failed(self) -> None:
        """Test a watcher thread that ignores force-stop is marked failed."""
        runner = WatcherRunner(
            paths=[Path(".")],
            ignore_filter=IgnoreFilter(),
            on_changes=MagicMock(),
        )
        loop = MagicMock()
        thread = MagicMock()
        thread.is_alive.return_value = True

        runner._thread = thread
        runner._loop = loop
        runner._state = _WatcherState.RUNNING
        runner._JOIN_TIMEOUT_SECONDS = 0.01
        runner._FORCE_JOIN_TIMEOUT_SECONDS = 0.01

        runner.stop()

        assert thread.join.call_count == 2
        assert loop.call_soon_threadsafe.call_count == 1
        assert runner._thread is None
        assert runner._state is _WatcherState.FAILED
        assert isinstance(runner._failure, RuntimeError)


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


class TestWatcherRunnerEventTypes:
    """Tests for WatcherRunner event type handling."""

    def test_initializes_empty_event_types(self) -> None:
        """Test that WatcherRunner initializes with empty pending event types."""
        runner = WatcherRunner(
            paths=[Path(".")],
            ignore_filter=IgnoreFilter(),
            on_changes=MagicMock(),
        )

        assert runner._pending_event_types == set()

    def test_callback_receives_event_types(self) -> None:
        """Test that the callback signature includes event types.

        The on_changes callback should receive (set[Path], set[str]) where
        the second argument contains event type strings like 'created',
        'modified', 'deleted'.
        """
        callback = MagicMock()

        runner = WatcherRunner(
            paths=[Path(".")],
            ignore_filter=IgnoreFilter(),
            on_changes=callback,
        )

        # Verify the callback type matches expected signature
        # This is a static check that the callback will be called correctly
        assert runner.on_changes is callback

        # Simulate what _debounce_loop does when calling the callback
        test_paths = {Path("test.md")}
        test_event_types = {"created", "modified"}

        # This mimics the callback invocation in _debounce_loop
        runner.on_changes(test_paths, test_event_types)

        callback.assert_called_once_with(test_paths, test_event_types)

    def test_pending_event_types_accumulate(self) -> None:
        """Test that pending event types accumulate from multiple changes."""
        runner = WatcherRunner(
            paths=[Path(".")],
            ignore_filter=IgnoreFilter(),
            on_changes=MagicMock(),
        )

        # Simulate accumulating event types (what _process_changes does)
        with runner._changes_lock:
            runner._pending_changes.add(Path("new.md"))
            runner._pending_event_types.add("created")

        with runner._changes_lock:
            runner._pending_changes.add(Path("existing.md"))
            runner._pending_event_types.add("modified")

        assert runner._pending_event_types == {"created", "modified"}
        assert len(runner._pending_changes) == 2

    def test_event_types_cleared_after_callback(self) -> None:
        """Test that event types are cleared after callback (simulated)."""
        runner = WatcherRunner(
            paths=[Path(".")],
            ignore_filter=IgnoreFilter(),
            on_changes=MagicMock(),
        )

        # Simulate what happens in _debounce_loop
        with runner._changes_lock:
            runner._pending_changes.add(Path("test.md"))
            runner._pending_event_types.add("modified")

        # Simulate clearing (what _debounce_loop does after callback)
        with runner._changes_lock:
            changes = runner._pending_changes.copy()
            event_types = runner._pending_event_types.copy()
            runner._pending_changes.clear()
            runner._pending_event_types.clear()

        assert changes == {Path("test.md")}
        assert event_types == {"modified"}
        assert runner._pending_changes == set()
        assert runner._pending_event_types == set()
