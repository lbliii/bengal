"""
Traceback renderers for different verbosity styles.

This module provides renderer classes for displaying exceptions at
different verbosity levels. Renderers complement the global Rich
traceback installation and can be used for manual exception display.

Renderer Classes
================

**FullTracebackRenderer**
    Uses Rich's full exception rendering with local variables.
    Falls back to standard Python traceback if Rich unavailable.

**CompactTracebackRenderer**
    Shows last 3 stack frames with context-aware help from
    ``bengal.errors.handlers``. Best for development.

**MinimalTracebackRenderer**
    One-line output with error type, location, and hint.
    Best for CI/CD or when many errors are expected.

**OffTracebackRenderer**
    Standard Python traceback via ``traceback.print_exc()``.
    For compatibility or when Rich is not desired.

Usage
=====

Get a renderer from config::

    from bengal.errors.traceback import TracebackConfig

    config = TracebackConfig.from_environment()
    renderer = config.get_renderer()
    renderer.display_exception(error)

Direct instantiation::

    from bengal.errors.traceback import CompactTracebackRenderer, TracebackConfig

    config = TracebackConfig(style=TracebackStyle.COMPACT)
    renderer = CompactTracebackRenderer(config)
    renderer.display_exception(error)

See Also
========

- ``bengal/errors/handlers.py`` - Context-aware help for compact/minimal
- ``bengal/output/`` - CLIOutput used for styled output
"""

from __future__ import annotations

import traceback as _traceback
from dataclasses import dataclass
from typing import Any

from bengal.errors.handlers import get_context_aware_help
from bengal.output import CLIOutput
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TracebackRenderer:
    """
    Base class for traceback renderers.

    Subclasses implement ``display_exception()`` to render exceptions
    at different verbosity levels.

    Attributes:
        config: TracebackConfig controlling rendering behavior.
    """

    config: Any

    def display_exception(self, error: BaseException) -> None:  # pragma: no cover - interface
        """
        Display an exception to the user.

        Args:
            error: The exception to display.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError


class FullTracebackRenderer(TracebackRenderer):
    """
    Full traceback renderer with local variables.

    Uses Rich's ``print_exception()`` with ``show_locals=True`` for
    complete debugging information. Falls back to standard Python
    traceback if Rich is unavailable.
    """

    def display_exception(self, error: BaseException) -> None:
        # Prefer Rich pretty exception if available and active
        try:
            from bengal.utils.rich_console import get_console, should_use_rich

            if should_use_rich():
                console = get_console()
                console.print_exception(show_locals=True, width=None)
                return
        except Exception as e:
            logger.debug(
                "traceback_renderer_rich_display_failed",
                error=str(e),
                error_type=type(e).__name__,
                action="falling_back_to_standard",
            )
            pass

        # Fallback to standard Python
        _traceback.print_exc()


class CompactTracebackRenderer(TracebackRenderer):
    """
    Compact traceback renderer with context-aware help.

    Shows the last 3 stack frames focused on user code, plus
    context-aware help from ``bengal.errors.handlers``. This is
    the default style, balancing detail with readability.

    Output includes:
    - Error type and message
    - Last 3 frames with file:line and function name
    - Context-aware suggestions (if available)
    """

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
    """
    Minimal one-line traceback renderer.

    Shows only the error type, location (last frame), and message
    on a single line, plus a one-line hint if available.

    Best for CI/CD output or situations where many errors are
    expected and a compact summary is preferred.
    """

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
    """
    Standard Python traceback renderer.

    Uses ``traceback.print_exc()`` for default Python formatting.
    Useful when Rich styling is not desired or for maximum
    compatibility with existing tools and log parsers.
    """

    def display_exception(self, error: BaseException) -> None:
        # Respect standard Python formatting
        _traceback.print_exc()
