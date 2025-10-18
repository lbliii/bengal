"""
Rich console wrapper with profile-aware output.

Provides a singleton console instance that respects:
- Build profiles (Writer/Theme-Dev/Developer)
- Terminal capabilities
- CI/CD environments
"""

import os

from rich.console import Console
from rich.theme import Theme

# Bengal color palette
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

# Bengal theme
bengal_theme = Theme(
    {
        "info": PALETTE["info"],
        "success": PALETTE["success"],
        "warning": PALETTE["warning"],
        "error": f"{PALETTE['error']} bold",
        "highlight": f"{PALETTE['accent']} bold",
        "dim": "dim",
        "bengal": f"{PALETTE['bengal']} bold",
        # Semantic styles
        "header": f"{PALETTE['primary']} bold",
        "phase": "bold",
        "path": f"{PALETTE['secondary']}",
        "metric_label": f"{PALETTE['accent']} bold",
        "metric_value": "default",
        "link": f"underline {PALETTE['secondary']}",
        "prompt": f"{PALETTE['accent']}",  # Yellow for prompts
        "mouse": f"{PALETTE['error']}",  # Red for mice (errors)
    }
)

_console: Console | None = None


def get_console() -> Console:
    """
    Get singleton rich console instance.

    Returns:
        Configured Console instance
    """
    global _console

    if _console is None:
        # Detect environment
        force_terminal = None
        no_color = os.getenv("NO_COLOR") is not None
        ci_mode = os.getenv("CI") is not None

        if ci_mode:
            # In CI, force simple output
            force_terminal = False

        _console = Console(
            theme=bengal_theme,
            force_terminal=force_terminal,
            no_color=no_color,
            highlight=True,
            emoji=True,  # Support emoji on all platforms
        )

    return _console


def should_use_rich() -> bool:
    """
    Determine if we should use rich features.

    Returns:
        True if rich features should be enabled
    """
    console = get_console()

    # Disable in CI environments
    if os.getenv("CI"):
        return False

    # TERM=dumb should disable rich (test expectation)
    term = os.getenv("TERM", "").lower()
    if term == "dumb":
        return False

    # Disable if no terminal
    return console.is_terminal


def detect_environment() -> dict:
    """
    Detect terminal and environment capabilities.

    Returns:
        Dictionary with environment info
    """
    env = {}

    # Terminal info
    console = get_console()
    env["is_terminal"] = console.is_terminal
    env["color_system"] = console.color_system
    env["width"] = console.width
    env["height"] = console.height

    # CI detection
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

    # Docker detection
    env["is_docker"] = os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")

    # Git detection
    env["is_git_repo"] = os.path.exists(".git")

    # CPU cores (for parallel suggestions)
    import multiprocessing

    env["cpu_count"] = multiprocessing.cpu_count()

    # Terminal emulator detection
    term_program = os.getenv("TERM_PROGRAM", "")
    env["terminal_app"] = term_program or "unknown"

    return env


def reset_console():
    """Reset the console singleton (mainly for testing)."""
    global _console
    _console = None


def is_live_display_active():
    """
    Check if a Live display is currently active on the console.

    This function accesses the private `_live` attribute using `getattr()`
    to safely handle cases where it might not exist, with a fallback that
    assumes no Live display is active if an exception occurs.

    Returns:
        True if a Live display is currently active, False otherwise

    Note:
        Tested against Rich >= 13.7.0 (as specified in pyproject.toml).
        Uses the private _live attribute since Rich does not provide a public API
        for detecting active Live displays. The getattr() call provides safe access
        with a sensible default value (None).
    """
    console = get_console()

    # Primary approach: Try to detect using the public API
    # If console has a _live attribute and it's not None, a Live display is active
    # We check this carefully to maintain forward compatibility
    try:
        # Check if _live attribute exists and is not None
        # This is the most reliable way to detect an active Live display
        return getattr(console, "_live", None) is not None
    except Exception:
        # Fallback: assume no live display if we can't determine
        return False
