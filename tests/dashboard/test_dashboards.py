"""
Tests for Bengal Textual Dashboards.

Tests the dashboard modules for:
- Module imports
- Dashboard instantiation
- Message handling
- Screen navigation

For snapshot testing, see test_snapshots.py.
"""

from __future__ import annotations


class TestDashboardImports:
    """Test that all dashboard modules can be imported."""

    def test_import_messages(self):
        """Test message imports."""
        from bengal.cli.dashboard import (
            BuildComplete,
            BuildEvent,
            FileChanged,
            HealthScanComplete,
            HealthScanStarted,
            PhaseComplete,
            PhaseProgress,
            PhaseStarted,
            RebuildTriggered,
            WatcherStatus,
        )

        # All messages should be importable
        assert BuildEvent is not None
        assert PhaseStarted is not None
        assert PhaseProgress is not None
        assert PhaseComplete is not None
        assert BuildComplete is not None
        assert FileChanged is not None
        assert RebuildTriggered is not None
        assert WatcherStatus is not None
        assert HealthScanStarted is not None
        assert HealthScanComplete is not None

    def test_import_dashboards(self):
        """Test dashboard class imports."""
        from bengal.cli.dashboard import (
            BengalApp,
            BengalBuildDashboard,
            BengalHealthDashboard,
            BengalServeDashboard,
            run_build_dashboard,
            run_health_dashboard,
            run_serve_dashboard,
            run_unified_dashboard,
        )

        assert BengalBuildDashboard is not None
        assert BengalServeDashboard is not None
        assert BengalHealthDashboard is not None
        assert BengalApp is not None
        assert run_build_dashboard is not None
        assert run_serve_dashboard is not None
        assert run_health_dashboard is not None
        assert run_unified_dashboard is not None

    def test_import_base(self):
        """Test base class imports."""
        from bengal.cli.dashboard.base import BengalDashboard

        assert BengalDashboard is not None

    def test_import_widgets(self):
        """Test widget re-exports."""
        from bengal.cli.dashboard.widgets import (
            DataTable,
            Footer,
            Header,
            Log,
            ProgressBar,
            Static,
            TabbedContent,
            Tree,
        )

        assert Header is not None
        assert Footer is not None
        assert Static is not None
        assert Log is not None
        assert DataTable is not None
        assert ProgressBar is not None
        assert Tree is not None
        assert TabbedContent is not None


class TestMessages:
    """Test message dataclasses."""

    def test_build_event_base(self):
        """Test BuildEvent base class."""
        from bengal.cli.dashboard import BuildEvent

        event = BuildEvent()
        assert event is not None

    def test_phase_started(self):
        """Test PhaseStarted message."""
        from bengal.cli.dashboard import PhaseStarted

        msg = PhaseStarted(name="discovery", total_items=100)
        assert msg.name == "discovery"
        assert msg.total_items == 100

    def test_phase_complete(self):
        """Test PhaseComplete message."""
        from bengal.cli.dashboard import PhaseComplete

        msg = PhaseComplete(name="rendering", duration_ms=150.5, details="42 pages")
        assert msg.name == "rendering"
        assert msg.duration_ms == 150.5
        assert msg.details == "42 pages"

    def test_build_complete(self):
        """Test BuildComplete message."""
        from bengal.cli.dashboard import BuildComplete

        msg = BuildComplete(success=True, duration_ms=500.0, stats={"pages": 100})
        assert msg.success is True
        assert msg.duration_ms == 500.0
        assert msg.stats == {"pages": 100}
        assert msg.error is None

    def test_build_complete_with_error(self):
        """Test BuildComplete message with error."""
        from bengal.cli.dashboard import BuildComplete

        msg = BuildComplete(
            success=False,
            duration_ms=100.0,
            error="Template not found",
        )
        assert msg.success is False
        assert msg.error == "Template not found"

    def test_file_changed(self):
        """Test FileChanged message."""
        from bengal.cli.dashboard import FileChanged

        msg = FileChanged(path="/content/index.md", change_type="modified")
        assert msg.path == "/content/index.md"
        assert msg.change_type == "modified"


