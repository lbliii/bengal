"""
Navigation tests for Bengal dashboard.

Tests keyboard navigation between screens using Textual pilot API.
Verifies screen transitions, help overlay, and quit behavior.

Reference: https://textual.textualize.io/guide/testing/
"""

from __future__ import annotations

import pytest


class TestScreenNavigation:
    """Test screen navigation via keyboard shortcuts."""

    @pytest.mark.asyncio
    async def test_press_1_goes_to_build(self, pilot):
        """Pressing '1' switches to build screen."""
        await pilot.press("1")
        assert pilot.app.screen.name == "build"

    @pytest.mark.asyncio
    async def test_press_2_goes_to_serve(self, pilot):
        """Pressing '2' switches to serve screen."""
        await pilot.press("2")
        assert pilot.app.screen.name == "serve"

    @pytest.mark.asyncio
    async def test_press_3_goes_to_health(self, pilot):
        """Pressing '3' switches to health screen."""
        await pilot.press("3")
        assert pilot.app.screen.name == "health"

    @pytest.mark.asyncio
    async def test_press_0_goes_to_landing(self, pilot):
        """Pressing '0' switches to landing screen."""
        await pilot.press("1")  # Go somewhere first
        await pilot.press("0")
        assert pilot.app.screen.name == "landing"

    @pytest.mark.asyncio
    async def test_navigation_cycle(self, pilot):
        """Navigate through all screens in sequence."""
        # Start on landing
        await pilot.press("0")
        assert pilot.app.screen.name == "landing"

        # Build
        await pilot.press("1")
        assert pilot.app.screen.name == "build"

        # Serve
        await pilot.press("2")
        assert pilot.app.screen.name == "serve"

        # Health
        await pilot.press("3")
        assert pilot.app.screen.name == "health"

        # Back to landing
        await pilot.press("0")
        assert pilot.app.screen.name == "landing"


class TestHelpScreen:
    """Test help screen toggle behavior."""

    @pytest.mark.asyncio
    async def test_question_mark_opens_help(self, pilot):
        """Pressing '?' opens help screen."""
        await pilot.press("?")
        assert pilot.app.screen.name == "help"

    @pytest.mark.asyncio
    async def test_escape_closes_help(self, pilot):
        """Pressing 'escape' closes help screen."""
        await pilot.press("?")
        assert pilot.app.screen.name == "help"

        await pilot.press("escape")
        assert pilot.app.screen.name != "help"

    @pytest.mark.asyncio
    async def test_q_closes_help(self, pilot):
        """Pressing 'q' from help screen closes it (not quit app)."""
        await pilot.press("1")  # Go to build first
        await pilot.press("?")
        assert pilot.app.screen.name == "help"

        await pilot.press("q")
        # Should close help, not quit the app
        assert pilot.app.screen.name == "build"

    @pytest.mark.asyncio
    async def test_help_from_different_screens(self, pilot):
        """Help can be opened from any screen."""
        # From build
        await pilot.press("1")
        await pilot.press("?")
        assert pilot.app.screen.name == "help"
        await pilot.press("escape")

        # From serve
        await pilot.press("2")
        await pilot.press("?")
        assert pilot.app.screen.name == "help"
        await pilot.press("escape")

        # From health
        await pilot.press("3")
        await pilot.press("?")
        assert pilot.app.screen.name == "help"


class TestQuitAction:
    """Test quit action from various screens."""

    @pytest.mark.asyncio
    async def test_quit_from_landing(self, pilot):
        """Pressing 'q' on landing screen exits app."""
        await pilot.press("0")
        await pilot.press("q")
        # App should have exited
        assert pilot.app._exit is True

    @pytest.mark.asyncio
    async def test_quit_from_build(self, pilot):
        """Pressing 'q' on build screen exits app."""
        await pilot.press("1")
        await pilot.press("q")
        assert pilot.app._exit is True

    @pytest.mark.asyncio
    async def test_quit_from_serve(self, pilot):
        """Pressing 'q' on serve screen exits app."""
        await pilot.press("2")
        await pilot.press("q")
        assert pilot.app._exit is True

    @pytest.mark.asyncio
    async def test_quit_from_health(self, pilot):
        """Pressing 'q' on health screen exits app."""
        await pilot.press("3")
        await pilot.press("q")
        assert pilot.app._exit is True


class TestBuildScreenActions:
    """Test build screen specific key bindings."""

    @pytest.mark.asyncio
    async def test_clear_log_action(self, pilot):
        """Pressing 'c' clears the build log."""
        from textual.widgets import Log

        await pilot.press("1")  # Go to build screen

        log = pilot.app.query_one("#build-log", Log)
        log.write_line("Test line 1")
        log.write_line("Test line 2")
        assert log.line_count > 0

        await pilot.press("c")
        assert log.line_count == 0

    @pytest.mark.asyncio
    async def test_rebuild_without_site_notifies(self, pilot_no_site):
        """Pressing 'r' without site shows error notification."""
        await pilot_no_site.press("1")  # Go to build screen
        await pilot_no_site.press("r")  # Trigger rebuild

        # Should have posted a notification
        # Notifications are stored in app._notifications in newer Textual
        # or we can check the screen for notification widgets


class TestServeScreenActions:
    """Test serve screen specific key bindings."""

    @pytest.mark.asyncio
    async def test_open_browser_action(self, pilot):
        """Pressing 'o' triggers open browser action."""
        await pilot.press("2")  # Go to serve screen
        # Just verify the action doesn't crash
        await pilot.press("o")

    @pytest.mark.asyncio
    async def test_force_rebuild_action(self, pilot):
        """Pressing 'r' triggers force rebuild action."""
        await pilot.press("2")
        await pilot.press("r")


class TestHealthScreenActions:
    """Test health screen specific key bindings."""

    @pytest.mark.asyncio
    async def test_rescan_action(self, pilot):
        """Pressing 'r' triggers rescan action."""
        await pilot.press("3")  # Go to health screen
        await pilot.press("r")


class TestQuickActionClicks:
    """Test QuickAction widget click interactions."""

    @pytest.mark.asyncio
    async def test_click_build_action_switches_screen(self, pilot):
        """Clicking Build quick action switches to build screen."""
        await pilot.press("0")  # Go to landing

        await pilot.click("#action-build")
        assert pilot.app.screen.name == "build"

    @pytest.mark.asyncio
    async def test_click_serve_action_switches_screen(self, pilot):
        """Clicking Serve quick action switches to serve screen."""
        await pilot.press("0")

        await pilot.click("#action-serve")
        assert pilot.app.screen.name == "serve"

    @pytest.mark.asyncio
    async def test_click_health_action_switches_screen(self, pilot):
        """Clicking Health quick action switches to health screen."""
        await pilot.press("0")

        await pilot.click("#action-health")
        assert pilot.app.screen.name == "health"
