"""Milo/Kida CLI output bridge.

Provides the central CLIOutput class for terminal output in Bengal. This class
bridges Milo command execution to Bengal's Kida templates and theme tokens, so
command results, prompts, raw progress, and compatibility helpers share one
rendering path.

- Profile-aware formatting (Writer sees minimal output, Developer sees everything)
- Consistent spacing and indentation across all commands
- Automatic TTY detection with color/plain text fallback
- Icon sets (ASCII default, emoji opt-in)

Powered by milo's theme system (ThemeStyle + ANSI SGR codes). No Rich or
Click dependency for output rendering.

Classes:
CLIOutput: The primary output manager class.

Related:
- bengal/output/globals.py: Singleton access via get_cli_output()
- bengal/output/theme.py: BENGAL_THEME style definitions
- bengal/output/enums.py: MessageLevel and OutputStyle enums
- bengal/output/icons.py: Icon set definitions
- bengal/output/dev_server.py: DevServerOutputMixin for dev server output

"""

from __future__ import annotations

import os
import re
import sys
from contextlib import contextmanager
from typing import Any

from bengal.output.dev_server import DevServerOutputMixin
from bengal.output.enums import MessageLevel
from bengal.output.icons import IconSet, get_icon_set
from bengal.output.theme import BENGAL_THEME

_RESET = "\033[0m"
_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_UNSET = object()
_ASCII_REPLACEMENTS = {
    "ᓚᘏᗢ": "Bengal",
    "ᗢ": "Bengal",
    "ᘛ⁐̤ᕐᐷ": "!",
    "✓": "v",
    "✗": "x",
    "✖": "x",
    "❌": "x",
    "⚠️": "!",
    "⚠": "!",
    "ℹ️": "i",
    "ℹ": "i",
    "▲": "!",
    "◆": "^",
    "█": "#",
    "░": ".",
    "│": "|",
    "├": "+",
    "└": "`",
    "─": "-",
    "╭": "+",
    "╮": "+",
    "╰": "+",
    "╯": "+",
    "→": ">",
    "↪": ">",
    "•": "*",
    "·": ".",
    "…": "...",
    "—": "-",
    "–": "-",
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
    "🚀": "++",
    "⚡": "+",
    "📊": "~",
    "🐌": "-",
}


def _plain_ascii(text: str) -> str:
    """Normalize command-owned output for ASCII-only logs."""
    for old, new in _ASCII_REPLACEMENTS.items():
        text = text.replace(old, new)
    return text.encode("ascii", "replace").decode("ascii")


def _panel_content_width(content: str, title: str = "") -> int:
    """Return the widest visible line for Bengal terminal panels."""
    lines = str(content).splitlines()
    body_width = max((len(line) for line in lines), default=0)
    title_width = len(str(title)) + 4 if title else 0
    return max(body_width, title_width)


