"""
Serve Dashboard for Bengal.

Interactive Textual dashboard for `bengal serve --dashboard` that shows:
- Server status with URL
- Tabbed content (Changes/Stats/Errors)
- Build history sparkline
- Live file change log
- Keyboard shortcuts (q=quit, o=open browser, r=rebuild)

Usage:
    bengal serve --dashboard

The dashboard runs the dev server in a background thread and updates
the UI reactively based on file changes and rebuild events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Log,
    Sparkline,
    Static,
    TabbedContent,
    TabPane,
)

from bengal.cli.dashboard.base import BengalDashboard
from bengal.cli.dashboard.messages import (
    BuildComplete,
    FileChanged,
    RebuildTriggered,
    WatcherStatus,
)
from bengal.cli.dashboard.notifications import (
    notify_build_complete,
    notify_file_changed,
    notify_rebuild_triggered,
    notify_server_started,
)

if TYPE_CHECKING:
    from bengal.core.site import Site


@dataclass
class ChangeEntry:
    """A file change entry for the log."""

    path: str
    change_type: str  # "created", "modified", "deleted"
    timestamp: datetime = field(default_factory=datetime.now)


class BengalServeDashboard(BengalDashboard):
    """
    Interactive serve dashboard with live file watching.

    Shows:
    - Header with Bengal branding and server URL
    - Tabbed content area:
        - Changes: Live log of file changes
        - Stats: Build statistics and cache info
        - Errors: Any build errors or warnings
    - Sparkline showing build time history
    - Footer with keyboard shortcuts

    Bindings:
        q: Quit (stops server)
        o: Open in browser
        r: Force rebuild
        c: Clear log
        ?: Help
    """

    TITLE: ClassVar[str] = "Bengal Serve"
    SUB_TITLE: ClassVar[str] = "Dev Server"

    BINDINGS: ClassVar[list[Binding]] = [
        *BengalDashboard.BINDINGS,
        Binding("o", "open_browser", "Open Browser", show=True),
        Binding("r", "force_rebuild", "Rebuild", show=True),
        Binding("c", "clear_log", "Clear Log"),
    ]

    # Reactive state
    server_url: reactive[str] = reactive("")
    is_watching: reactive[bool] = reactive(False)
    rebuild_count: reactive[int] = reactive(0)
    last_rebuild_ms: reactive[float] = reactive(0)

    # Build history (for sparkline)
    MAX_HISTORY: ClassVar[int] = 20

    def __init__(
        self,
        site: Site | None = None,
        *,
        host: str = "localhost",
        port: int = 3000,
        watch: bool = True,
        open_browser: bool = False,
        **kwargs: Any,
    ):
        """
        Initialize serve dashboard.

        Args:
            site: Site instance to serve
            host: Server host
            port: Server port
            watch: Enable file watching
            open_browser: Open browser on start
            **kwargs: Additional server options
        """
        super().__init__()
        self.site = site
        self.host = host
        self.port = port
        self.watch = watch
        self.auto_open_browser = open_browser
        self.server_kwargs = kwargs

        # Build history for sparkline (bounded)
        self.build_history: list[float] = []

        # Change log entries
        self.changes: list[ChangeEntry] = []

        # Server thread
        self._server_thread = None
        self._stop_event = None

        # Update timer
        self._status_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        yield Header()

        with Vertical(id="main-content"):
            # Server status bar
            yield Static(
                f"{self.mascot}  Starting server...",
                id="server-status",
                classes="section-header",
            )

            # URL display
            yield Static("", id="server-url", classes="label-primary")

            # Build history sparkline
            with Vertical(classes="section", id="sparkline-section"):
                yield Static("Build History (ms):", classes="section-header")
                yield Sparkline([], id="build-sparkline")

            # Tabbed content
            with TabbedContent(id="serve-tabs"):
                with TabPane("Changes", id="changes-tab"):
                    yield Log(id="changes-log", auto_scroll=True)

                with TabPane("Stats", id="stats-tab"):
                    yield DataTable(id="stats-table")

                with TabPane("Errors", id="errors-tab"):
                    yield Log(id="errors-log", auto_scroll=True)

        yield Footer()

    def on_mount(self) -> None:
        """Set up widgets when dashboard mounts."""
        # Configure stats table
        stats_table = self.query_one("#stats-table", DataTable)
        stats_table.add_columns("Metric", "Value")
        stats_table.add_row("Status", "Starting...", key="status")
        stats_table.add_row("Rebuilds", "0", key="rebuilds")
        stats_table.add_row("Last Build", "-", key="last_build")
        stats_table.add_row("Watching", "-", key="watching")
        stats_table.add_row("Cache Hit", "-", key="cache_hit")

        # Initialize sparkline with empty data
        sparkline = self.query_one("#build-sparkline", Sparkline)
        sparkline.data = [0]

        # Start the server
        if self.site:
            self._start_server()

        # Start status update timer
        self._status_timer = self.set_interval(1.0, self._update_status)

    def _start_server(self) -> None:
        """Start the dev server in a background thread."""
        import threading

        from bengal.server.dev_server import DevServer

        self._stop_event = threading.Event()

        def run_server():
            """Run server in background thread."""
            try:
                # Create server
                server = DevServer(
                    self.site,
                    host=self.host,
                    port=self.port,
                    watch=self.watch,
                    auto_port=True,
                    open_browser=self.auto_open_browser,
                )

                # Get actual port (may have changed due to auto_port)
                actual_port = server.port
                url = f"http://{self.host}:{actual_port}"

                # Update UI
                self.call_from_thread(self._on_server_started, url)

                # Start server (blocks until stopped)
                server.start()
            except Exception as e:
                self.call_from_thread(self._on_server_error, str(e))

        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_thread.start()

    def _on_server_started(self, url: str) -> None:
        """Handle server started event."""
        self.server_url = url
        self.is_watching = self.watch

        # Update status
        status = self.query_one("#server-status", Static)
        status.update(f"{self.mascot}  Server running")

        # Update URL
        url_label = self.query_one("#server-url", Static)
        url_label.update(f"   → {url}")

        # Update stats
        self._update_stat("status", "Running")
        self._update_stat("watching", "Yes" if self.watch else "No")

        # Show notification
        notify_server_started(self, url)

        # Log
        changes_log = self.query_one("#changes-log", Log)
        changes_log.write_line(f"✓ Server started at {url}")
        if self.watch:
            changes_log.write_line("✓ Watching for file changes...")

    def _on_server_error(self, error: str) -> None:
        """Handle server error."""
        status = self.query_one("#server-status", Static)
        status.update(f"{self.error_mascot}  Server error: {error}")

        errors_log = self.query_one("#errors-log", Log)
        errors_log.write_line(f"✗ Server error: {error}")

        self._update_stat("status", "Error")

    def _update_status(self) -> None:
        """Periodic status update."""
        # Update rebuild count display
        self._update_stat("rebuilds", str(self.rebuild_count))

        # Update last build time
        if self.last_rebuild_ms > 0:
            self._update_stat("last_build", f"{int(self.last_rebuild_ms)}ms")

    def _update_stat(self, key: str, value: str) -> None:
        """Update a row in the stats table."""
        try:
            stats_table = self.query_one("#stats-table", DataTable)
            stats_table.update_cell(key, "Value", value)
        except Exception:
            pass

    def _add_build_to_history(self, duration_ms: float) -> None:
        """Add a build duration to history and update sparkline."""
        self.build_history.append(duration_ms)

        # Keep bounded
        if len(self.build_history) > self.MAX_HISTORY:
            self.build_history = self.build_history[-self.MAX_HISTORY :]

        # Update sparkline
        sparkline = self.query_one("#build-sparkline", Sparkline)
        sparkline.data = self.build_history

    # === Message Handlers ===

    def on_file_changed(self, message: FileChanged) -> None:
        """Handle file changed event."""
        entry = ChangeEntry(
            path=message.path,
            change_type=message.change_type,
        )
        self.changes.append(entry)

        # Update log
        changes_log = self.query_one("#changes-log", Log)
        icons = {"created": "+", "modified": "~", "deleted": "-"}
        icon = icons.get(message.change_type, "?")

        # Shorten path for display
        short_path = Path(message.path).name
        timestamp = entry.timestamp.strftime("%H:%M:%S")

        changes_log.write_line(f"[{timestamp}] {icon} {short_path}")

        # Show notification (only for first few)
        if len(self.changes) < 5:
            notify_file_changed(self, message.path, message.change_type)

    def on_rebuild_triggered(self, message: RebuildTriggered) -> None:
        """Handle rebuild triggered event."""
        self.rebuild_count += 1

        changes_log = self.query_one("#changes-log", Log)
        changes_log.write_line(f"→ Rebuilding ({len(message.changed_files)} files changed)...")

        notify_rebuild_triggered(self, len(message.changed_files))

    def on_build_complete(self, message: BuildComplete) -> None:
        """Handle build complete event."""
        self.last_rebuild_ms = message.duration_ms

        # Add to history
        self._add_build_to_history(message.duration_ms)

        # Update stats
        pages = (message.stats or {}).get("pages_rendered", 0)
        self._update_stat("last_build", f"{int(message.duration_ms)}ms")

        # Log
        changes_log = self.query_one("#changes-log", Log)
        if message.success:
            changes_log.write_line(f"✓ Rebuilt in {int(message.duration_ms)}ms ({pages} pages)")
        else:
            changes_log.write_line(f"✗ Build failed: {message.error}")

            # Also log to errors tab
            errors_log = self.query_one("#errors-log", Log)
            errors_log.write_line(f"✗ {message.error}")

        # Notification
        notify_build_complete(
            self,
            duration_ms=message.duration_ms,
            pages=pages,
            success=message.success,
        )

    def on_watcher_status(self, message: WatcherStatus) -> None:
        """Handle watcher status update."""
        self.is_watching = message.watching
        self._update_stat("watching", f"Yes ({message.watched_files} files)")

    # === Actions ===

    def action_open_browser(self) -> None:
        """Open the site in the default browser."""
        if self.server_url:
            import webbrowser

            webbrowser.open(self.server_url)
            self.notify(f"Opening {self.server_url}", title="Browser")
        else:
            self.notify("Server not started yet", severity="warning")

    def action_force_rebuild(self) -> None:
        """Force a full rebuild."""
        if self.site:
            self.notify("Triggering rebuild...", title="Rebuild")

            # Log
            changes_log = self.query_one("#changes-log", Log)
            changes_log.write_line("→ Manual rebuild triggered...")

            # The actual rebuild would be triggered through the server
            # For now, post a message
            self.post_message(RebuildTriggered(changed_files=["(manual trigger)"]))
        else:
            self.notify("No site loaded", severity="warning")

    def action_clear_log(self) -> None:
        """Clear the changes log."""
        changes_log = self.query_one("#changes-log", Log)
        changes_log.clear()
        self.changes.clear()

    def action_quit(self) -> None:
        """Quit the dashboard and stop the server."""
        if self._stop_event:
            self._stop_event.set()

        if self._status_timer:
            self._status_timer.stop()

        self.exit()


def run_serve_dashboard(
    site: Site,
    *,
    host: str = "localhost",
    port: int = 3000,
    watch: bool = True,
    open_browser: bool = False,
    **kwargs: Any,
) -> None:
    """
    Run the serve dashboard for a site.

    This is the entry point called by `bengal serve --dashboard`.

    Args:
        site: Site instance to serve
        host: Server host
        port: Server port
        watch: Enable file watching
        open_browser: Open browser on start
        **kwargs: Additional server options
    """
    app = BengalServeDashboard(
        site=site,
        host=host,
        port=port,
        watch=watch,
        open_browser=open_browser,
        **kwargs,
    )
    app.run()
