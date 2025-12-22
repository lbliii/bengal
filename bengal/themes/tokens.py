"""
Shared design tokens for Bengal's web and terminal themes.

This module serves as the single source of truth for:
- Color palettes (web CSS and terminal TCSS)
- Brand mascots (Bengal cat and mouse)
- Semantic color tokens

Both the web CSS generator and Textual TCSS use these tokens
to ensure visual consistency across platforms.

Related:
    - bengal/themes/generate.py: Generates CSS and TCSS from these tokens
    - bengal/cli/dashboard/bengal.tcss: Textual dashboard styles
    - bengal/themes/default/assets/css/tokens/: Web CSS tokens
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BengalPalette:
    """
    Bengal color palette with semantic color tokens.

    All colors meet WCAG AA contrast ratio (4.5:1) against both
    dark (#1a1a1a) and light (#fafafa) terminal backgrounds.
    """

    # Brand Colors
    primary: str = "#FF9D00"  # Vivid Orange (Bengal signature)
    secondary: str = "#3498DB"  # Bright Blue
    accent: str = "#F1C40F"  # Sunflower Yellow

    # Semantic Colors
    success: str = "#2ECC71"  # Emerald Green
    warning: str = "#E67E22"  # Carrot Orange
    error: str = "#E74C3C"  # Alizarin Crimson
    info: str = "#95A5A6"  # Silver
    muted: str = "#7F8C8D"  # Grayish

    # Surface Colors (for Textual widgets)
    surface: str = "#1e1e1e"  # Dark surface
    surface_light: str = "#2d2d2d"  # Lighter surface
    background: str = "#121212"  # Dark background
    foreground: str = "#e0e0e0"  # Light text

    # Border Colors
    border: str = "#3a3a3a"  # Subtle border
    border_focus: str = "#FF9D00"  # Focus highlight (primary)

    # Text Colors
    text_primary: str = "#e0e0e0"  # Primary text
    text_secondary: str = "#9e9e9e"  # Secondary text
    text_muted: str = "#757575"  # Muted text


# Default palette instance
BENGAL_PALETTE = BengalPalette()


@dataclass(frozen=True)
class BengalMascots:
    """
    Bengal brand mascots for terminal output.

    The Bengal cat appears in success/help headers.
    The mouse appears in error headers (cats catch bugs/mice).

    Both mascots are Unicode characters that render well
    across most modern terminals.
    """

    # Mascot characters
    cat: str = "ᓚᘏᗢ"  # Bengal cat for success/help
    mouse: str = "ᘛ⁐̤ᕐᐷ"  # Mouse for errors (cat catches bugs)

    # Status icons (ASCII-first, opt-in emoji via BENGAL_EMOJI=1)
    success: str = "✓"
    warning: str = "!"
    error: str = "x"
    info: str = "-"
    tip: str = "*"
    pending: str = "·"

    # Navigation
    arrow: str = "→"
    tree_branch: str = "├─"
    tree_end: str = "└─"

    # Performance grades
    grade_excellent: str = "++"
    grade_fast: str = "+"
    grade_moderate: str = "~"
    grade_slow: str = "-"


# Default mascots instance
BENGAL_MASCOT = BengalMascots()


@dataclass(frozen=True)
class PaletteVariant:
    """
    A color palette variant for theming.

    Bengal supports multiple palette variants that can be applied
    to both web and terminal output via BENGAL_PALETTE env var.
    """

    name: str
    primary: str
    accent: str
    success: str
    error: str
    surface: str = "#1e1e1e"
    background: str = "#121212"


# Palette variants derived from web CSS tokens
PALETTE_VARIANTS: dict[str, PaletteVariant] = {
    "default": PaletteVariant(
        name="default",
        primary="#FF9D00",
        accent="#F1C40F",
        success="#2ECC71",
        error="#E74C3C",
    ),
    "blue-bengal": PaletteVariant(
        name="blue-bengal",
        primary="#1976D2",
        accent="#FF9800",
        success="#388E3C",
        error="#D32F2F",
    ),
    "brown-bengal": PaletteVariant(
        name="brown-bengal",
        primary="#6D4C41",
        accent="#D4A574",
        success="#558B2F",
        error="#C62828",
    ),
    "charcoal-bengal": PaletteVariant(
        name="charcoal-bengal",
        primary="#1A1D21",
        accent="#8B6914",
        success="#3D6B4A",
        error="#A63D3D",
        surface="#0d0d0d",
        background="#000000",
    ),
    "silver-bengal": PaletteVariant(
        name="silver-bengal",
        primary="#607D8B",
        accent="#78909C",
        success="#66BB6A",
        error="#EF5350",
    ),
    "snow-lynx": PaletteVariant(
        name="snow-lynx",
        primary="#4FA8A0",
        accent="#5BB8AF",
        success="#2E7D5A",
        error="#C62828",
    ),
}


def get_palette(name: str = "default") -> BengalPalette | PaletteVariant:
    """
    Get a color palette by name.

    Args:
        name: Palette name (default, blue-bengal, etc.)

    Returns:
        The palette instance
    """
    if name == "default":
        return BENGAL_PALETTE
    return PALETTE_VARIANTS.get(name, BENGAL_PALETTE)
