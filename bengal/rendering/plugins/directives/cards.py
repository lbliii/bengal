"""
Cards directive for Bengal SSG.

Provides a modern, simple card grid system with auto-layout and responsive columns.

Syntax:
    :::{cards}
    :columns: 3  # or "auto" or "1-2-3-4" for responsive
    :gap: medium
    :style: default
    :variant: navigation  # or "info", "concept" for non-interactive use
    :layout: default  # or "horizontal", "portrait", "compact"

    :::{card} Card Title
    :icon: book
    :link: /docs/
    :color: blue
    :image: /hero.jpg
    :footer: Updated 2025
    :pull: title, description  # Auto-fetch from linked page
    :layout: horizontal  # Override grid layout for this card

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

    # Auto-pull metadata from linked pages
    :::{cards}
    :::{card}
    :link: docs/quickstart
    :pull: title, description
    :::
    ::::

    # Portrait layout (TCG/phone style)
    :::{cards}
    :layout: portrait
    :columns: 3
    :::{card} Card 1
    :image: /hero.png
    :::
    ::::
"""

from __future__ import annotations

from re import Match
from typing import Any

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = [
    "CardDirective",
    "CardsDirective",
    "ChildCardsDirective",
    "GridDirective",
    "GridItemCardDirective",
    "render_card",
    "render_cards_grid",
    "render_child_cards",
]

# Valid layout options
VALID_LAYOUTS = ("default", "horizontal", "portrait", "compact")


