"""Built-in palettes for Rosettes.

Provides a collection of carefully designed syntax highlighting palettes
with WCAG AA contrast validation.

All palettes are lazy-loaded on first access for fast import times.

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

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rosettes.themes._palette import AdaptivePalette, SyntaxPalette

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

# Lazy loading registry: name -> (module, attribute)
_PALETTE_SPECS: dict[str, tuple[str, str]] = {
    # Dark themes
    "MONOKAI": ("rosettes.themes.palettes.monokai", "MONOKAI"),
    "DRACULA": ("rosettes.themes.palettes.dracula", "DRACULA"),
    "ONE_DARK": ("rosettes.themes.palettes.one_dark", "ONE_DARK"),
    # Adaptive themes
    "GITHUB": ("rosettes.themes.palettes.github", "GITHUB"),
    "CATPPUCCIN": ("rosettes.themes.palettes.catppuccin", "CATPPUCCIN"),
    "NORD": ("rosettes.themes.palettes.nord", "NORD"),
    # Bengal themes
    "BENGAL_TIGER": ("rosettes.themes.palettes.bengal", "BENGAL_TIGER"),
    "BENGAL_SNOW_LYNX": ("rosettes.themes.palettes.bengal", "BENGAL_SNOW_LYNX"),
    "BENGAL_CHARCOAL": ("rosettes.themes.palettes.bengal", "BENGAL_CHARCOAL"),
    # Terminal palettes
    "TERMINAL_MONOKAI": ("rosettes.themes.palettes.monokai", "TERMINAL_MONOKAI"),
}

# Cache for loaded palettes
_loaded: dict[str, SyntaxPalette | AdaptivePalette] = {}


def __getattr__(name: str) -> SyntaxPalette | AdaptivePalette:
    """Lazy-load palettes on first access."""
    if name in _PALETTE_SPECS:
        if name not in _loaded:
            from importlib import import_module

            module_path, attr_name = _PALETTE_SPECS[name]
            module = import_module(module_path)
            _loaded[name] = getattr(module, attr_name)
        return _loaded[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """List available attributes for tab completion."""
    return list(__all__)
