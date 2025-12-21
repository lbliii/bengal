"""
Dropdown directive for Mistune.

Provides collapsible sections with markdown support including
nested directives and code blocks.

Architecture:
    Uses typed DropdownOptions and encapsulated render method.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken
from bengal.utils.logger import get_logger

__all__ = ["DropdownDirective", "DropdownOptions"]

logger = get_logger(__name__)

# Valid color variants (match CSS classes in dropdowns.css)
DROPDOWN_COLORS = frozenset(["success", "warning", "danger", "info", "minimal"])


@dataclass
class DropdownOptions(DirectiveOptions):
    """
    Options for dropdown directive.

    Attributes:
        open: Whether dropdown is initially open (expanded)
        icon: Icon name to display next to the title
        badge: Badge text (e.g., "New", "Advanced", "Beta")
        color: Color variant (success, warning, danger, info, minimal)
        description: Secondary text below the title to elaborate on the dropdown content
        css_class: Additional CSS classes for the container

    Example:
        :::{dropdown} My Title
        :open: true
        :icon: info
        :badge: Advanced
        :color: info
        :description: Additional context about what's inside this dropdown
        :class: my-custom-class

        Content here
        :::
    """

    open: bool = False
    icon: str = ""
    badge: str = ""
    color: str = ""
    description: str = ""
    css_class: str = ""

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


class DropdownDirective(BengalDirective):
    """
    Collapsible dropdown directive with markdown support.

    Syntax:
        :::{dropdown} Title
        :open: true
        :icon: info
        :badge: Advanced
        :color: info
        :description: Brief explanation of the dropdown content
        :class: custom-class

        Content with **markdown**, code blocks, etc.

        :::{note}
        Even nested admonitions work!
        :::
        :::

    Or using the HTML5 semantic alias:
        :::{details} Summary Text
        Content
        :::

    Aliases:
        - dropdown: Primary name
        - details: HTML5 semantic alias (renders as <details>)

    Options:
        :open: true/false - Whether initially expanded (default: false)
        :icon: string - Icon name to display next to title
        :badge: string - Badge text (e.g., "New", "Advanced")
        :color: string - Color variant (success, warning, danger, info, minimal)
        :description: string - Secondary text to elaborate on dropdown content
        :class: string - Additional CSS classes
    """

    # Directive names to register
    NAMES: ClassVar[list[str]] = ["dropdown", "details"]

    # Token type for AST
    TOKEN_TYPE: ClassVar[str] = "dropdown"

    # Typed options class
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = DropdownOptions

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["dropdown", "details"]

    def parse_directive(
        self,
        title: str,
        options: DropdownOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """
        Build dropdown token from parsed components.

        Args:
            title: Dropdown title (text after directive name)
            options: Typed dropdown options
            content: Raw content string (unused, children are already parsed)
            children: Parsed nested content tokens
            state: Parser state

        Returns:
            DirectiveToken for the dropdown
        """
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "title": title or "Details",
                "open": options.open,
                "icon": options.icon,
                "badge": options.badge,
                "color": options.color,
                "description": options.description,
                "css_class": options.css_class,
            },
            children=children,
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render dropdown to HTML.

        Renders as HTML5 <details>/<summary> elements for native
        collapsible behavior without JavaScript.

        Args:
            renderer: Mistune renderer instance
            text: Pre-rendered children HTML
            **attrs: Token attributes (title, open, icon, badge, color, css_class)

        Returns:
            HTML string
        """
        title = attrs.get("title", "Details")
        is_open = attrs.get("open", False)
        icon = attrs.get("icon", "")
        badge = attrs.get("badge", "")
        color = attrs.get("color", "")
        description = attrs.get("description", "")
        css_class = attrs.get("css_class", "")

        # Add color variant to class string if valid, warn if invalid
        if color:
            if color in DROPDOWN_COLORS:
                css_class = f"{color} {css_class}".strip() if css_class else color
            else:
                logger.warning(
                    "dropdown_invalid_color",
                    color=color,
                    title=title,
                    valid_colors=list(DROPDOWN_COLORS),
                )

        # Build class string
        class_str = self.build_class_string("dropdown", css_class)

        # Build summary content with optional icon, description, and badge
        summary_parts = []

        # Add icon if specified
        if icon:
            icon_html = _render_dropdown_icon(icon, title)
            if icon_html:
                summary_parts.append(f'<span class="dropdown-icon">{icon_html}</span>')

        # Build title block (title + optional description)
        title_block = f'<span class="dropdown-title">{self.escape_html(title)}</span>'
        if description:
            title_block += (
                f'<span class="dropdown-description">{self.escape_html(description)}</span>'
            )
        summary_parts.append(f'<span class="dropdown-header">{title_block}</span>')

        # Add badge if specified
        if badge:
            summary_parts.append(f'<span class="dropdown-badge">{self.escape_html(badge)}</span>')

        summary_content = "".join(summary_parts)

        return (
            f'<details class="{class_str}"{self.bool_attr("open", is_open)}>\n'
            f"  <summary>{summary_content}</summary>\n"
            f'  <div class="dropdown-content">\n'
            f"{text}"
            f"  </div>\n"
            f"</details>\n"
        )


def _render_dropdown_icon(icon_name: str, dropdown_title: str = "") -> str:
    """
    Render dropdown icon using shared icon utilities.

    Args:
        icon_name: Name of the icon to render
        dropdown_title: Title of the dropdown (for warning context)

    Returns:
        SVG HTML string, or empty string if icon not found
    """
    from bengal.directives._icons import (
        ICON_MAP,
        render_svg_icon,
        warn_missing_icon,
    )

    # Map semantic name to actual icon name (e.g., "alert" -> "warning")
    mapped_icon_name = ICON_MAP.get(icon_name, icon_name)
    icon_html = render_svg_icon(mapped_icon_name, size=18, css_class="dropdown-summary-icon")

    if not icon_html:
        warn_missing_icon(icon_name, directive="dropdown", context=dropdown_title)

    return icon_html
