"""
Terminal capability detection and environment utilities.

This module previously provided a Rich console wrapper. It now delegates
to bengal.utils.observability.terminal for all functionality.

All public names are re-exported for backward compatibility.
"""

from __future__ import annotations

from bengal.utils.observability.terminal import (
    PALETTE,
    detect_environment,
    is_interactive_terminal,
    should_use_emoji,
)

# Backward-compatible aliases
should_use_rich = is_interactive_terminal

# Stub theme dict for code that referenced bengal_theme
bengal_theme = {
    "info": PALETTE["info"],
    "success": PALETTE["success"],
    "warning": PALETTE["warning"],
    "error": PALETTE["error"],
    "highlight": PALETTE["accent"],
    "bengal": PALETTE["bengal"],
    "header": PALETTE["primary"],
    "path": PALETTE["secondary"],
}


def get_console() -> None:
    """Deprecated — Rich console is no longer used. Returns None."""


def reset_console() -> None:
    """No-op — Rich console is no longer used."""


def is_live_display_active() -> bool:
    """Always returns False — Rich Live is no longer used."""
    return False


__all__ = [
    "PALETTE",
    "bengal_theme",
    "detect_environment",
    "get_console",
    "is_live_display_active",
    "reset_console",
    "should_use_emoji",
    "should_use_rich",
]
