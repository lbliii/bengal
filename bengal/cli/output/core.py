"""
Core CLI output manager.

Provides the main CLIOutput class for all terminal output with profile-aware
formatting, consistent spacing, and automatic TTY detection.

CLIOutput is the central hub for all terminal output in Bengal CLI:
- Profile-aware formatting (Writer sees less detail, Developer sees timing)
- Automatic Rich/plain text detection based on TTY
- Consistent visual hierarchy (headers, phases, details, tips)
- Dev server deduplication to prevent log spam

Classes:
    CLIOutput: Main output manager class

See Also:
    bengal.cli.output.globals: Global singleton management
    bengal.output.dev_server: Dev server output mixin
"""

from __future__ import annotations

from typing import Any

import click
from rich.panel import Panel
from rich.table import Table

from bengal.output.dev_server import DevServerOutputMixin
from bengal.output.enums import MessageLevel
from bengal.output.icons import get_icon_set
from bengal.utils.logger import get_logger
from bengal.utils.rich_console import should_use_emoji

logger = get_logger(__name__)


class CLIOutput(DevServerOutputMixin):
    """
    Centralized CLI output manager.

    Handles all terminal output with profile-aware formatting,
    consistent spacing, and automatic TTY detection. This is the
    primary interface for all user-facing CLI messages.

    Features:
        - Profile-aware: Writer sees minimal info, Developer sees timing
        - TTY detection: Rich output for terminals, plain text for pipes
        - Consistent styling: Visual hierarchy with headers, phases, tips
        - Dev server aware: Deduplicates rapid phase updates

    Message Types:
        - header(): Major section start with mascot
        - subheader(): Minor section divider
        - phase(): Build phase completion with optional timing
        - detail(): Indented sub-information
        - success/info/warning/error(): Standard message levels
        - tip(): Subtle suggestion or instruction

    Example:
        cli = CLIOutput(profile=BuildProfile.WRITER)

        cli.header("Building your site...")
        cli.phase("Discovery", duration_ms=61, details="245 pages")
        cli.detail("Processing markdown files", indent=1)
        cli.success("Built 245 pages in 0.8s")
        cli.tip("Run 'bengal serve' to preview")

    Attributes:
        profile: Active build profile (controls verbosity)
        quiet: Suppress non-critical output
        verbose: Show debug-level output
        use_rich: Use Rich library for styled output
        console: Rich console instance
        dev_server: True if running in dev server context
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

        # Always create console (even when not using Rich features)
        # This simplifies type checking - console is never None
        from bengal.utils.rich_console import get_console

        self.console = get_console()

        # Dev mode detection (set by dev server)
        try:
            import os as _os

            self.dev_server = (_os.environ.get("BENGAL_DEV_SERVER") or "") == "1"
            # Phase deduplication window (ms) to suppress duplicate phase lines
            self._phase_dedup_ms = int(_os.environ.get("BENGAL_CLI_PHASE_DEDUP_MS", "1500"))
        except Exception as e:
            logger.debug(
                "cli_output_env_init_failed",
                error=str(e),
                error_type=type(e).__name__,
                action="using_defaults",
            )
            self.dev_server = False
            self._phase_dedup_ms = 1500

        # Track last phase line for deduplication
        self._last_phase_key: str | None = None
        self._last_phase_time_ms: int = 0

        # Get profile config
        self.profile_config = profile.get_config() if profile else {}

        # Get icon set based on emoji preference
        self.icons = get_icon_set(should_use_emoji())

        # Spacing and indentation rules
        self.indent_char = " "
        self.indent_size = 2

    def should_show(self, level: MessageLevel) -> bool:
        """
        Determine if a message should be shown based on level and settings.

        Args:
            level: The message severity level

        Returns:
            True if the message should be displayed
        """
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

    def subheader(
        self,
        text: str,
        icon: str | None = None,
        leading_blank: bool = True,
        trailing_blank: bool = False,
        width: int = 60,
    ) -> None:
        """
        Print a subheader with subtle border (lighter than header).

        Args:
            text: The subheader text
            icon: Optional icon/emoji to display before text
            leading_blank: Add blank line before (default: True)
            trailing_blank: Add blank line after (default: False)
            width: Total width of the border line (default: 60)
        """
        if not self.should_show(MessageLevel.INFO):
            return

        if leading_blank:
            self.blank()

        # Format: === icon text ========================================
        icon_str = f"{icon} " if icon else ""
        label = f"{icon_str}{text}"

        # Calculate remaining border length
        label_len = len(label)
        prefix = "=== "
        remaining = width - len(prefix) - label_len - 1
        if remaining < 0:
            remaining = 0

        border = "=" * remaining

        if self.use_rich:
            line = f"{prefix}[header]{label}[/header] {border}"
            self.console.print(line)
        else:
            line = f"{prefix}{label} {border}"
            click.echo(click.style(line, bold=True))

        if trailing_blank:
            self.blank()

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

        parts = [f"[success]{icon}[/success]", f"[phase]{name}[/phase]"]

        if duration_ms is not None and self._show_timing():
            parts.append(f"[dim]{int(duration_ms)}ms[/dim]")

        if details and self._show_details():
            parts.append(f"([dim]{details}[/dim])")

        line = self._format_phase_line(parts)

        if self._should_dedup_phase(line):
            return
        self._mark_phase_emit(line)

        if self.use_rich:
            self.console.print(line)
        else:
            click.echo(click.style(line, fg="green"))

    def detail(self, text: str, indent: int = 1, icon: str | None = None) -> None:
        """Print a detail/sub-item."""
        if not self.should_show(MessageLevel.INFO):
            return

        indent_str = self.indent_char * (self.indent_size * indent)
        icon_str = f"{icon} " if icon else ""
        line = f"{indent_str}{icon_str}{text}"

        if self.use_rich:
            self.console.print(line)
        else:
            click.echo(line)

    def success(self, text: str, icon: str | None = None) -> None:
        """Print a success message."""
        if not self.should_show(MessageLevel.SUCCESS):
            return

        icon_str = icon if icon is not None else self.icons.success
        if self.use_rich:
            self.console.print()
            self.console.print(f"{icon_str} [success]{text}[/success]")
            self.console.print()
        else:
            click.echo(f"\n{icon_str} {text}\n", color=True)

    def info(self, text: str, icon: str | None = None) -> None:
        """Print an info message."""
        if not self.should_show(MessageLevel.INFO):
            return

        icon_str = f"{icon} " if icon else ""

        if self.use_rich:
            self.console.print(f"{icon_str}{text}")
        else:
            click.echo(f"{icon_str}{text}")

    def warning(self, text: str, icon: str | None = None) -> None:
        """Print a warning message."""
        if not self.should_show(MessageLevel.WARNING):
            return

        icon_str = icon if icon is not None else self.icons.warning
        if self.use_rich:
            self.console.print(f"{icon_str} [warning]{text}[/warning]")
        else:
            click.echo(click.style(f"{icon_str} {text}", fg="yellow"))

    def error(self, text: str, icon: str | None = None) -> None:
        """Print an error message."""
        if not self.should_show(MessageLevel.ERROR):
            return

        icon_str = icon if icon is not None else self.icons.error
        if self.use_rich:
            self.console.print(f"{icon_str} [error]{text}[/error]")
        else:
            click.echo(click.style(f"{icon_str} {text}", fg="red", bold=True))

    def tip(self, text: str, icon: str | None = None) -> None:
        """Print a subtle tip/instruction line."""
        if not self.should_show(MessageLevel.INFO):
            return

        icon_str = icon if icon is not None else self.icons.tip
        if self.use_rich:
            self.console.print(f"{icon_str} [tip]{text}[/tip]")
        else:
            click.echo(f"{icon_str} {text}")

    def error_header(self, text: str, mouse: bool = True) -> None:
        """
        Print an error header with mouse emoji.
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

    def path(self, path: str, icon: str | None = None, label: str = "Output") -> None:
        """Print a path with icon and label."""
        if not self.should_show(MessageLevel.INFO):
            return

        display_path = self._format_path(path)
        icon_str = icon if icon is not None else ""

        if self.use_rich:
            if label:
                self.console.print(f"{icon_str}{label}:" if icon_str else f"{label}:")
            self.console.print(f"   {self.icons.arrow} [path]{display_path}[/path]")
        else:
            if label:
                click.echo(f"{icon_str}{label}:" if icon_str else f"{label}:")
            click.echo(click.style(f"   {self.icons.arrow} {display_path}", fg="cyan"))

    def metric(self, label: str, value: Any, unit: str | None = None, indent: int = 0) -> None:
        """Print a metric with label and optional unit."""
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
            for row in data:
                values = [f"{k}: {v}" for k, v in row.items()]
                click.echo(" | ".join(values))

    def prompt(
        self, text: str, default: Any = None, type: Any = str, show_default: bool = True
    ) -> Any:
        """Prompt user for input with themed styling."""
        if self.use_rich:
            from rich.prompt import Prompt

            return Prompt.ask(
                f"[prompt]{text}[/prompt]",
                default=default,
                console=self.console,
                show_default=show_default,
            )
        else:
            return click.prompt(text, default=default, type=type, show_default=show_default)

    def confirm(self, text: str, default: bool = False) -> bool:
        """Prompt user for yes/no confirmation with themed styling."""
        if self.use_rich:
            from rich.prompt import Confirm

            return Confirm.ask(f"[prompt]{text}[/prompt]", default=default, console=self.console)
        else:
            return click.confirm(text, default=default)

    def blank(self, count: int = 1) -> None:
        """Print blank lines."""
        for _ in range(count):
            if self.use_rich:
                self.console.print()
            else:
                click.echo()

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

        return "WRITER" not in profile_name

    def _show_details(self) -> bool:
        """Should we show detailed info based on profile?"""
        if not self.profile:
            return True
        return True

    def _format_phase_line(self, parts: list[str]) -> str:
        """Format a phase line with consistent spacing."""
        if len(parts) < 2:
            return " ".join(parts)

        icon = parts[0]
        name = parts[1]
        rest = parts[2:] if len(parts) > 2 else []

        name_width = 12
        name_padded = name.ljust(name_width)

        if rest:
            return f"{icon} {name_padded} {' '.join(rest)}"
        else:
            if getattr(self, "dev_server", False):
                return f"{icon} {name_padded}".rstrip()
            return f"{icon} {name_padded} Done"

    def _now_ms(self) -> int:
        try:
            import time as _time

            return int(_time.monotonic() * 1000)
        except Exception as e:
            logger.debug(
                "cli_output_now_ms_failed",
                error=str(e),
                error_type=type(e).__name__,
                action="returning_zero",
            )
            return 0

    def _should_dedup_phase(self, line: str) -> bool:
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

        if "WRITER" in profile_name:
            from pathlib import Path

            return Path(path).name or path

        if "THEME" in profile_name and len(path) > 60:
            parts = path.split("/")
            if len(parts) > 3:
                return f"{parts[0]}/.../{'/'.join(parts[-2:])}"

        return path
