"""
Request Log Widget.

HTTP request logging display for dev server dashboard.
Shows method, path, status, and duration for each request.

Usage:
from bengal.cli.dashboard.widgets import RequestLog

    log = RequestLog()

# Connect to request handler callback
BengalRequestHandler.set_on_request(
    lambda method, path, status, duration: log.add_request(method, path, status, duration)
)

RFC: rfc-dashboard-api-integration

"""

from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import DataTable, Static

# Status code color categories
STATUS_CATEGORIES: dict[int, str] = {
    200: "success",
    201: "success",
    204: "success",
    301: "info",
    302: "info",
    304: "info",
    400: "warning",
    401: "warning",
    403: "warning",
    404: "warning",
    500: "error",
    502: "error",
    503: "error",
}


def get_status_icon(status_code: int) -> str:
    """Get icon for HTTP status code."""
    if 200 <= status_code < 300:
        return "✓"
    elif 300 <= status_code < 400:
        return "→"
    elif 400 <= status_code < 500:
        return "⚠"
    else:
        return "✗"


class RequestLog(Vertical):
    """
    HTTP request log for dev server dashboard.

    Features:
    - Request table with method, path, status, duration
    - Status-based coloring (2xx green, 4xx yellow, 5xx red)
    - Request count and average latency tracking
    - Max entries with auto-trim

    Example:
        log = RequestLog(id="request-log")

        # Connect to request handler
        BengalRequestHandler.set_on_request(log.add_request)

    """

    DEFAULT_CSS = """
    RequestLog {
        height: 100%;
        border: solid $primary;
    }
    RequestLog .log-header {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    RequestLog DataTable {
        height: 1fr;
    }
    RequestLog .status-success {
        color: $success;
    }
    RequestLog .status-info {
        color: $text;
    }
    RequestLog .status-warning {
        color: $warning;
    }
    RequestLog .status-error {
        color: $error;
    }
    """

    request_count: reactive[int] = reactive(0)
    total_duration_ms: reactive[float] = reactive(0.0)
    max_entries: int = 50

    def __init__(
        self,
        *,
        id: str | None = None,
        classes: str | None = None,
        max_entries: int = 50,
    ) -> None:
        """Initialize request log."""
        super().__init__(id=id, classes=classes)
        self.max_entries = max_entries
        self._table: DataTable | None = None
        self._row_keys: list = []  # Track row keys for trimming

    def compose(self) -> ComposeResult:
        """Compose the request log."""
        yield Static(
            self._format_header(),
            classes="log-header",
            id="request-header",
        )
        self._table = DataTable(id="request-table")
        self._table.add_columns("Time", "Method", "Path", "Status", "Duration")
        yield self._table

    def add_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        """
        Add a request entry to the log.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
        """
        if self._table is None:
            return

        # Format entry
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_icon = get_status_icon(status_code)
        status_str = f"{status_icon} {status_code}"

        # Format duration
        if duration_ms < 1:
            duration_str = "<1ms"
        elif duration_ms < 1000:
            duration_str = f"{duration_ms:.0f}ms"
        else:
            duration_str = f"{duration_ms / 1000:.1f}s"

        # Shorten path for display
        display_path = path
        if len(display_path) > 40:
            display_path = "..." + display_path[-37:]

        # Add row
        row_key = self._table.add_row(
            timestamp,
            method,
            display_path,
            status_str,
            duration_str,
        )
        self._row_keys.append(row_key)

        # Update stats
        self.request_count += 1
        self.total_duration_ms += duration_ms
        self._update_header()

        # Trim old entries
        while len(self._row_keys) > self.max_entries:
            old_key = self._row_keys.pop(0)
            self._table.remove_row(old_key)

    def _format_header(self) -> str:
        """Format header with stats."""
        if self.request_count == 0:
            return "📡 Requests (0)"

        avg_ms = self.total_duration_ms / self.request_count
        if avg_ms < 1:
            avg_str = "<1ms"
        elif avg_ms < 1000:
            avg_str = f"{avg_ms:.0f}ms"
        else:
            avg_str = f"{avg_ms / 1000:.1f}s"

        return f"📡 Requests ({self.request_count}, avg {avg_str})"

    def _update_header(self) -> None:
        """Update the header widget."""
        try:
            header = self.query_one("#request-header", Static)
            header.update(self._format_header())
        except Exception:
            pass  # Widget may not be mounted yet during compose

    def clear(self) -> None:
        """Clear the log and reset stats."""
        if self._table is not None:
            self._table.clear()
        self._row_keys.clear()
        self.request_count = 0
        self.total_duration_ms = 0.0
        self._update_header()
