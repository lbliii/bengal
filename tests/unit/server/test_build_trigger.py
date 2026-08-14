"""Tests for BuildTrigger facade."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.orchestration.build.options import BuildCompletionPolicy
from bengal.orchestration.stats import ReloadHint
from bengal.server.build_trigger import BuildTrigger
from bengal.server.reload_types import BuildReloadInfo, SerializedOutputRecord


class TestBuildTrigger:
    """Tests for BuildTrigger facade."""

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

    def test_init(self, mock_site: MagicMock, mock_executor: MagicMock) -> None:
        """Test BuildTrigger initialization."""
        trigger = BuildTrigger(
            site=mock_site,
            host="localhost",
            port=5173,
            executor=mock_executor,
        )

        assert trigger.site is mock_site
        assert trigger.host == "localhost"
        assert trigger.port == 5173
        assert trigger._executor is mock_executor
        assert trigger.completion_policy is BuildCompletionPolicy.SERVE_READY

    def test_init_with_completion_policy(
        self, mock_site: MagicMock, mock_executor: MagicMock
    ) -> None:
        """Test BuildTrigger initialization with complete rebuild policy."""
        trigger = BuildTrigger(
            site=mock_site,
            host="localhost",
            port=5173,
            executor=mock_executor,
            completion_policy=BuildCompletionPolicy.COMPLETE,
        )

        assert trigger.completion_policy is BuildCompletionPolicy.COMPLETE

    def test_skips_content_hash_baseline_for_typed_watcher_rebuild(
        self, mock_site: MagicMock, mock_executor: MagicMock
    ) -> None:
        """Normal watcher rebuilds use typed outputs instead of pre-build tree scans."""
        controller = MagicMock()
        controller._use_content_hashes = True
        trigger = BuildTrigger(site=mock_site, executor=mock_executor, controller=controller)

        assert trigger._should_capture_content_hash_baseline(["content/page.md"]) is False
        assert trigger._should_capture_content_hash_baseline([]) is True

    def test_shutdown_calls_executor_shutdown(
        self, mock_site: MagicMock, mock_executor: MagicMock
    ) -> None:
        """Test that shutdown calls executor shutdown."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)
        trigger.shutdown()

        mock_executor.shutdown.assert_called_once_with(wait=True)


