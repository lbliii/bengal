"""
Syntax theme resolution for Bengal's Rosettes integration.

This module handles the mapping from Bengal's site palettes to Rosettes
syntax highlighting themes, implementing the "zero-config" experience
where syntax themes auto-inherit from the site palette.

RFC-0003: Rosettes Theming Architecture

Usage:
    >>> from bengal.rendering.highlighting.theme_resolver import resolve_syntax_theme
    >>> palette_name = resolve_syntax_theme(config)
    >>> # Returns: "bengal-snow-lynx" if site uses snow-lynx palette
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from typing import Any

__all__ = [
    "resolve_syntax_theme",
    "resolve_css_class_style",
    "PALETTE_INHERITANCE",
    "CssClassStyle",
]

# Type alias for CSS class style
CssClassStyle = Literal["semantic", "pygments"]

# Mapping from Bengal site palettes to Rosettes syntax themes.
# When syntax_highlighting.theme is "auto", we look up the site's
# default_palette here to find the matching syntax theme.
PALETTE_INHERITANCE: dict[str, str] = {
    # Default Bengal theme → Bengal Tiger (orange accent, dark)
    "default": "bengal-tiger",
    "": "bengal-tiger",
    # Light themes
    "snow-lynx": "bengal-snow-lynx",
    # Dark themes
    "brown-bengal": "bengal-tiger",
    "silver-bengal": "bengal-charcoal",
    "charcoal-bengal": "bengal-charcoal",
    "blue-bengal": "bengal-blue",
}


def resolve_syntax_theme(config: dict[str, Any]) -> str:
    """
    Resolve which syntax palette to use based on site configuration.
    
    This implements the "auto" theme inheritance from RFC-0003:
    - If theme is "auto", inherit from default_palette
    - Otherwise, use the explicitly specified theme
    
    Args:
        config: Full site configuration dictionary.
    
    Returns:
        Name of the Rosettes syntax palette to use.
    
    Example:
            >>> config = {"theme": {"default_palette": "snow-lynx"}}
            >>> resolve_syntax_theme(config)
            'bengal-snow-lynx'
    
            >>> config = {"theme": {"syntax_highlighting": {"theme": "monokai"}}}
            >>> resolve_syntax_theme(config)
            'monokai'
        
    """
    theme_config = config.get("theme", {})
    syntax_config = theme_config.get("syntax_highlighting", {})

    theme_name = syntax_config.get("theme", "auto")

    if theme_name == "auto":
        # Inherit from site palette
        site_palette = theme_config.get("default_palette", "default")
        return PALETTE_INHERITANCE.get(site_palette, "bengal-tiger")

    return theme_name


def resolve_css_class_style(config: dict[str, Any]) -> CssClassStyle:
    """
    Resolve which CSS class style to use for syntax highlighting.
    
    Args:
        config: Full site configuration dictionary.
    
    Returns:
        Either "semantic" (default) or "pygments".
    
    Example:
            >>> config = {"theme": {"syntax_highlighting": {"css_class_style": "pygments"}}}
            >>> resolve_css_class_style(config)
            'pygments'
        
    """
    theme_config = config.get("theme", {})
    syntax_config = theme_config.get("syntax_highlighting", {})

    style = syntax_config.get("css_class_style", "semantic")

    # Validate the value
    if style not in ("semantic", "pygments"):
        return "semantic"

    return style  # type: ignore[return-value]
