"""
Traceback renderers for different verbosity styles.

These are used to display exceptions in a consistent, configurable way
across commands, complementing the global Rich traceback installation.
"""

from __future__ import annotations

import traceback as _traceback
from dataclasses import dataclass
from typing import Any

from bengal.utils.cli_output import CLIOutput
from bengal.utils.error_handlers import get_context_aware_help


@dataclass
class TracebackRenderer:
    config: Any

    def display_exception(self, error: BaseException) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class FullTracebackRenderer(TracebackRenderer):
    def display_exception(self, error: BaseException) -> None:
        # Prefer Rich pretty exception if available and active
        try:
            from bengal.utils.rich_console import get_console, should_use_rich

            if should_use_rich():
                console = get_console()
                console.print_exception(show_locals=True, width=None)
                return
        except Exception:
            pass

        # Fallback to standard Python
        _traceback.print_exc()


class CompactTracebackRenderer(TracebackRenderer):
    def display_exception(self, error: BaseException) -> None:
        # Show a concise summary with last few frames (user code focus)
        cli = CLIOutput()
        tb = error.__traceback__
        frames = _traceback.extract_tb(tb)
        summary_lines: list[str] = []

        # Keep last up to 3 frames
        for frame in frames[-3:]:
            summary_lines.append(f"{frame.filename}:{frame.lineno} in {frame.name}")

        cli.blank()
        cli.error(f"{type(error).__name__}: {error}")
        if summary_lines:
            cli.info("Trace (most recent calls):")
            for line in summary_lines:
                cli.info(f"  • {line}")

        # Context-aware help
        help_info = get_context_aware_help(error)
        if help_info and help_info.lines:
            cli.blank()
            cli.tip(help_info.title)
            for line in help_info.lines:
                cli.info(line)


class MinimalTracebackRenderer(TracebackRenderer):
    def display_exception(self, error: BaseException) -> None:
        # Only show type, message, and error location (last frame)
        cli = CLIOutput()
        tb = error.__traceback__
        last = _traceback.extract_tb(tb)[-1] if tb else None
        location = f" at {last.filename}:{last.lineno}" if last else ""
        cli.error(f"{type(error).__name__}{location} - {error}")
        # One-line hint if available
        help_info = get_context_aware_help(error)
        if help_info and help_info.lines:
            cli.info(f"Hint: {help_info.lines[0]}")


class OffTracebackRenderer(TracebackRenderer):
    def display_exception(self, error: BaseException) -> None:
        # Respect standard Python formatting
        _traceback.print_exc()
