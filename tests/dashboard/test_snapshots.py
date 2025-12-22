"""
Snapshot tests for Bengal Textual dashboards.

Uses pytest-textual-snapshot for visual regression testing.
Captures SVG screenshots of dashboard screens and compares
against baseline snapshots.

Run tests:
    pytest tests/dashboard/test_snapshots.py -v

Update snapshots after intentional changes:
    pytest tests/dashboard/test_snapshots.py --snapshot-update

Reference: https://textual.textualize.io/guide/testing/#snapshot-testing
"""

from __future__ import annotations

from tests.dashboard.conftest import APP_PATH


class TestScreenSnapshots:
    """Snapshot tests for all dashboard screens in default state."""

    def test_landing_screen(self, snap_compare):
        """Snapshot of landing screen with branding and quick actions."""
        assert snap_compare(APP_PATH, press=["0"])

    def test_build_screen(self, snap_compare):
        """Snapshot of build screen with phase table and log."""
        assert snap_compare(APP_PATH, press=["1"])

    def test_serve_screen(self, snap_compare):
        """Snapshot of serve screen with tabs and sparkline."""
        assert snap_compare(APP_PATH, press=["2"])

    def test_health_screen(self, snap_compare):
        """Snapshot of health screen with issue tree."""
        assert snap_compare(APP_PATH, press=["3"])

    def test_help_screen(self, snap_compare):
        """Snapshot of help overlay with keyboard shortcuts."""
        assert snap_compare(APP_PATH, press=["?"])


class TestNavigationSnapshots:
    """Snapshot tests for screen navigation sequences."""

    def test_navigation_build_to_serve(self, snap_compare):
        """Navigate from build to serve screen."""
        assert snap_compare(APP_PATH, press=["1", "2"])

    def test_navigation_serve_to_health(self, snap_compare):
        """Navigate from serve to health screen."""
        assert snap_compare(APP_PATH, press=["2", "3"])

    def test_navigation_health_to_landing(self, snap_compare):
        """Navigate from health back to landing."""
        assert snap_compare(APP_PATH, press=["3", "0"])

    def test_navigation_full_cycle(self, snap_compare):
        """Cycle through all screens: landing → build → serve → health → landing."""
        assert snap_compare(APP_PATH, press=["0", "1", "2", "3", "0"])


class TestTerminalSizeSnapshots:
    """Snapshot tests for different terminal sizes."""

    def test_small_terminal(self, snap_compare):
        """Dashboard in small terminal (40x20)."""
        assert snap_compare(APP_PATH, terminal_size=(40, 20))

    def test_medium_terminal(self, snap_compare):
        """Dashboard in medium terminal (80x24) - default."""
        assert snap_compare(APP_PATH, terminal_size=(80, 24))

    def test_large_terminal(self, snap_compare):
        """Dashboard in large terminal (160x50)."""
        assert snap_compare(APP_PATH, terminal_size=(160, 50))

    def test_wide_terminal(self, snap_compare):
        """Dashboard in wide terminal (200x30)."""
        assert snap_compare(APP_PATH, terminal_size=(200, 30))

    def test_tall_terminal(self, snap_compare):
        """Dashboard in tall terminal (80x60)."""
        assert snap_compare(APP_PATH, terminal_size=(80, 60))


class TestWidgetStateSnapshots:
    """Snapshot tests for specific widget states."""

    def test_build_screen_with_throbber_active(self, snap_compare):
        """Build screen with throbber animation active."""

        async def run_before(pilot) -> None:
            await pilot.press("1")  # Go to build screen
            try:
                from bengal.cli.dashboard.widgets import BengalThrobber

                throbber = pilot.app.query_one("#build-throbber", BengalThrobber)
                throbber.active = True
            except Exception:
                pass  # Widget may not exist in all configurations

        assert snap_compare(APP_PATH, run_before=run_before)

    def test_build_screen_with_flash_success(self, snap_compare):
        """Build screen showing success flash message."""

        async def run_before(pilot) -> None:
            await pilot.press("1")
            try:
                from bengal.cli.dashboard.widgets import BuildFlash

                flash = pilot.app.query_one("#build-flash", BuildFlash)
                flash.show_success("Build complete in 245ms")
            except Exception:
                pass

        assert snap_compare(APP_PATH, run_before=run_before)

    def test_build_screen_with_flash_error(self, snap_compare):
        """Build screen showing error flash message."""

        async def run_before(pilot) -> None:
            await pilot.press("1")
            try:
                from bengal.cli.dashboard.widgets import BuildFlash

                flash = pilot.app.query_one("#build-flash", BuildFlash)
                flash.show_error("Template not found: base.html")
            except Exception:
                pass

        assert snap_compare(APP_PATH, run_before=run_before)

    def test_build_screen_with_flash_building(self, snap_compare):
        """Build screen showing building flash message."""

        async def run_before(pilot) -> None:
            await pilot.press("1")
            try:
                from bengal.cli.dashboard.widgets import BuildFlash

                flash = pilot.app.query_one("#build-flash", BuildFlash)
                flash.show_building("Rendering 245 pages...")
            except Exception:
                pass

        assert snap_compare(APP_PATH, run_before=run_before)


class TestHelpScreenSnapshots:
    """Snapshot tests for help screen states."""

    def test_help_from_build_screen(self, snap_compare):
        """Help screen opened from build screen."""
        assert snap_compare(APP_PATH, press=["1", "?"])

    def test_help_from_health_screen(self, snap_compare):
        """Help screen opened from health screen."""
        assert snap_compare(APP_PATH, press=["3", "?"])