class CardsDirective(DirectivePlugin):
    """
    Cards grid container directive.

    Creates a responsive grid of cards with sensible defaults and powerful options.
    Uses modern CSS Grid for layout.
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["cards"]

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
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

        # Get layout option (default, horizontal, portrait, compact)
        layout = options.get("layout", "default")
        if layout not in VALID_LAYOUTS:
            layout = "default"

        return {
            "type": "cards_grid",
            "attrs": {
                "columns": self._normalize_columns(columns),
                "gap": gap,
                "style": style,
                "variant": variant,
                "layout": layout,
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

    def __call__(self, directive: Any, md: Any) -> None:
        """Register the directive with mistune."""
        directive.register("cards", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("cards_grid", render_cards_grid)


class CardDirective(DirectivePlugin):
    """
    Individual card directive (nested in cards).

    Creates a single card with optional icon, link, color, image, and footer.
    Supports full markdown in content.

    Supports footer separator:
        :::{card} Title
        Body content
        +++
        Footer content
        :::
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["card"]

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
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

        # Check for +++ footer separator (can use either :footer: option or +++ separator)
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
        valid_colors = (
            "blue",
            "green",
            "red",
            "yellow",
            "orange",
            "purple",
            "gray",
            "pink",
            "indigo",
        )
        if color and color not in valid_colors:
            color = ""

        # Parse pull option (comma-separated list of fields to pull from linked page)
        pull_str = options.get("pull", "")
        pull_fields = [f.strip() for f in pull_str.split(",") if f.strip()]

        # Get layout option (can override grid-level layout)
        layout = options.get("layout", "")
        if layout and layout not in VALID_LAYOUTS:
            layout = ""

        return {
            "type": "card",
            "attrs": {
                "title": title,
                "icon": icon,
                "link": link,
                "color": color,
                "image": image,
                "footer": footer,
                "pull": pull_fields,
                "layout": layout,
            },
            "children": children,
        }

    def __call__(self, directive: Any, md: Any) -> None:
        """Register the directive with mistune."""
        directive.register("card", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("card", render_card)


class GridDirective(DirectivePlugin):
    """
    Grid layout compatibility layer.

    Accepts legacy grid syntax and converts to modern cards syntax.

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

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["grid"]

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
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

        # Convert legacy breakpoints to our responsive format
        columns = self._convert_legacy_columns(title)

        # Convert gutter to gap
        gap = self._convert_legacy_gutter(options.get("gutter", ""))

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

    def _convert_legacy_columns(self, title: str) -> str:
        """
        Convert legacy column breakpoints to our format.

        "1 2 2 2" -> "1-2-2-2"
        "2" -> "2"
        "" -> "auto"

        Args:
            title: Legacy breakpoint string (e.g., "1 2 2 2")

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

    def _convert_legacy_gutter(self, gutter: str) -> str:
        """
        Convert legacy gutter to our gap format.

        Legacy format uses numbers like "1", "2", "3" or "1 1 1 2"
        We use "small", "medium", "large"

        Args:
            gutter: Legacy gutter value

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

    def __call__(self, directive: Any, md: Any) -> None:
        """Register the directive with mistune."""
        directive.register("grid", self.parse)

        # Uses the same renderer as CardsDirective
        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("cards_grid", render_cards_grid)


class GridItemCardDirective(DirectivePlugin):
    """
    Grid item card compatibility layer.

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

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["grid-item-card"]

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
        """
        Parse grid-item-card directive (compatibility mode).

        Supports footer separator:
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

        # Check for +++ footer separator
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

        # Ignore link-type (not needed in our implementation - we auto-detect)

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

    def __call__(self, directive: Any, md: Any) -> None:
        """Register the directive with mistune."""
        directive.register("grid-item-card", self.parse)

        # Uses the same renderer as CardDirective
        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("card", render_card)


# Render functions


def render_cards_grid(renderer: Any, text: str, **attrs: Any) -> str:
    """
    Render cards grid container to HTML.

    Args:
        renderer: Mistune renderer
        text: Rendered children (cards)
        attrs: Grid attributes (columns, gap, style, variant, layout)

    Returns:
        HTML string for card grid
    """
    columns = attrs.get("columns", "auto")
    gap = attrs.get("gap", "medium")
    style = attrs.get("style", "default")
    variant = attrs.get("variant", "navigation")
    layout = attrs.get("layout", "default")

    # Build data attributes for CSS
    html = (
        f'<div class="card-grid" '
        f'data-columns="{columns}" '
        f'data-gap="{gap}" '
        f'data-style="{style}" '
        f'data-variant="{variant}" '
        f'data-layout="{layout}">\n'
        f"{text}"
        f"</div>\n"
    )
    return html


def render_card(renderer: Any, text: str, **attrs: Any) -> str:
    """
    Render individual card to HTML.

    Supports pulling metadata from linked pages via the :pull: option.
    When pull fields are specified and a link is provided, metadata is
    fetched from the linked page via xref_index (O(1) lookup).

    Args:
        renderer: Mistune renderer
        text: Rendered card content
        attrs: Card attributes (title, icon, link, color, image, footer, pull, layout)

    Returns:
        HTML string for card
    """
    title = attrs.get("title", "")
    icon = attrs.get("icon", "")
    link = attrs.get("link", "")
    color = attrs.get("color", "")
    image = attrs.get("image", "")
    footer = attrs.get("footer", "")
    pull_fields = attrs.get("pull", [])
    layout = attrs.get("layout", "")

    # Pull metadata from linked page if requested
    if link and pull_fields:
        pulled = _pull_from_linked_page(renderer, link, pull_fields)
        # Pulled values fill in missing/empty attrs
        if "title" in pull_fields and not title:
            title = pulled.get("title", "")
        if "description" in pull_fields and not text.strip():
            text = f"<p>{_escape_html(pulled.get('description', ''))}</p>"
        if "icon" in pull_fields and not icon:
            icon = pulled.get("icon", "")
        if "image" in pull_fields and not image:
            image = pulled.get("image", "")

    # Resolve link URL if it's a reference (id:xxx or path)
    resolved_link = _resolve_link_url(renderer, link) if link else ""

    # Card wrapper (either <a> or <div>)
    if resolved_link:
        card_tag = "a"
        card_attrs_str = f' href="{_escape_html(resolved_link)}"'
    else:
        card_tag = "div"
        card_attrs_str = ""

    # Build class list
    classes = ["card"]
    if color:
        classes.append(f"card-color-{color}")
    if layout:
        classes.append(f"card-layout-{layout}")

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


def _pull_from_linked_page(renderer: Any, link: str, fields: list[str]) -> dict[str, Any]:
    """
    Pull metadata from a linked page using the object tree (preferred) or xref_index.

    NEW: Uses page._section.subsections for O(1) direct access when possible.
    Falls back to xref_index for non-relative paths.

    Supports:
    - ./child/ - Direct object tree lookup (fast, reliable!)
    - id:xxx - xref_index lookup
    - path/to/page - xref_index lookup
    - slug - xref_index lookup

    Args:
        renderer: Mistune renderer (has _current_page for object tree access)
        link: Link string (./relative/, id:xxx, path, or slug)
        fields: List of field names to pull

    Returns:
        Dict of pulled field values (empty dict if page not found)
    """
    page = None

    # Strategy 1: Object tree for relative paths (NEW - fast and reliable!)
    if link.startswith("./"):
        current_page = getattr(renderer, "_current_page", None)
        if current_page:
            section = getattr(current_page, "_section", None)
            if section:
                # Extract child name from ./child/ or ./child
                child_name = link[2:].rstrip("/").split("/")[0]

                # Look in subsections first
                for subsection in getattr(section, "subsections", []):
                    if getattr(subsection, "name", "") == child_name:
                        # Found subsection - use its index_page for metadata
                        page = getattr(subsection, "index_page", None)
                        if page:
                            logger.debug(
                                "pull_object_tree_subsection",
                                link=link,
                                found=child_name,
                            )
                            break

                # If not found in subsections, look in pages
                if not page:
                    for p in getattr(section, "pages", []):
                        source_str = str(getattr(p, "source_path", ""))
                        # Match by filename (without extension)
                        if f"/{child_name}." in source_str or f"/{child_name}/" in source_str:
                            page = p
                            logger.debug("pull_object_tree_page", link=link, found=child_name)
                            break

    # Strategy 2: Fall back to xref_index for other patterns
    if not page:
        xref_index = getattr(renderer, "_xref_index", None)
        current_page_dir = getattr(renderer, "_current_page_dir", None)

        if xref_index:
            page = _resolve_page(xref_index, link, current_page_dir)

    if not page:
        logger.debug("pull_page_not_found", link=link)
        return {}

    # Extract requested fields from found page
    return _extract_page_fields(page, fields)


def _extract_page_fields(page: Any, fields: list[str]) -> dict[str, Any]:
    """Extract requested fields from a page object."""
    result: dict[str, Any] = {}

    for field in fields:
        if field == "title":
            result["title"] = getattr(page, "title", "")
        elif field == "description":
            result["description"] = (
                page.metadata.get("description", "") if hasattr(page, "metadata") else ""
            )
        elif field == "date":
            result["date"] = getattr(page, "date", None)
        elif field == "tags":
            result["tags"] = getattr(page, "tags", [])
        elif field == "icon":
            result["icon"] = page.metadata.get("icon", "") if hasattr(page, "metadata") else ""
        elif field == "image":
            result["image"] = page.metadata.get("image", "") if hasattr(page, "metadata") else ""
        elif field == "card_color":
            result["card_color"] = (
                page.metadata.get("card_color", "") if hasattr(page, "metadata") else ""
            )
        elif field == "estimated_time":
            result["estimated_time"] = (
                page.metadata.get("estimated_time", "") if hasattr(page, "metadata") else ""
            )
        elif field == "difficulty":
            result["difficulty"] = (
                page.metadata.get("difficulty", "") if hasattr(page, "metadata") else ""
            )

    logger.debug("pull_success", fields=list(result.keys()))
    return result


def _resolve_page(
    xref_index: dict[str, Any], link: str, current_page_dir: str | None = None
) -> Any:
    """
    Resolve a link to a page object via xref_index.

    Args:
        xref_index: Cross-reference index with by_id, by_path, by_slug
        link: Link string
        current_page_dir: Current page's content-relative directory (for relative paths)

    Returns:
        Page object or None
    """
    # Strategy 0: Relative path (./child/ or ../sibling/)
    if link.startswith("./") or link.startswith("../"):
        if current_page_dir:
            # Resolve relative path
            clean_link = link.replace(".md", "").rstrip("/")
            if clean_link.startswith("./"):
                # ./child -> current_dir/child
                resolved_path = f"{current_page_dir}/{clean_link[2:]}"
            else:
                # ../sibling -> parent_dir/sibling
                parts = current_page_dir.split("/")
                up_count = 0
                remaining = clean_link
                while remaining.startswith("../"):
                    up_count += 1
                    remaining = remaining[3:]
                if up_count < len(parts):
                    parent = "/".join(parts[:-up_count]) if up_count > 0 else current_page_dir
                    resolved_path = f"{parent}/{remaining}" if remaining else parent
                else:
                    resolved_path = remaining

            # Try exact path
            page = xref_index.get("by_path", {}).get(resolved_path)
            if page:
                return page
            # Try without trailing _index
            if resolved_path.endswith("/_index"):
                page = xref_index.get("by_path", {}).get(resolved_path[:-7])
                if page:
                    return page
            logger.debug("pull_relative_path_not_found", link=link, resolved=resolved_path)
        else:
            logger.debug("pull_relative_path_no_context", link=link)
        return None

    # Strategy 1: Custom ID (id:xxx)
    if link.startswith("id:"):
        ref_id = link[3:]
        return xref_index.get("by_id", {}).get(ref_id)

    # Strategy 2: Path lookup (contains / or ends with .md)
    if "/" in link or link.endswith(".md"):
        clean_path = link.replace(".md", "").strip("/")
        # Try exact path
        page = xref_index.get("by_path", {}).get(clean_path)
        if page:
            return page
        # Try without trailing _index
        if clean_path.endswith("/_index"):
            return xref_index.get("by_path", {}).get(clean_path[:-7])
        return None

    # Strategy 3: Slug lookup
    pages = xref_index.get("by_slug", {}).get(link, [])
    return pages[0] if pages else None


def _resolve_link_url(renderer: Any, link: str) -> str:
    """
    Resolve a link reference to a URL.

    If link is an id: reference or path, resolve to actual URL.
    If link is already a URL (starts with / or http), return as-is.

    Args:
        renderer: Mistune renderer
        link: Link string

    Returns:
        Resolved URL string
    """
    # Already a URL
    if link.startswith("/") or link.startswith("http://") or link.startswith("https://"):
        return link

    # Try to resolve via xref_index
    xref_index = getattr(renderer, "_xref_index", None)
    if not xref_index:
        # Can't resolve, return as relative path
        return link

    # Get current page directory for relative path resolution
    current_page_dir = getattr(renderer, "_current_page_dir", None)

    page = _resolve_page(xref_index, link, current_page_dir)
    if page and hasattr(page, "url"):
        url: str = page.url
        return url

    # Fallback: treat as relative path
    return link


def _render_icon(icon_name: str, use_svg: bool = False) -> str:
    """
    Render icon using Bengal SVG icons with emoji fallback.

    Args:
        icon_name: Name of the icon (e.g., "folder", "file", "terminal")
        use_svg: Legacy parameter, now always attempts SVG first

    Returns:
        HTML for icon (inline SVG preferred, emoji fallback)
    """
    from bengal.rendering.plugins.directives._icons import render_icon

    # Always try SVG first now (use_svg parameter kept for API compatibility)
    return render_icon(icon_name, size=20)


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


# =============================================================================
# Child Cards Directive - Auto-generates cards from page children
# =============================================================================


class ChildCardsDirective(DirectivePlugin):
    """
    Auto-generate cards from current page's child sections/pages.

    Automatically generates cards by walking the page/section tree.
    No manual card definitions needed.

    Syntax:
        :::{child-cards}
        :columns: 3
        :layout: default
        :include: sections  # "sections", "pages", or "all"
        :fields: title, description, icon
        :::

    Example:
        # On an _index.md page, shows all child sections as cards:
        :::{child-cards}
        :columns: 2
        :include: sections
        :fields: title, description, icon
        :::
    """

    # Directive names this class registers (for health check introspection)
    DIRECTIVE_NAMES = ["child-cards"]

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
        """Parse child-cards directive options."""
        options = dict(self.parse_options(m))

        # Normalize columns
        columns = options.get("columns", "auto")
        if not columns:
            columns = "auto"

        # Normalize gap
        gap = options.get("gap", "medium")
        if gap not in ("small", "medium", "large"):
            gap = "medium"

        # What to include: sections, pages, or all
        include = options.get("include", "all")
        if include not in ("sections", "pages", "all"):
            include = "all"

        # Fields to pull from children
        fields_str = options.get("fields", "title, description")
        fields = [f.strip() for f in fields_str.split(",") if f.strip()]

        # Layout
        layout = options.get("layout", "default")
        if layout not in VALID_LAYOUTS:
            layout = "default"

        # Style
        style = options.get("style", "default")
        if style not in ("default", "minimal", "bordered"):
            style = "default"

        return {
            "type": "child_cards",
            "attrs": {
                "columns": columns,
                "gap": gap,
                "include": include,
                "fields": fields,
                "layout": layout,
                "style": style,
            },
            "children": [],
        }

    def __call__(self, directive: Any, md: Any) -> None:
        """Register the directive with mistune."""
        directive.register("child-cards", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("child_cards", render_child_cards)


def render_child_cards(renderer: Any, text: str, **attrs: Any) -> str:
    """
    Render child cards by walking the page object tree.

    This is where the magic happens! We access renderer._current_page
    and walk the section tree to generate cards.

    Args:
        renderer: Mistune renderer (has _current_page attribute)
        text: Unused (no nested content)
        attrs: Directive options

    Returns:
        HTML string with card grid
    """
    columns = attrs.get("columns", "auto")
    gap = attrs.get("gap", "medium")
    include = attrs.get("include", "all")
    fields = attrs.get("fields", ["title", "description"])
    layout = attrs.get("layout", "default")
    style = attrs.get("style", "default")

    # Get current page from renderer
    current_page = getattr(renderer, "_current_page", None)
    if not current_page:
        logger.debug("child_cards_no_current_page")
        return '<div class="card-grid" data-columns="auto"><p><em>No page context available</em></p></div>'

    # Get section (parent container for children)
    section = getattr(current_page, "_section", None)
    if not section:
        logger.debug("child_cards_no_section", page=str(current_page.source_path))
        return (
            '<div class="card-grid" data-columns="auto"><p><em>Page has no section</em></p></div>'
        )

    # Collect children based on include setting
    children = []

    if include in ("sections", "all"):
        # Add subsections
        for subsection in getattr(section, "subsections", []):
            children.append(
                {
                    "type": "section",
                    "obj": subsection,
                    "title": getattr(subsection, "title", subsection.name),
                    "description": subsection.metadata.get("description", "")
                    if hasattr(subsection, "metadata")
                    else "",
                    "icon": subsection.metadata.get("icon", "")
                    if hasattr(subsection, "metadata")
                    else "",
                    "url": _get_section_url(subsection),
                    "weight": subsection.metadata.get("weight", 0)
                    if hasattr(subsection, "metadata")
                    else 0,
                }
            )

    if include in ("pages", "all"):
        # Add sibling pages (excluding _index pages)
        for page in getattr(section, "pages", []):
            # Skip _index pages (they're sections, not content)
            source_str = str(getattr(page, "source_path", ""))
            if source_str.endswith("_index.md") or source_str.endswith("index.md"):
                continue
            # Skip the current page itself
            if (
                hasattr(current_page, "source_path")
                and hasattr(page, "source_path")
                and page.source_path == current_page.source_path
            ):
                continue
            children.append(
                {
                    "type": "page",
                    "obj": page,
                    "title": getattr(page, "title", ""),
                    "description": page.metadata.get("description", "")
                    if hasattr(page, "metadata")
                    else "",
                    "icon": page.metadata.get("icon", "") if hasattr(page, "metadata") else "",
                    "url": getattr(page, "url", ""),
                    "weight": page.metadata.get("weight", 0) if hasattr(page, "metadata") else 0,
                }
            )

    # Sort by weight, then title
    children.sort(key=lambda c: (c.get("weight", 0), c.get("title", "").lower()))

    if not children:
        logger.debug("child_cards_no_children", page=str(current_page.source_path))
        return '<div class="card-grid" data-columns="auto"><p><em>No child content found</em></p></div>'

    # Generate card HTML for each child
    cards_html = []
    for child in children:
        card_html = _render_child_card(child, fields, layout)
        cards_html.append(card_html)

    # Wrap in grid container
    html = (
        f'<div class="card-grid" '
        f'data-columns="{columns}" '
        f'data-gap="{gap}" '
        f'data-style="{style}" '
        f'data-variant="navigation" '
        f'data-layout="{layout}">\n'
        f"{''.join(cards_html)}"
        f"</div>\n"
    )

    logger.debug("child_cards_rendered", count=len(children), page=str(current_page.source_path))
    return html


def _render_child_card(child: dict[str, Any], fields: list[str], layout: str) -> str:
    """Render a single card for a child section/page."""
    title = child.get("title", "") if "title" in fields else ""
    description = child.get("description", "") if "description" in fields else ""
    icon = child.get("icon", "") if "icon" in fields else ""
    url = child.get("url", "")
    child_type = child.get("type", "page")  # "section" or "page"

    # Fallback icon based on type (matches theme template icons)
    if not icon and "icon" in fields:
        icon = "folder" if child_type == "section" else "file"

    # Build card classes
    classes = ["card"]
    if layout:
        classes.append(f"card-layout-{layout}")
    class_str = " ".join(classes)

    parts = [f'<a class="{class_str}" href="{_escape_html(url)}">']

    # Card header (icon and title)
    if icon or title:
        parts.append('  <div class="card-header">')
        if icon:
            # Always use SVG icons (Phosphor icons) - no emoji fallback
            rendered_icon = _render_icon(icon, use_svg=True)
            if rendered_icon:
                parts.append(f'    <span class="card-icon" data-icon="{_escape_html(icon)}">')
                parts.append(f"      {rendered_icon}")
                parts.append("    </span>")
        if title:
            parts.append(f'    <div class="card-title">{_escape_html(title)}</div>')
        parts.append("  </div>")

    # Card content (description)
    if description:
        parts.append('  <div class="card-content">')
        parts.append(f"    <p>{_escape_html(description)}</p>")
        parts.append("  </div>")

    parts.append("</a>")

    return "\n".join(parts) + "\n"


def _get_section_url(section: Any) -> str:
    """Get URL for a section (uses index_page if available)."""
    if hasattr(section, "index_page") and section.index_page:
        return getattr(section.index_page, "url", "/")
    # Fallback: construct from path
    path = getattr(section, "path", None)
    if path:
        return f"/{path}/"
    return "/"
