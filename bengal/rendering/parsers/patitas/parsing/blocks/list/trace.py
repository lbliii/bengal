"""Debug tracing for list parsing.

Enable via PATITAS_DEBUG=list environment variable or programmatically.

Usage:
    # Enable tracing
    from bengal.rendering.parsers.patitas.parsing.blocks.list.trace import enable_trace
    enable_trace()

    # In list parsing code:
    from .trace import trace
    trace("handle_blank_line", token=tok.value, indent=check_indent, result="EndItem")
"""

from __future__ import annotations

import os
from typing import Any

# Global enable flag - check env var once at import time
_ENABLED = os.environ.get("PATITAS_DEBUG", "").lower() in ("list", "all", "1", "true")
_INDENT_LEVEL = 0


def enable_trace() -> None:
    """Enable list parsing tracing programmatically."""
    global _ENABLED
    _ENABLED = True


def disable_trace() -> None:
    """Disable list parsing tracing."""
    global _ENABLED
    _ENABLED = False


def is_trace_enabled() -> bool:
    """Check if tracing is enabled."""
    return _ENABLED


def trace(event: str, **kwargs: Any) -> None:
    """Log a trace event if tracing is enabled.
    
    Args:
        event: Event name (e.g., "parse_list", "handle_blank_line")
        **kwargs: Key-value pairs to include in trace output
        
    """
    if not _ENABLED:
        return

    indent = "  " * _INDENT_LEVEL
    parts = [f"{indent}[{event}]"]
    for key, value in kwargs.items():
        if isinstance(value, str) and len(value) > 40:
            value = repr(value[:40] + "...")
        else:
            value = repr(value)
        parts.append(f"{key}={value}")

    print(" ".join(parts))


class trace_scope:
    """Context manager for indented trace scopes.
    
    Usage:
        with trace_scope("parse_list_item", marker="1."):
            # traces within here will be indented
            trace("found_content", line="foo")
        
    """

    def __init__(self, event: str, **kwargs: Any):
        self.event = event
        self.kwargs = kwargs

    def __enter__(self) -> trace_scope:
        global _INDENT_LEVEL
        trace(f"{self.event} START", **self.kwargs)
        _INDENT_LEVEL += 1
        return self

    def __exit__(self, *args: Any) -> None:
        global _INDENT_LEVEL
        _INDENT_LEVEL -= 1
        trace(f"{self.event} END")


def trace_decision(
    event: str,
    condition: str,
    result: bool,
    **context: Any,
) -> None:
    """Trace a decision point with its inputs and outcome.
    
    Args:
        event: Decision event name
        condition: The condition being evaluated (as string)
        result: The boolean result
        **context: Additional context values
        
    """
    if not _ENABLED:
        return

    symbol = "✓" if result else "✗"
    trace(event, condition=condition, result=f"{symbol} {result}", **context)
