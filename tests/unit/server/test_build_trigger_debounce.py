"""Tests for BuildTrigger debounce/coalesce."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.server.build_trigger import BuildTrigger


class TestBuildTriggerQueuing:
    """Tests for BuildTrigger change queuing during builds.

    When a build is in progress, changes should be queued instead of discarded.
    This prevents lost changes during rapid editing (important for autodoc pages).

    """

    @pytest.fixture
    def mock_site(self) -> MagicMock:
        """Create a mock site for testing."""
        site = MagicMock()
        site.root_path = Path("/test/site")
        site.output_dir = Path("/test/site/public")
        site.config = {}
        site.theme = None
        return site

    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        """Create a mock executor for testing."""
        executor = MagicMock()
        result = MagicMock()
        result.success = True
        result.pages_built = 5
        result.build_time_ms = 100.0
        result.error_message = None
        result.changed_outputs = ()
        executor.submit.return_value = result
        return executor

    def test_pending_changes_initialized_empty(
        self, mock_site: MagicMock, mock_executor: MagicMock
    ) -> None:
        """Test that pending changes are initialized as empty sets."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        assert trigger._pending_changes == set()
        assert trigger._pending_event_types == set()

    @patch("bengal.server.build_trigger.execute.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.execute.run_post_build_hooks")
    @patch("bengal.server.build_trigger.execute.show_building_indicator")
    @patch("bengal.server.build_trigger.execute.get_cli_output")
    @patch("bengal.server.build_trigger.reload.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_changes_queued_when_build_in_progress(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_display: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_post_hooks: MagicMock,
        mock_pre_hooks: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that changes are queued when a build is in progress."""
        import threading

        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        # Control build timing via site.build (warm builds call it directly)
        build_started = threading.Event()
        build_can_finish = threading.Event()

        def slow_build(*args, **kwargs):
            build_started.set()
            build_can_finish.wait(timeout=5.0)
            stats = MagicMock()
            stats.total_pages = 5
            stats.changed_outputs = []
            return stats

        mock_site.build.side_effect = slow_build

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Start first build in background thread
        first_build = threading.Thread(
            target=trigger.trigger_build,
            args=({Path("first.md")}, {"modified"}),
        )
        first_build.start()

        # Wait for first build to start
        build_started.wait(timeout=5.0)

        # Try to trigger second build while first is in progress
        trigger.trigger_build({Path("second.md")}, {"created"})

        # Changes should be queued
        assert Path("second.md") in trigger._pending_changes
        assert "created" in trigger._pending_event_types

        # Let first build finish
        build_can_finish.set()
        first_build.join(timeout=5.0)

    @patch("bengal.server.build_trigger.execute.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.execute.run_post_build_hooks")
    @patch("bengal.server.build_trigger.execute.show_building_indicator")
    @patch("bengal.server.build_trigger.execute.get_cli_output")
    @patch("bengal.server.build_trigger.reload.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_queued_changes_trigger_another_build(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_display: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_post_hooks: MagicMock,
        mock_pre_hooks: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that queued changes trigger another build after first completes."""
        import threading

        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        # Track build calls via site.build (warm builds)
        build_call_count = 0
        build_started = threading.Event()
        build_can_finish = threading.Event()

        def tracking_build(*args, **kwargs):
            nonlocal build_call_count
            build_call_count += 1
            if build_call_count == 1:
                build_started.set()
                build_can_finish.wait(timeout=5.0)
            stats = MagicMock()
            stats.total_pages = 5
            stats.changed_outputs = []
            return stats

        mock_site.build.side_effect = tracking_build

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Start first build in background thread
        first_build = threading.Thread(
            target=trigger.trigger_build,
            args=({Path("first.md")}, {"modified"}),
        )
        first_build.start()

        # Wait for first build to start
        build_started.wait(timeout=5.0)

        # Queue a second change
        trigger.trigger_build({Path("second.md")}, {"created"})

        # Let first build finish (which should trigger second build)
        build_can_finish.set()
        first_build.join(timeout=5.0)

        # Should have two builds: first + queued
        assert mock_site.build.call_count == 2

    @patch("bengal.server.build_trigger.execute.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.execute.run_post_build_hooks")
    @patch("bengal.server.build_trigger.execute.show_building_indicator")
    @patch("bengal.server.build_trigger.execute.get_cli_output")
    @patch("bengal.server.build_trigger.reload.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_multiple_queued_changes_batched(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_display: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_post_hooks: MagicMock,
        mock_pre_hooks: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that multiple queued changes are batched into a single build."""
        import threading

        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        build_call_count = 0
        build_started = threading.Event()
        build_can_finish = threading.Event()

        def tracking_build(*args, **kwargs):
            nonlocal build_call_count
            build_call_count += 1
            if build_call_count == 1:
                build_started.set()
                build_can_finish.wait(timeout=5.0)
            stats = MagicMock()
            stats.total_pages = 5
            stats.changed_outputs = []
            return stats

        mock_site.build.side_effect = tracking_build

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Start first build
        first_build = threading.Thread(
            target=trigger.trigger_build,
            args=({Path("first.md")}, {"modified"}),
        )
        first_build.start()
        build_started.wait(timeout=5.0)

        # Queue multiple changes while first build is running
        trigger.trigger_build({Path("second.md")}, {"created"})
        trigger.trigger_build({Path("third.md")}, {"modified"})
        trigger.trigger_build({Path("fourth.md")}, {"deleted"})

        # All should be queued
        assert len(trigger._pending_changes) == 3
        assert {"created", "modified", "deleted"} == trigger._pending_event_types

        # Let first build finish
        build_can_finish.set()
        first_build.join(timeout=5.0)

        # Should have exactly 2 builds: first + batched queued changes
        assert mock_site.build.call_count == 2

    @patch("bengal.server.build_trigger.execute.time.sleep")
    @patch("bengal.server.build_trigger.execute.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.execute.run_post_build_hooks")
    @patch("bengal.server.build_trigger.execute.show_building_indicator")
    @patch("bengal.server.build_trigger.execute.get_cli_output")
    @patch("bengal.server.build_trigger.reload.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_no_stabilization_delay_with_double_buffer(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_display: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_post_hooks: MagicMock,
        mock_pre_hooks: MagicMock,
        mock_sleep: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Double-buffered output eliminates the need for stabilization delays.

        Queued builds execute immediately because the ASGI app serves from the
        active buffer, which is never written to during a build.
        """
        import threading

        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        build_call_count = 0
        build_started = threading.Event()
        build_can_finish = threading.Event()

        def tracking_build(*args, **kwargs):
            nonlocal build_call_count
            build_call_count += 1
            if build_call_count == 1:
                build_started.set()
                build_can_finish.wait(timeout=5.0)
            stats = MagicMock()
            stats.total_pages = 5
            stats.changed_outputs = []
            return stats

        mock_site.build.side_effect = tracking_build

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        first_build = threading.Thread(
            target=trigger.trigger_build,
            args=({Path("first.md")}, {"modified"}),
        )
        first_build.start()
        build_started.wait(timeout=5.0)

        trigger.trigger_build({Path("second.md")}, {"created"})

        build_can_finish.set()
        first_build.join(timeout=5.0)

        assert mock_site.build.call_count == 2
        mock_sleep.assert_not_called()


class TestBuildStabilizationTiming:
    """Tests for build stabilization timing behavior."""

    @pytest.fixture
    def mock_site(self) -> MagicMock:
        """Create a mock site for testing."""
        site = MagicMock()
        site.content_dir = Path("/test/site/content")
        site.output_dir = Path("/test/site/public")
        site.config = {}
        site.theme = None
        return site

    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        """Create a mock executor for testing."""
        executor = MagicMock()
        result = MagicMock()
        result.success = True
        result.pages_built = 5
        result.build_time_ms = 100.0
        result.error_message = None
        result.changed_outputs = ()
        executor.submit.return_value = result
        return executor

    @patch("bengal.server.build_trigger.execute.time.sleep")
    @patch("bengal.server.build_trigger.execute.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.execute.run_post_build_hooks")
    @patch("bengal.server.build_trigger.execute.show_building_indicator")
    @patch("bengal.server.build_trigger.execute.get_cli_output")
    @patch("bengal.server.build_trigger.reload.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_no_delay_for_first_build(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_display: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_post_hooks: MagicMock,
        mock_pre_hooks: MagicMock,
        mock_sleep: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that no stabilization delay is applied for the first build.

        The delay only applies when triggering a queued build after
        another build completes.
        """
        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True
        mock_controller.decide_from_changed_paths.return_value = MagicMock(
            action="reload", reason="test", changed_paths=()
        )

        sleep_calls = []

        def instant_submit(request, **kwargs):
            result = MagicMock()
            result.success = True
            result.pages_built = 5
            result.build_time_ms = 100.0
            result.error_message = None
            result.changed_outputs = ()
            return result

        def tracking_sleep(seconds):
            sleep_calls.append(seconds)

        mock_executor.submit.side_effect = instant_submit
        mock_sleep.side_effect = tracking_sleep

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Single build (no queued changes)
        trigger.trigger_build({Path("only.md")}, {"modified"})

        # No stabilization delay should have been called
        # (we only delay when processing queued changes)
        assert 0.1 not in sleep_calls, f"Unexpected delay for first build: {sleep_calls}"