def _should_use_color() -> bool:
    """Detect whether the terminal supports color output."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _should_use_emoji() -> bool:
    """Check if emoji output is requested."""
    return os.environ.get("BENGAL_EMOJI", "") == "1"


class CLIOutput(DevServerOutputMixin):
    """
    Milo/Kida renderer bridge for Bengal CLI output.

    CLIOutput owns Bengal-specific terminal presentation while leaning on Milo's
    theme and Kida template environment. High-level helpers such as ``success``
    and ``section`` sit beside low-level ``raw`` and progress methods so legacy
    CLI utilities can route unavoidable terminal writes through the same bridge.

    Attributes:
        profile: Active build profile controlling output verbosity and style.
        quiet: If True, suppresses INFO-level and below messages.
        verbose: If True, includes DEBUG-level messages.
        use_color: True if ANSI color codes are used for output.
        dev_server: True when running inside the development server.
        profile_config: Configuration dict from the active profile.
        indent_char: Character used for indentation (default: space).
        indent_size: Number of indent_char per indent level (default: 2).

    """

    def __init__(
        self,
        profile: Any | None = None,
        quiet: bool = False,
        verbose: bool = False,
        use_rich: bool | None = None,
    ):
        self.profile = profile
        self.quiet = quiet
        self.verbose = verbose
        self.use_color = _should_use_color()

        # Backward compat: use_rich maps to use_color
        if use_rich is not None:
            self.use_color = use_rich
        # Alias for code that checks use_rich
        self.use_rich = self.use_color

        # Lazy-init console only when directly accessed
        self._console = None

        # Dev mode detection
        try:
            self.dev_server = os.environ.get("BENGAL_DEV_SERVER", "") == "1"
            self._phase_dedup_ms = int(os.environ.get("BENGAL_CLI_PHASE_DEDUP_MS", "1500"))
        except Exception:
            self.dev_server = False
            self._phase_dedup_ms = 1500

        # Phase deduplication tracking
        self._last_phase_key: str | None = None
        self._last_phase_time_ms: int = 0

        # Blank line deduplication
        self._last_was_blank: bool = False

        # Profile config
        self.profile_config = profile.get_config() if profile else {}

        # Spacing
        self.indent_char = " "
        self.indent_size = 2

        # Icons
        self._icons = get_icon_set(
            use_emoji=_should_use_emoji(),
            plain_ascii=os.environ.get("BENGAL_CLI_ASCII", "") == "1",
        )

        # Theme styles (pre-resolve SGR prefixes for speed)
        self._styles: dict[str, str] = {}
        for name, style in BENGAL_THEME.items():
            self._styles[name] = style.sgr_prefix() if self.use_color else ""

    @property
    def console(self):
        """Deprecated — returns None. Use cli.render_write() or cli.info() instead."""
        return self._console

    @console.setter
    def console(self, value):
        """Allow direct assignment for backward compat and tests."""
        self._console = value

    @property
    def icons(self) -> IconSet:
        """Get the current icon set (ASCII or Emoji)."""
        return self._icons

    @property
    def _kida_env(self):
        """Lazy kida template environment with BENGAL_THEME and Bengal templates."""
        if not hasattr(self, "_kida_env_cache"):
            from pathlib import Path

            from kida import FileSystemLoader
            from milo.templates import get_env

            bengal_tpl = Path(__file__).parent / "templates"
            self._kida_env_cache = get_env(
                loader=FileSystemLoader(str(bengal_tpl)),
                theme=BENGAL_THEME,
            )
            self._kida_env_cache.add_global("bengal_panel_width", _panel_content_width)
        return self._kida_env_cache

    def render(self, template_name: str, **context: Any) -> str:
        """Render a kida template with Bengal theme and return the string.

        Templates are loaded from bengal/output/templates/ with fallback to
        milo's built-in templates. All milo components (_defs.kida) and
        terminal filters (bold, dim, green, etc.) are available.
        """
        tpl = self._kida_env.get_template(template_name)
        return tpl.render(**context)

    def render_write(self, template_name: str, **context: Any) -> None:
        """Render a kida template and write it to stdout."""
        self._mark_output()
        result = self.render(template_name, **context).strip("\n")
        if result.strip():
            self._write(result)

    def _render_component(self, source: str, component: str, call_expr: str, **context: Any) -> str:
        """Render a component from a kida source file.

        Args:
            source: Template file to import from (e.g. "_bengal.kida")
            component: Component name to import
            call_expr: The kida expression to render (e.g. "bengal_header(text, mascot=mascot)")
            **context: Variables available in the template
        """
        if not hasattr(self, "_component_cache"):
            self._component_cache: dict[str, Any] = {}
        cache_key = f"{source}:{call_expr}"
        if cache_key not in self._component_cache:
            self._component_cache[cache_key] = self._kida_env.from_string(
                f'{{% from "{source}" import {component} %}}{{{{ {call_expr} }}}}'
            )
        return self._component_cache[cache_key].render(**context)

    def _s(self, name: str) -> str:
        """Get SGR prefix for a style name."""
        return self._styles.get(name, "")

    def set_color_enabled(self, enabled: bool) -> None:
        """Enable or disable ANSI color for subsequent output."""
        self.use_color = enabled
        self.use_rich = enabled
        if enabled:
            os.environ.pop("BENGAL_CLI_NO_COLOR", None)
        else:
            os.environ["BENGAL_CLI_NO_COLOR"] = "1"
        for name, style in BENGAL_THEME.items():
            self._styles[name] = style.sgr_prefix() if self.use_color else ""

    def set_ascii_enabled(self, enabled: bool) -> None:
        """Enable or disable strict ASCII glyphs for subsequent output."""
        if enabled:
            os.environ["BENGAL_CLI_ASCII"] = "1"
        else:
            os.environ.pop("BENGAL_CLI_ASCII", None)
        self._icons = get_icon_set(use_emoji=_should_use_emoji(), plain_ascii=enabled)

    @contextmanager
    def output_mode(self, style: str = "dense"):
        """Temporarily apply an output style and restore previous process state."""
        style_value = (style or "dense").lower()
        if style_value not in {"dense", "ascii", "ci"}:
            msg = f"Unknown output style {style!r}; expected dense, ascii, or ci."
            raise ValueError(msg)

        previous_color = self.use_color
        previous_rich = self.use_rich
        previous_icons = self._icons
        previous_styles = self._styles.copy()
        previous_ascii = os.environ.get("BENGAL_CLI_ASCII", _UNSET)
        previous_no_color = os.environ.get("BENGAL_CLI_NO_COLOR", _UNSET)

        try:
            if style_value in {"ascii", "ci"}:
                self.set_color_enabled(False)
                self.set_ascii_enabled(True)
            yield self
        finally:
            self.use_color = previous_color
            self.use_rich = previous_rich
            self._icons = previous_icons
            self._styles = previous_styles
            if previous_ascii is _UNSET:
                os.environ.pop("BENGAL_CLI_ASCII", None)
            else:
                os.environ["BENGAL_CLI_ASCII"] = str(previous_ascii)
            if previous_no_color is _UNSET:
                os.environ.pop("BENGAL_CLI_NO_COLOR", None)
            else:
                os.environ["BENGAL_CLI_NO_COLOR"] = str(previous_no_color)

    def _styled(self, text: str, style: str) -> str:
        """Wrap text in ANSI style codes."""
        prefix = self._s(style)
        if not prefix:
            return text
        return f"{prefix}{text}{_RESET}"

    def _stream(self, name: str):
        """Return a standard output stream by public bridge name."""
        match name:
            case "stdout":
                return sys.stdout
            case "stderr":
                return sys.stderr
            case _:
                msg = f"Unknown CLI output stream {name!r}; expected 'stdout' or 'stderr'."
                raise ValueError(msg)

    def raw(
        self,
        text: str = "",
        *,
        stream: str = "stdout",
        level: MessageLevel | None = MessageLevel.INFO,
        end: str = "\n",
    ) -> None:
        """Write unavoidable raw terminal text through the CLIOutput bridge.

        This exists for compatibility surfaces such as carriage-return progress,
        Milo generator progress, and prompts. Prefer semantic helpers when a
        structured message type exists.
        """
        if level is not None and not self.should_show(level):
            return

        if text:
            self._mark_output()
        elif "\n" in end:
            self._last_was_blank = True

        if text and not self.use_color:
            text = _ANSI_RE.sub("", text)
        if text and os.environ.get("BENGAL_CLI_ASCII") == "1":
            text = _plain_ascii(text)

        target = self._stream(stream)
        target.write(text + end)
        target.flush()

    def _write(self, text: str) -> None:
        """Write a semantic stdout line."""
        self.raw(text, level=None)

    def should_show(self, level: MessageLevel) -> bool:
        """Determine if a message should be shown based on level and settings."""
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
        """Print a prominent header message with optional Bengal cat mascot."""
        if not self.should_show(MessageLevel.INFO):
            return

        self._mark_output()
        if leading_blank:
            self._write("")
        if os.environ.get("BENGAL_CLI_ASCII") == "1":
            prefix = f"{self.icons.mascot} " if mascot else ""
            self._write(f"{prefix}{text}")
            if trailing_blank:
                self._write("")
            return
        result = self._render_component(
            "_bengal.kida",
            "bengal_header",
            "bengal_header(text, mascot=mascot)",
            text=text,
            mascot=mascot,
        )
        self._write(result)
        if trailing_blank:
            self._write("")

    def subheader(
        self,
        text: str,
        icon: str | None = None,
        leading_blank: bool = True,
        trailing_blank: bool = False,
        width: int = 60,
    ) -> None:
        """Print a subheader as simple bold text."""
        if not self.should_show(MessageLevel.INFO):
            return

        if leading_blank:
            self.blank()

        icon_str = f"{icon} " if icon else ""
        self._write(self._styled(f"{icon_str}{text}", "emphasis"))

        if trailing_blank:
            self.blank()

    def section(self, title: str, icon: str | None = None) -> None:
        """Print a section header with colon suffix."""
        if not self.should_show(MessageLevel.INFO):
            return

        self.blank()
        self._mark_output()

        section_icon = icon if icon is not None else self.icons.section
        icon_str = f"{section_icon} " if section_icon else ""
        self._write(self._styled(f"{icon_str}{title}:", "header"))

    def phase(
        self,
        name: str,
        status: str = "Done",
        duration_ms: float | None = None,
        details: str | None = None,
        icon: str | None = None,
    ) -> None:
        """Print a build phase status line with timing and details."""
        if not self.should_show(MessageLevel.SUCCESS):
            return

        self._mark_output()
        phase_icon = icon if icon is not None else self.icons.success

        parts = [self._styled(phase_icon, "success"), self._styled(name, "phase")]

        if duration_ms is not None and self._show_timing():
            parts.append(self._styled(f"{int(duration_ms)}ms", "dim"))

        if details and self._show_details():
            parts.append(f"({self._styled(details, 'dim')})")

        line = self._format_phase_line(parts)

        if self._should_dedup_phase(line):
            return
        self._mark_phase_emit(line)
        self._write(line)

    def detail(self, text: str, indent: int = 1, icon: str | None = None) -> None:
        """Print a detail line with indentation."""
        if not self.should_show(MessageLevel.INFO):
            return

        self._mark_output()
        indent_str = self.indent_char * (self.indent_size * indent)
        icon_str = f"{icon} " if icon else ""
        self._write(f"{indent_str}{icon_str}{text}")

    def success(self, text: str, icon: str | None = None) -> None:
        """Print a success message with checkmark icon."""
        if not self.should_show(MessageLevel.SUCCESS):
            return

        success_icon = icon if icon is not None else self.icons.success
        self._message_line("success", text, icon=success_icon)

    def info(self, text: str, icon: str | None = None) -> None:
        """Print an informational message."""
        if not self.should_show(MessageLevel.INFO):
            return

        self._message_line("info", text, icon=icon or "")

    def warning(self, text: str, icon: str | None = None) -> None:
        """Print a warning message."""
        if not self.should_show(MessageLevel.WARNING):
            return

        warning_icon = icon if icon is not None else self.icons.warning
        self._message_line("warning", text, icon=warning_icon)

    def error(self, text: str, icon: str | None = None) -> None:
        """Print an error message."""
        if not self.should_show(MessageLevel.ERROR):
            return

        error_icon = icon if icon is not None else self.icons.error
        self._message_line("error", text, icon=error_icon)

    def tip(self, text: str, icon: str | None = None) -> None:
        """Print a subtle tip or instruction."""
        if not self.should_show(MessageLevel.INFO):
            return

        tip_icon = icon if icon is not None else self.icons.tip
        self._message_line("tip", text, icon=tip_icon)

    def _message_line(self, level: str, text: str, *, icon: str = "") -> None:
        """Render a semantic one-line message through Bengal's Kida templates."""
        result = self.render("message_line.kida", level=level, text=text, icon=icon).strip("\n")
        if result:
            self._write(result)

    def error_header(self, text: str, mouse: bool = True) -> None:
        """Print a prominent error header with optional mouse mascot."""
        if not self.should_show(MessageLevel.ERROR):
            return

        if os.environ.get("BENGAL_CLI_ASCII") == "1":
            prefix = f"{self.icons.error_mascot} " if mouse else ""
            self._write(f"{prefix}{_plain_ascii(text)}")
            return

        result = self._render_component(
            "_bengal.kida",
            "error_header",
            "error_header(text, mouse=mouse)",
            text=text,
            mouse=mouse,
        )
        self._write(result)

    def path(self, path: str, icon: str | None = None, label: str = "Output") -> None:
        """Print a labeled path with arrow indicator."""
        if not self.should_show(MessageLevel.INFO):
            return

        display_path = self._format_path(path)
        path_icon = icon if icon is not None else self.icons.section
        icon_prefix = f"{path_icon} " if path_icon else ""
        self._write(f"{icon_prefix}{label}:")
        self._write(f"   {self.icons.arrow} {self._styled(display_path, 'path')}")

    def metric(self, label: str, value: Any, unit: str | None = None, indent: int = 0) -> None:
        """Print a labeled metric value with optional unit."""
        if not self.should_show(MessageLevel.INFO):
            return

        indent_str = self.indent_char * (self.indent_size * indent)
        unit_str = f" {unit}" if unit else ""
        styled_label = self._styled(label, "metric_label")
        self._write(f"{indent_str}{styled_label}: {value}{unit_str}")

    def table(self, data: list[dict[str, str]], headers: list[str]) -> None:
        """Print a formatted table."""
        if not self.should_show(MessageLevel.INFO):
            return

        self._mark_output()
        # Convert dicts to row lists for kida table filter
        rows = [[str(row.get(h, "")) for h in headers] for row in data]
        if not hasattr(self, "_table_tpl"):
            self._table_tpl = self._kida_env.from_string(
                "{{ rows | table(headers=headers, border='light') }}"
            )
        self._write(self._table_tpl.render(rows=rows, headers=headers))

    def progress_start(self, description: str) -> None:
        """Start an inline progress line."""
        self.raw(f"  {description}...", end="")

    def progress_update(
        self,
        description: str,
        *,
        current: int,
        total: int | None = None,
    ) -> None:
        """Update an inline progress line with a carriage return."""
        suffix = f"{current}/{total}" if total else str(current)
        self.raw(f"\r  {description} {suffix}", end="")

    def progress_finish(self) -> None:
        """Finish an inline progress line."""
        self.raw("")

    def progress_status(
        self,
        status: str,
        *,
        step: int = 0,
        total: int = 0,
        stream: str = "stderr",
    ) -> None:
        """Render a one-line progress status from Milo generator commands."""
        if step and total:
            status = f"{status} {step}/{total}"
        self.raw(f"  {status}", stream=stream)

    def interrupted(self) -> None:
        """Render the standard Ctrl-C message."""
        self.raw(f"\n{self._styled('Interrupted.', 'dim')}", level=None)

    def prompt(
        self,
        text: str,
        default: Any = None,
        type: Any = str,
        show_default: bool = True,
    ) -> Any:
        """Prompt user for text input."""
        default_str = f" [{default}]" if default and show_default else ""
        self.raw(f"{self._styled(text, 'prompt')}{default_str}: ", level=None, end="")
        try:
            result = input()
        except EOFError, KeyboardInterrupt:
            self.raw("", level=None)
            return default
        self._last_was_blank = True
        if not result and default is not None:
            return default
        return type(result) if type is not str else result

    def confirm(self, text: str, default: bool = False) -> bool:
        """Prompt user for yes/no confirmation."""
        suffix = " [Y/n] " if default else " [y/N] "
        self.raw(f"{self._styled(text, 'prompt')}{suffix}", level=None, end="")
        try:
            answer = input().strip().lower()
        except EOFError, KeyboardInterrupt:
            self.raw("", level=None)
            return default
        self._last_was_blank = True
        if not answer:
            return default
        return answer in ("y", "yes")

    def blank(self) -> None:
        """Print a blank line, preventing consecutive blanks."""
        if self._last_was_blank:
            return
        self._last_was_blank = True
        self._write("")

    def _mark_output(self) -> None:
        """Mark that non-blank output was printed, resetting blank tracking."""
        self._last_was_blank = False

    # === Internal helpers ===

    def _get_profile_name(self) -> str | None:
        """Get normalized profile name for feature checks."""
        if not self.profile:
            return None
        return (
            self.profile.__class__.__name__
            if hasattr(self.profile, "__class__")
            else str(self.profile)
        )

    def _show_timing(self) -> bool:
        """Check if timing info should be shown based on profile."""
        profile_name = self._get_profile_name()
        if not profile_name:
            return False
        return "WRITER" not in profile_name

    def _show_details(self) -> bool:
        """Check if detailed info should be shown based on profile."""
        return True

    def _format_phase_line(self, parts: list[str]) -> str:
        """Format a phase line with consistent column spacing."""
        if len(parts) < 2:
            return " ".join(parts)

        icon = parts[0]
        name = parts[1]
        rest = parts[2:] if len(parts) > 2 else []

        # Strip ANSI to measure actual display width for padding
        import re

        plain_name = re.sub(r"\033\[[0-9;]*m", "", name)
        name_width = 12
        pad = max(0, name_width - len(plain_name))
        name_padded = name + " " * pad

        if rest:
            return f"{icon} {name_padded} {' '.join(rest)}"
        if getattr(self, "dev_server", False):
            return f"{icon} {name_padded}".rstrip()
        return f"{icon} {name_padded} Done"

    def _now_ms(self) -> int:
        """Get current monotonic time in milliseconds for phase deduplication."""
        import time as _time

        return int(_time.monotonic() * 1000)

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
        """Format path based on active profile."""
        profile_name = self._get_profile_name()
        if not profile_name:
            return path

        if "WRITER" in profile_name:
            from pathlib import Path

            return Path(path).name or path

        if "THEME" in profile_name and len(path) > 60:
            parts = path.split("/")
            if len(parts) > 3:
                return f"{parts[0]}/.../{'/'.join(parts[-2:])}"

        return path
