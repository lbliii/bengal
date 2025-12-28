"""Admonition directive for callout boxes.

Supports standard admonition types:
    - note: General information
    - warning: Potential issues
    - tip: Helpful suggestions
    - danger: Serious risk
    - error: Error conditions
    - info: Informational callout
    - example: Example content
    - success: Success messages
    - caution: Proceed carefully (maps to warning CSS)
    - seealso: Related information

Example:
    :::{note} Optional Title
    :class: custom-class

    This is the note content.
    :::

Thread Safety:
    Stateless handler. Safe for concurrent use across threads.

HTML Output:
    Matches Bengal's admonition directive exactly:
    <div class="admonition note">
      <p class="admonition-title">
        <span class="admonition-icon-wrapper">{SVG}</span>
        <span class="admonition-title-text">Title</span>
      </p>
      {content}
    </div>
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from bengal.rendering.parsers.patitas.directives.contracts import DirectiveContract
from bengal.rendering.parsers.patitas.directives.options import AdmonitionOptions
from bengal.rendering.parsers.patitas.nodes import Directive

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation
    from bengal.rendering.parsers.patitas.nodes import Block
    from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder


# All supported admonition types (matches Bengal)
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
TYPE_TO_CSS: dict[str, str] = {
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

# Map types to icon names (matches Bengal)
TYPE_TO_ICON: dict[str, str] = {
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


def _render_admonition_icon(icon_name: str) -> str:
    """Render admonition icon using Phosphor icons.

    Args:
        icon_name: Name of the icon to render

    Returns:
        SVG HTML string, or empty string if icon not found
    """
    try:
        from bengal.directives._icons import render_svg_icon

        return render_svg_icon(icon_name, size=20, css_class="admonition-icon")
    except ImportError:
        # Fallback if Bengal icons not available
        return ""


class AdmonitionDirective:
    """Handler for admonition directives.

    Renders callout boxes for notes, warnings, tips, etc.
    Produces HTML identical to Bengal's admonition directive.

    Thread Safety:
        Stateless handler. Safe for concurrent use.
    """

    names: ClassVar[tuple[str, ...]] = tuple(ADMONITION_TYPES)
    token_type: ClassVar[str] = "admonition"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[AdmonitionOptions]] = AdmonitionOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: AdmonitionOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build admonition AST node.

        Args:
            name: Admonition type (note, warning, etc.)
            title: Custom title (uses type name if None)
            options: Typed admonition options
            content: Raw content (unused, prefer children)
            children: Parsed child blocks
            location: Source location

        Returns:
            Directive node for AST
        """
        # Use custom title or capitalize the type name
        effective_title = title if title else name.capitalize()

        # Convert options to frozenset, including admon_type for rendering
        opts_dict = asdict(options)
        opts_dict["admon_type"] = name
        # Filter out None values and convert
        opts_items = [(k, str(v)) for k, v in opts_dict.items() if v is not None]

        return Directive(
            location=location,
            name=name,
            title=effective_title,
            options=frozenset(opts_items),
            children=tuple(children),
        )

    def render(
        self,
        node: Directive,
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render admonition to HTML.

        Produces HTML matching Bengal's admonition directive exactly,
        including icon wrapper structure.

        Args:
            node: Directive AST node
            rendered_children: Pre-rendered child content
            sb: StringBuilder for output
        """
        opts = dict(node.options)
        admon_type = opts.get("admon_type", node.name)
        title = node.title or admon_type.capitalize()

        # Get CSS class for type (caution → warning)
        css_class = TYPE_TO_CSS.get(admon_type, "note")

        # Add extra class if specified (parser stores as "class", not "class_")
        extra_class = opts.get("class", "") or opts.get("class_", "")
        if extra_class and extra_class != "None":
            css_class = f"{css_class} {extra_class}"

        # Render icon
        icon_name = TYPE_TO_ICON.get(admon_type, "info")
        icon_html = _render_admonition_icon(icon_name)

        # Build title with icon (matching Bengal's structure)
        if icon_html:
            title_html = (
                f'<span class="admonition-icon-wrapper">{icon_html}</span>'
                f'<span class="admonition-title-text">{html_escape(title)}</span>'
            )
        else:
            title_html = html_escape(title)

        # Output HTML (matching Bengal's exact structure)
        sb.append(f'<div class="admonition {html_escape(css_class)}">\n')
        sb.append(f'  <p class="admonition-title">{title_html}</p>\n')
        sb.append(rendered_children)
        sb.append("</div>\n")
