"""
Tests for BuildHandler concurrency and failure recovery scenarios.

These tests verify that:
1. File changes during a build are queued and processed after
2. Build failures properly reset state (no stuck build_in_progress)
3. Debouncing correctly batches rapid changes
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.server.build_handler import BuildHandler
from bengal.server.request_handler import BengalRequestHandler


class DummyStats:
    """Dummy build stats for testing."""

    def __init__(self):
        self.total_pages = 1
        self.build_time_ms = 100
        self.incremental = True
        self.parallel = True
        self.skipped = False
        self.changed_outputs = None


class DummySite:
    """Dummy site for testing."""

    def __init__(self, root_path):
        self.root_path = root_path
        self.output_dir = root_path / "public"
        self.pages = []
        self.sections = []
        self.assets = []
        self.config = {}
        self.theme = None
        self._build_count = 0
        self._build_delay = 0

    def build(self, *args, **kwargs):
        self._build_count += 1
        if self._build_delay > 0:
            time.sleep(self._build_delay)
        return DummyStats()

    def invalidate_regular_pages_cache(self):
        pass

    def reset_ephemeral_state(self):
        pass


def _make_handler(tmp_path) -> BuildHandler:
    """Create a BuildHandler for testing."""
    site = DummySite(tmp_path)
    handler = BuildHandler(site, host="localhost", port=5173)
    return handler


class TestBuildInProgressState:
    """Test build_in_progress state management."""

    def test_build_sets_in_progress_then_clears(self, tmp_path, monkeypatch):
        """Build should set in_progress=True at start and False at end."""
        handler = _make_handler(tmp_path)

        states_during_build = []

        original_build = handler.site.build

        def capturing_build(*args, **kwargs):
            # Capture state during build
            with BengalRequestHandler._build_lock:
                states_during_build.append(BengalRequestHandler._build_in_progress)
            return original_build(*args, **kwargs)

        handler.site.build = capturing_build
        handler.pending_changes = {str(tmp_path / "content" / "page.md")}

        # Silence output
        monkeypatch.setattr(
            "bengal.server.build_handler.display_build_stats", lambda *a, **k: None
        )
        monkeypatch.setattr(
            "bengal.server.build_handler.show_building_indicator", lambda *a, **k: None
        )

        # Reset state before test
        BengalRequestHandler.set_build_in_progress(False)

        with (
            patch("bengal.server.reload_controller.controller") as mock_controller,
            patch("bengal.server.live_reload.send_reload_payload", lambda *a, **k: None),
        ):
            from bengal.server.reload_controller import ReloadDecision

            mock_controller.decide_and_update.return_value = ReloadDecision(
                action="reload", reason="content-changed", changed_paths=[]
            )
            handler._trigger_build()

        # State during build should have been True
        assert any(states_during_build), "build_in_progress should be True during build"

        # State after build should be False
        with BengalRequestHandler._build_lock:
            assert not BengalRequestHandler._build_in_progress

    def test_build_failure_clears_in_progress_state(self, tmp_path, monkeypatch):
        """If build() raises an exception, in_progress should still be cleared."""
        handler = _make_handler(tmp_path)

        def failing_build(*args, **kwargs):
            raise RuntimeError("Simulated build failure")

        handler.site.build = failing_build
        handler.pending_changes = {str(tmp_path / "content" / "page.md")}

        # Silence output
        monkeypatch.setattr(
            "bengal.server.build_handler.display_build_stats", lambda *a, **k: None
        )
        monkeypatch.setattr(
            "bengal.server.build_handler.show_building_indicator", lambda *a, **k: None
        )

        # Reset state before test
        BengalRequestHandler.set_build_in_progress(False)

        # Build will fail, but state should be cleaned up
        with (
            patch("bengal.server.reload_controller.controller"),
            patch("bengal.server.live_reload.send_reload_payload", lambda *a, **k: None),
        ):
            handler._trigger_build()

        # State should be False even after failure
        with BengalRequestHandler._build_lock:
            assert not BengalRequestHandler._build_in_progress


class TestConcurrentFileChanges:
    """Test behavior when file changes occur during build."""

    def test_changes_during_build_are_queued(self, tmp_path, monkeypatch):
        """File changes during a build should be queued for next build."""
        handler = _make_handler(tmp_path)

        build_started = threading.Event()
        allow_build_finish = threading.Event()
        queued_changes_during_build = []

        def slow_build(*args, **kwargs):
            build_started.set()
            # Wait for test to queue changes
            allow_build_finish.wait(timeout=5)
            # Capture pending changes that accumulated
            queued_changes_during_build.extend(handler.pending_changes)
            return DummyStats()

        handler.site.build = slow_build
        handler.pending_changes = {str(tmp_path / "content" / "page1.md")}

        monkeypatch.setattr(
            "bengal.server.build_handler.display_build_stats", lambda *a, **k: None
        )
        monkeypatch.setattr(
            "bengal.server.build_handler.show_building_indicator", lambda *a, **k: None
        )

        with (
            patch("bengal.server.reload_controller.controller") as mock_ctrl,
            patch("bengal.server.live_reload.send_reload_payload", lambda *a, **k: None),
        ):
            from bengal.server.reload_controller import ReloadDecision

            mock_ctrl.decide_and_update.return_value = ReloadDecision(
                action="reload", reason="content", changed_paths=[]
            )

            # Start build in background
            build_thread = threading.Thread(target=handler._trigger_build)
            build_thread.start()

            # Wait for build to start
            build_started.wait(timeout=5)

            # Simulate file change during build (add to pending)
            new_change = str(tmp_path / "content" / "page2.md")
            handler.pending_changes.add(new_change)

            # Let build finish
            allow_build_finish.set()
            build_thread.join(timeout=5)

        # The change during build was captured
        assert new_change in queued_changes_during_build

    def test_debounce_batches_rapid_changes(self, tmp_path, monkeypatch):
        """Multiple rapid file changes should be batched via debouncing."""
        handler = _make_handler(tmp_path)

        # Simulate multiple rapid changes
        files = [
            str(tmp_path / "content" / f"page{i}.md")
            for i in range(5)
        ]

        for f in files:
            event = MagicMock()
            event.is_directory = False
            event.src_path = f
            handler.on_modified(event)

        # All changes should be in pending_changes
        assert len(handler.pending_changes) == 5
        for f in files:
            assert f in handler.pending_changes

        # There should be only one debounce timer (not 5)
        assert handler.debounce_timer is not None


class TestBuildHandlerBuildingFlag:
    """Test the internal 'building' flag to prevent concurrent builds."""

    def test_building_flag_prevents_concurrent_builds(self, tmp_path, monkeypatch):
        """Setting building=True should prevent _trigger_build from running."""
        handler = _make_handler(tmp_path)
        handler.building = True

        build_called = False
        original_build = handler.site.build

        def tracking_build(*args, **kwargs):
            nonlocal build_called
            build_called = True
            return original_build(*args, **kwargs)

        handler.site.build = tracking_build
        handler.pending_changes = {str(tmp_path / "content" / "page.md")}

        monkeypatch.setattr(
            "bengal.server.build_handler.display_build_stats", lambda *a, **k: None
        )
        monkeypatch.setattr(
            "bengal.server.build_handler.show_building_indicator", lambda *a, **k: None
        )

        with (
            patch("bengal.server.reload_controller.controller"),
            patch("bengal.server.live_reload.send_reload_payload", lambda *a, **k: None),
        ):
            handler._trigger_build()

        # Build should not have been called because building=True
        assert not build_called

    def test_building_flag_cleared_after_build(self, tmp_path, monkeypatch):
        """The building flag should be cleared after build completes."""
        handler = _make_handler(tmp_path)
        handler.pending_changes = {str(tmp_path / "content" / "page.md")}

        monkeypatch.setattr(
            "bengal.server.build_handler.display_build_stats", lambda *a, **k: None
        )
        monkeypatch.setattr(
            "bengal.server.build_handler.show_building_indicator", lambda *a, **k: None
        )

        assert not handler.building

        with (
            patch("bengal.server.reload_controller.controller") as mock_ctrl,
            patch("bengal.server.live_reload.send_reload_payload", lambda *a, **k: None),
        ):
            from bengal.server.reload_controller import ReloadDecision

            mock_ctrl.decide_and_update.return_value = ReloadDecision(
                action="reload", reason="content", changed_paths=[]
            )
            handler._trigger_build()

        # building flag should be False after build
        assert not handler.building

    def test_building_flag_cleared_on_failure(self, tmp_path, monkeypatch):
        """The building flag should be cleared even if build fails."""
        handler = _make_handler(tmp_path)
        handler.pending_changes = {str(tmp_path / "content" / "page.md")}

        def failing_build(*args, **kwargs):
            raise RuntimeError("Build failed")

        handler.site.build = failing_build

        monkeypatch.setattr(
            "bengal.server.build_handler.display_build_stats", lambda *a, **k: None
        )
        monkeypatch.setattr(
            "bengal.server.build_handler.show_building_indicator", lambda *a, **k: None
        )

        with (
            patch("bengal.server.reload_controller.controller"),
            patch("bengal.server.live_reload.send_reload_payload", lambda *a, **k: None),
        ):
            handler._trigger_build()

        # building flag should still be False after failed build
        assert not handler.building

