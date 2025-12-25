"""Rosettes themes package.

Semantic token system for syntax highlighting with modern CSS support.
Provides palettes, CSS generation, and accessibility validation.

Quick Start:
    >>> from bengal.rendering.rosettes.themes import MONOKAI, get_palette
    >>> palette = get_palette("monokai")

Types:
    - SyntaxRole: Semantic roles for code elements
    - SyntaxPalette: Immutable theme definition
    - AdaptivePalette: Light/dark adaptive theme

Palettes:
    Bengal: BENGAL_TIGER, BENGAL_SNOW_LYNX, BENGAL_CHARCOAL
    Third-party: MONOKAI, DRACULA, GITHUB
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.rosettes.themes._mapping import (
    PYGMENTS_CLASS_MAP,
    ROLE_MAPPING,
    get_role,
)
from bengal.rendering.rosettes.themes._palette import AdaptivePalette, SyntaxPalette
from bengal.rendering.rosettes.themes._roles import SyntaxRole

# Built-in palettes
from bengal.rendering.rosettes.themes.palettes import (
    BENGAL_BLUE,
    BENGAL_CHARCOAL,
    BENGAL_SNOW_LYNX,
    BENGAL_TIGER,
    DRACULA,
    GITHUB,
    GITHUB_DARK,
    GITHUB_LIGHT,
    MONOKAI,
)

if TYPE_CHECKING:
    from typing import Literal

    CssClassStyle = Literal["semantic", "pygments"]

__all__ = [
    # Core types
    "SyntaxRole",
    "SyntaxPalette",
    "AdaptivePalette",
    # Mappings
    "ROLE_MAPPING",
    "PYGMENTS_CLASS_MAP",
    "get_role",
    # Bengal palettes
    "BENGAL_TIGER",
    "BENGAL_SNOW_LYNX",
    "BENGAL_CHARCOAL",
    "BENGAL_BLUE",
    # Third-party palettes
    "MONOKAI",
    "DRACULA",
    "GITHUB",
    "GITHUB_LIGHT",
    "GITHUB_DARK",
    # Registry
    "register_palette",
    "get_palette",
    "list_palettes",
    # Type alias
    "Palette",
]


# Type alias for any palette type
Palette = SyntaxPalette | AdaptivePalette


# Palette registry (populated with built-ins)
_PALETTES: dict[str, Palette] = {}


def _init_registry() -> None:
    """Initialize the palette registry with built-in palettes."""
    global _PALETTES

    # Bengal themes
    _PALETTES["bengal-tiger"] = BENGAL_TIGER
    _PALETTES["bengal-snow-lynx"] = BENGAL_SNOW_LYNX
    _PALETTES["bengal-charcoal"] = BENGAL_CHARCOAL
    _PALETTES["bengal-blue"] = BENGAL_BLUE

    # Third-party themes
    _PALETTES["monokai"] = MONOKAI
    _PALETTES["dracula"] = DRACULA
    _PALETTES["github"] = GITHUB
    _PALETTES["github-light"] = GITHUB_LIGHT
    _PALETTES["github-dark"] = GITHUB_DARK


def register_palette(palette: Palette) -> None:
    """Register a custom palette.

    Args:
        palette: The palette to register.
    """
    _PALETTES[palette.name] = palette


def get_palette(name: str) -> Palette:
    """Get a registered palette by name.

    Args:
        name: The palette name.

    Returns:
        The requested palette.

    Raises:
        KeyError: If the palette is not registered.
    """
    # Lazy init
    if not _PALETTES:
        _init_registry()

    if name not in _PALETTES:
        available = ", ".join(sorted(_PALETTES.keys()))
        raise KeyError(f"Unknown palette: {name!r}. Available: {available}")

    return _PALETTES[name]


def list_palettes() -> list[str]:
    """List all registered palette names.

    Returns:
        Sorted list of palette names.
    """
    # Lazy init
    if not _PALETTES:
        _init_registry()

    return sorted(_PALETTES.keys())
