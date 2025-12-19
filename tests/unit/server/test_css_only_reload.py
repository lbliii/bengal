"""Test that CSS-only changes trigger reload-css action."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.server.build_trigger import BuildTrigger


@pytest.fixture
def mock_executor() -> MagicMock:
    """Create a mock executor for testing."""
    executor = MagicMock()
    result = MagicMock()
    result.success = True
    result.pages_built = 1
    result.build_time_ms = 100.0
    result.error_message = None
    result.changed_outputs = ()
    executor.submit.return_value = result
    return executor


@pytest.fixture
def mock_site(tmp_path: Path) -> MagicMock:
    """Create a mock site for testing."""
    site = MagicMock()
    site.root_path = tmp_path
    site.output_dir = tmp_path / "public"
    site.output_dir.mkdir(parents=True, exist_ok=True)
    site.config = {}
    site.theme = None
    return site


@patch("bengal.server.build_trigger.run_pre_build_hooks")
@patch("bengal.server.build_trigger.run_post_build_hooks")
@patch("bengal.server.build_trigger.show_building_indicator")
@patch("bengal.server.build_trigger.CLIOutput")
@patch("bengal.server.build_trigger.display_build_stats")
@patch("bengal.server.build_trigger.controller")
@patch("bengal.server.live_reload.send_reload_payload")
def test_css_only_change_triggers_reload_css(
    mock_send_reload: MagicMock,
    mock_controller: MagicMock,
    mock_display: MagicMock,
    mock_cli: MagicMock,
    mock_building: MagicMock,
    mock_post_hooks: MagicMock,
    mock_pre_hooks: MagicMock,
    mock_site: MagicMock,
    mock_executor: MagicMock,
    tmp_path: Path,
) -> None:
    """Test that CSS-only changes trigger reload-css action."""
    mock_pre_hooks.return_value = True
    mock_post_hooks.return_value = True

    # Create trigger
    trigger = BuildTrigger(site=mock_site, executor=mock_executor)

    # Simulate CSS-only change
    css_file = tmp_path / "assets" / "styles.css"
    css_file.parent.mkdir(parents=True, exist_ok=True)
    css_file.write_text("body{color:black}")

    # Trigger build with CSS-only change
    trigger.trigger_build(
        changed_paths={css_file},
        event_types={"modified"},
    )

    # Verify reload was called with reload-css action
    mock_send_reload.assert_called_once()
    call_args = mock_send_reload.call_args[0]
    assert call_args[0] == "reload-css"  # action
    assert call_args[1] == "css-only"  # reason

    trigger.shutdown()


@patch("bengal.server.build_trigger.run_pre_build_hooks")
@patch("bengal.server.build_trigger.run_post_build_hooks")
@patch("bengal.server.build_trigger.show_building_indicator")
@patch("bengal.server.build_trigger.CLIOutput")
@patch("bengal.server.build_trigger.display_build_stats")
@patch("bengal.server.build_trigger.controller")
@patch("bengal.server.live_reload.send_reload_payload")
def test_mixed_change_triggers_full_reload(
    mock_send_reload: MagicMock,
    mock_controller: MagicMock,
    mock_display: MagicMock,
    mock_cli: MagicMock,
    mock_building: MagicMock,
    mock_post_hooks: MagicMock,
    mock_pre_hooks: MagicMock,
    mock_site: MagicMock,
    mock_executor: MagicMock,
    tmp_path: Path,
) -> None:
    """Test that mixed changes (CSS + other) trigger full reload."""
    mock_pre_hooks.return_value = True
    mock_post_hooks.return_value = True

    # Create trigger
    trigger = BuildTrigger(site=mock_site, executor=mock_executor)

    # Simulate mixed changes (CSS + markdown)
    css_file = tmp_path / "assets" / "styles.css"
    css_file.parent.mkdir(parents=True, exist_ok=True)
    css_file.write_text("body{color:black}")

    md_file = tmp_path / "content" / "post.md"
    md_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.write_text("# Hello")

    # Trigger build with mixed changes
    trigger.trigger_build(
        changed_paths={css_file, md_file},
        event_types={"modified"},
    )

    # Verify reload was called with full reload action
    mock_send_reload.assert_called_once()
    call_args = mock_send_reload.call_args[0]
    assert call_args[0] == "reload"  # action (not reload-css)
    assert call_args[1] == "source-change"  # reason

    trigger.shutdown()
