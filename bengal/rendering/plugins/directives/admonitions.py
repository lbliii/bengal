"""
Admonition directive for Mistune.

Provides note, warning, tip, danger, and other callout boxes with
full markdown support.

Architecture:
    Migrated to BengalDirective base class as part of directive system v2.
    Uses multi-name registration pattern for 10 admonition types.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.rendering.plugins.directives.base import BengalDirective
from bengal.rendering.plugins.directives.options import DirectiveOptions
from bengal.rendering.plugins.directives.tokens import DirectiveToken

__all__ = ["AdmonitionDirective", "AdmonitionOptions"]


# All supported admonition types
ADMONITION_TYPES = frozenset(
    [
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
)

# Map types to CSS classes (caution maps to warning)
TYPE_TO_CSS = {
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

# Map types to icon names
TYPE_TO_ICON = {
    "note": "note",
    "info": "info",
    "tip": "tip",
    "warning": "warning",
    "caution": "caution",
    "danger": "danger",
    "error": "error",
    "success": "success",
    "example": "example",
    "seealso": "info",
}


@dataclass
class AdmonitionOptions(DirectiveOptions):
    """
    Options for admonition directive.

    Attributes:
        css_class: Additional CSS classes

    Example:
        :::{note} Title
        :class: holo custom-class
        Content
        :::
    """

    css_class: str = ""

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


class AdmonitionDirective(BengalDirective):
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

    Supported types: note, tip, warning, danger, error, info,
                    example, success, caution, seealso
    """

    # All admonition types registered as names
    NAMES: ClassVar[list[str]] = list(ADMONITION_TYPES)
    TOKEN_TYPE: ClassVar[str] = "admonition"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = AdmonitionOptions

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = list(ADMONITION_TYPES)
    ADMONITION_TYPES: ClassVar[list[str]] = list(ADMONITION_TYPES)

    def parse_directive(
        self,
        title: str,
        options: AdmonitionOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """
        Build admonition token from parsed components.

        Note: The admonition type comes from parse_type(), which is called
        in the base class parse() method. We need to access it from the match.
        """
        # The admon_type is captured by the base class but we need to get it
        # This is a limitation of the current base class design
        # We'll store it during parse() and retrieve it here
        admon_type = getattr(self, "_current_admon_type", "note")

        # Use type as title if no title provided
        display_title = title if title else admon_type.capitalize()

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "admon_type": admon_type,
                "title": display_title,
                "extra_class": options.css_class,
            },
            children=children,
        )

    def parse(self, block: Any, m: Any, state: Any) -> dict[str, Any]:
        """
        Override parse to capture admonition type before calling parent.

        The admonition type (note, tip, warning, etc.) comes from parse_type().
        """
        # Capture the admonition type
        self._current_admon_type = self.parse_type(m)

        # Call parent parse which handles options, content, children
        return super().parse(block, m, state)

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render admonition to HTML."""
        admon_type = attrs.get("admon_type", "note")
        title = attrs.get("title", admon_type.capitalize())
        extra_class = attrs.get("extra_class", "")

        # Get CSS class for type
        css_class = TYPE_TO_CSS.get(admon_type, "note")
        if extra_class:
            css_class = f"{css_class} {extra_class}"

        # Render icon
        icon_name = TYPE_TO_ICON.get(admon_type, "info")
        icon_html = _render_admonition_icon(icon_name)

        # Build title with icon
        if icon_html:
            title_html = (
                f'<span class="admonition-icon-wrapper">{icon_html}</span>'
                f'<span class="admonition-title-text">{self.escape_html(title)}</span>'
            )
        else:
            title_html = self.escape_html(title)

        return (
            f'<div class="admonition {css_class}">\n'
            f'  <p class="admonition-title">{title_html}</p>\n'
            f"{text}"
            f"</div>\n"
        )


def _render_admonition_icon(icon_name: str) -> str:
    """Render admonition icon using Phosphor icons."""
    from bengal.rendering.plugins.directives._icons import render_svg_icon

    return render_svg_icon(icon_name, size=20, css_class="admonition-icon")


# Backward compatibility
def render_admonition(
    renderer: Any, text: str, admon_type: str, title: str, extra_class: str = ""
) -> str:
    """Legacy render function for backward compatibility."""
    return AdmonitionDirective().render(
        renderer, text, admon_type=admon_type, title=title, extra_class=extra_class
    )