class TestDashboardInstantiation:
    """Test dashboard instantiation (without running)."""

    def test_build_dashboard_init(self):
        """Test BengalBuildDashboard can be instantiated."""
        from bengal.cli.dashboard.build import BengalBuildDashboard

        app = BengalBuildDashboard(site=None)
        assert app.TITLE == "Bengal Build"
        assert app.site is None

    def test_serve_dashboard_init(self):
        """Test BengalServeDashboard can be instantiated."""
        from bengal.cli.dashboard.serve import BengalServeDashboard

        app = BengalServeDashboard(site=None)
        assert app.TITLE == "Bengal Serve"
        assert app.site is None
        assert app.host == "localhost"
        assert app.port == 3000  # Default port is 3000

    def test_health_dashboard_init(self):
        """Test BengalHealthDashboard can be instantiated."""
        from bengal.cli.dashboard.health import BengalHealthDashboard

        app = BengalHealthDashboard(site=None)
        assert app.TITLE == "Bengal Health"
        assert app.site is None

    def test_unified_app_init(self):
        """Test BengalApp can be instantiated."""
        from bengal.cli.dashboard.app import BengalApp

        app = BengalApp(site=None, start_screen="build")
        assert app.TITLE == "Bengal"
        assert app.site is None
        assert app.start_screen == "build"


class TestTokens:
    """Test design tokens."""

    def test_bengal_palette(self):
        """Test BENGAL_PALETTE contains required colors."""
        from bengal.themes.tokens import BENGAL_PALETTE

        assert BENGAL_PALETTE.primary is not None
        assert BENGAL_PALETTE.secondary is not None
        assert BENGAL_PALETTE.success is not None
        assert BENGAL_PALETTE.warning is not None
        assert BENGAL_PALETTE.error is not None

    def test_bengal_mascot(self):
        """Test BENGAL_MASCOT has cat character."""
        from bengal.themes.tokens import BENGAL_MASCOT

        # Bengal uses ASCII art cat, not emoji
        assert BENGAL_MASCOT.cat == "ᓚᘏᗢ"

    def test_mouse_mascot(self):
        """Test BENGAL_MASCOT.mouse has mouse character."""
        from bengal.themes.tokens import BENGAL_MASCOT

        # Mouse is accessed from BENGAL_MASCOT, not separate constant
        assert BENGAL_MASCOT.mouse == "ᘛ⁐̤ᕐᐷ"


class TestNotifications:
    """Test notification helpers."""

    def test_notification_imports(self):
        """Test notification functions can be imported."""
        from bengal.cli.dashboard.notifications import (
            notify_build_complete,
            notify_file_changed,
            notify_health_issues,
            notify_rebuild_triggered,
        )

        assert notify_build_complete is not None
        assert notify_file_changed is not None
        assert notify_health_issues is not None
        assert notify_rebuild_triggered is not None


class TestScreens:
    """Test screen classes."""

    def test_screen_imports(self):
        """Test screen classes can be imported."""
        from bengal.cli.dashboard.screens import (
            BengalScreen,
            BuildScreen,
            HealthScreen,
            HelpScreen,
            ServeScreen,
        )

        assert BengalScreen is not None
        assert BuildScreen is not None
        assert ServeScreen is not None
        assert HealthScreen is not None
        assert HelpScreen is not None


class TestCommands:
    """Test command provider."""

    def test_command_provider_import(self):
        """Test BengalCommandProvider can be imported."""
        from bengal.cli.dashboard.commands import (
            BengalCommandProvider,
            PageSearchProvider,
        )

        assert BengalCommandProvider is not None
        assert PageSearchProvider is not None

    def test_command_definitions(self):
        """Test command definitions are present."""
        from bengal.cli.dashboard.commands import BengalCommandProvider

        assert len(BengalCommandProvider.COMMANDS) > 0

        # Check required commands exist
        command_names = [c["name"] for c in BengalCommandProvider.COMMANDS]
        assert "Rebuild Site" in command_names
        assert "Quit" in command_names
