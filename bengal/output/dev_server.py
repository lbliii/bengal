"""
Development server specific CLI output methods.

This module provides a mixin class with output methods specifically designed
for the Bengal development server. These methods handle request logging,
file change notifications, and server status display — all rendered through
kida templates.

Related:
- bengal/output/core.py: Main CLIOutput class that uses this mixin
- bengal/output/templates/server_dashboard.kida: kida template for all modes
- bengal/cli/commands/serve.py: Dev server command that uses these methods

"""

from __future__ import annotations

from typing import Any

from bengal.output.enums import MessageLevel


class DevServerOutputMixin:
    """
    Mixin providing development server specific output methods.

    All output is rendered through the server_dashboard.kida template.

    Required Attributes (from CLIOutput):
        should_show: Method to check message visibility based on level
        render_write: Method to render kida templates to stdout

    """

    def should_show(self, level: MessageLevel) -> bool:
        """Check if message should be shown based on level and settings."""
        raise NotImplementedError("should_show must be provided by CLIOutput")

    def render_write(self, template_name: str, **context: Any) -> None:
        """Render a kida template and write to stdout."""
        raise NotImplementedError("render_write must be provided by CLIOutput")

    def separator(self, width: int = 78, style: str = "dim") -> None:
        """Print a horizontal separator line."""
        if not self.should_show(MessageLevel.INFO):
            return
        self.render_write("server_dashboard.kida", mode="separator")

    def file_change_notice(self, file_name: str, timestamp: str | None = None) -> None:
        """
        Print a file change notification for dev server.

        Args:
            file_name: Name of the changed file (or summary like "file.md (+3 more)")
            timestamp: Optional timestamp string (defaults to current time HH:MM:SS)

        """
        if not self.should_show(MessageLevel.INFO):
            return

        if timestamp is None:
            from datetime import datetime

            timestamp = datetime.now().strftime("%H:%M:%S")

        self.render_write(
            "server_dashboard.kida",
            mode="file_change",
            file_name=file_name,
            timestamp=timestamp,
        )

    def server_url_inline(self, host: str, port: int) -> None:
        """
        Print server URL in inline format (for after rebuild).

        Args:
            host: Server host
            port: Server port

        """
        if not self.should_show(MessageLevel.INFO):
            return

        self.render_write("server_dashboard.kida", mode="url", host=host, port=port)

    def request_log_header(self) -> None:
        """Print table header for HTTP request logging."""
        if not self.should_show(MessageLevel.INFO):
            return
        self.render_write("server_dashboard.kida", mode="header")

    def http_request(
        self,
        timestamp: str,
        method: str,
        status_code: str,
        path: str,
        is_asset: bool = False,
    ) -> None:
        """
        Print a formatted HTTP request log line.

        Args:
            timestamp: Request timestamp in HH:MM:SS format
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            status_code: HTTP status code as string (e.g., "200", "404")
            path: Request path (truncated if > 60 characters)
            is_asset: If True, suppress status indicator icons

        """
        if not self.should_show(MessageLevel.INFO):
            return

        self.render_write(
            "server_dashboard.kida",
            mode="request",
            timestamp=timestamp,
            method=method,
            status=status_code,
            path=path,
            is_asset=is_asset,
        )
