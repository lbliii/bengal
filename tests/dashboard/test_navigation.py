"""
Navigation tests for Bengal dashboard.

Tests keyboard navigation between screens using Textual pilot API.
Verifies screen transitions, help overlay, and quit behavior.

Reference: https://textual.textualize.io/guide/testing/
"""

from __future__ import annotations

import pytest

from bengal.cli.dashboard.screens import (
    BuildScreen,
    HealthScreen,
    HelpScreen,
    LandingScreen,
    ServeScreen,
)


class TestScreenNavigation:
    """Test screen navigation via keyboard shortcuts."""

    @pytest.mark.asyncio
    async def test_press_1_goes_to_build(self, pilot):
        """Pressing '1' switches to build screen."""
        await pilot.press("1")
        await pilot.pause()
        assert isinstance(pilot.app.screen, BuildScreen)

    @pytest.mark.asyncio
    async def test_press_2_goes_to_serve(self, pilot):
        """Pressing '2' switches to serve screen."""
        await pilot.press("2")
        await pilot.pause()
        assert isinstance(pilot.app.screen, ServeScreen)

    @pytest.mark.asyncio
    async def test_press_3_goes_to_health(self, pilot):
        """Pressing '3' switches to health screen."""
        await pilot.press("3")
        await pilot.pause()
        assert isinstance(pilot.app.screen, HealthScreen)

    @pytest.mark.asyncio
    async def test_press_0_goes_to_landing(self, pilot):
        """Pressing '0' switches to landing screen."""
        await pilot.press("1")  # Go somewhere first
        await pilot.pause()
        await pilot.press("0")
        await pilot.pause()
        assert isinstance(pilot.app.screen, LandingScreen)

    @pytest.mark.asyncio
    async def test_navigation_build_to_serve(self, pilot):
        """Navigate from build to serve screen."""
        await pilot.press("1")
        await pilot.pause()
        assert isinstance(pilot.app.screen, BuildScreen)

        await pilot.press("2")
        await pilot.pause()
        assert isinstance(pilot.app.screen, ServeScreen)


class TestHelpScreen:
    """Test help screen toggle behavior."""

    @pytest.mark.asyncio
    async def test_question_mark_opens_help(self, pilot):
        """Pressing '?' opens help screen."""
        await pilot.press("?")
        await pilot.pause()
        assert isinstance(pilot.app.screen, HelpScreen)

    @pytest.mark.asyncio
    async def test_escape_closes_help(self, pilot):
        """Pressing 'escape' closes help screen."""
        await pilot.press("?")
        await pilot.pause()
        assert isinstance(pilot.app.screen, HelpScreen)

        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(pilot.app.screen, HelpScreen)

    @pytest.mark.asyncio
    async def test_escape_from_help_returns_to_previous(self, pilot):
        """Pressing 'escape' from help screen returns to previous screen."""
        await pilot.press("1")  # Go to build first
        await pilot.pause()
        await pilot.press("?")
        await pilot.pause()
        assert isinstance(pilot.app.screen, HelpScreen)

        await pilot.press("escape")
        await pilot.pause()
        # Should close help, return to build
        assert isinstance(pilot.app.screen, BuildScreen)


class TestQuitAction:
    """Test quit action from various screens."""

    @pytest.mark.asyncio
    async def test_quit_from_landing(self, pilot):
        """Pressing 'q' on landing screen exits app."""
        await pilot.press("0")
        await pilot.pause()
        await pilot.press("q")
        # App should have requested exit
        assert pilot.app._exit is True

    @pytest.mark.asyncio
    async def test_quit_from_build(self, pilot):
        """Pressing 'q' on build screen exits app."""
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("q")
        assert pilot.app._exit is True


class TestBuildScreenActions:
    """Test build screen specific key bindings."""

    @pytest.mark.asyncio
    async def test_clear_log_action(self, pilot):
        """Pressing 'c' clears the build log."""
        from textual.widgets import Log

        await pilot.press("1")  # Go to build screen
        await pilot.pause()

        log = pilot.app.screen.query_one("#build-log", Log)
        log.write_line("Test line 1")
        log.write_line("Test line 2")
        assert log.line_count > 0

        await pilot.press("c")
        await pilot.pause()
        assert log.line_count == 0


class TestServeScreenActions:
    """Test serve screen specific key bindings."""

    @pytest.mark.asyncio
    async def test_navigate_to_serve(self, pilot):
        """Can navigate to serve screen."""
        await pilot.press("2")  # Go to serve screen
        await pilot.pause()
        assert isinstance(pilot.app.screen, ServeScreen)


class TestQuickActionClicks:
    """Test QuickAction widget click interactions."""

    @pytest.mark.asyncio
    async def test_click_build_action_switches_screen(self, pilot):
        """Clicking Build quick action switches to build screen."""
        await pilot.press("0")  # Go to landing
        await pilot.pause()

        await pilot.click("#action-build")
        await pilot.pause()
        assert isinstance(pilot.app.screen, BuildScreen)

    @pytest.mark.asyncio
    async def test_click_serve_action_switches_screen(self, pilot):
        """Clicking Serve quick action switches to serve screen."""
        await pilot.press("0")
        await pilot.pause()

        await pilot.click("#action-serve")
        await pilot.pause()
        assert isinstance(pilot.app.screen, ServeScreen)

    @pytest.mark.asyncio
    async def test_click_health_action_switches_screen(self, pilot):
        """Clicking Health quick action switches to health screen."""
        await pilot.press("0")
        await pilot.pause()

        await pilot.click("#action-health")
        await pilot.pause()
        assert isinstance(pilot.app.screen, HealthScreen)
