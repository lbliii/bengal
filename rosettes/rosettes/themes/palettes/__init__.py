"""Built-in palettes for Rosettes.

Provides a collection of carefully designed syntax highlighting palettes
with WCAG AA contrast validation.

Available Palettes:
    Dark Themes:
        - MONOKAI: Classic Monokai (warm, vibrant)
        - DRACULA: Dracula theme (purple accents)
        - ONE_DARK: Atom One Dark (balanced)

    Adaptive Themes (light/dark):
        - GITHUB: GitHub's syntax theme
        - CATPPUCCIN: Catppuccin (Latte/Mocha)
        - NORD: Nord (frost colors)

    Bengal Brand Themes:
        - BENGAL_TIGER: Bengal brand (orange accent)
        - BENGAL_SNOW_LYNX: Light Bengal variant
        - BENGAL_CHARCOAL: Minimal dark variant

Terminal Palettes:
    - TERMINAL_MONOKAI
    - TERMINAL_DRACULA
"""

from rosettes.themes.palettes.bengal import (
    BENGAL_CHARCOAL,
    BENGAL_SNOW_LYNX,
    BENGAL_TIGER,
)
from rosettes.themes.palettes.catppuccin import CATPPUCCIN
from rosettes.themes.palettes.dracula import DRACULA
from rosettes.themes.palettes.github import GITHUB
from rosettes.themes.palettes.monokai import MONOKAI, TERMINAL_MONOKAI
from rosettes.themes.palettes.nord import NORD
from rosettes.themes.palettes.one_dark import ONE_DARK

__all__ = [
    # Dark themes
    "MONOKAI",
    "DRACULA",
    "ONE_DARK",
    # Adaptive themes
    "GITHUB",
    "CATPPUCCIN",
    "NORD",
    # Bengal themes
    "BENGAL_TIGER",
    "BENGAL_SNOW_LYNX",
    "BENGAL_CHARCOAL",
    # Terminal palettes
    "TERMINAL_MONOKAI",
]
