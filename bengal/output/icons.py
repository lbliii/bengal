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


@dataclass(frozen=True, slots=True)
class IconSet:
    """
    Icon set for CLI output.

    Provides consistent symbols for status indicators, navigation, and branding.
    Frozen to ensure immutability of icon definitions.

    Attributes:
        mascot: Bengal cat symbol for success headers
        error_mascot: Mouse symbol for error headers
        rosettes: Rosettes syntax highlighter logo (spots pattern)
        kida: Kida template engine logo (face + whiskers)
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
    rosettes: str = "⌾⌾⌾"  # Rosettes syntax highlighter (spots)
    kida: str = ")彡"  # Kida template engine (face + whiskers)

    # Status indicators
    success: str = "✓"
    warning: str = "▲"
    error: str = "✗"
    info: str = "·"
    tip: str = "→"

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


#: Default icon set using ASCII symbols. Provides clean, universally-supported
#: output across all terminals. This is Bengal's default choice.
ASCII_ICONS = IconSet()

PLAIN_ASCII_ICONS = IconSet(
    mascot="Bengal",
    error_mascot="!",
    rosettes="***",
    kida="Kida",
    success="v",
    warning="!",
    error="x",
    info=".",
    tip=">",
    arrow=">",
    tree_branch="+-",
    tree_end="`-",
)

#: Emoji icon set for users who prefer richer visual output.
#: Enabled via BENGAL_EMOJI=1 environment variable.
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


def get_icon_set(use_emoji: bool = False, plain_ascii: bool = False) -> IconSet:
    """
    Get icon set based on user preference.

    Returns the appropriate IconSet instance based on the emoji preference.
    The default is ASCII icons for maximum terminal compatibility.

    Args:
        use_emoji: If True, returns EMOJI_ICONS with rich visual symbols.
            If False (default), returns ASCII_ICONS with simple text symbols.

    Returns:
        The IconSet instance matching the preference (ASCII or Emoji).

    Example:
            >>> icons = get_icon_set()
            >>> print(f"{icons.success} Done")  # "✓ Done"

            >>> icons = get_icon_set(use_emoji=True)
            >>> print(f"{icons.success} Done")  # "✨ Done"

    """
    if plain_ascii:
        return PLAIN_ASCII_ICONS
    return EMOJI_ICONS if use_emoji else ASCII_ICONS
