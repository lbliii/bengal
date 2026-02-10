"""Test that CSS-only changes trigger reload-css action."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.server.build_trigger import BuildTrigger as _BuildTrigger
from bengal.server.reload_controller import ReloadDecision

DEFAULT_RELOAD_CONTROLLER: object | None = None


def BuildTrigger(*args: object, **kwargs: object) -> _BuildTrigger:
    """Create BuildTrigger with explicit test reload controller."""
    kwargs.setdefault("reload_controller", DEFAULT_RELOAD_CONTROLLER or MagicMock())
    return _BuildTrigger(*args, **kwargs)


def _make_build_stats(changed_outputs: list | None = None) -> MagicMock:
    """Create a mock build stats object for warm builds."""
    stats = MagicMock()
    stats.total_pages = 1
    if changed_outputs is None:
        changed_outputs = []
    stats.changed_outputs = changed_outputs
    return stats


def _make_css_output(path: str = "public/assets/styles.css") -> MagicMock:
    """Create a mock OutputRecord-like object for CSS output."""
    record = MagicMock()
    record.path = Path(path)
    record.output_type = MagicMock()
    record.output_type.value = "css"
    record.phase = "asset"
    return record


def _make_html_output(path: str = "public/index.html") -> MagicMock:
    """Create a mock OutputRecord-like object for HTML output."""
    record = MagicMock()
    record.path = Path(path)
    record.output_type = MagicMock()
    record.output_type.value = "html"
    record.phase = "render"
    return record


@pytest.fixture
def mock_executor() -> MagicMock:
    """Create a mock executor for testing."""
    return MagicMock()


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
@patch("tests.unit.server.test_css_only_reload.DEFAULT_RELOAD_CONTROLLER")
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

    # Setup warm build to return CSS-only outputs
    css_output = _make_css_output()
    mock_site.build.return_value = _make_build_stats([css_output])

    # Controller should detect CSS-only and return reload-css decision
    mock_controller.decide_from_outputs.return_value = ReloadDecision(
        action="reload-css", reason="css-only", changed_paths=[]
    )
    mock_controller._use_content_hashes = False

    trigger = BuildTrigger(site=mock_site, executor=mock_executor)

    css_file = tmp_path / "assets" / "styles.css"
    css_file.parent.mkdir(parents=True, exist_ok=True)
    css_file.write_text("body{color:black}")

    trigger.trigger_build(
        changed_paths={css_file},
        event_types={"modified"},
    )

    # Verify reload was called with reload-css action
    mock_send_reload.assert_called_once()
    call_args = mock_send_reload.call_args
    assert call_args[0][0] == "reload-css"
    assert call_args[0][1] == "css-only"

    trigger.shutdown()


@patch("bengal.server.build_trigger.run_pre_build_hooks")
@patch("bengal.server.build_trigger.run_post_build_hooks")
@patch("bengal.server.build_trigger.show_building_indicator")
@patch("bengal.server.build_trigger.CLIOutput")
@patch("bengal.server.build_trigger.display_build_stats")
@patch("tests.unit.server.test_css_only_reload.DEFAULT_RELOAD_CONTROLLER")
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

    # Setup warm build to return mixed outputs (CSS + HTML)
    css_output = _make_css_output()
    html_output = _make_html_output()
    mock_site.build.return_value = _make_build_stats([css_output, html_output])

    # Controller should detect mixed outputs and return full reload
    mock_controller.decide_from_outputs.return_value = ReloadDecision(
        action="reload", reason="source-change", changed_paths=[]
    )
    mock_controller._use_content_hashes = False

    trigger = BuildTrigger(site=mock_site, executor=mock_executor)

    css_file = tmp_path / "assets" / "styles.css"
    css_file.parent.mkdir(parents=True, exist_ok=True)
    css_file.write_text("body{color:black}")

    md_file = tmp_path / "content" / "post.md"
    md_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.write_text("# Hello")

    trigger.trigger_build(
        changed_paths={css_file, md_file},
        event_types={"modified"},
    )

    # Verify reload was called with full reload action
    mock_send_reload.assert_called_once()
    call_args = mock_send_reload.call_args
    assert call_args[0][0] == "reload"
    assert call_args[0][1] == "source-change"

    trigger.shutdown()
