"""Tests for BuildTrigger."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.server.build_trigger import BuildTrigger


class TestBuildTrigger:
    """Tests for BuildTrigger class."""

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

    def test_shutdown_calls_executor_shutdown(
        self, mock_site: MagicMock, mock_executor: MagicMock
    ) -> None:
        """Test that shutdown calls executor shutdown."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)
        trigger.shutdown()

        mock_executor.shutdown.assert_called_once_with(wait=True)

    def test_needs_full_rebuild_for_structural_changes(
        self, mock_site: MagicMock, mock_executor: MagicMock
    ) -> None:
        """Test that structural changes trigger full rebuild."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Created file
        assert trigger._needs_full_rebuild({Path("test.md")}, {"created"}) is True

        # Deleted file
        assert trigger._needs_full_rebuild({Path("test.md")}, {"deleted"}) is True

        # Moved file
        assert trigger._needs_full_rebuild({Path("test.md")}, {"moved"}) is True

        # Modified file (should not need full rebuild)
        assert trigger._needs_full_rebuild({Path("test.md")}, {"modified"}) is False

    def test_needs_full_rebuild_for_template_changes(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that template changes trigger full rebuild."""
        # Create a real template directory
        mock_site.root_path = tmp_path
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        template_file = templates_dir / "base.html"
        template_file.write_text("<html></html>")

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        assert trigger._is_template_change({template_file}) is True

    def test_detect_nav_changes_finds_nav_frontmatter(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that nav frontmatter detection works."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create a test file with nav frontmatter
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
title: Test Page
weight: 10
---

Content here.
"""
        )

        result = trigger._detect_nav_changes({test_file}, needs_full_rebuild=False)
        assert test_file in result

    def test_detect_nav_changes_skips_non_nav_frontmatter(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that non-nav frontmatter is skipped."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create a test file without nav-affecting frontmatter
        # (no title, weight, order, draft, headless, etc.)
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
author: Someone
description: A test page
tags:
  - test
---

Content here.
"""
        )

        result = trigger._detect_nav_changes({test_file}, needs_full_rebuild=False)
        assert test_file not in result

    def test_detect_nav_changes_skips_when_full_rebuild(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that nav detection is skipped for full rebuilds."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
title: Test
weight: 10
---
"""
        )

        result = trigger._detect_nav_changes({test_file}, needs_full_rebuild=True)
        assert len(result) == 0


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

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.CLIOutput")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.controller")
    @patch("bengal.server.live_reload.send_reload_payload")
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
        """Test that version_scope is passed to BuildRequest."""
        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True
        mock_controller.decide_from_changed_paths.return_value = MagicMock(
            action="reload", reason="test", changed_paths=[]
        )

        trigger = BuildTrigger(
            site=mock_site,
            executor=mock_executor,
            version_scope="v2",
        )

        trigger.trigger_build(
            changed_paths={Path("test.md")},
            event_types={"modified"},
        )

        # Verify BuildRequest was created with version_scope
        mock_executor.submit.assert_called_once()
        request = mock_executor.submit.call_args[0][0]
        assert request.version_scope == "v2"

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.CLIOutput")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.controller")
    @patch("bengal.server.live_reload.send_reload_payload")
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
        """Test that BuildRequest has None version_scope when not set."""
        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True
        mock_controller.decide_from_changed_paths.return_value = MagicMock(
            action="reload", reason="test", changed_paths=[]
        )

        trigger = BuildTrigger(
            site=mock_site,
            executor=mock_executor,
        )

        trigger.trigger_build(
            changed_paths={Path("test.md")},
            event_types={"modified"},
        )

        mock_executor.submit.assert_called_once()
        request = mock_executor.submit.call_args[0][0]
        assert request.version_scope is None


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

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.CLIOutput")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.controller")
    @patch("bengal.server.live_reload.send_reload_payload")
    def test_trigger_build_submits_to_executor(
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
        """Test that trigger_build submits build to executor."""
        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True
        mock_controller.decide_from_changed_paths.return_value = MagicMock(
            action="reload", reason="test", changed_paths=[]
        )

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        trigger.trigger_build(
            changed_paths={Path("test.md")},
            event_types={"modified"},
        )

        mock_executor.submit.assert_called_once()
        request = mock_executor.submit.call_args[0][0]
        assert request.site_root == str(mock_site.root_path)
        assert "test.md" in request.changed_paths[0]


class TestBuildTriggerCaching:
    """Tests for BuildTrigger caching optimizations.

    RFC: rfc-server-package-optimizations

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

    def test_frontmatter_cache_hit(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that frontmatter parsing is cached by mtime."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create a test file with nav frontmatter
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
title: Test Page
weight: 10
---

Content here.
"""
        )

        # First call - cache miss
        result1 = trigger._has_nav_affecting_frontmatter(test_file)
        assert result1 is True
        assert test_file in trigger._frontmatter_cache

        # Second call - cache hit (same mtime)
        result2 = trigger._has_nav_affecting_frontmatter(test_file)
        assert result2 is True

    def test_frontmatter_cache_invalidation_on_mtime_change(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that frontmatter cache is invalidated when mtime changes."""
        import os
        import time

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create initial file with nav frontmatter
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
title: Test Page
weight: 10
---
"""
        )

        # First call
        result1 = trigger._has_nav_affecting_frontmatter(test_file)
        assert result1 is True

        # Modify file (change content, touch mtime)
        time.sleep(0.01)  # Ensure mtime changes
        test_file.write_text(
            """---
author: Someone
---
"""
        )
        # Force mtime update
        os.utime(test_file, None)

        # Second call - should re-parse due to mtime change
        result2 = trigger._has_nav_affecting_frontmatter(test_file)
        assert result2 is False  # No nav-affecting keys now

    def test_frontmatter_partial_read(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that only first 4KB is read for frontmatter."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create a file with frontmatter and lots of content
        large_content = "x" * 100000  # 100KB of content
        test_file = tmp_path / "large.md"
        test_file.write_text(
            f"""---
title: Large File
---

{large_content}
"""
        )

        # Should still detect nav frontmatter without reading entire file
        result = trigger._has_nav_affecting_frontmatter(test_file)
        assert result is True

    def test_template_dirs_cached(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that template directories are cached."""
        mock_site.root_path = tmp_path

        # Create template directory
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # First call - populates cache
        dirs1 = trigger._get_template_dirs()
        assert templates_dir in dirs1

        # Second call - returns cached
        dirs2 = trigger._get_template_dirs()
        assert dirs1 == dirs2

        # Should be same list object (cached)
        assert dirs1 is dirs2

    def test_template_change_early_exit_non_html(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that template check exits early for non-.html files."""
        mock_site.root_path = tmp_path

        # Create template directory
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Non-HTML files should not be detected as template changes
        non_html_paths = {
            Path(templates_dir / "style.css"),
            Path(tmp_path / "content" / "post.md"),
        }

        result = trigger._is_template_change(non_html_paths)
        assert result is False

    def test_detect_nav_changes_uses_cache(
        self, mock_site: MagicMock, mock_executor: MagicMock, tmp_path: Path
    ) -> None:
        """Test that _detect_nav_changes uses the frontmatter cache."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Create test file
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
title: Test
weight: 5
---
"""
        )

        # First detection
        result1 = trigger._detect_nav_changes({test_file}, needs_full_rebuild=False)
        assert test_file in result1

        # File should be cached now
        assert test_file in trigger._frontmatter_cache

        # Second detection should use cache
        result2 = trigger._detect_nav_changes({test_file}, needs_full_rebuild=False)
        assert test_file in result2


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

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.CLIOutput")
    @patch("bengal.server.build_trigger.show_error")
    @patch("bengal.server.build_trigger.controller")
    @patch("bengal.server.build_trigger.create_dev_error")
    @patch("bengal.server.build_trigger.get_dev_server_state")
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

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.CLIOutput")
    @patch("bengal.server.build_trigger.show_error")
    @patch("bengal.server.build_trigger.controller")
    @patch("bengal.server.build_trigger.create_dev_error")
    @patch("bengal.server.build_trigger.get_dev_server_state")
    def test_trigger_file_extracted_without_mutation(
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
        """Test that trigger_file is extracted without modifying the set."""
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

        paths = {Path("test.md")}
        trigger.trigger_build(paths, {"modified"})

        # Verify create_dev_error was called with a trigger_file
        mock_create_error.assert_called_once()
        call_kwargs = mock_create_error.call_args[1]
        assert call_kwargs["trigger_file"] is not None
        assert "test.md" in call_kwargs["trigger_file"]

        # Set should still have the element
        assert len(paths) == 1


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

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.CLIOutput")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.controller")
    @patch("bengal.server.live_reload.send_reload_payload")
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
        mock_controller.decide_from_changed_paths.return_value = MagicMock(
            action="reload", reason="test", changed_paths=[]
        )

        # Create an event to control build timing
        build_started = threading.Event()
        build_can_finish = threading.Event()

        def slow_submit(*args, **kwargs):
            build_started.set()
            build_can_finish.wait(timeout=5.0)
            result = MagicMock()
            result.success = True
            result.pages_built = 5
            result.build_time_ms = 100.0
            result.error_message = None
            result.changed_outputs = ()
            return result

        mock_executor.submit.side_effect = slow_submit

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

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.CLIOutput")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.controller")
    @patch("bengal.server.live_reload.send_reload_payload")
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
        mock_controller.decide_from_changed_paths.return_value = MagicMock(
            action="reload", reason="test", changed_paths=[]
        )

        # Track build requests
        build_requests = []
        build_started = threading.Event()
        build_can_finish = threading.Event()
        first_build_done = False

        def tracking_submit(request, **kwargs):
            nonlocal first_build_done
            build_requests.append(request)
            if not first_build_done:
                build_started.set()
                build_can_finish.wait(timeout=5.0)
                first_build_done = True
            result = MagicMock()
            result.success = True
            result.pages_built = 5
            result.build_time_ms = 100.0
            result.error_message = None
            result.changed_outputs = ()
            return result

        mock_executor.submit.side_effect = tracking_submit

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
        assert len(build_requests) == 2
        assert "first.md" in build_requests[0].changed_paths[0]
        assert "second.md" in build_requests[1].changed_paths[0]

    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.CLIOutput")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.controller")
    @patch("bengal.server.live_reload.send_reload_payload")
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
        mock_controller.decide_from_changed_paths.return_value = MagicMock(
            action="reload", reason="test", changed_paths=[]
        )

        build_requests = []
        build_started = threading.Event()
        build_can_finish = threading.Event()
        first_build_done = False

        def tracking_submit(request, **kwargs):
            nonlocal first_build_done
            build_requests.append(request)
            if not first_build_done:
                build_started.set()
                build_can_finish.wait(timeout=5.0)
                first_build_done = True
            result = MagicMock()
            result.success = True
            result.pages_built = 5
            result.build_time_ms = 100.0
            result.error_message = None
            result.changed_outputs = ()
            return result

        mock_executor.submit.side_effect = tracking_submit

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
        assert len(build_requests) == 2

        # Second build should contain all three queued files
        second_build_paths = set(build_requests[1].changed_paths)
        assert len(second_build_paths) == 3

    @patch("bengal.server.build_trigger.time.sleep")
    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.CLIOutput")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.controller")
    @patch("bengal.server.live_reload.send_reload_payload")
    def test_stabilization_delay_before_queued_build(
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
        """Test that a stabilization delay is applied before executing queued builds.

        This delay allows browsers to fetch updated assets from the just-completed
        build before the next build potentially replaces them again.
        """
        import threading

        mock_pre_hooks.return_value = True
        mock_post_hooks.return_value = True
        mock_controller.decide_from_changed_paths.return_value = MagicMock(
            action="reload", reason="test", changed_paths=[]
        )

        # Track build order and sleep calls
        build_requests = []
        sleep_calls = []
        build_started = threading.Event()
        build_can_finish = threading.Event()
        first_build_done = False

        def tracking_submit(request, **kwargs):
            nonlocal first_build_done
            build_requests.append(request)
            if not first_build_done:
                build_started.set()
                build_can_finish.wait(timeout=5.0)
                first_build_done = True
            result = MagicMock()
            result.success = True
            result.pages_built = 5
            result.build_time_ms = 100.0
            result.error_message = None
            result.changed_outputs = ()
            return result

        def tracking_sleep(seconds):
            sleep_calls.append(seconds)

        mock_executor.submit.side_effect = tracking_submit
        mock_sleep.side_effect = tracking_sleep

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Start first build
        first_build = threading.Thread(
            target=trigger.trigger_build,
            args=({Path("first.md")}, {"modified"}),
        )
        first_build.start()
        build_started.wait(timeout=5.0)

        # Queue a second change
        trigger.trigger_build({Path("second.md")}, {"created"})

        # Let first build finish (which should trigger queued build with delay)
        build_can_finish.set()
        first_build.join(timeout=5.0)

        # Should have two builds
        assert len(build_requests) == 2

        # Stabilization delay should have been called (0.1 seconds)
        assert len(sleep_calls) >= 1
        assert 0.1 in sleep_calls, f"Expected 0.1s delay, got calls: {sleep_calls}"


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

    @patch("bengal.server.build_trigger.controller")
    @patch("bengal.server.live_reload.send_reload_payload")
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
            action="reload-css", reason="css-only", changed_paths=["style.css"]
        )
        mock_controller._use_content_hashes = False

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # CSS-only outputs
        changed_outputs = (
            ("style.css", "css", "asset"),
            ("theme.css", "css", "asset"),
        )
        trigger._handle_reload(["assets/style.css"], changed_outputs)

        # Should use decide_from_outputs
        mock_controller.decide_from_outputs.assert_called_once()
        mock_send_reload.assert_called_once_with("reload-css", "css-only", ["style.css"])

    @patch("bengal.server.build_trigger.controller")
    @patch("bengal.server.live_reload.send_reload_payload")
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
            action="reload", reason="content-changed", changed_paths=["index.html"]
        )
        mock_controller._use_content_hashes = False

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # HTML outputs
        changed_outputs = (
            ("index.html", "html", "render"),
            ("about.html", "html", "render"),
        )
        trigger._handle_reload(["content/index.md"], changed_outputs)

        mock_controller.decide_from_outputs.assert_called_once()
        mock_send_reload.assert_called_once_with("reload", "content-changed", ["index.html"])

    @patch("bengal.server.build_trigger.controller")
    @patch("bengal.server.live_reload.send_reload_payload")
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
        trigger._handle_reload(["content/draft.md"], ())

        # Should trigger full reload via fallback
        mock_send_reload.assert_called_once_with("reload", "source-change-no-outputs", [])

    @patch("bengal.server.build_trigger.controller")
    def test_no_outputs_no_sources_suppresses_reload(
        self,
        mock_controller: MagicMock,
        mock_site: MagicMock,
        mock_executor: MagicMock,
    ) -> None:
        """Test that empty outputs AND empty sources suppress reload."""
        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # No sources, no outputs
        trigger._handle_reload([], ())

        # Should NOT call decide_from_outputs or send reload
        mock_controller.decide_from_outputs.assert_not_called()
        mock_controller.decide_from_changed_paths.assert_not_called()

    @patch("bengal.server.build_trigger.controller")
    @patch("bengal.server.live_reload.send_reload_payload")
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
            action="reload", reason="content-changed", changed_paths=["index.html"]
        )
        mock_controller._use_content_hashes = False

        trigger = BuildTrigger(site=mock_site, executor=mock_executor)

        # Invalid output type that can't be reconstructed
        changed_outputs = (
            ("index.html", "invalid_type", "render"),
        )
        trigger._handle_reload(["content/index.md"], changed_outputs)

        # Should fall back to decide_from_changed_paths
        mock_controller.decide_from_outputs.assert_not_called()
        mock_controller.decide_from_changed_paths.assert_called_once()


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

    @patch("bengal.server.build_trigger.time.sleep")
    @patch("bengal.server.build_trigger.run_pre_build_hooks")
    @patch("bengal.server.build_trigger.run_post_build_hooks")
    @patch("bengal.server.build_trigger.show_building_indicator")
    @patch("bengal.server.build_trigger.CLIOutput")
    @patch("bengal.server.build_trigger.display_build_stats")
    @patch("bengal.server.build_trigger.controller")
    @patch("bengal.server.live_reload.send_reload_payload")
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
            action="reload", reason="test", changed_paths=[]
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