class TestVersionScopedBuilds:
    """
    Tests for version-scoped build functionality.

    RFC: rfc-versioned-docs-pipeline-integration (Phase 3)

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

    def test_init_with_version_scope(self, mock_site: MagicMock, mock_executor: MagicMock) -> None:
        """Test BuildTrigger initialization with version_scope."""
        trigger = BuildTrigger(
            site=mock_site,
            host="localhost",
            port=5173,
            executor=mock_executor,
            version_scope="v2",
        )

        assert trigger.version_scope == "v2"

    def test_init_without_version_scope(
        self, mock_site: MagicMock, mock_executor: MagicMock
    ) -> None:
        """Test BuildTrigger initialization without version_scope."""
        trigger = BuildTrigger(
            site=mock_site,
            host="localhost",
            port=5173,
            executor=mock_executor,
        )

        assert trigger.version_scope is None

    @patch("bengal.server.build_trigger.execute.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.execute.run_post_build_hooks")
    @patch("bengal.server.build_trigger.execute.show_building_indicator")
    @patch("bengal.server.build_trigger.execute.get_cli_output")
    @patch("bengal.server.build_trigger.reload.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_version_scope_passed_to_build_request(
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
        """Test that version_scope is applied to site config before warm build."""
        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        # mock_site.build() must return a real stats object for warm build
        mock_stats = MagicMock()
        mock_stats.total_pages = 5
        mock_stats.changed_outputs = []
        mock_site.build.return_value = mock_stats

        trigger = BuildTrigger(
            site=mock_site,
            executor=mock_executor,
            version_scope="v2",
        )

        trigger.trigger_build(
            changed_paths={Path("test.md")},
            event_types={"modified"},
        )

        # Warm builds call site.build() directly (not executor.submit)
        mock_site.build.assert_called_once()
        # Version scope is set on site.config before build
        assert mock_site.config["_version_scope"] == "v2"

    @patch("bengal.server.build_trigger.execute.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.execute.run_post_build_hooks")
    @patch("bengal.server.build_trigger.execute.show_building_indicator")
    @patch("bengal.server.build_trigger.execute.get_cli_output")
    @patch("bengal.server.build_trigger.reload.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_no_version_scope_in_build_request(
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
        """Test that site.config has no _version_scope when not set."""
        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        mock_stats = MagicMock()
        mock_stats.total_pages = 5
        mock_stats.changed_outputs = []
        mock_site.build.return_value = mock_stats

        trigger = BuildTrigger(
            site=mock_site,
            executor=mock_executor,
        )

        trigger.trigger_build(
            changed_paths={Path("test.md")},
            event_types={"modified"},
        )

        mock_site.build.assert_called_once()
        assert "_version_scope" not in mock_site.config


class TestBuildTriggerIntegration:
    """Integration tests for BuildTrigger."""

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

    @patch("bengal.server.build_trigger.execute.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.execute.run_post_build_hooks")
    @patch("bengal.server.build_trigger.execute.show_building_indicator")
    @patch("bengal.server.build_trigger.execute.get_cli_output")
    @patch("bengal.server.build_trigger.reload.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_trigger_build_calls_site_build(
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
        """Test that trigger_build calls site.build() directly (warm build)."""
        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        mock_stats = MagicMock()
        mock_stats.total_pages = 5
        mock_stats.changed_outputs = []
        mock_site.build.return_value = mock_stats

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        trigger.trigger_build(
            changed_paths={Path("test.md")},
            event_types={"modified"},
        )

        # Warm builds call site.build() directly
        mock_site.build.assert_called_once()
        build_opts = mock_site.build.call_args[1]["options"]
        assert Path("test.md") in build_opts.changed_sources
        assert build_opts.completion_policy is BuildCompletionPolicy.SERVE_READY

    @patch("bengal.server.build_trigger.execute.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.execute.run_post_build_hooks")
    @patch("bengal.server.build_trigger.execute.show_building_indicator")
    @patch("bengal.server.build_trigger.execute.get_cli_output")
    @patch("bengal.server.build_trigger.reload.display_build_stats")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_trigger_build_uses_configured_completion_policy(
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
        """Watched builds should honor the dev server completion policy."""
        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True

        mock_stats = MagicMock()
        mock_stats.total_pages = 5
        mock_stats.changed_outputs = []
        mock_site.build.return_value = mock_stats

        trigger = BuildTrigger(
            site=mock_site,
            executor=mock_executor,
            completion_policy=BuildCompletionPolicy.COMPLETE,
        )

        trigger.trigger_build(
            changed_paths={Path("test.md")},
            event_types={"modified"},
        )

        build_opts = mock_site.build.call_args[1]["options"]
        assert build_opts.completion_policy is BuildCompletionPolicy.COMPLETE


class TestBuildTriggerErrorHandling:
    """
    Tests for BuildTrigger error handling.

    BUG FIX: Error handling should not mutate the changed_paths set.
    Previously, using set.pop() would modify the set unexpectedly.
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
        """Create a mock executor that raises an exception."""
        executor = MagicMock()
        executor.submit.side_effect = RuntimeError("Build failed")
        return executor

    @patch("bengal.server.build_trigger.execute.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.execute.show_building_indicator")
    @patch("bengal.server.build_trigger.execute.get_cli_output")
    @patch("bengal.server.build_trigger.execute.show_error")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.build_trigger.execute.create_dev_error")
    @patch("bengal.server.build_trigger.execute.get_dev_server_state")
    def test_changed_paths_not_mutated_on_error(
        self,
        mock_get_state: MagicMock,
        mock_create_error: MagicMock,
        mock_controller: MagicMock,
        mock_show_error: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_pre_hooks: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """
        Test that changed_paths set is not mutated during error handling.

        BUG FIX: Previously used set.pop() which would modify the set.
        Now uses next(iter(...)) which doesn't modify the set.
        """
        mock_pre_hooks.return_value = True
        mock_state = MagicMock()
        mock_state.record_failure.return_value = True
        mock_get_state.return_value = mock_state
        mock_context = MagicMock()
        mock_context.get_likely_cause.return_value = "test"
        mock_context.quick_actions = []
        mock_context.auto_fixable = False
        mock_context.auto_fix_command = None
        mock_create_error.return_value = mock_context

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create a set of changed paths
        original_paths = {Path("a.md"), Path("b.md"), Path("c.md")}
        paths_copy = original_paths.copy()

        # Trigger build which will raise an exception
        trigger.trigger_build(paths_copy, {"modified"})

        # The set should NOT have been modified by the error handler
        # (Previously, pop() would remove an element)
        assert len(paths_copy) == 3
        assert paths_copy == original_paths

    @patch("bengal.server.build_trigger.execute.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.execute.show_building_indicator")
    @patch("bengal.server.build_trigger.execute.get_cli_output")
    @patch("bengal.server.build_trigger.execute.show_error")
    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.build_trigger.execute.get_dev_server_state")
    def test_trigger_file_extracted_without_mutation(
        self,
        mock_get_state: MagicMock,
        mock_controller: MagicMock,
        mock_show_error: MagicMock,
        mock_cli: MagicMock,
        mock_building: MagicMock,
        mock_pre_hooks: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that trigger_file is extracted without modifying the set.

        The warm build path calls site.build() directly, so we make that
        raise to exercise the error handler (the executor mock is unused
        because warm builds bypass subprocess execution).
        """
        mock_pre_hooks.return_value = True
        mock_state = MagicMock()
        mock_state.record_failure.return_value = True
        mock_get_state.return_value = mock_state
        # Make site.build() raise so the error handler runs
        mock_site.build.side_effect = RuntimeError("Build failed")

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        paths = {Path("test.md")}
        trigger.trigger_build(paths, {"modified"})

        # Error handler should have been invoked (show_error called)
        mock_show_error.assert_called_once()

        # Set should still have the element (not mutated by error handler)
        assert len(paths) == 1


class TestReloadDecisionFlow:
    """Tests for simplified reload decision flow.

    The reload decision flow uses typed outputs from builds:
    1. Primary: Typed outputs (CSS-only vs full reload)
    2. Fallback: Path-based decision (when types unavailable)
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
        return executor

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_typed_outputs_css_only_reload(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that CSS-only outputs trigger CSS-only reload."""
        from bengal.server.reload_controller import ReloadDecision

        mock_controller.decide_from_outputs.return_value = ReloadDecision(
            action="reload-css", reason="css-only", changed_paths=("style.css",)
        )
        mock_controller._use_content_hashes = False

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # CSS-only outputs
        changed_outputs = (
            SerializedOutputRecord("style.css", "css", "asset"),
            SerializedOutputRecord("theme.css", "css", "asset"),
        )
        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=("assets/style.css",),
                changed_outputs=changed_outputs,
                reload_hint=None,
            )
        )

        # Should use decide_from_outputs
        mock_controller.decide_from_outputs.assert_called_once()
        mock_send_reload.assert_called_once_with("reload-css", "css-only", ("style.css",))

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_typed_outputs_full_reload(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that HTML outputs trigger full reload."""
        from bengal.server.reload_controller import ReloadDecision

        mock_controller.decide_from_outputs.return_value = ReloadDecision(
            action="reload", reason="content-changed", changed_paths=("index.html",)
        )
        mock_controller._use_content_hashes = False

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # HTML outputs
        changed_outputs = (
            SerializedOutputRecord("index.html", "html", "render"),
            SerializedOutputRecord("about.html", "html", "render"),
        )
        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=("content/index.md",),
                changed_outputs=changed_outputs,
                reload_hint=None,
            )
        )

        mock_controller.decide_from_outputs.assert_called_once()
        mock_send_reload.assert_called_once_with("reload", "content-changed", ("index.html",))

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_no_outputs_but_sources_changed_triggers_reload(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test fallback reload when sources changed but no typed outputs recorded."""
        mock_controller._use_content_hashes = False

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Sources changed but empty outputs (fallback case)
        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=("content/draft.md",),
                changed_outputs=(),
                reload_hint=None,
            )
        )

        # Should trigger full reload via fallback
        mock_send_reload.assert_called_once_with("reload", "source-change-no-outputs", ())

    @patch("bengal.server.build_trigger.default_reload_controller")
    def test_no_outputs_no_sources_suppresses_reload(
        self,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that empty outputs AND empty sources suppress reload."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # No sources, no outputs
        trigger._handle_reload(
            BuildReloadInfo(changed_files=(), changed_outputs=(), reload_hint=None)
        )

        # Should NOT call decide_from_outputs or send reload
        mock_controller.decide_from_outputs.assert_not_called()
        mock_controller.decide_from_changed_paths.assert_not_called()

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_reload_hint_none_with_empty_outputs_still_triggers_fallback_reload(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """When outputs empty, reload_hint must not suppress fallback reload.

        Build now sets reload_hint=None when outputs empty. This test validates
        backward compatibility: if reload_hint='none' is passed with empty outputs
        (legacy path), we still run the fallback so changed_files triggers reload.
        """
        mock_controller._use_content_hashes = False

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # reload_hint=NONE (from empty outputs) but sources changed
        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=("content/contact.md",),
                changed_outputs=(),
                reload_hint=ReloadHint.NONE,
            )
        )

        # Fallback should trigger reload despite reload_hint
        mock_send_reload.assert_called_once_with("reload", "source-change-no-outputs", ())

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_fallback_to_path_based_decision(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test fallback to path-based decision when type reconstruction fails."""
        from bengal.server.reload_controller import ReloadDecision

        mock_controller.decide_from_changed_paths.return_value = ReloadDecision(
            action="reload", reason="content-changed", changed_paths=("index.html",)
        )
        mock_controller._use_content_hashes = False

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Invalid output type that can't be reconstructed
        changed_outputs = (SerializedOutputRecord("index.html", "invalid_type", "render"),)
        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=("content/index.md",),
                changed_outputs=changed_outputs,
                reload_hint=None,
            )
        )

        # Should fall back to decide_from_changed_paths
        mock_controller.decide_from_outputs.assert_not_called()
        mock_controller.decide_from_changed_paths.assert_called_once()

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_reload_hint_none_with_outputs_returns_early(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """When reload_hint='none' and we have typed outputs, suppress reload."""
        from bengal.orchestration.stats import ReloadHint

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=("content/index.md",),
                changed_outputs=(SerializedOutputRecord("index.html", "html", "render"),),
                reload_hint=ReloadHint.NONE,
            )
        )

        mock_send_reload.assert_not_called()

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_content_hash_aggregate_only_suppresses_reload(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """When content-hash says aggregate-only and no source files changed, suppress reload."""
        from bengal.server.reload_controller import EnhancedReloadDecision, ReloadDecision

        mock_controller.decide_from_outputs.return_value = ReloadDecision(
            action="reload", reason="content-changed", changed_paths=("sitemap.xml",)
        )
        mock_controller._use_content_hashes = True
        mock_controller._baseline_content_hashes = {"sitemap.xml": "abc"}
        mock_controller.decide_with_content_hashes.return_value = EnhancedReloadDecision(
            action="reload",
            reason="aggregate-only",
            changed_paths=("sitemap.xml",),
            content_changes=(),
            aggregate_changes=("sitemap.xml",),
            asset_changes=(),
        )

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Empty changed_files: build was triggered by something other than user edit
        # (e.g. timer, cache validation). Content-hash says aggregate-only → suppress.
        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=(),
                changed_outputs=(SerializedOutputRecord("sitemap.xml", "html", "postprocess"),),
                reload_hint=None,
            )
        )

        mock_send_reload.assert_not_called()

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_reload_bypass_when_decision_none_but_sources_changed(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """When decision is 'none' (not aggregate-only) but changed_files non-empty, bypass."""
        from bengal.server.reload_controller import ReloadDecision

        mock_controller.decide_from_outputs.return_value = ReloadDecision(
            action="none", reason="throttled", changed_paths=()
        )
        mock_controller._use_content_hashes = False

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=("content/contact.md",),
                changed_outputs=(SerializedOutputRecord("index.html", "html", "render"),),
                reload_hint=None,
            )
        )

        mock_send_reload.assert_called_once_with("reload", "source-changes-bypass", ())

    @patch("bengal.server.build_trigger.default_reload_controller")
    @patch("bengal.server.live_reload.notification.send_reload_payload")
    def test_fallback_source_change_skips_content_hash_filtering(
        self,
        mock_send_reload: MagicMock,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Fallback-source-change must not run content-hash filtering (always reload)."""
        mock_controller._use_content_hashes = True
        mock_controller._baseline_content_hashes = {"x": "y"}

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Empty outputs, sources changed → fallback-source-change
        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=("content/contact.md",),
                changed_outputs=(),
                reload_hint=None,
            )
        )

        # Should trigger reload despite content-hash being enabled
        mock_send_reload.assert_called_once_with("reload", "source-change-no-outputs", ())
        mock_controller.decide_with_content_hashes.assert_not_called()
