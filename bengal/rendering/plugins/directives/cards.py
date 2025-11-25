"""
Cards directive for Bengal SSG.

Provides a modern, simple card grid system with auto-layout and responsive columns.

Syntax:
    :::{cards}
    :columns: 3  # or "auto" or "1-2-3-4" for responsive
    :gap: medium
    :style: default
    :variant: navigation  # or "info", "concept" for non-interactive use

    :::{card} Card Title
    :icon: book
    :link: /docs/
    :color: blue
    :image: /hero.jpg
    :footer: Updated 2025

    Card content with **full markdown** support.
    :::
    ::::

Examples:
    # Auto-layout (default)
    :::{cards}
    :::{card} One
    :::
    :::{card} Two
    :::
    ::::

    # Responsive columns
    :::{cards}
    :columns: 1-2-3  # 1 col mobile, 2 tablet, 3 desktop
    :::{card} Card 1
    :::
    :::{card} Card 2
    :::
    ::::
"""


from __future__ import annotations

from re import Match
from typing import Any

from mistune.directives import DirectivePlugin

__all__ = [
    "CardDirective",
    "CardsDirective",
    "GridDirective",
    "GridItemCardDirective",
    "render_card",
    "render_cards_grid",
]


class CardsDirective(DirectivePlugin):
    """
    Cards grid container directive.

    Creates a responsive grid of cards with sensible defaults and powerful options.
    Uses modern CSS Grid for layout.
    """

    def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]:
        """
        Parse cards directive.

        Args:
            block: Block parser
            m: Regex match object
            state: Parser state

        Returns:
            Token dict with type 'cards_grid'
        """
        # Parse options from directive
        options = dict(self.parse_options(m))

        # Get content and parse nested markdown
        content = self.parse_content(m)
        children = self.parse_tokens(block, content, state)

        # Normalize columns option
        columns = options.get("columns", "auto")
        if not columns:
            columns = "auto"

        # Normalize gap option
        gap = options.get("gap", "medium")
        if gap not in ("small", "medium", "large"):
            gap = "medium"

        # Normalize style option
        style = options.get("style", "default")
        if style not in ("default", "minimal", "bordered"):
            style = "default"

        # Get variant option (e.g. "info", "concept" vs default "navigation")
        variant = options.get("variant", "navigation")

        return {
            "type": "cards_grid",
            "attrs": {
                "columns": self._normalize_columns(columns),
                "gap": gap,
                "style": style,
                "variant": variant,
            },
            "children": children,
        }

    def _normalize_columns(self, columns: str) -> str:
        """
        Normalize columns specification.

        Accepts:
        - "auto" - auto-fit layout
        - "2", "3", "4" - fixed columns
        - "1-2-3", "1-2-3-4" - responsive (mobile-tablet-desktop-wide)

        Args:
            columns: Column specification string

        Returns:
            Normalized column string
        """
        columns = str(columns).strip()

        # Auto layout
        if columns in ("auto", ""):
            return "auto"

        # Fixed columns (1-6)
        if columns.isdigit():
            num = int(columns)
            if 1 <= num <= 6:
                return str(num)
            return "auto"

        # Responsive columns (e.g., "1-2-3-4")
        if "-" in columns:
            parts = columns.split("-")
            # Validate each part is a digit 1-6
            if all(p.isdigit() and 1 <= int(p) <= 6 for p in parts) and len(parts) in (2, 3, 4):
                return columns

        # Default to auto if invalid
        return "auto"

    def __call__(self, directive, md):
        """Register the directive with mistune."""
        directive.register("cards", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("cards_grid", render_cards_grid)


class CardDirective(DirectivePlugin):
    """
    Individual card directive (nested in cards).

    Creates a single card with optional icon, link, color, image, and footer.
    Supports full markdown in content.

    Supports footer separator (Sphinx-Design convention):
        :::{card} Title
        Body content
        +++
        Footer content
        :::
    """

    def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]:
        """
        Parse card directive.

        Args:
            block: Block parser
            m: Regex match object
            state: Parser state

        Returns:
            Token dict with type 'card'
        """
        # Get card title from directive line
        title = self.parse_title(m)

        # Parse options
        options = dict(self.parse_options(m))

        # Parse card content (full markdown support)
        raw_content = self.parse_content(m)

        # Check for +++ footer separator (Sphinx-Design convention)
        # Can use either :footer: option or +++ separator
        footer = options.get("footer", "").strip()
        if not footer and ("+++" in raw_content):
            parts = raw_content.split("+++", 1)
            content = parts[0].strip()
            footer = parts[1].strip() if len(parts) > 1 else ""
        else:
            content = raw_content

        children = self.parse_tokens(block, content, state)

        # Extract and normalize options
        icon = options.get("icon", "").strip()
        link = options.get("link", "").strip()
        color = options.get("color", "").strip()
        image = options.get("image", "").strip()

        # Validate color (optional)
        valid_colors = ("blue", "green", "red", "yellow", "purple", "gray", "pink", "indigo")
        if color and color not in valid_colors:
            color = ""

        return {
            "type": "card",
            "attrs": {
                "title": title,
                "icon": icon,
                "link": link,
                "color": color,
                "image": image,
                "footer": footer,
            },
            "children": children,
        }

    def __call__(self, directive, md):
        """Register the directive with mistune."""
        directive.register("card", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("card", render_card)


class GridDirective(DirectivePlugin):
    """
    Sphinx-Design grid compatibility layer.

    Accepts old Sphinx-Design syntax and converts to modern cards syntax.

    Old syntax:
        ::::{grid} 1 2 2 2
        :gutter: 1
        ::::

    Converts to:
        :::{cards}
        :columns: 1-2-2-2
        :gap: medium
        :::
    """

    def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]:
        """
        Parse grid directive (compatibility mode).

        Args:
            block: Block parser
            m: Regex match object
            state: Parser state

        Returns:
            Token dict with type 'cards_grid' (same as CardsDirective)
        """
        # Parse title which contains column breakpoints (e.g., "1 2 2 2")
        title = self.parse_title(m)
        options = dict(self.parse_options(m))

        # Convert Sphinx breakpoints to our responsive format
        columns = self._convert_sphinx_columns(title)

        # Convert gutter to gap
        gap = self._convert_sphinx_gutter(options.get("gutter", ""))

        # Parse content
        content = self.parse_content(m)
        children = self.parse_tokens(block, content, state)

        return {
            "type": "cards_grid",
            "attrs": {
                "columns": columns,
                "gap": gap,
                "style": "default",
            },
            "children": children,
        }

    def _convert_sphinx_columns(self, title: str) -> str:
        """
        Convert Sphinx column breakpoints to our format.

        "1 2 2 2" -> "1-2-2-2"
        "2" -> "2"
        "" -> "auto"

        Args:
            title: Sphinx breakpoint string

        Returns:
            Normalized column string
        """
        if not title:
            return "auto"

        parts = title.strip().split()

        # Single number - fixed columns
        if len(parts) == 1 and parts[0].isdigit():
            return parts[0]

        # Multiple numbers - responsive
        if len(parts) >= 2:
            # Filter valid numbers
            valid_parts = [p for p in parts if p.isdigit() and 1 <= int(p) <= 6]
            if valid_parts:
                return "-".join(valid_parts[:4])  # Max 4 breakpoints

        return "auto"

    def _convert_sphinx_gutter(self, gutter: str) -> str:
        """
        Convert Sphinx gutter to our gap format.

        Sphinx uses numbers like "1", "2", "3" or "1 1 1 2"
        We use "small", "medium", "large"

        Args:
            gutter: Sphinx gutter value

        Returns:
            Gap value (small/medium/large)
        """
        if not gutter:
            return "medium"

        # Extract first number
        parts = str(gutter).strip().split()
        if parts and parts[0].isdigit():
            num = int(parts[0])
            if num <= 1:
                return "small"
            elif num >= 3:
                return "large"

        return "medium"

    def __call__(self, directive, md):
        """Register the directive with mistune."""
        directive.register("grid", self.parse)

        # Uses the same renderer as CardsDirective
        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("cards_grid", render_cards_grid)


