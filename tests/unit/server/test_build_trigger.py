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
