"""
Unit tests for Bengal dashboard custom widgets.

Tests widget initialization, state management, and message posting.
"""

from __future__ import annotations

import pytest

from bengal.cli.dashboard.widgets import BengalThrobber, BuildFlash, QuickAction
from bengal.cli.dashboard.widgets.phase_plan import BuildPhase, BuildPhasePlan


class TestBengalThrobber:
    """Tests for BengalThrobber widget."""

    def test_init_inactive(self):
        """Throbber starts inactive by default."""
        throbber = BengalThrobber()
        assert throbber.active is False

    def test_activate_throbber(self):
        """Setting active=True activates the throbber."""
        throbber = BengalThrobber()
        throbber.active = True
        assert throbber.active is True

    def test_deactivate_throbber(self):
        """Setting active=False deactivates the throbber."""
        throbber = BengalThrobber()
        throbber.active = True
        throbber.active = False
        assert throbber.active is False

    def test_toggle_active_state(self):
        """Throbber active state can be toggled multiple times."""
        throbber = BengalThrobber()

        throbber.active = True
        assert throbber.active is True

        throbber.active = False
        assert throbber.active is False

        throbber.active = True
        assert throbber.active is True


class TestBuildFlash:
    """Tests for BuildFlash widget."""

    def test_init(self):
        """BuildFlash initializes without error."""
        flash = BuildFlash()
        assert flash is not None

    def test_has_show_success_method(self):
        """BuildFlash has show_success method."""
        flash = BuildFlash()
        assert hasattr(flash, "show_success")
        assert callable(flash.show_success)

    def test_has_show_error_method(self):
        """BuildFlash has show_error method."""
        flash = BuildFlash()
        assert hasattr(flash, "show_error")
        assert callable(flash.show_error)

    def test_has_show_building_method(self):
        """BuildFlash has show_building method."""
        flash = BuildFlash()
        assert hasattr(flash, "show_building")
        assert callable(flash.show_building)


class TestBuildPhase:
    """Tests for BuildPhase dataclass."""

    def test_create_phase(self):
        """BuildPhase dataclass creates correctly."""
        phase = BuildPhase(
            name="discovery",
            status="running",
            duration_ms=150,
        )
        assert phase.name == "discovery"
        assert phase.status == "running"
        assert phase.duration_ms == 150

    def test_phase_default_duration(self):
        """BuildPhase defaults duration_ms to None."""
        phase = BuildPhase(name="rendering", status="pending")
        assert phase.name == "rendering"
        assert phase.status == "pending"
        assert phase.duration_ms is None

    def test_phase_with_duration(self):
        """BuildPhase can include duration."""
        phase = BuildPhase(
            name="rendering",
            status="complete",
            duration_ms=500,
        )
        assert phase.duration_ms == 500


class TestBuildPhasePlan:
    """Tests for BuildPhasePlan widget."""

    def test_status_icons_defined(self):
        """All status icons are defined."""
        icons = BuildPhasePlan.STATUS_ICONS
        assert icons["pending"] == "○"
        assert icons["running"] == "●"
        assert icons["complete"] == "✓"
        assert icons["error"] == "✗"

    def test_status_icons_complete(self):
        """All expected statuses have icons."""
        icons = BuildPhasePlan.STATUS_ICONS
        expected_statuses = {"pending", "running", "complete", "error"}
        assert set(icons.keys()) == expected_statuses


class TestQuickAction:
    """Tests for QuickAction widget."""

    def test_init_with_params(self):
        """QuickAction initializes with emoji, title, description."""
        action = QuickAction(
            "🚀",
            "Launch",
            "Launch the application",
            id="launch-action",
        )
        assert action.emoji == "🚀"
        assert action.action_title == "Launch"
        assert action.description == "Launch the application"
        assert action.id == "launch-action"

    def test_selected_message_class_exists(self):
        """QuickAction has Selected message class."""
        assert hasattr(QuickAction, "Selected")

    def test_different_emojis(self):
        """QuickAction works with different emoji types."""
        action1 = QuickAction("🔨", "Build", "Build the site")
        assert action1.emoji == "🔨"

        action2 = QuickAction("🌐", "Serve", "Start server")
        assert action2.emoji == "🌐"

        action3 = QuickAction("🏥", "Health", "Check health")
        assert action3.emoji == "🏥"


class TestWidgetIntegration:
    """Integration tests for widget combinations."""

    @pytest.mark.asyncio
    async def test_throbber_in_app_context(self, pilot):
        """Throbber widget works in app context."""
        await pilot.pause()  # Wait for app to mount
        await pilot.press("1")  # Go to build screen
        await pilot.pause()  # Wait for screen transition

        throbber = pilot.app.screen.query_one("#build-throbber", BengalThrobber)
        assert throbber is not None
        assert throbber.active is False

    @pytest.mark.asyncio
    async def test_flash_in_app_context(self, pilot):
        """BuildFlash widget works in app context."""
        await pilot.pause()
        await pilot.press("1")  # Go to build screen
        await pilot.pause()

        flash = pilot.app.screen.query_one("#build-flash", BuildFlash)
        assert flash is not None

    @pytest.mark.asyncio
    async def test_quick_actions_on_landing(self, pilot):
        """Quick action widgets exist on landing screen."""
        await pilot.pause()
        await pilot.press("0")  # Go to landing screen
        await pilot.pause()

        build_action = pilot.app.screen.query_one("#action-build", QuickAction)
        serve_action = pilot.app.screen.query_one("#action-serve", QuickAction)
        health_action = pilot.app.screen.query_one("#action-health", QuickAction)

        assert build_action is not None
        assert serve_action is not None
        assert health_action is not None

    @pytest.mark.asyncio
    async def test_phase_progress_on_build_screen(self, pilot):
        """Phase progress widget exists on build screen."""
        from bengal.cli.dashboard.widgets import PhaseProgress

        await pilot.pause()
        await pilot.press("1")  # Go to build screen
        await pilot.pause()

        progress = pilot.app.screen.query_one("#phase-progress", PhaseProgress)
        assert progress is not None
        # Should have phases defined
        assert len(progress.PHASE_NAMES) > 0
