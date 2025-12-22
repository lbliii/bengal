"""
Unified Bengal Dashboard Application.

The main Textual app that provides a unified dashboard experience
with multiple screens for Build, Serve, Health, and Landing operations.

Inspired by Toad's multi-screen architecture with:
- SCREENS dict for lazy screen loading
- Command palette with providers
- Config signal for reactive updates

Usage:
    bengal --dashboard
    bengal --dashboard --start health
    bengal --dashboard --serve --port 8000

Features:
- Multi-screen navigation (1=Build, 2=Serve, 3=Health)
- Command palette (Ctrl+P) for quick actions
- Consistent styling across all screens
- Keyboard-driven workflow
- Web serve mode via textual-serve
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import App
from textual.binding import Binding
from textual.signal import Signal

from bengal.cli.dashboard.commands import BengalCommandProvider, BengalPageProvider
from bengal.cli.dashboard.screens import (
    BuildScreen,
    HealthScreen,
    HelpScreen,
    LandingScreen,
    ServeScreen,
)
from bengal.themes.tokens import BENGAL_MASCOT, BENGAL_PALETTE, BengalPalette

if TYPE_CHECKING:
    from bengal.core.site import Site


class BengalApp(App):
    """
    Unified Bengal dashboard application.

    Provides a multi-screen dashboard with:
    - Landing screen: Site overview and quick actions
    - Build screen: Build progress and phase timing
    - Serve screen: Dev server with file watching
    - Health screen: Site health explorer

    Navigate between screens with number keys (1, 2, 3)
    or use the command palette (Ctrl+P).

    Signals:
        config_changed_signal: Published when config values change
            Payload: tuple of (key: str, value: Any)

    Example:
        >>> app = BengalApp(site=site)
        >>> app.run()
    """

    # Load CSS from bengal.tcss
    CSS_PATH: ClassVar[str | Path] = Path(__file__).parent / "bengal.tcss"

    TITLE: ClassVar[str] = "Bengal"
    SUB_TITLE: ClassVar[str] = "Dashboard"

    # Command palette providers
    COMMANDS: ClassVar[set[type]] = {
        BengalCommandProvider,
        BengalPageProvider,
    }

    # Global bindings
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("0", "goto_landing", "Home", show=False, priority=True),
        Binding("1", "goto_build", "Build", show=True, priority=True),
        Binding("2", "goto_serve", "Serve", show=True, priority=True),
        Binding("3", "goto_health", "Health", show=True, priority=True),
        Binding("q", "quit", "Quit", priority=True),
        Binding("?", "toggle_help", "Help"),
        Binding("ctrl+p", "command_palette", "Commands", show=False),
        Binding("s", "toggle_stats", "Stats", show=False),
        Binding("r", "rebuild", "Rebuild", show=False),
        Binding("o", "open_browser", "Browser", show=False),
        Binding("c", "clear_log", "Clear", show=False),
    ]

    def __init__(
        self,
        site: Site | None = None,
        *,
        start_screen: str = "build",
        startup_error: str | None = None,
        **kwargs: Any,
    ):
        """
        Initialize the unified dashboard.

        Args:
            site: Site instance
            start_screen: Initial screen to show (landing, build, serve, health)
            startup_error: Error message from site loading (shown as notification)
            **kwargs: Additional app options
        """
        super().__init__(**kwargs)
        self.site = site
        self.start_screen = start_screen
        self.startup_error = startup_error

        # Config signal for reactive updates (Toad pattern)
        self.config_changed_signal: Signal[tuple[str, Any]] = Signal(self, "config_changed")

        # Internal config storage
        self._config: dict[str, Any] = {
            "show_stats": True,
            "show_log": True,
            "compact_mode": False,
        }

        # Server URL for page links
        self.server_url = "http://localhost:1313"

    def on_mount(self) -> None:
        """Set up the app when it mounts."""
        # Install all screens with site reference
        self.install_screen(LandingScreen(site=self.site), name="landing")
        self.install_screen(BuildScreen(site=self.site), name="build")
        self.install_screen(ServeScreen(site=self.site), name="serve")
        self.install_screen(HealthScreen(site=self.site), name="health")
        self.install_screen(HelpScreen(), name="help")

        # Push initial screen onto stack
        self.push_screen(self.start_screen)

        # Show startup error notification if site failed to load
        if self.startup_error:
            self.notify(
                f"{self.error_mascot}  {self.startup_error}",
                title="Site Load Failed",
                severity="warning",
                timeout=10,  # Longer timeout for important info
            )
            self.notify(
                "Running in demo mode without site features",
                severity="information",
                timeout=5,
            )

    @property
    def mascot(self) -> str:
        """Get the Bengal cat mascot."""
        return BENGAL_MASCOT.cat

    @property
    def error_mascot(self) -> str:
        """Get the mouse mascot (for errors)."""
        return BENGAL_MASCOT.mouse

    @property
    def palette(self) -> BengalPalette:
        """Get the color palette."""
        return BENGAL_PALETTE

    def update_config(self, key: str, value: Any) -> None:
        """
        Update dashboard config and notify subscribers.

        Args:
            key: Configuration key (e.g., "show_stats")
            value: New value
        """
        self._config[key] = value
        self.config_changed_signal.publish((key, value))

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self._config.get(key, default)

    # === Actions ===

    def action_goto_landing(self) -> None:
        """Switch to landing screen."""
        self.switch_screen("landing")

    def action_goto_build(self) -> None:
        """Switch to build screen."""
        self.switch_screen("build")

    def action_goto_serve(self) -> None:
        """Switch to serve screen."""
        self.switch_screen("serve")

    def action_goto_health(self) -> None:
        """Switch to health screen."""
        self.switch_screen("health")

    def action_toggle_help(self) -> None:
        """Toggle help screen."""
        if self.screen.name == "help":
            self.pop_screen()
        else:
            self.push_screen("help")

    def action_toggle_stats(self) -> None:
        """Toggle statistics panel visibility."""
        current = self.get_config("show_stats", True)
        self.update_config("show_stats", not current)
        self.notify("Stats panel " + ("shown" if not current else "hidden"))

    def action_rebuild(self) -> None:
        """Trigger a site rebuild."""
        # If on build screen, delegate to its rebuild action
        if hasattr(self.screen, "action_rebuild") and self.screen.name == "build":
            self.screen.action_rebuild()
        else:
            # Switch to build screen and trigger rebuild
            self.push_screen("build")
            self.notify("Switch to Build screen and press 'r' to rebuild", title="Build")

    def action_open_browser(self) -> None:
        """Open site in browser."""
        import webbrowser

        webbrowser.open(self.server_url)
        self.notify(f"Opening {self.server_url}", title="Browser")

    def action_clear_log(self) -> None:
        """Clear the output log on current screen."""
        from textual.widgets import Log

        # Try to find any log widget on current screen
        log_ids = ["#build-log", "#changes-log", "#errors-log", "#activity-log"]
        cleared = False

        for log_id in log_ids:
            try:
                log = self.screen.query_one(log_id, Log)
                log.clear()
                cleared = True
            except Exception:
                continue

        if cleared:
            self.notify("Log cleared")
        else:
            self.notify("No log to clear")

    async def action_quit(self) -> None:
        """Quit the app."""
        self.exit()


def run_unified_dashboard(
    site: Site | None = None,
    *,
    start_screen: str = "build",
    startup_error: str | None = None,
    **kwargs: Any,
) -> None:
    """
    Run the unified Bengal dashboard.

    This is the entry point called by `bengal --dashboard`.

    Args:
        site: Site instance (optional, will load from current dir if not provided)
        start_screen: Initial screen to show (build, serve, health)
        startup_error: Error from site loading (displayed as notification on mount)
        **kwargs: Additional options
    """
    app = BengalApp(
        site=site,
        start_screen=start_screen,
        startup_error=startup_error,
        **kwargs,
    )
    app.run()
