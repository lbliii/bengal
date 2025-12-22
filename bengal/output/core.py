"""
Core CLI output manager.

Provides the central CLIOutput class for all terminal output in Bengal.
All CLI messaging flows through this class, which ensures:

- Profile-aware formatting (Writer sees minimal output, Developer sees everything)
- Consistent spacing and indentation across all commands
- Automatic TTY detection with Rich/plain text fallback
- Icon sets (ASCII default, emoji opt-in)

Icon Policy:
    - ASCII-first by default (✓, !, x, etc.)
    - Cat mascot (ᓚᘏᗢ) for success headers
    - Mouse mascot (ᘛ⁐̤ᕐᐷ) for error headers (cat catches the bug!)
    - Emoji opt-in via BENGAL_EMOJI=1 environment variable

Classes:
    CLIOutput: The primary output manager class.

Related:
    - bengal/output/globals.py: Singleton access via get_cli_output()
    - bengal/output/enums.py: MessageLevel and OutputStyle enums
    - bengal/output/icons.py: Icon set definitions
    - bengal/output/dev_server.py: DevServerOutputMixin for dev server output
    - bengal/utils/rich_console.py: Rich console configuration
"""

from __future__ import annotations

import logging
from typing import Any

import click
from rich.panel import Panel
from rich.table import Table

from bengal.output.dev_server import DevServerOutputMixin
from bengal.output.enums import MessageLevel
from bengal.output.icons import IconSet, get_icon_set

logger = logging.getLogger(__name__)


