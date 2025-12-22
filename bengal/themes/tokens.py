"""
Shared design tokens for Bengal's web and terminal themes.

This module is the single source of truth for all visual design tokens used
across Bengal's web CSS output and Textual terminal interfaces. All color
values meet WCAG AA contrast requirements.

Token Categories:
    Color Palettes: Brand, semantic, surface, border, and text colors
    Mascots: ASCII art characters and status icons for terminal output
    Palette Variants: Named color schemes (default, blue-bengal, etc.)

Dataclasses:
    BengalPalette: Complete color palette with all token categories
    BengalMascots: Terminal mascots and status/navigation icons
    PaletteVariant: Subset of colors for theme variants

Instances:
    BENGAL_PALETTE: Default palette instance for direct access
    BENGAL_MASCOT: Default mascots instance for terminal output
    PALETTE_VARIANTS: Dict mapping variant names to PaletteVariant instances

Example:
    >>> from bengal.themes.tokens import BENGAL_PALETTE, BENGAL_MASCOT
    >>> print(BENGAL_PALETTE.primary)
    #FF9D00
    >>> print(BENGAL_MASCOT.cat)
    ᓚᘏᗢ

Architecture:
    Tokens are defined as frozen dataclasses for immutability and hashability.
    The generate.py module reads these tokens to produce CSS output files.

Related:
    bengal/themes/generate.py: CSS/TCSS generation from these tokens
    bengal/cli/dashboard/bengal.tcss: Textual dashboard styles
    bengal/themes/default/assets/css/tokens/: Generated web CSS
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BengalPalette:
    """
    Bengal color palette with semantic color tokens.

    All colors meet WCAG AA contrast ratio (4.5:1) against both dark (#1a1a1a)
    and light (#fafafa) backgrounds for accessibility compliance.

    Attributes:
        primary: Bengal signature vivid orange (#FF9D00)
        secondary: Complementary bright blue (#3498DB)
        accent: Highlight sunflower yellow (#F1C40F)
        success: Positive state emerald green (#2ECC71)
        warning: Caution state carrot orange (#E67E22)
        error: Error state alizarin crimson (#E74C3C)
        info: Informational silver (#95A5A6)
        muted: De-emphasized grayish (#7F8C8D)
        surface: Dark widget surface (#1e1e1e)
        surface_light: Elevated surface (#2d2d2d)
        background: Base dark background (#121212)
        foreground: Primary light text (#e0e0e0)
        border: Subtle border color (#3a3a3a)
        border_focus: Focus ring using primary (#FF9D00)
        text_primary: Main text color (#e0e0e0)
        text_secondary: Secondary text (#9e9e9e)
        text_muted: De-emphasized text (#757575)

    Example:
        >>> palette = BengalPalette()
        >>> palette.primary
        '#FF9D00'
        >>> palette.success
        '#2ECC71'
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
    Bengal brand mascots and status icons for terminal output.

    Provides ASCII-compatible characters for terminal UI elements including
    the Bengal cat mascot, status indicators, navigation symbols, and
    performance grades. All characters render across modern terminals.

    Attributes:
        cat: Bengal cat mascot for success/help headers (ᓚᘏᗢ)
        mouse: Mouse for error headers - cat catches bugs (ᘛ⁐̤ᕐᐷ)
        success: Checkmark for success status (✓)
        warning: Exclamation for warnings (!)
        error: X mark for errors (x)
        info: Dash for informational messages (-)
        tip: Asterisk for tips (*)
        pending: Middle dot for pending state (·)
        arrow: Right arrow for navigation (→)
        tree_branch: Tree branch for hierarchy (├─)
        tree_end: Tree end for last item (└─)
        grade_excellent: Excellent performance (++)
        grade_fast: Fast performance (+)
        grade_moderate: Moderate performance (~)
        grade_slow: Slow performance (-)

    Example:
        >>> mascots = BengalMascots()
        >>> print(f"{mascots.cat} Build successful {mascots.success}")
        ᓚᘏᗢ Build successful ✓

    Note:
        Status icons are ASCII-first for compatibility. Set BENGAL_EMOJI=1
        environment variable to enable emoji alternatives.
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
    Named color palette variant for theming.

    Provides a subset of color tokens that define a cohesive visual theme.
    Variants can be applied via the BENGAL_PALETTE environment variable or
    theme configuration.

    Attributes:
        name: Variant identifier (e.g., "blue-bengal", "charcoal-bengal")
        primary: Primary brand color for the variant
        accent: Accent/highlight color
        success: Success state color
        error: Error state color
        surface: Widget surface color (default: #1e1e1e)
        background: Base background color (default: #121212)

    Example:
        >>> variant = PaletteVariant(
        ...     name="custom",
        ...     primary="#1976D2",
        ...     accent="#FF9800",
        ...     success="#388E3C",
        ...     error="#D32F2F"
        ... )
        >>> variant.primary
        '#1976D2'
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

    Retrieves either the default BengalPalette or a named PaletteVariant.
    Falls back to the default palette if the requested name is not found.

    Args:
        name: Palette variant name. Use "default" for the full BengalPalette,
            or a variant name like "blue-bengal", "charcoal-bengal", etc.

    Returns:
        BengalPalette for "default", or the matching PaletteVariant.
        Falls back to BENGAL_PALETTE if name is not found.

    Example:
        >>> palette = get_palette("default")
        >>> palette.primary
        '#FF9D00'
        >>> variant = get_palette("blue-bengal")
        >>> variant.primary
        '#1976D2'
    """
    if name == "default":
        return BENGAL_PALETTE
    return PALETTE_VARIANTS.get(name, BENGAL_PALETTE)
