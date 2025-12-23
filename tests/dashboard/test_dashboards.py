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

    def test_import_custom_widgets(self):
        """Test custom Bengal widget imports."""
        from bengal.cli.dashboard.widgets import (
            BengalThrobber,
            BuildFlash,
            BuildPhasePlan,
            QuickAction,
        )

        assert BengalThrobber is not None
        assert BuildFlash is not None
        assert BuildPhasePlan is not None
        assert QuickAction is not None


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
        assert app.port == 5173  # Default port is 5173 (Vite default)

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
            LandingScreen,
            ServeScreen,
        )

        assert BengalScreen is not None
        assert BuildScreen is not None
        assert ServeScreen is not None
        assert HealthScreen is not None
        assert HelpScreen is not None
        assert LandingScreen is not None


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

    def test_discover_method_exists(self):
        """Test BengalCommandProvider has discover method."""
        import inspect

        from bengal.cli.dashboard.commands import BengalCommandProvider

        # Provider should have discover method for showing hits before typing
        assert hasattr(BengalCommandProvider, "discover")
        # discover is an async generator (async def ... yield)
        assert inspect.isasyncgenfunction(BengalCommandProvider.discover)


class TestCustomWidgets:
    """Test custom Bengal widgets."""

    def test_throbber_visual_import(self):
        """Test BengalThrobberVisual can be imported."""
        from bengal.cli.dashboard.widgets.throbber import BengalThrobberVisual

        assert BengalThrobberVisual is not None

    def test_throbber_widget_init(self):
        """Test BengalThrobber widget initialization."""
        from bengal.cli.dashboard.widgets import BengalThrobber

        throbber = BengalThrobber()
        assert throbber.active is False

    def test_flash_widget_init(self):
        """Test BuildFlash widget initialization."""
        from bengal.cli.dashboard.widgets import BuildFlash

        flash = BuildFlash()
        assert flash is not None

    def test_phase_plan_widget_import(self):
        """Test BuildPhasePlan widget can be imported."""
        from bengal.cli.dashboard.widgets import BuildPhasePlan
        from bengal.cli.dashboard.widgets.phase_plan import BuildPhase

        assert BuildPhasePlan is not None
        assert BuildPhase is not None

    def test_build_phase_dataclass(self):
        """Test BuildPhase dataclass."""
        from bengal.cli.dashboard.widgets.phase_plan import BuildPhase

        phase = BuildPhase(
            name="discovery",
            status="running",
            duration_ms=150,
        )
        assert phase.name == "discovery"
        assert phase.status == "running"
        assert phase.duration_ms == 150

    def test_build_phase_plan_status_icons(self):
        """Test BuildPhasePlan has status icons."""
        from bengal.cli.dashboard.widgets import BuildPhasePlan

        # Test all status icons via the class
        icons = BuildPhasePlan.STATUS_ICONS
        assert icons["pending"] == "○"
        assert icons["running"] == "●"
        assert icons["complete"] == "✓"
        assert icons["error"] == "✗"

    def test_quick_action_widget_init(self):
        """Test QuickAction widget initialization."""
        from bengal.cli.dashboard.widgets import QuickAction

        # QuickAction uses positional args: emoji, title, description
        action = QuickAction(
            "🚀",
            "Test Action",
            "Test description",
            id="test-action",
        )
        assert action.emoji == "🚀"
        assert action.action_title == "Test Action"  # Note: stored as action_title
        assert action.description == "Test description"
        assert action.id == "test-action"

    def test_quick_action_message(self):
        """Test QuickAction.Selected message."""
        from bengal.cli.dashboard.widgets.quick_action import QuickAction

        # Check message class exists
        assert hasattr(QuickAction, "Selected")


class TestAppConfiguration:
    """Test BengalApp configuration and signals."""

    def test_app_with_start_screen(self):
        """Test BengalApp with different start screens."""
        from bengal.cli.dashboard.app import BengalApp

        # Test build start screen
        app = BengalApp(site=None, start_screen="build")
        assert app.start_screen == "build"

        # Test serve start screen
        app = BengalApp(site=None, start_screen="serve")
        assert app.start_screen == "serve"

        # Test health start screen
        app = BengalApp(site=None, start_screen="health")
        assert app.start_screen == "health"

    def test_app_config_signal_exists(self):
        """Test BengalApp has config_changed_signal."""
        from bengal.cli.dashboard.app import BengalApp

        app = BengalApp(site=None)
        assert hasattr(app, "config_changed_signal")

    def test_app_update_config(self):
        """Test BengalApp.update_config method."""
        from bengal.cli.dashboard.app import BengalApp

        app = BengalApp(site=None)

        # Update config
        app.update_config("test_key", "test_value")

        # Check config was stored
        assert app._config["test_key"] == "test_value"

    def test_app_command_providers(self):
        """Test BengalApp has command providers."""
        from bengal.cli.dashboard.app import BengalApp

        # BengalApp registers command providers via COMMANDS class var
        assert hasattr(BengalApp, "COMMANDS")
        assert len(BengalApp.COMMANDS) > 0
