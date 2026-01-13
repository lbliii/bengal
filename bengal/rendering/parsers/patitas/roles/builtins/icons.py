"""Icon role for inline SVG icons.

Provides inline icon rendering via the {icon} role:
{icon}`name` - Icon at default size (24px)
{icon}`name:size` - Icon at custom size
{icon}`name:size:class` - Icon with size and CSS class

Example:
See the {icon}`warning` icon for alerts.
Use {icon}`terminal:16` for small inline icons.
Style with {icon}`star:24:icon-primary`.

"""

from __future__ import annotations

import re
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from patitas.nodes import Role

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.stringbuilder import StringBuilder


class IconRole:
    """Handler for {icon}`name:size:class` role.
    
    Renders inline SVG icons from Bengal's icon library.
    Icons are loaded via the theme-aware resolver.
    
    Syntax:
        {icon}`warning` - Default size (24px)
        {icon}`terminal:16` - Custom size
        {icon}`star:24:icon-primary` - Size and CSS class
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        Icon loading uses thread-safe resolver.
        
    """

    names: ClassVar[tuple[str, ...]] = ("icon", "svg-icon")
    token_type: ClassVar[str] = "icon"

    def parse(
        self,
        name: str,
        content: str,
        location: SourceLocation,
    ) -> Role:
        """Parse icon role content.

        Format: name[:size[:class]]
        """
        content = content.strip()

        # Parse name:size:class format
        parts = content.split(":")
        icon_name = parts[0].strip().lower().replace(" ", "-") if parts else ""
        size = 24
        css_class = ""

        if len(parts) >= 2 and parts[1].strip():
            try:
                size = int(parts[1].strip())
                if size <= 0:
                    size = 24
            except ValueError:
                # If second part isn't a number, treat as class
                css_class = parts[1].strip()

        if len(parts) >= 3 and parts[2].strip():
            css_class = parts[2].strip()

        # Store parsed data in target field as "size|class"
        return Role(
            location=location,
            name=name,
            content=icon_name,
            target=f"{size}|{css_class}",
        )

    def render(
        self,
        node: Role,
        sb: StringBuilder,
    ) -> None:
        """Render icon to inline SVG."""
        # Parse name:size:class from node.content
        # The parser stores raw content, we parse here
        content = node.content.strip() if node.content else ""

        if not content:
            sb.append('<span class="bengal-icon bengal-icon--error" aria-hidden="true">⚠️</span>')
            return

        # Parse name:size:class format
        parts = content.split(":")
        icon_name = parts[0].strip().lower().replace(" ", "-") if parts else ""
        size = 24
        css_class = ""

        if len(parts) >= 2 and parts[1].strip():
            try:
                size = int(parts[1].strip())
                if size <= 0:
                    size = 24
            except ValueError:
                # If second part isn't a number, treat as class
                css_class = parts[1].strip()

        if len(parts) >= 3 and parts[2].strip():
            css_class = parts[2].strip()

        if not icon_name:
            sb.append('<span class="bengal-icon bengal-icon--error" aria-hidden="true">⚠️</span>')
            return

        # Load SVG via Bengal's icon resolver
        try:
            from bengal.icons import resolver as icon_resolver

            svg_content = icon_resolver.load_icon(icon_name)
        except ImportError:
            svg_content = None

        if svg_content is None:
            sb.append(
                f'<span class="bengal-icon bengal-icon--missing" aria-hidden="true" '
                f'title="Icon not found: {html_escape(icon_name)}">❓</span>'
            )
            return

        # Build class list
        classes = ["bengal-icon", f"icon-{icon_name}"]
        if css_class:
            classes.extend(css_class.split())
        class_attr = " ".join(classes)

        # Accessibility - icons are decorative
        aria_attrs = 'aria-hidden="true"'

        # Modify SVG to set size and add attributes
        svg_modified = re.sub(r'\s+(width|height)="[^"]*"', "", svg_content)
        svg_modified = re.sub(r'\s+class="[^"]*"', "", svg_modified)

        svg_modified = re.sub(
            r"<svg\s",
            f'<svg width="{size}" height="{size}" class="{class_attr}" {aria_attrs} ',
            svg_modified,
            count=1,
        )

        sb.append(svg_modified)
