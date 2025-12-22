"""
Unified Bengal Dashboard Application.

The main Textual app that provides a unified dashboard experience
with multiple screens for Build, Serve, and Health operations.

Usage:
    bengal --dashboard

Features:
- Multi-screen navigation (1=Build, 2=Serve, 3=Health)
- Command palette (Ctrl+P) for quick actions
- Consistent styling across all screens
- Keyboard-driven workflow
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import App
from textual.binding import Binding

from bengal.cli.dashboard.screens import (
    BuildScreen,
    HealthScreen,
    HelpScreen,
    ServeScreen,
)
from bengal.themes.tokens import BENGAL_MASCOT, BENGAL_PALETTE

if TYPE_CHECKING:
    from bengal.core.site import Site


class BengalApp(App):
    """
    Unified Bengal dashboard application.

    Provides a multi-screen dashboard with:
    - Build screen: Build progress and phase timing
    - Serve screen: Dev server with file watching
    - Health screen: Site health explorer

    Navigate between screens with number keys (1, 2, 3)
    or use the command palette (Ctrl+P).

    Example:
        >>> app = BengalApp(site=site)
        >>> app.run()
    """

    # Load CSS from bengal.tcss
    CSS_PATH: ClassVar[str | Path] = Path(__file__).parent / "bengal.tcss"

    TITLE: ClassVar[str] = "Bengal"
    SUB_TITLE: ClassVar[str] = "Dashboard"

    # Screen registry
    SCREENS: ClassVar[dict] = {
        "build": BuildScreen,
        "serve": ServeScreen,
        "health": HealthScreen,
        "help": HelpScreen,
    }

    # Global bindings
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("1", "goto_build", "Build", show=True, priority=True),
        Binding("2", "goto_serve", "Serve", show=True, priority=True),
        Binding("3", "goto_health", "Health", show=True, priority=True),
        Binding("q", "quit", "Quit", priority=True),
        Binding("?", "toggle_help", "Help"),
        Binding("ctrl+p", "command_palette", "Commands", show=False),
    ]

    def __init__(
        self,
        site: Site | None = None,
        *,
        start_screen: str = "build",
        **kwargs: Any,
    ):
        """
        Initialize the unified dashboard.

        Args:
            site: Site instance
            start_screen: Initial screen to show (build, serve, health)
            **kwargs: Additional app options
        """
        super().__init__(**kwargs)
        self.site = site
        self.start_screen = start_screen

    def on_mount(self) -> None:
        """Set up the app when it mounts."""
        # Install all screens
        for name, screen_class in self.SCREENS.items():
            if name == "help":
                self.install_screen(screen_class(), name=name)
            else:
                self.install_screen(screen_class(site=self.site), name=name)

        # Switch to initial screen
        self.switch_screen(self.start_screen)

    @property
    def mascot(self) -> str:
        """Get the Bengal cat mascot."""
        return BENGAL_MASCOT.cat

    @property
    def error_mascot(self) -> str:
        """Get the mouse mascot (for errors)."""
        return BENGAL_MASCOT.mouse

    @property
    def palette(self):
        """Get the color palette."""
        return BENGAL_PALETTE

    # === Actions ===

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

    def action_command_palette(self) -> None:
        """Open command palette."""
        # For now, show a notification
        # Full implementation would use Textual's CommandPalette
        self.notify("Command palette: Ctrl+P (coming soon)", title="Commands")

    def action_quit(self) -> None:
        """Quit the app."""
        self.exit()


def run_unified_dashboard(
    site: Site | None = None,
    *,
    start_screen: str = "build",
    **kwargs: Any,
) -> None:
    """
    Run the unified Bengal dashboard.

    This is the entry point called by `bengal --dashboard`.

    Args:
        site: Site instance (optional, will load from current dir if not provided)
        start_screen: Initial screen to show (build, serve, health)
        **kwargs: Additional options
    """
    app = BengalApp(
        site=site,
        start_screen=start_screen,
        **kwargs,
    )
    app.run()
