"""
Admonition directive for Mistune.

Provides note, warning, tip, danger, and other callout boxes with
full markdown support.
"""

from __future__ import annotations

from re import Match
from typing import Any

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

__all__ = ["AdmonitionDirective", "render_admonition"]

logger = get_logger(__name__)


class AdmonitionDirective(DirectivePlugin):
    """
    Admonition directive using Mistune's fenced syntax.

    Syntax:
        :::{note} Optional Title
        Content with **markdown** support.
        :::

    With custom classes:
        :::{note} Optional Title
        :class: holo custom-class
        Content with **markdown** support.
        :::

    Supported types: note, tip, warning, danger, error, info, example, success, caution, seealso
    """

    ADMONITION_TYPES = [
        "note",
        "tip",
        "warning",
        "danger",
        "error",
        "info",
        "example",
        "success",
        "caution",
        "seealso",
    ]

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ADMONITION_TYPES

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
        """Parse admonition directive."""
        admon_type = self.parse_type(m)
        title = self.parse_title(m)
        options = dict(self.parse_options(m))

        # Use type as title if no title provided
        if not title:
            title = admon_type.capitalize()

        content = self.parse_content(m)

        # Parse nested markdown content
        children = self.parse_tokens(block, content, state)

        return {
            "type": "admonition",
            "attrs": {
                "admon_type": admon_type,
                "title": title,
                "extra_class": options.get("class", ""),
            },
            "children": children,
        }

    def __call__(self, directive: Any, md: Any) -> None:
        """Register all admonition types as directives."""
        for admon_type in self.ADMONITION_TYPES:
            directive.register(admon_type, self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("admonition", render_admonition)


def render_admonition(
    renderer: Any, text: str, admon_type: str, title: str, extra_class: str = ""
) -> str:
    """Render admonition to HTML."""
    # Map types to CSS classes
    type_map = {
        "note": "note",
        "tip": "tip",
        "warning": "warning",
        "caution": "warning",
        "danger": "danger",
        "error": "error",
        "info": "info",
        "example": "example",
        "success": "success",
        "seealso": "seealso",
    }

    css_class = type_map.get(admon_type, "note")

    # Add extra classes if provided
    if extra_class:
        css_class = f"{css_class} {extra_class}"

    # Map admonition types to icon names (using Phosphor icons from icons directory)
    # These names must match the actual .svg files in themes/default/assets/icons/
    icon_map = {
        "note": "note",
        "info": "info",
        "tip": "tip",
        "warning": "warning",
        "caution": "caution",
        "danger": "danger",
        "error": "error",
        "success": "success",
        "example": "example",
        "seealso": "info",  # Default to info for seealso
    }

    # Render icon using Phosphor icons
    icon_name = icon_map.get(admon_type, "info")
    from bengal.rendering.plugins.directives._icons import render_svg_icon

    icon_html = render_svg_icon(icon_name, size=20, css_class="admonition-icon")

    # Build title with icon
    if icon_html:
        title_html = f'<span class="admonition-icon-wrapper">{icon_html}</span><span class="admonition-title-text">{title}</span>'
    else:
        title_html = title

    # text contains the rendered children
    html = (
        f'<div class="admonition {css_class}">\n'
        f'  <p class="admonition-title">{title_html}</p>\n'
        f"{text}"
        f"</div>\n"
    )
    return html
