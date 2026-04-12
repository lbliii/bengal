"""
Terminal capability detection utilities.

Provides environment and terminal detection without Rich dependency.
Replaces the Rich-dependent parts of rich_console.py.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Bengal color palette (moved from rich_console.py)
PALETTE = {
    "primary": "#FF9D00",  # Vivid Orange
    "secondary": "#3498DB",  # Bright Blue
    "accent": "#F1C40F",  # Sunflower Yellow
    "success": "#2ECC71",  # Emerald Green
    "error": "#E74C3C",  # Alizarin Crimson
    "warning": "#E67E22",  # Carrot Orange
    "info": "#95A5A6",  # Silver
    "muted": "#7F8C8D",  # Grayish
    "bengal": "#FF9D00",  # For the cat mascot
}


def should_use_emoji() -> bool:
    """Check BENGAL_EMOJI env var. ASCII-first by default."""
    return os.getenv("BENGAL_EMOJI", "").strip() == "1"


def is_interactive_terminal() -> bool:
    """Determine if fancy terminal features should be enabled.

    Returns False in CI, dumb terminals, non-TTY, or when NO_COLOR is set.
    """
    if os.getenv("CI"):
        return False
    if os.getenv("NO_COLOR") is not None:
        return False
    term = os.getenv("TERM", "").lower()
    if term == "dumb":
        return False
    return sys.stdout.isatty()


def detect_environment() -> dict[str, bool | str | int | None]:
    """Detect terminal and environment capabilities without Rich."""
    import multiprocessing

    env: dict[str, bool | str | int | None] = {}

    env["is_terminal"] = sys.stdout.isatty()
    env["color_system"] = "truecolor" if env["is_terminal"] else None

    try:
        size = os.get_terminal_size()
        env["width"] = size.columns
        env["height"] = size.lines
    except OSError:
        env["width"] = 80
        env["height"] = 24

    env["is_ci"] = any(
        [
            os.getenv("CI"),
            os.getenv("CONTINUOUS_INTEGRATION"),
            os.getenv("GITHUB_ACTIONS"),
            os.getenv("GITLAB_CI"),
            os.getenv("CIRCLECI"),
            os.getenv("TRAVIS"),
        ]
    )

    env["is_docker"] = Path("/.dockerenv").exists() or Path("/run/.containerenv").exists()
    env["is_git_repo"] = Path(".git").exists()
    env["cpu_count"] = multiprocessing.cpu_count()
    env["terminal_app"] = os.getenv("TERM_PROGRAM", "") or "unknown"

    return env
