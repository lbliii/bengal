"""
Screen classes for Bengal unified dashboard.

Each screen represents a mode of the unified dashboard:
- BuildScreen: Build progress and phase timing
- ServeScreen: Dev server with file watching
- HealthScreen: Site health explorer

Screens are navigated via number keys (1, 2, 3) or command palette.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

if TYPE_CHECKING:
    from bengal.core.site import Site


class BengalScreen(Screen):
    """
    Base screen for Bengal unified dashboard.

    All screens share common bindings and styling.
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("1", "goto_build", "Build", show=True),
        Binding("2", "goto_serve", "Serve", show=True),
        Binding("3", "goto_health", "Health", show=True),
        Binding("q", "quit", "Quit"),
        Binding("?", "toggle_help", "Help"),
    ]

    def action_goto_build(self) -> None:
        """Switch to build screen."""
        self.app.switch_screen("build")

    def action_goto_serve(self) -> None:
        """Switch to serve screen."""
        self.app.switch_screen("serve")

    def action_goto_health(self) -> None:
        """Switch to health screen."""
        self.app.switch_screen("health")

    def action_toggle_help(self) -> None:
        """Toggle help screen."""
        self.app.push_screen("help")


class BuildScreen(BengalScreen):
    """
    Build screen for the unified dashboard.

    Shows build progress, phase timing, and output log.
    Reuses components from BengalBuildDashboard.
    """

    def __init__(self, site: Site | None = None, **kwargs):
        """Initialize build screen."""
        super().__init__(**kwargs)
        self.site = site

    def compose(self) -> ComposeResult:
        """Compose build screen layout."""
        from textual.widgets import DataTable, Log, ProgressBar

        yield Header()

        with Vertical(id="main-content"):
            yield Static("🔨 Build Dashboard", id="screen-title", classes="section-header")
            yield ProgressBar(total=100, show_eta=False, id="build-progress")

            with Vertical(classes="section"):
                yield Static("Build Phases:", classes="section-header")
                yield DataTable(id="phase-table")

            with Vertical(classes="section"):
                yield Static("Output:", classes="section-header")
                yield Log(id="build-log", auto_scroll=True)

        yield Footer()

    def on_mount(self) -> None:
        """Set up build screen."""
        from textual.widgets import DataTable

        table = self.query_one("#phase-table", DataTable)
        table.add_columns("Status", "Phase", "Time", "Details")

        phases = ["Discovery", "Taxonomies", "Rendering", "Assets", "Postprocess"]
        for phase in phases:
            table.add_row("·", phase, "-", "", key=phase)


class ServeScreen(BengalScreen):
    """
    Serve screen for the unified dashboard.

    Shows dev server status, file changes, and build history.
    Reuses components from BengalServeDashboard.
    """

    BINDINGS: ClassVar[list[Binding]] = [
        *BengalScreen.BINDINGS,
        Binding("o", "open_browser", "Open Browser"),
        Binding("r", "force_rebuild", "Rebuild"),
    ]

    def __init__(self, site: Site | None = None, **kwargs):
        """Initialize serve screen."""
        super().__init__(**kwargs)
        self.site = site

    def compose(self) -> ComposeResult:
        """Compose serve screen layout."""
        from textual.widgets import Log, Sparkline, TabbedContent, TabPane

        yield Header()

        with Vertical(id="main-content"):
            yield Static("🌐 Serve Dashboard", id="screen-title", classes="section-header")
            yield Static("", id="server-url", classes="label-primary")

            with Vertical(classes="section"):
                yield Static("Build History (ms):", classes="section-header")
                yield Sparkline([0], id="build-sparkline")

            with TabbedContent(id="serve-tabs"):
                with TabPane("Changes", id="changes-tab"):
                    yield Log(id="changes-log", auto_scroll=True)
                with TabPane("Stats", id="stats-tab"):
                    yield Static("Server statistics will appear here")
                with TabPane("Errors", id="errors-tab"):
                    yield Log(id="errors-log", auto_scroll=True)

        yield Footer()

    def action_open_browser(self) -> None:
        """Open browser."""
        self.app.notify("Opening browser...", title="Browser")

    def action_force_rebuild(self) -> None:
        """Force rebuild."""
        self.app.notify("Triggering rebuild...", title="Rebuild")


class HealthScreen(BengalScreen):
    """
    Health screen for the unified dashboard.

    Shows health issues in a tree with details panel.
    Reuses components from BengalHealthDashboard.
    """

    BINDINGS: ClassVar[list[Binding]] = [
        *BengalScreen.BINDINGS,
        Binding("r", "rescan", "Rescan"),
    ]

    def __init__(self, site: Site | None = None, **kwargs):
        """Initialize health screen."""
        super().__init__(**kwargs)
        self.site = site

    def compose(self) -> ComposeResult:
        """Compose health screen layout."""
        from textual.containers import Horizontal
        from textual.widgets import Static, Tree

        yield Header()

        with Vertical(id="main-content"):
            yield Static("🏥 Health Dashboard", id="screen-title", classes="section-header")
            yield Static("Select an issue to view details", id="health-summary")

            with Horizontal(classes="health-layout"):
                with Vertical(id="tree-container"):
                    yield Static("Issues:", classes="section-header")
                    yield Tree("Health Report", id="health-tree")

                with Vertical(id="details-container", classes="panel"):
                    yield Static("Details:", classes="panel-title")
                    yield Static("Select an issue", id="issue-details")

        yield Footer()

    def on_mount(self) -> None:
        """Set up health screen."""
        from textual.widgets import Tree

        tree = self.query_one("#health-tree", Tree)
        tree.show_root = False

        # Add sample categories
        links = tree.root.add("Links (0)")
        links.add_leaf("✓ No issues")

    def action_rescan(self) -> None:
        """Rescan site health."""
        self.app.notify("Scanning site health...", title="Health")


class HelpScreen(Screen):
    """
    Help screen showing keyboard shortcuts.
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "pop_screen", "Close"),
        Binding("q", "pop_screen", "Close"),
    ]

    def compose(self) -> ComposeResult:
        """Compose help screen."""
        yield Header()

        with Vertical(id="help-content", classes="panel"):
            yield Static("⌨️  Keyboard Shortcuts", classes="panel-title")
            yield Static("""
[bold]Navigation[/bold]
  1, 2, 3      Switch screens (Build, Serve, Health)
  Ctrl+P       Command palette
  ?            Toggle this help

[bold]Build Screen[/bold]
  r            Rebuild site
  c            Clear log

[bold]Serve Screen[/bold]
  o            Open in browser
  r            Force rebuild
  c            Clear log

[bold]Health Screen[/bold]
  r            Rescan site
  Enter        View issue details

[bold]General[/bold]
  q            Quit dashboard
  Escape       Close dialogs
""")

        yield Footer()

    def action_pop_screen(self) -> None:
        """Close help screen."""
        self.app.pop_screen()
