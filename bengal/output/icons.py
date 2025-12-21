"""
Icon set definitions for CLI output.

Provides ASCII-first icons with optional emoji support. The default icon set
uses ASCII symbols (✓, !, x, etc.) with cat+mouse branding, while an optional
emoji set is available for users who prefer emoji-rich output.

Usage:
    from bengal.output.icons import get_icon_set

    icons = get_icon_set()  # ASCII by default
    print(f"{icons.success} Build complete")  # "✓ Build complete"

    icons = get_icon_set(use_emoji=True)
    print(f"{icons.success} Build complete")  # "✨ Build complete"

Related:
    - bengal/utils/rich_console.py: Console configuration
    - bengal/output/core.py: CLIOutput that consumes icons
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IconSet:
    """
    Icon set for CLI output.

    Provides consistent symbols for status indicators, navigation, and branding.
    Frozen to ensure immutability of icon definitions.

    Attributes:
        mascot: Bengal cat symbol for success headers
        error_mascot: Mouse symbol for error headers
        success: Success/check indicator
        warning: Warning indicator
        error: Error indicator
        info: Info indicator
        tip: Tip/suggestion indicator
        arrow: Navigation arrow
        tree_branch: Tree branch for hierarchical display
        tree_end: Tree end branch
        section: Section header prefix (empty by default for clean headers)
    """

    # Branding
    mascot: str = "ᓚᘏᗢ"  # Bengal cat
    error_mascot: str = "ᘛ⁐̤ᕐᐷ"  # Mouse (for errors)

    # Status indicators
    success: str = "✓"
    warning: str = "!"
    error: str = "x"
    info: str = "-"
    tip: str = "*"

    # Navigation
    arrow: str = "↪"
    tree_branch: str = "├─"
    tree_end: str = "└─"

    # Sections (no emoji by default for clean headers)
    section: str = ""

    # Performance grades
    grade_excellent: str = "++"
    grade_fast: str = "+"
    grade_moderate: str = "~"
    grade_slow: str = "-"


# Default ASCII icon set
ASCII_ICONS = IconSet()

# Emoji icon set for opt-in users
EMOJI_ICONS = IconSet(
    success="✨",
    warning="⚠️",
    error="❌",
    info="ℹ️",
    tip="💡",
    section="📊",
    grade_excellent="🚀",
    grade_fast="⚡",
    grade_moderate="📊",
    grade_slow="🐌",
)


def get_icon_set(use_emoji: bool = False) -> IconSet:
    """
    Get icon set based on preference.

    Args:
        use_emoji: If True, return emoji icon set; otherwise ASCII

    Returns:
        IconSet with appropriate symbols
    """
    return EMOJI_ICONS if use_emoji else ASCII_ICONS
