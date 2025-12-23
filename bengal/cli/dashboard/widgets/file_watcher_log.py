"""
File Watcher Log Widget.

Real-time file change stream display for dev server.
Shows file modifications with timestamps and event types.

Usage:
    from bengal.cli.dashboard.widgets import FileWatcherLog

    log = FileWatcherLog()

    # Connect to watcher callback
    def on_file_change(path: Path, event_type: str) -> None:
        log.add_change(path, event_type)

RFC: rfc-dashboard-api-integration
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Log, Static

# Event type icons
EVENT_ICONS: dict[str, str] = {
    "created": "➕",
    "modified": "✏️",
    "deleted": "🗑️",
    "renamed": "📝",
}


class FileWatcherLog(Vertical):
    """
    Real-time file change log for dev server dashboard.

    Features:
    - Timestamped change entries
    - Event type icons (created, modified, deleted)
    - Auto-scroll with max history
    - Clear functionality

    Example:
        log = FileWatcherLog(id="file-changes")

        # Connect to watcher
        watcher = WatcherRunner(
            on_file_change=lambda p, e: log.add_change(p, e),
            ...
        )
    """

    DEFAULT_CSS = """
    FileWatcherLog {
        height: 100%;
        border: solid $primary;
    }
    FileWatcherLog .log-header {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    FileWatcherLog Log {
        height: 1fr;
    }
    FileWatcherLog .log-entry-created {
        color: $success;
    }
    FileWatcherLog .log-entry-modified {
        color: $warning;
    }
    FileWatcherLog .log-entry-deleted {
        color: $error;
    }
    """

    change_count: reactive[int] = reactive(0)
    max_entries: int = 100

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
        max_entries: int = 100,
    ) -> None:
        """Initialize file watcher log."""
        super().__init__(id=id, classes=classes)
        self.max_entries = max_entries
        self._log: Log | None = None

    def compose(self) -> ComposeResult:
        """Compose the file watcher log."""
        yield Static(
            self._format_header(),
            classes="log-header",
            id="watcher-header",
        )
        self._log = Log(id="change-log", auto_scroll=True)
        yield self._log

    def add_change(self, path: Path | str, event_type: str) -> None:
        """
        Add a file change entry to the log.

        Args:
            path: Path to the changed file
            event_type: Type of change (created, modified, deleted)
        """
        if self._log is None:
            return

        # Format entry
        timestamp = datetime.now().strftime("%H:%M:%S")
        icon = EVENT_ICONS.get(event_type.lower(), "📄")

        # Shorten path for display
        path_str = str(path)
        if len(path_str) > 50:
            path_str = "..." + path_str[-47:]

        entry = f"[{timestamp}] {icon} {event_type}: {path_str}"
        self._log.write_line(entry)

        # Update count
        self.change_count += 1
        self._update_header()

        # Trim old entries if needed
        # Note: Textual Log doesn't have a built-in trim, so we track externally
        # and clear/rebuild if needed

    def _format_header(self) -> str:
        """Format header with change count."""
        return f"👁️ File Watcher ({self.change_count} changes)"

    def _update_header(self) -> None:
        """Update the header widget."""
        try:
            header = self.query_one("#watcher-header", Static)
            header.update(self._format_header())
        except Exception:
            pass

    def clear(self) -> None:
        """Clear the log and reset count."""
        if self._log is not None:
            self._log.clear()
        self.change_count = 0
        self._update_header()

    def write(self, message: str) -> None:
        """Write a raw message to the log (for general status updates)."""
        if self._log is not None:
            self._log.write_line(message)