class GridItemCardDirective(DirectivePlugin):
    """
    Sphinx-Design grid-item-card compatibility layer.

    Converts old syntax to modern card syntax.

    Old syntax:
        :::{grid-item-card} {octicon}`book;1.5em` Title
        :link: docs/page
        :link-type: doc
        Content
        :::

    Converts to:
        :::{card} Title
        :icon: book
        :link: docs/page
        Content
        :::
    """

    def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]:
        """
        Parse grid-item-card directive (compatibility mode).

        Supports Sphinx-Design footer separator:
            :::{grid-item-card} Title
            Body content
            +++
            Footer content
            :::

        Args:
            block: Block parser
            m: Regex match object
            state: Parser state

        Returns:
            Token dict with type 'card' (same as CardDirective)
        """
        # Parse title (may contain octicon syntax)
        title = self.parse_title(m)
        options = dict(self.parse_options(m))
        raw_content = self.parse_content(m)

        # Check for +++ footer separator (Sphinx-Design convention)
        footer_text = ""
        if "\n+++\n" in raw_content or "\n+++" in raw_content:
            parts = raw_content.split("+++", 1)
            content = parts[0].strip()
            footer_content = parts[1].strip() if len(parts) > 1 else ""
            # Parse footer markdown to plain text (for badges, etc)
            if footer_content:
                footer_children = self.parse_tokens(block, footer_content, state)
                # Render footer children to get the HTML
                for child in footer_children:
                    if isinstance(child, dict) and "type" in child:
                        # Will be rendered later - just note we have footer
                        footer_text = footer_content  # Keep raw for now
                    else:
                        footer_text = footer_content
        else:
            content = raw_content

        children = self.parse_tokens(block, content, state)

        # Extract icon from octicon syntax in title
        icon, clean_title = self._extract_octicon(title)

        # Convert options
        link = options.get("link", "").strip()

        # Ignore link-type (not needed in our implementation)
        # Sphinx uses :link-type: doc|url|ref, we auto-detect

        return {
            "type": "card",
            "attrs": {
                "title": clean_title,
                "icon": icon,
                "link": link,
                "color": "",
                "image": "",
                "footer": footer_text,  # Footer from +++ separator
            },
            "children": children,
        }

    def _extract_octicon(self, title: str) -> tuple[str, str]:
        """
        Extract octicon from title and return clean title.

        "{octicon}`book;1.5em;sd-mr-1` My Title" -> ("book", "My Title")
        "My Title" -> ("", "My Title")

        Args:
            title: Card title possibly with octicon

        Returns:
            Tuple of (icon_name, clean_title)
        """
        import re

        # Pattern: {octicon}`icon-name;size;classes`
        pattern = r"\{octicon\}`([^;`]+)(?:;[^`]*)?`\s*"
        match = re.search(pattern, title)

        if match:
            icon_name = match.group(1).strip()
            # Remove octicon syntax from title
            clean_title = re.sub(pattern, "", title).strip()
            return icon_name, clean_title

        return "", title

    def __call__(self, directive, md):
        """Register the directive with mistune."""
        directive.register("grid-item-card", self.parse)

        # Uses the same renderer as CardDirective
        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("card", render_card)


