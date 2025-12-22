"""
Development server specific CLI output methods.

This module provides a mixin class with output methods specifically designed
for the Bengal development server. These methods handle request logging,
file change notifications, and server status display.

Features:
    - HTTP request logging with colorized status codes and methods
    - File change notifications with timestamps
    - Server URL display
    - Table-style request log headers

Architecture:
    DevServerOutputMixin is mixed into CLIOutput to provide dev server
    functionality without bloating the core output class. It expects
    certain attributes (use_rich, console) to be defined by CLIOutput.

Related:
    - bengal/output/core.py: Main CLIOutput class that uses this mixin
    - bengal/output/colors.py: Color utilities for HTTP status/method
    - bengal/cli/commands/serve.py: Dev server command that uses these methods
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from bengal.output.colors import (
    get_method_color_code,
    get_method_style,
    get_status_color_code,
    get_status_style,
)
from bengal.output.enums import MessageLevel

if TYPE_CHECKING:
    from rich.console import Console


class DevServerOutputMixin:
    """
    Mixin providing development server specific output methods.

    This mixin adds HTTP request logging, file change notifications,
    and server status display methods to CLIOutput. It is designed
    to be mixed into CLIOutput and relies on attributes defined there.

    Required Attributes (from CLIOutput):
        use_rich: Whether to use Rich console output
        console: Rich Console instance for styled output
        should_show: Method to check message visibility based on level
    """

    # These attributes are defined in CLIOutput
    use_rich: bool
    console: Console

    def should_show(self, level: MessageLevel) -> bool:
        """Check if message should be shown based on level and settings."""
        ...

    def separator(self, width: int = 78, style: str = "dim") -> None:
        """
        Print a horizontal separator line.

        Outputs a line of box-drawing characters (─) to visually separate
        content sections in the terminal.

        Args:
            width: Character width of the separator line (default: 78)
            style: Rich style name to apply (default: "dim" for subtle appearance)

        Example:
            >>> cli.separator()
            ────────────────────────────────────────
        """
        if not self.should_show(MessageLevel.INFO):
            return

        line = "─" * width

        if self.use_rich:
            self.console.print(f"  [{style}]{line}[/{style}]")
        else:
            # ANSI dim for fallback
            click.echo(f"  \033[90m{line}\033[0m")

    def file_change_notice(self, file_name: str, timestamp: str | None = None) -> None:
        """
        Print a file change notification for dev server.

        Args:
            file_name: Name of the changed file (or summary like "file.md (+3 more)")
            timestamp: Optional timestamp string (defaults to current time HH:MM:SS)

        Example:
            ────────────────────────────────────────
            12:34:56 │ 📝 File changed: index.md
            ────────────────────────────────────────
        """
        if not self.should_show(MessageLevel.INFO):
            return

        if timestamp is None:
            from datetime import datetime

            timestamp = datetime.now().strftime("%H:%M:%S")

        self.separator()
        if self.use_rich:
            self.console.print(f"  {timestamp} │ [warning]📝 File changed:[/warning] {file_name}")
        else:
            click.echo(f"  {timestamp} │ \033[33m📝 File changed:\033[0m {file_name}")
        self.separator()
        click.echo()  # Blank line after

    def server_url_inline(self, host: str, port: int) -> None:
        """
        Print server URL in inline format (for after rebuild).

        Args:
            host: Server host
            port: Server port

        Example:
            ➜  Local: http://localhost:5173/
        """
        if not self.should_show(MessageLevel.INFO):
            return

        url = f"http://{host}:{port}/"

        if self.use_rich:
            self.console.print(f"\n  [cyan]➜[/cyan]  Local: [bold]{url}[/bold]\n")
        else:
            click.echo(f"\n  \033[36m➜\033[0m  Local: \033[1m{url}\033[0m\n")

    def request_log_header(self) -> None:
        """
        Print table header for HTTP request logging.

        Example:
            TIME     │ METHOD │ STA │ PATH
            ─────────┼────────┼─────┼──────────────────────
        """
        if not self.should_show(MessageLevel.INFO):
            return

        if self.use_rich:
            self.console.print(f"  [dim]{'TIME':8} │ {'METHOD':6} │ {'STATUS':3} │ PATH[/dim]")
            self.console.print(f"  [dim]{'─' * 8}─┼─{'─' * 6}─┼─{'─' * 3}─┼─{'─' * 60}[/dim]")
        else:
            click.echo(f"  \033[90m{'TIME':8} │ {'METHOD':6} │ {'STATUS':3} │ PATH\033[0m")
            click.echo(f"  \033[90m{'─' * 8}─┼─{'─' * 6}─┼─{'─' * 3}─┼─{'─' * 60}\033[0m")

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

        Outputs a table-formatted log entry with colorized status code
        and method. Non-asset requests show status indicators (success/error
        icons), while asset requests are displayed without icons to reduce
        visual noise.

        Args:
            timestamp: Request timestamp in HH:MM:SS format
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            status_code: HTTP status code as string (e.g., "200", "404")
            path: Request path (truncated if > 60 characters)
            is_asset: If True, suppress status indicator icons

        Example:
            >>> cli.http_request("12:34:56", "GET", "200", "/index.html")
            12:34:56 │ GET    │ 200 │ - /index.html

            >>> cli.http_request("12:34:57", "GET", "404", "/missing.html")
            12:34:57 │ GET    │ 404 │ x /missing.html
        """
        if not self.should_show(MessageLevel.INFO):
            return

        # Truncate long paths
        display_path = path
        if len(path) > 60:
            display_path = path[:57] + "..."

        # Add indicator icon
        from bengal.output.icons import get_icon_set
        from bengal.utils.rich_console import should_use_emoji

        icons = get_icon_set(should_use_emoji())
        indicator = ""
        if not is_asset:
            if status_code.startswith("2"):
                indicator = f"{icons.info} "  # Page load
            elif status_code.startswith("4"):
                indicator = f"{icons.error} "  # Error

        # Color codes for status
        status_color_code = get_status_color_code(status_code)
        method_color_code = get_method_color_code(method)

        if self.use_rich:
            # Use Rich markup for colors
            status_style = get_status_style(status_code)
            method_style = get_method_style(method)
            self.console.print(
                f"  {timestamp} │ [{method_style}]{method:6}[/{method_style}] │ "
                f"[{status_style}]{status_code:3}[/{status_style}] │ {indicator}{display_path}"
            )
        else:
            # Use ANSI codes for fallback
            print(
                f"  {timestamp} │ {method_color_code}{method:6}\033[0m │ "
                f"{status_color_code}{status_code:3}\033[0m │ {indicator}{display_path}"
            )
