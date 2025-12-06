"""
Template functions for rendering SVG icons.

Provides icon rendering functions for use in Jinja2 templates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from markupsafe import Markup

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site

from bengal.rendering.plugins.directives._icons import ICON_MAP, render_svg_icon


def register(env: Environment, site: Site) -> None:
    """
    Register icon template functions.

    Args:
        env: Jinja2 environment
        site: Site instance (unused but required by signature)
    """
    env.globals["icon"] = icon
    env.globals["render_icon"] = icon  # Alias


def icon(name: str, size: int = 24, css_class: str = "", aria_label: str = "") -> Markup:
    """
    Render an SVG icon for use in templates.

    Uses render_svg_icon() with ICON_MAP mapping for backwards compatibility
    and semantic naming. Falls back to the original name if the mapped name
    doesn't have an SVG file. Returns Markup to prevent Jinja2 auto-escaping.

    Args:
        name: Icon name (e.g., "search", "menu", "close", "arrow-up")
        size: Icon size in pixels (default: 24)
        css_class: Additional CSS classes
        aria_label: Accessibility label (if empty, uses aria-hidden)

    Returns:
        Markup object containing inline SVG HTML, or empty Markup if icon not found

    Example:
        {{ icon("search", size=20) }}
        {{ icon("menu", size=24, css_class="nav-icon") }}
        {{ icon("arrow-up", size=18, aria_label="Back to top") }}
    """
    if not name:
        return Markup("")

    # Map semantic name to Phosphor icon name via ICON_MAP
    mapped_name = ICON_MAP.get(name, name)

    # Try the mapped name first
    svg_html = render_svg_icon(mapped_name, size=size, css_class=css_class, aria_label=aria_label)

    # If mapped name didn't work and it's different from original, try the original
    if not svg_html and mapped_name != name:
        svg_html = render_svg_icon(name, size=size, css_class=css_class, aria_label=aria_label)

    # Return as Markup to prevent Jinja2 auto-escaping
    return Markup(svg_html)
