"""
Centralized CLI output system for Bengal.

Provides a unified interface for all CLI messaging with:
- Profile-aware formatting (Writer, Theme-Dev, Developer)
- Consistent indentation and spacing
- Automatic TTY detection
- Rich/fallback rendering
"""

from enum import Enum
from typing import Any

import click
from rich.panel import Panel
from rich.table import Table


class MessageLevel(Enum):
    """Message importance levels."""

    DEBUG = 0  # Only in --verbose
    INFO = 1  # Normal operations
    SUCCESS = 2  # Successful operations
    WARNING = 3  # Non-critical issues
    ERROR = 4  # Errors
    CRITICAL = 5  # Fatal errors


class OutputStyle(Enum):
    """Visual styles for messages."""

    PLAIN = "plain"
    HEADER = "header"
    PHASE = "phase"
    DETAIL = "detail"
    METRIC = "metric"
    PATH = "path"
    SUMMARY = "summary"


class CLIOutput:
    """
    Centralized CLI output manager.

    Handles all terminal output with profile-aware formatting,
    consistent spacing, and automatic TTY detection.

    Example:
        cli = CLIOutput(profile=BuildProfile.WRITER)

        cli.header("Building your site...")
        cli.phase_start("Discovery")
        cli.detail("Found 245 pages", indent=1)
        cli.phase_complete("Discovery", duration_ms=61)
        cli.success("Built 245 pages in 0.8s")
    """

    def __init__(
        self,
        profile: Any | None = None,
        quiet: bool = False,
        verbose: bool = False,
        use_rich: bool | None = None,
    ):
        """
        Initialize CLI output manager.

        Args:
            profile: Build profile (Writer, Theme-Dev, Developer)
            quiet: Suppress non-critical output
            verbose: Show detailed output
            use_rich: Force rich/plain output (None = auto-detect)
        """
        self.profile = profile
        self.quiet = quiet
        self.verbose = verbose

        # Auto-detect rich support
        if use_rich is None:
            from bengal.utils.rich_console import should_use_rich

            use_rich = should_use_rich()

        self.use_rich = use_rich

        # Use themed console for semantic styles (header, success, etc.)
        if use_rich:
            from bengal.utils.rich_console import get_console

            self.console = get_console()
        else:
            self.console = None

        # Dev mode detection (set by dev server)
        try:
            import os as _os

            self.dev_server = (_os.environ.get("BENGAL_DEV_SERVER") or "") == "1"
            # Phase deduplication window (ms) to suppress duplicate phase lines
            self._phase_dedup_ms = int(_os.environ.get("BENGAL_CLI_PHASE_DEDUP_MS", "1500"))
        except Exception:
            self.dev_server = False
            self._phase_dedup_ms = 1500

        # Track last phase line for deduplication
        self._last_phase_key: str | None = None
        self._last_phase_time_ms: int = 0

        # Get profile config
        self.profile_config = profile.get_config() if profile else {}

        # Spacing and indentation rules
        self.indent_char = " "
        self.indent_size = 2

    def should_show(self, level: MessageLevel) -> bool:
        """Determine if message should be shown based on level and settings."""
        if self.quiet and level.value < MessageLevel.WARNING.value:
            return False
        return not (not self.verbose and level == MessageLevel.DEBUG)

    # === High-level message types ===

    def header(
        self,
        text: str,
        mascot: bool = True,
        leading_blank: bool = True,
        trailing_blank: bool = True,
    ) -> None:
        """
        Print a header message.
        Example: "ᓚᘏᗢ  Building your site..."
        """
        if not self.should_show(MessageLevel.INFO):
            return

        if self.use_rich:
            mascot_str = "[bengal]ᓚᘏᗢ[/bengal]  " if mascot else ""
            if leading_blank:
                self.console.print()
            self.console.print(
                Panel(
                    f"{mascot_str}{text}",
                    expand=False,
                    border_style="header",
                    padding=(0, 5),
                )
            )
            if trailing_blank:
                self.console.print()
        else:
            mascot_str = "ᓚᘏᗢ  " if mascot else ""
            prefix = "\n" if leading_blank else ""
            suffix = "\n" if trailing_blank else ""
            click.echo(f"{prefix}    {mascot_str}{text}{suffix}", color=True)

    def phase(
        self,
        name: str,
        status: str = "Done",
        duration_ms: float | None = None,
        details: str | None = None,
        icon: str = "✓",
    ) -> None:
        """
        Print a phase status line.

        Examples:
            ✓ Discovery     Done
            ✓ Rendering     501ms (245 pages)
            ✓ Assets        Done
        """
        if not self.should_show(MessageLevel.SUCCESS):
            return

        # Format based on profile
        parts = [f"[success]{icon}[/success]", f"[phase]{name}[/phase]"]

        # Add timing if available and profile shows it
        if duration_ms is not None and self._show_timing():
            parts.append(f"[dim]{int(duration_ms)}ms[/dim]")

        # Add details if provided and profile shows them
        if details and self._show_details():
            parts.append(f"([dim]{details}[/dim])")

        # Render (compute without side-effects for dedup key)
        line = self._format_phase_line(parts)

        # Deduplicate identical phase lines within a short window to avoid spam in dev
        if self._should_dedup_phase(line):
            return
        self._mark_phase_emit(line)

        if self.use_rich:
            self.console.print(line)
        else:
            click.echo(click.style(line, fg="green"))

    def detail(self, text: str, indent: int = 1, icon: str | None = None) -> None:
        """
        Print a detail/sub-item.

        Example:
            ├─ RSS feed ✓
            └─ Sitemap ✓
        """
        if not self.should_show(MessageLevel.INFO):
            return

        indent_str = self.indent_char * (self.indent_size * indent)
        icon_str = f"{icon} " if icon else ""
        line = f"{indent_str}{icon_str}{text}"

        if self.use_rich:
            self.console.print(line)
        else:
            click.echo(line)

    def success(self, text: str, icon: str = "✨") -> None:
        """
        Print a success message.

        Example: "✨ Built 245 pages in 0.8s"
        """
        if not self.should_show(MessageLevel.SUCCESS):
            return

        if self.use_rich:
            self.console.print()
            self.console.print(f"{icon} [success]{text}[/success]")
            self.console.print()
        else:
            click.echo(f"\n{icon} {text}\n", color=True)

    def info(self, text: str, icon: str | None = None) -> None:
        """Print an info message."""
        if not self.should_show(MessageLevel.INFO):
            return

        icon_str = f"{icon} " if icon else ""

        if self.use_rich:
            self.console.print(f"{icon_str}{text}")
        else:
            click.echo(f"{icon_str}{text}")

    def warning(self, text: str, icon: str = "⚠️") -> None:
        """Print a warning message."""
        if not self.should_show(MessageLevel.WARNING):
            return

        if self.use_rich:
            self.console.print(f"{icon}  [warning]{text}[/warning]")
        else:
            click.echo(click.style(f"{icon}  {text}", fg="yellow"))

    def error(self, text: str, icon: str = "❌") -> None:
        """Print an error message."""
        if not self.should_show(MessageLevel.ERROR):
            return

        if self.use_rich:
            self.console.print(f"{icon} [error]{text}[/error]")
        else:
            click.echo(click.style(f"{icon} {text}", fg="red", bold=True))

    def tip(self, text: str, icon: str = "💡") -> None:
        """Print a subtle tip/instruction line."""
        if not self.should_show(MessageLevel.INFO):
            return

        if self.use_rich:
            self.console.print(f"{icon} [tip]{text}[/tip]")
        else:
            click.echo(f"{icon} {text}")

    def error_header(self, text: str, mouse: bool = True) -> None:
        """
        Print an error header with mouse emoji.

        Example: "ᘛ⁐̤ᕐᐷ  3 template errors found"

        The mouse represents errors that Bengal (the cat) needs to catch!
        """
        if not self.should_show(MessageLevel.ERROR):
            return

        if self.use_rich:
            mouse_str = "[mouse]ᘛ⁐̤ᕐᐷ[/mouse]  " if mouse else ""
            self.console.print()
            self.console.print(
                Panel(
                    f"{mouse_str}{text}",
                    expand=False,
                    border_style="error",
                    padding=(0, 5),
                )
            )
            self.console.print()
        else:
            mouse_str = "ᘛ⁐̤ᕐᐷ  " if mouse else ""
            click.echo(click.style(f"\n    {mouse_str}{text}\n", fg="red", bold=True))

    def path(self, path: str, icon: str = "📂", label: str = "Output") -> None:
        """
        Print a path.

        Example:
            📂 Output:
               ↪ /Users/.../public
        """
        if not self.should_show(MessageLevel.INFO):
            return

        # Shorten path based on profile
        display_path = self._format_path(path)

        if self.use_rich:
            self.console.print(f"{icon} {label}:")
            self.console.print(f"   ↪ [path]{display_path}[/path]")
        else:
            click.echo(f"{icon} {label}:")
            click.echo(click.style(f"   ↪ {display_path}", fg="cyan"))

    def metric(self, label: str, value: Any, unit: str | None = None, indent: int = 0) -> None:
        """
        Print a metric.

        Example:
            ⏱️  Performance:
               ├─ Total: 834ms
               └─ Throughput: 293.7 pages/sec
        """
        if not self.should_show(MessageLevel.INFO):
            return

        indent_str = self.indent_char * (self.indent_size * indent)
        unit_str = f" {unit}" if unit else ""

        if self.use_rich:
            line = (
                f"{indent_str}[metric_label]{label}[/metric_label]: "
                f"[metric_value]{value}{unit_str}[/metric_value]"
            )
            self.console.print(line)
        else:
            line = f"{indent_str}{label}: {value}{unit_str}"
            click.echo(line)

    def table(self, data: list[dict[str, str]], headers: list[str]) -> None:
        """Print a table (rich only, falls back to simple list)."""
        if not self.should_show(MessageLevel.INFO):
            return

        if self.use_rich:
            table = Table(show_header=True, header_style="bold")
            for header in headers:
                table.add_column(header)

            for row in data:
                table.add_row(*[row.get(h, "") for h in headers])

            self.console.print(table)
        else:
            # Fallback to simple list
            for row in data:
                values = [f"{k}: {v}" for k, v in row.items()]
                click.echo(" | ".join(values))

    def prompt(
        self, text: str, default: Any = None, type: Any = str, show_default: bool = True
    ) -> Any:
        """
        Prompt user for input with themed styling.

        Args:
            text: The prompt text to display
            default: Default value if user presses enter
            type: Type to convert input to (str, int, float, etc.)
            show_default: Whether to show the default value

        Returns:
            User's input converted to the specified type

        Example:
            name = cli.prompt("Enter site name")
            count = cli.prompt("How many pages?", default=3, type=int)
        """
        if self.use_rich:
            from rich.prompt import Prompt

            # Use Rich's Prompt with our themed console
            return Prompt.ask(
                f"[prompt]{text}[/prompt]",
                default=default,
                console=self.console,
                show_default=show_default,
            )
        else:
            # Fallback to click.prompt
            return click.prompt(text, default=default, type=type, show_default=show_default)

    def confirm(self, text: str, default: bool = False) -> bool:
        """
        Prompt user for yes/no confirmation with themed styling.

        Args:
            text: The prompt text to display
            default: Default value if user presses enter

        Returns:
            True if user confirms, False otherwise

        Example:
            if cli.confirm("Delete all files?"):
                do_deletion()
        """
        if self.use_rich:
            from rich.prompt import Confirm

            return Confirm.ask(f"[prompt]{text}[/prompt]", default=default, console=self.console)
        else:
            # Fallback to click.confirm
            return click.confirm(text, default=default)

    def blank(self, count: int = 1) -> None:
        """Print blank lines."""
        for _ in range(count):
            if self.use_rich:
                self.console.print()
            else:
                click.echo()

    # === Dev server specific methods ===

    def separator(self, width: int = 78, style: str = "dim") -> None:
        """
        Print a horizontal separator line.

        Args:
            width: Width of the separator line
            style: Style to apply (dim, info, header, etc.)

        Example:
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
            self.console.print(
                f"  {timestamp} │ [warning]📝 File changed:[/warning] {file_name}"
            )
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
            self.console.print(
                f"  [dim]{'─' * 8}─┼─{'─' * 6}─┼─{'─' * 3}─┼─{'─' * 60}[/dim]"
            )
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

        Args:
            timestamp: Request timestamp (HH:MM:SS format)
            method: HTTP method (GET, POST, etc.)
            status_code: HTTP status code as string
            path: Request path
            is_asset: Whether this is an asset request (affects icon display)

        Example:
            12:34:56 │ GET    │ 200 │ 📄 /index.html
            12:34:57 │ GET    │ 404 │ ❌ /missing.html
        """
        if not self.should_show(MessageLevel.INFO):
            return

        # Truncate long paths
        display_path = path
        if len(path) > 60:
            display_path = path[:57] + "..."

        # Add indicator emoji
        indicator = ""
        if not is_asset:
            if status_code.startswith("2"):
                indicator = "📄 "  # Page load
            elif status_code.startswith("4"):
                indicator = "❌ "  # Error

        # Color codes for status
        status_color_code = self._get_status_color_code(status_code)
        method_color_code = self._get_method_color_code(method)

        if self.use_rich:
            # Use Rich markup for colors
            status_style = self._get_status_style(status_code)
            method_style = self._get_method_style(method)
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

    def _get_status_color_code(self, status: str) -> str:
        """Get ANSI color code for status code."""
        try:
            code = int(status)
            if 200 <= code < 300:
                return "\033[32m"  # Green
            elif code == 304:
                return "\033[90m"  # Gray
            elif 300 <= code < 400:
                return "\033[36m"  # Cyan
            elif 400 <= code < 500:
                return "\033[33m"  # Yellow
            else:
                return "\033[31m"  # Red
        except (ValueError, TypeError):
            return ""

    def _get_method_color_code(self, method: str) -> str:
        """Get ANSI color code for HTTP method."""
        colors = {
            "GET": "\033[36m",  # Cyan
            "POST": "\033[33m",  # Yellow
            "PUT": "\033[35m",  # Magenta
            "DELETE": "\033[31m",  # Red
            "PATCH": "\033[35m",  # Magenta
        }
        return colors.get(method, "\033[37m")  # Default white

    def _get_status_style(self, status: str) -> str:
        """Get Rich style name for status code."""
        try:
            code = int(status)
            if 200 <= code < 300:
                return "green"
            elif code == 304:
                return "dim"
            elif 300 <= code < 400:
                return "cyan"
            elif 400 <= code < 500:
                return "yellow"
            else:
                return "red"
        except (ValueError, TypeError):
            return "default"

    def _get_method_style(self, method: str) -> str:
        """Get Rich style name for HTTP method."""
        styles = {
            "GET": "cyan",
            "POST": "yellow",
            "PUT": "magenta",
            "DELETE": "red",
            "PATCH": "magenta",
        }
        return styles.get(method, "default")

    # === Internal helpers ===

    def _show_timing(self) -> bool:
        """Should we show timing info based on profile?"""
        if not self.profile:
            return False

        profile_name = (
            self.profile.__class__.__name__
            if hasattr(self.profile, "__class__")
            else str(self.profile)
        )

        # Writer: no timing, Theme-Dev: yes, Developer: yes
        return "WRITER" not in profile_name

    def _show_details(self) -> bool:
        """Should we show detailed info based on profile?"""
        if not self.profile:
            return True

        # All profiles can show details (but format may differ)
        return True

    def _format_phase_line(self, parts: list[str]) -> str:
        """
        Format a phase line with consistent spacing.

        Examples:
            ✓ Discovery     Done
            ✓ Rendering     501ms (245 pages)
        """
        if len(parts) < 2:
            return " ".join(parts)

        icon = parts[0]
        name = parts[1]
        rest = parts[2:] if len(parts) > 2 else []

        # Calculate padding for alignment
        # Phase names are typically 10-12 chars, pad to 12
        name_width = 12
        name_padded = name.ljust(name_width)

        if rest:
            return f"{icon} {name_padded} {' '.join(rest)}"
        else:
            # In dev server mode, omit the trailing "Done" to reduce noise
            if getattr(self, "dev_server", False):
                return f"{icon} {name_padded}".rstrip()
            return f"{icon} {name_padded} Done"

    def _now_ms(self) -> int:
        try:
            import time as _time

            return int(_time.monotonic() * 1000)
        except Exception:
            return 0

    def _should_dedup_phase(self, line: str) -> bool:
        # Only dedup in dev mode
        if not getattr(self, "dev_server", False):
            return False
        key = line
        now = self._now_ms()
        return (
            self._last_phase_key == key and (now - self._last_phase_time_ms) < self._phase_dedup_ms
        )

    def _mark_phase_emit(self, line: str) -> None:
        if not getattr(self, "dev_server", False):
            return
        self._last_phase_key = line
        self._last_phase_time_ms = self._now_ms()

    def _format_path(self, path: str) -> str:
        """Format path based on profile (shorten for Writer, full for Developer)."""
        if not self.profile:
            return path

        profile_name = (
            self.profile.__class__.__name__
            if hasattr(self.profile, "__class__")
            else str(self.profile)
        )

        # Writer: just show "public/" or last segment
        if "WRITER" in profile_name:
            from pathlib import Path

            return Path(path).name or path

        # Theme-Dev: abbreviate middle
        if "THEME" in profile_name and len(path) > 60:
            parts = path.split("/")
            if len(parts) > 3:
                return f"{parts[0]}/.../{'/'.join(parts[-2:])}"

        # Developer: full path
        return path


# === Global instance ===

_cli_output: CLIOutput | None = None


def get_cli_output() -> CLIOutput:
    """Get the global CLI output instance."""
    global _cli_output
    if _cli_output is None:
        _cli_output = CLIOutput()
    return _cli_output


def init_cli_output(
    profile: Any | None = None, quiet: bool = False, verbose: bool = False
) -> CLIOutput:
    """Initialize the global CLI output instance with settings."""
    global _cli_output
    _cli_output = CLIOutput(profile=profile, quiet=quiet, verbose=verbose)
    return _cli_output