class CLIOutput(DevServerOutputMixin):
    """
    Centralized CLI output manager.

    All terminal output in Bengal flows through this class. It provides
    profile-aware formatting (Writer/Theme-Dev/Developer), consistent
    spacing, automatic TTY detection, and Rich/plain text rendering.

    The class inherits dev server output methods from DevServerOutputMixin
    for request logging and file change notifications.

    Attributes:
        profile: Active build profile controlling output verbosity and style.
        quiet: If True, suppresses INFO-level and below messages.
        verbose: If True, includes DEBUG-level messages.
        use_rich: True if Rich library is used for output, False for plain text.
        console: Rich Console instance (always present, even when Rich disabled).
        dev_server: True when running inside the development server.
        profile_config: Configuration dict from the active profile.
        indent_char: Character used for indentation (default: space).
        indent_size: Number of indent_char per indent level (default: 2).

    Example:
        >>> cli = CLIOutput(profile=BuildProfile.WRITER)
        >>> cli.header("Building your site...")
        >>> cli.phase("Discovery", duration_ms=61, details="245 pages")
        >>> cli.success("Built 245 pages in 0.8s")

    Note:
        Use get_cli_output() from bengal.output.globals for singleton access.
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
            profile: Build profile (Writer, Theme-Dev, Developer). Controls
                which details are shown (timing, paths, etc.). Writer profile
                shows minimal output; Developer shows everything.
            quiet: If True, suppress INFO-level and below messages. Only
                WARNING, ERROR, and CRITICAL messages are shown.
            verbose: If True, include DEBUG-level messages for detailed
                diagnostic output.
            use_rich: Force Rich (True) or plain text (False) output.
                If None (default), auto-detects based on TTY capabilities.
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

        # Track blank lines to prevent consecutive blanks
        self._last_was_blank: bool = False

        # Get profile config
        self.profile_config = profile.get_config() if profile else {}

        # Spacing and indentation rules
        self.indent_char = " "
        self.indent_size = 2

        # Icon set (ASCII by default, emoji opt-in via BENGAL_EMOJI=1)
        from bengal.utils.rich_console import should_use_emoji

        self._icons = get_icon_set(use_emoji=should_use_emoji())

    @property
    def icons(self) -> IconSet:
        """
        Get the current icon set (ASCII or Emoji).

        Returns:
            The active IconSet instance based on BENGAL_EMOJI environment variable.
        """
        return self._icons

    def should_show(self, level: MessageLevel) -> bool:
        """
        Determine if a message should be shown based on level and settings.

        Args:
            level: The MessageLevel of the message to check.

        Returns:
            True if the message should be displayed, False if suppressed.

        Note:
            - In quiet mode, only WARNING and above are shown.
            - DEBUG messages require verbose mode to be enabled.
        """
        if self.quiet and level.value < MessageLevel.WARNING.value:
            return False
        return not (not self.verbose and level == MessageLevel.DEBUG)

    # === High-level message types ===

    def header(
        self,
        text: str,
        mascot: bool = True,
        leading_blank: bool = False,
        trailing_blank: bool = True,
    ) -> None:
        """
        Print a prominent header message with optional Bengal cat mascot.

        Headers are used for major command announcements (e.g., "Building your site...").
        In Rich mode, headers display in a bordered panel for visual emphasis.

        Args:
            text: The header text to display.
            mascot: If True, include Bengal cat (ᓚᘏᗢ) before text.
            leading_blank: If True, add blank line before header.
                Defaults to False since shell prompt provides spacing.
            trailing_blank: If True, add blank line after header.

        Example:
            >>> cli.header("Building your site...")
            # Output: ┌─────────────────────────────┐
            #         │  ᓚᘏᗢ  Building your site...  │
            #         └─────────────────────────────┘
        """
        if not self.should_show(MessageLevel.INFO):
            return

        self._mark_output()
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
        Print a subheader as simple bold text without decorations.

        Subheaders are less prominent than headers. Use them to introduce
        major sections within a command's output.

        Args:
            text: The subheader text to display.
            icon: Optional icon to display before text.
            leading_blank: If True, add blank line before subheader.
            trailing_blank: If True, add blank line after subheader.
            width: Unused, kept for API compatibility.

        Example:
            >>> cli.subheader("Build Summary")
            # Output: (blank line)
            #         Build Summary
        """
        if not self.should_show(MessageLevel.INFO):
            return

        if leading_blank:
            self.blank()

        # Simple format: just the text, bold
        icon_str = f"{icon} " if icon else ""
        label = f"{icon_str}{text}"

        if self.use_rich:
            self.console.print(f"[bold]{label}[/bold]")
        else:
            click.echo(click.style(label, bold=True))

        if trailing_blank:
            self.blank()

    def section(self, title: str, icon: str | None = None) -> None:
        """
        Print a section header with colon suffix.

        Sections group related output. A blank line is automatically added
        before the section header if the previous output wasn't blank.

        Args:
            title: Section title text. A colon is automatically appended.
            icon: Optional icon to display before title. Uses section icon
                from IconSet if not provided (empty in ASCII mode).

        Example:
            >>> cli.section("Post-processing")
            # Output: (blank line)
            #         Post-processing:
        """
        if not self.should_show(MessageLevel.INFO):
            return

        # Add blank line before section (uses tracking to prevent doubles)
        self.blank()
        self._mark_output()

        # Use section icon from icon set (empty by default in ASCII mode)
        section_icon = icon if icon is not None else self.icons.section
        icon_str = f"{section_icon} " if section_icon else ""

        if self.use_rich:
            self.console.print(f"[header]{icon_str}{title}:[/header]")
        else:
            click.echo(f"{icon_str}{title}:")

    def phase(
        self,
        name: str,
        status: str = "Done",
        duration_ms: float | None = None,
        details: str | None = None,
        icon: str | None = None,
    ) -> None:
        """
        Print a build phase status line with timing and details.

        Phases represent major build steps (Discovery, Rendering, Assets).
        Output format is profile-aware: timing is hidden for Writer profile.
        In dev server mode, duplicate phase messages are deduplicated.

        Args:
            name: Phase name (e.g., "Discovery", "Rendering").
            status: Status text, shown when no timing/details provided.
            duration_ms: Phase duration in milliseconds. Shown for non-Writer profiles.
            details: Additional context (e.g., "245 pages"). Shown in parentheses.
            icon: Override default success icon.

        Example:
            >>> cli.phase("Discovery", duration_ms=61, details="245 pages")
            # Output: ✓ Discovery     61ms (245 pages)

            >>> cli.phase("Assets")
            # Output: ✓ Assets        Done
        """
        if not self.should_show(MessageLevel.SUCCESS):
            return

        self._mark_output()
        phase_icon = icon if icon is not None else self.icons.success

        if self.use_rich:
            parts = [f"[success]{phase_icon}[/success]", f"[phase]{name}[/phase]"]

            if duration_ms is not None and self._show_timing():
                parts.append(f"[dim]{int(duration_ms)}ms[/dim]")

            if details and self._show_details():
                parts.append(f"([dim]{details}[/dim])")

            line = self._format_phase_line(parts)

            if self._should_dedup_phase(line):
                return
            self._mark_phase_emit(line)
            self.console.print(line)
        else:
            parts = [phase_icon, name]

            if duration_ms is not None and self._show_timing():
                parts.append(f"{int(duration_ms)}ms")

            if details and self._show_details():
                parts.append(f"({details})")

            line = self._format_phase_line(parts)

            if self._should_dedup_phase(line):
                return
            self._mark_phase_emit(line)
            click.echo(click.style(line, fg="green"))

    def detail(self, text: str, indent: int = 1, icon: str | None = None) -> None:
        """
        Print a detail line with indentation.

        Details are subordinate items shown under phases or sections.

        Args:
            text: The detail text to display.
            indent: Indentation level (each level = indent_size spaces).
            icon: Optional icon to prefix the text.

        Example:
            >>> cli.detail("Found 245 pages", indent=1)
            # Output:   Found 245 pages
        """
        if not self.should_show(MessageLevel.INFO):
            return

        self._mark_output()
        indent_str = self.indent_char * (self.indent_size * indent)
        icon_str = f"{icon} " if icon else ""
        line = f"{indent_str}{icon_str}{text}"

        if self.use_rich:
            self.console.print(line)
        else:
            click.echo(line)

    def success(self, text: str, icon: str | None = None) -> None:
        """
        Print a success message with checkmark icon.

        Args:
            text: The success message text.
            icon: Override default success icon (✓ or ✨).

        Example:
            >>> cli.success("Built 245 pages in 0.8s")
            # Output: ✓ Built 245 pages in 0.8s
        """
        if not self.should_show(MessageLevel.SUCCESS):
            return

        self._mark_output()
        success_icon = icon if icon is not None else self.icons.success
        if self.use_rich:
            self.console.print(f"{success_icon} [success]{text}[/success]")
        else:
            click.echo(f"{success_icon} {text}", color=True)

    def info(self, text: str, icon: str | None = None) -> None:
        """
        Print an informational message.

        Args:
            text: The info message text.
            icon: Optional icon to prefix the text.

        Example:
            >>> cli.info("Using cached assets")
        """
        if not self.should_show(MessageLevel.INFO):
            return

        self._mark_output()
        icon_str = f"{icon} " if icon else ""

        if self.use_rich:
            self.console.print(f"{icon_str}{text}")
        else:
            click.echo(f"{icon_str}{text}")

    def warning(self, text: str, icon: str | None = None) -> None:
        """
        Print a warning message in yellow.

        Warnings indicate non-critical issues that don't stop the build
        but should be addressed.

        Args:
            text: The warning message text.
            icon: Override default warning icon (! or ⚠️).

        Example:
            >>> cli.warning("Missing optional frontmatter field 'description'")
            # Output: !  Missing optional frontmatter field 'description'
        """
        if not self.should_show(MessageLevel.WARNING):
            return

        self._mark_output()
        warning_icon = icon if icon is not None else self.icons.warning
        if self.use_rich:
            self.console.print(f"{warning_icon}  [warning]{text}[/warning]")
        else:
            click.echo(click.style(f"{warning_icon}  {text}", fg="yellow"))

    def error(self, text: str, icon: str | None = None) -> None:
        """
        Print an error message in red.

        Errors indicate problems that may affect the build outcome.

        Args:
            text: The error message text.
            icon: Override default error icon (x or ❌).

        Example:
            >>> cli.error("Failed to parse frontmatter in about.md")
            # Output: x Failed to parse frontmatter in about.md
        """
        if not self.should_show(MessageLevel.ERROR):
            return

        self._mark_output()
        error_icon = icon if icon is not None else self.icons.error
        if self.use_rich:
            self.console.print(f"{error_icon} [error]{text}[/error]")
        else:
            click.echo(click.style(f"{error_icon} {text}", fg="red", bold=True))

    def tip(self, text: str, icon: str | None = None) -> None:
        """
        Print a subtle tip or instruction.

        Tips provide helpful suggestions without the urgency of warnings.

        Args:
            text: The tip text.
            icon: Override default tip icon (* or 💡).

        Example:
            >>> cli.tip("Run 'bengal serve' to preview your site")
            # Output: * Run 'bengal serve' to preview your site
        """
        if not self.should_show(MessageLevel.INFO):
            return

        self._mark_output()
        tip_icon = icon if icon is not None else self.icons.tip
        if self.use_rich:
            self.console.print(f"{tip_icon} [tip]{text}[/tip]")
        else:
            click.echo(f"{tip_icon} {text}")

    def error_header(self, text: str, mouse: bool = True) -> None:
        """
        Print a prominent error header with optional mouse mascot.

        Uses the mouse mascot (ᘛ⁐̤ᕐᐷ) to represent errors that Bengal (the cat)
        needs to catch! In Rich mode, displays in a red-bordered panel.

        Args:
            text: The error header text.
            mouse: If True, include mouse mascot before text.

        Example:
            >>> cli.error_header("Build failed")
            # Output: ┌──────────────────────┐
            #         │  ᘛ⁐̤ᕐᐷ  Build failed   │
            #         └──────────────────────┘
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
        """
        Print a labeled path with arrow indicator.

        Paths are formatted according to profile: Writer sees just the filename,
        Theme-Dev sees abbreviated paths, Developer sees full paths.

        Args:
            path: The filesystem path to display.
            icon: Optional icon before the label.
            label: Label text shown before the path (default: "Output").

        Example:
            >>> cli.path("/Users/dev/site/public", label="Output")
            # Output: Output:
            #            ↪ /Users/dev/site/public  (Developer)
            #            ↪ public                  (Writer)
        """
        if not self.should_show(MessageLevel.INFO):
            return

        display_path = self._format_path(path)

        # Use section icon from icon set (empty by default in ASCII mode)
        path_icon = icon if icon is not None else self.icons.section
        icon_prefix = f"{path_icon} " if path_icon else ""

        if self.use_rich:
            self.console.print(f"{icon_prefix}{label}:")
            self.console.print(f"   {self.icons.arrow} [path]{display_path}[/path]")
        else:
            click.echo(f"{icon_prefix}{label}:")
            click.echo(click.style(f"   {self.icons.arrow} {display_path}", fg="cyan"))

    def metric(self, label: str, value: Any, unit: str | None = None, indent: int = 0) -> None:
        """
        Print a labeled metric value with optional unit.

        Args:
            label: Metric name/label.
            value: Metric value (any type, will be stringified).
            unit: Optional unit suffix (e.g., "ms", "MB", "pages").
            indent: Indentation level for the output.

        Example:
            >>> cli.metric("Build time", 823, unit="ms")
            # Output: Build time: 823 ms

            >>> cli.metric("Pages", 245)
            # Output: Pages: 245
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
        """
        Print a formatted table.

        In Rich mode, displays a proper table with headers and borders.
        In plain mode, falls back to a simple key: value list format.

        Args:
            data: List of row dicts where keys match header names.
            headers: List of column header strings.

        Example:
            >>> cli.table(
            ...     [{"Name": "index.md", "Size": "2.3KB"}],
            ...     headers=["Name", "Size"]
            ... )
            # Rich output:
            # ┌──────────┬───────┐
            # │ Name     │ Size  │
            # ├──────────┼───────┤
            # │ index.md │ 2.3KB │
            # └──────────┴───────┘
        """
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
        """
        Prompt user for text input with themed styling.

        Uses Rich Prompt in Rich mode, Click prompt otherwise.

        Args:
            text: Prompt text shown to user.
            default: Default value if user presses Enter.
            type: Expected input type for validation.
            show_default: If True, display the default value in prompt.

        Returns:
            The user's input, converted to the specified type.

        Example:
            >>> name = cli.prompt("Project name", default="my-site")
            # Output: Project name [my-site]:
        """
        if self.use_rich:
            from rich.prompt import Prompt

            result = Prompt.ask(
                f"[prompt]{text}[/prompt]",
                default=default,
                console=self.console,
                show_default=show_default,
            )
        else:
            result = click.prompt(text, default=default, type=type, show_default=show_default)
        # User's Enter press added a newline, mark it
        self._last_was_blank = True
        return result

    def confirm(self, text: str, default: bool = False) -> bool:
        """
        Prompt user for yes/no confirmation.

        Uses Rich Confirm in Rich mode, Click confirm otherwise.

        Args:
            text: Confirmation prompt text.
            default: Default value if user presses Enter (False = no).

        Returns:
            True if user confirmed, False otherwise.

        Example:
            >>> if cli.confirm("Overwrite existing files?"):
            ...     # proceed with overwrite
        """
        if self.use_rich:
            from rich.prompt import Confirm

            result = Confirm.ask(f"[prompt]{text}[/prompt]", default=default, console=self.console)
        else:
            result = click.confirm(text, default=default)
        # User's Enter press added a newline, mark it
        self._last_was_blank = True
        return result

    def blank(self) -> None:
        """
        Print a blank line, preventing consecutive blanks.

        Tracks output state to ensure multiple consecutive blank() calls
        only produce a single blank line.
        """
        if self._last_was_blank:
            return  # Prevent consecutive blank lines
        self._last_was_blank = True
        if self.use_rich:
            self.console.print()
        else:
            click.echo()

    def _mark_output(self) -> None:
        """Mark that non-blank output was printed, resetting blank tracking."""
        self._last_was_blank = False

    # === Internal helpers ===

    def _show_timing(self) -> bool:
        """Check if timing info should be shown based on profile."""
        if not self.profile:
            return False

        profile_name = (
            self.profile.__class__.__name__
            if hasattr(self.profile, "__class__")
            else str(self.profile)
        )

        return "WRITER" not in profile_name

    def _show_details(self) -> bool:
        """Check if detailed info should be shown based on profile."""
        if not self.profile:
            return True
        return True

    def _format_phase_line(self, parts: list[str]) -> str:
        """Format a phase line with consistent column spacing."""
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
        """Get current monotonic time in milliseconds for phase deduplication."""
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
        """Check if phase line should be deduplicated in dev server mode."""
        if not getattr(self, "dev_server", False):
            return False
        key = line
        now = self._now_ms()
        return (
            self._last_phase_key == key and (now - self._last_phase_time_ms) < self._phase_dedup_ms
        )

    def _mark_phase_emit(self, line: str) -> None:
        """Record phase emission for deduplication tracking."""
        if not getattr(self, "dev_server", False):
            return
        self._last_phase_key = line
        self._last_phase_time_ms = self._now_ms()

    def _format_path(self, path: str) -> str:
        """
        Format path based on active profile.

        Writer: filename only, Theme-Dev: abbreviated, Developer: full path.
        """
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
