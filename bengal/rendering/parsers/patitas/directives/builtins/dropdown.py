"""Dropdown directive for collapsible content.

Provides collapsible sections with markdown support including
nested directives and code blocks.

Options:
:open: Start expanded (default: false)
:icon: Icon name to display next to the title
:badge: Badge text (e.g., "New", "Advanced", "Beta")
:color: Color variant (success, warning, danger, info, minimal)
:description: Secondary text below the title
:class: Additional CSS classes

Example:
:::{dropdown} Click to expand
:open:
:icon: info
:badge: New
:color: info
:description: Additional context about this content

Hidden content here with **markdown** support.
:::

Thread Safety:
Stateless handler. Safe for concurrent use across threads.

HTML Output:
Matches Bengal's dropdown directive exactly:
<details class="dropdown [color] [class]" [open]>
  <summary>
    <span class="dropdown-icon">{SVG}</span>
    <span class="dropdown-header">
      <span class="dropdown-title">Title</span>
      <span class="dropdown-description">Description</span>
    </span>
    <span class="dropdown-badge">Badge</span>
  </summary>
  <div class="dropdown-content">
    {content}
  </div>
</details>

"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from bengal.rendering.parsers.patitas.directives.contracts import (
    DROPDOWN_CONTRACT,
    DirectiveContract,
)
from bengal.rendering.parsers.patitas.directives.options import StyledOptions
from bengal.rendering.parsers.patitas.nodes import Directive

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation
    from bengal.rendering.parsers.patitas.nodes import Block
    from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder


# Valid color variants (match CSS classes in dropdowns.css)
DROPDOWN_COLORS = frozenset(["success", "warning", "danger", "info", "minimal"])


def _render_dropdown_icon(icon_name: str, dropdown_title: str = "") -> str:
    """Render dropdown icon using shared icon utilities.
    
    Args:
        icon_name: Name of the icon to render
        dropdown_title: Title of the dropdown (for warning context)
    
    Returns:
        SVG HTML string, or empty string if icon not found
        
    """
    try:
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
    except ImportError:
        # Fallback if Bengal icons not available
        return ""


@dataclass(frozen=True, slots=True)
class DropdownOptions(StyledOptions):
    """Options for dropdown directive.
    
    Attributes:
        open: Whether dropdown is initially open (expanded)
        icon: Icon name to display next to the title
        badge: Badge text (e.g., "New", "Advanced", "Beta")
        color: Color variant (success, warning, danger, info, minimal)
        description: Secondary text below the title
    
    Example:
        :::{dropdown} My Title
        :open: true
        :icon: info
        :badge: Advanced
        :color: info
        :description: Additional context about what's inside
    
        Content here
        :::
        
    """

    open: bool = False
    icon: str | None = None
    badge: str | None = None
    color: str | None = None
    description: str | None = None


class DropdownDirective:
    """Handler for dropdown (collapsible) directive.
    
    Renders collapsible content using <details>/<summary>.
    Produces HTML identical to Bengal's dropdown directive.
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("dropdown", "details")
    token_type: ClassVar[str] = "dropdown"
    contract: ClassVar[DirectiveContract | None] = DROPDOWN_CONTRACT
    options_class: ClassVar[type[DropdownOptions]] = DropdownOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: DropdownOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build dropdown AST node."""
        effective_title = title or "Details"

        return Directive(
            location=location,
            name=name,
            title=effective_title,
            options=options,  # Pass typed options directly
            children=tuple(children),
        )

    def render(
        self,
        node: Directive[DropdownOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render dropdown to HTML.

        Produces HTML matching Bengal's dropdown directive exactly.

        Args:
            node: Directive AST node
            rendered_children: Pre-rendered child content
            sb: StringBuilder for output
        """
        opts = node.options  # Direct typed access!
        title = node.title or "Details"
        is_open = opts.open
        icon = opts.icon or ""
        badge = opts.badge or ""
        color = opts.color or ""
        description = opts.description or ""
        css_class = opts.class_ or ""

        # Clean up None strings
        if icon == "None":
            icon = ""
        if badge == "None":
            badge = ""
        if color == "None":
            color = ""
        if description == "None":
            description = ""
        if css_class == "None":
            css_class = ""

        # Add color variant to class string if valid
        if color and color in DROPDOWN_COLORS:
            css_class = f"{color} {css_class}".strip() if css_class else color

        # Build class string
        class_parts = ["dropdown"]
        if css_class:
            class_parts.append(css_class)
        class_str = " ".join(class_parts)

        # Build summary content with optional icon, description, and badge
        summary_parts = []

        # Add icon if specified
        if icon:
            icon_html = _render_dropdown_icon(icon, title)
            if icon_html:
                summary_parts.append(f'<span class="dropdown-icon">{icon_html}</span>')

        # Build title block (title + optional description)
        title_block = f'<span class="dropdown-title">{html_escape(title)}</span>'
        if description:
            title_block += f'<span class="dropdown-description">{html_escape(description)}</span>'
        summary_parts.append(f'<span class="dropdown-header">{title_block}</span>')

        # Add badge if specified
        if badge:
            summary_parts.append(f'<span class="dropdown-badge">{html_escape(badge)}</span>')

        summary_content = "".join(summary_parts)

        # Build open attribute
        open_attr = " open" if is_open else ""

        # Output HTML (matching Bengal's exact structure)
        sb.append(f'<details class="{html_escape(class_str)}"{open_attr}>\n')
        sb.append(f"  <summary>{summary_content}</summary>\n")
        sb.append('  <div class="dropdown-content">\n')
        sb.append(rendered_children)
        sb.append("  </div>\n")
        sb.append("</details>\n")