# Render functions


def render_cards_grid(renderer, text: str, **attrs) -> str:
    """
    Render cards grid container to HTML.

    Args:
        renderer: Mistune renderer
        text: Rendered children (cards)
        attrs: Grid attributes (columns, gap, style)

    Returns:
        HTML string for card grid
    """
    columns = attrs.get("columns", "auto")
    gap = attrs.get("gap", "medium")
    style = attrs.get("style", "default")
    variant = attrs.get("variant", "navigation")

    # Build data attributes for CSS
    html = (
        f'<div class="card-grid" '
        f'data-columns="{columns}" '
        f'data-gap="{gap}" '
        f'data-style="{style}" '
        f'data-variant="{variant}">\n'
        f"{text}"
        f"</div>\n"
    )
    return html


def render_card(renderer, text: str, **attrs) -> str:
    """
    Render individual card to HTML.

    Args:
        renderer: Mistune renderer
        text: Rendered card content
        attrs: Card attributes (title, icon, link, color, image, footer)

    Returns:
        HTML string for card
    """
    title = attrs.get("title", "")
    icon = attrs.get("icon", "")
    link = attrs.get("link", "")
    color = attrs.get("color", "")
    image = attrs.get("image", "")
    footer = attrs.get("footer", "")

    # Card wrapper (either <a> or <div>)
    if link:
        card_tag = "a"
        card_attrs_str = f' href="{_escape_html(link)}"'
    else:
        card_tag = "div"
        card_attrs_str = ""

    # Build class list
    classes = ["card"]
    if color:
        classes.append(f"card-color-{color}")

    class_str = " ".join(classes)

    # Build card HTML
    parts = [f'<{card_tag} class="{class_str}"{card_attrs_str}>']

    # Optional header image (direct child of card)
    if image:
        parts.append(
            f'  <img class="card-image" src="{_escape_html(image)}" alt="{_escape_html(title)}" loading="lazy">'
        )

    # Card header (icon and title) - direct child of card
    if icon or title:
        parts.append('  <div class="card-header">')
        if icon:
            # Only render icon if it actually produces output
            rendered_icon = _render_icon(icon)
            if rendered_icon:
                parts.append(f'    <span class="card-icon" data-icon="{_escape_html(icon)}">')
                parts.append(rendered_icon)
                parts.append("    </span>")
        if title:
            # Use div, not h3, so it doesn't appear in TOC
            # Styled to look like a heading but not a semantic heading
            parts.append(f'    <div class="card-title">{_escape_html(title)}</div>')
        parts.append("  </div>")

    # Card content - direct child of card
    if text:
        parts.append('  <div class="card-content">')
        parts.append(f"    {text}")  # Already rendered markdown
        parts.append("  </div>")

    # Optional footer (may contain markdown like badges) - direct child of card
    if footer:
        parts.append('  <div class="card-footer">')
        # Footer might have markdown (badges, links, etc), don't escape
        parts.append(f"    {footer}")
        parts.append("  </div>")

    parts.append(f"</{card_tag}>")

    return "\n".join(parts) + "\n"


def _render_icon(icon_name: str) -> str:
    """
    Render icon as inline SVG or icon font.

    For now, renders a simple emoji/text representation.
    In the future, this will render actual SVG icons from Lucide.

    Args:
        icon_name: Name of the icon

    Returns:
        HTML for icon, or empty string if icon not found
    """
    # Simple icon mapping (temporary - will be replaced with Lucide icons)
    icon_map = {
        "book": "📖",
        "code": "💻",
        "rocket": "🚀",
        "users": "👥",
        "star": "⭐",
        "info": "ℹ️",
        "warning": "⚠️",
        "check": "✓",
        "database": "🗄️",
        "tools": "🔧",
        "shield": "🛡️",
        "graduation-cap": "🎓",
        "mortar-board": "🎓",
        "package": "📦",
        "pin": "📌",
        "graph": "📊",
        "shield-lock": "🔒",
    }

    # Return the emoji if found, empty string if not (no fallback bullet)
    return icon_map.get(icon_name, "")


def _escape_html(text: str) -> str:
    """
    Escape HTML special characters.

    Args:
        text: Text to escape

    Returns:
        Escaped text
    """
    if not text:
        return ""

    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
