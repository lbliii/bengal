"""
Base dashboard class for Bengal Textual apps.

Provides the BengalDashboard base class with:
- Common key bindings (q=quit, r=rebuild, c=clear, ?=help)
- Reactive state management
- Themed styling from bengal.tcss
- Consistent header/footer across dashboards

All specific dashboards (Build, Serve, Health) inherit from this.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive

from bengal.cli.dashboard.widgets import Footer, Header
from bengal.themes.tokens import BENGAL_MASCOT, BENGAL_PALETTE


class BengalDashboard(App[None]):
    """
    Base class for all Bengal Textual dashboards.

    Provides consistent styling, bindings, and reactive state
    shared across Build, Serve, and Health dashboards.

    Subclasses should:
    1. Override compose() to define layout
    2. Add custom bindings via BINDINGS class var
    3. Handle custom messages for their domain

    Example:
        class BengalBuildDashboard(BengalDashboard):
            BINDINGS = BengalDashboard.BINDINGS + [
                Binding("s", "stop_build", "Stop Build"),
            ]

            def compose(self) -> ComposeResult:
                yield Header()
                yield ProgressBar()
                yield Footer()
    """

    # Load CSS from bengal.tcss
    CSS_PATH: ClassVar[str | Path] = Path(__file__).parent / "bengal.tcss"

    # Title shown in header
    TITLE: ClassVar[str] = "Bengal"

    # Subtitle (overridden by subclasses)
    SUB_TITLE: ClassVar[str] = "Dashboard"

    # Common key bindings across all dashboards
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("?", "toggle_help", "Help"),
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]

    # Reactive state
    is_running: reactive[bool] = reactive(False)
    status_text: reactive[str] = reactive("Ready")
    error_count: reactive[int] = reactive(0)
    warning_count: reactive[int] = reactive(0)

    def __init__(
        self,
        *,
        title: str | None = None,
        sub_title: str | None = None,
    ):
        """
        Initialize Bengal dashboard.

        Args:
            title: Override default title
            sub_title: Override default subtitle
        """
        super().__init__()
        if title:
            self.title = title
        if sub_title:
            self.sub_title = sub_title

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

    def compose(self) -> ComposeResult:
        """
        Compose the dashboard layout.

        Subclasses should override this to add their own widgets
        between Header and Footer.
        """
        yield Header()
        yield Footer()

    def action_toggle_help(self) -> None:
        """Toggle the help screen."""
        # For now, just show a notification
        # TODO: Implement help screen in Phase 7
        self.notify("Help: Press 'q' to quit", title="Keyboard Shortcuts")

    def action_quit(self) -> None:
        """Quit the dashboard."""
        self.exit()

    def notify_success(self, message: str, title: str = "Success") -> None:
        """Show a success notification toast."""
        self.notify(message, title=title, severity="information")

    def notify_warning(self, message: str, title: str = "Warning") -> None:
        """Show a warning notification toast."""
        self.notify(message, title=title, severity="warning")

    def notify_error(self, message: str, title: str = "Error") -> None:
        """Show an error notification toast."""
        self.notify(message, title=title, severity="error")

    def update_status(self, text: str) -> None:
        """Update the status text (shown in footer/status bar)."""
        self.status_text = text
