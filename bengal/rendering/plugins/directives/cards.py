"""
Cards directive for Bengal SSG.

Provides a modern, simple card grid system with auto-layout and responsive columns.

Architecture:
    Migrated to BengalDirective base class with DirectiveContract validation.
    - CardsDirective: allows card children
    - CardDirective: requires_parent=["cards_grid"] (optional, not enforced)

Syntax:
    ::::{cards}
    :columns: 3
    :gap: medium

    :::{card} Card Title
    :icon: book
    :link: /docs/
    Card content
    :::
    ::::
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from re import Match
from typing import Any, ClassVar

from mistune.directives import DirectivePlugin

from bengal.rendering.plugins.directives.base import BengalDirective
from bengal.rendering.plugins.directives.contracts import (
    CARD_CONTRACT,
    CARDS_CONTRACT,
    DirectiveContract,
)
from bengal.rendering.plugins.directives.options import DirectiveOptions
from bengal.rendering.plugins.directives.tokens import DirectiveToken
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = [
    "CardDirective",
    "CardsDirective",
    "ChildCardsDirective",
    "GridDirective",
    "GridItemCardDirective",
    "CardsOptions",
    "CardOptions",
    "ChildCardsOptions",
]

# Valid layout options
VALID_LAYOUTS = frozenset(["default", "horizontal", "portrait", "compact"])
VALID_GAPS = frozenset(["small", "medium", "large"])
VALID_STYLES = frozenset(["default", "minimal", "bordered"])
VALID_COLORS = frozenset([
    "blue", "green", "red", "yellow", "orange", "purple", "gray", "pink", "indigo"
])


# =============================================================================
# Cards Grid Container Directive
# =============================================================================


@dataclass
class CardsOptions(DirectiveOptions):
    """
    Options for cards grid directive.

    Attributes:
        columns: Column layout ("auto", "1-6", or responsive "1-2-3")
        gap: Grid gap (small, medium, large)
        style: Visual style (default, minimal, bordered)
        variant: Card variant (navigation, info, concept)
        layout: Card layout (default, horizontal, portrait, compact)
    """

    columns: str = "auto"
    gap: str = "medium"
    style: str = "default"
    variant: str = "navigation"
    layout: str = "default"

    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "gap": list(VALID_GAPS),
        "style": list(VALID_STYLES),
        "layout": list(VALID_LAYOUTS),
    }


class CardsDirective(BengalDirective):
    """
    Cards grid container directive.

    Creates a responsive grid of cards with sensible defaults.

    Syntax:
        ::::{cards}
        :columns: 3
        :gap: medium
        :style: default
        :variant: navigation
        :layout: default

        :::{card} Title
        Content
        :::
        ::::

    Columns accept:
        - "auto" - Auto-fit layout
        - "2", "3", "4" - Fixed columns
        - "1-2-3" - Responsive (mobile-tablet-desktop)
    """

    NAMES: ClassVar[list[str]] = ["cards"]
    TOKEN_TYPE: ClassVar[str] = "cards_grid"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = CardsOptions

    # Contract: cards can have card children (optional, not strictly required)
    CONTRACT: ClassVar[DirectiveContract] = CARDS_CONTRACT

    DIRECTIVE_NAMES: ClassVar[list[str]] = ["cards"]

    def parse_directive(
        self,
        title: str,
        options: CardsOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build cards grid token."""
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "columns": _normalize_columns(options.columns),
                "gap": options.gap,
                "style": options.style,
                "variant": options.variant,
                "layout": options.layout,
            },
            children=children,
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render cards grid container to HTML."""
        columns = attrs.get("columns", "auto")
        gap = attrs.get("gap", "medium")
        style = attrs.get("style", "default")
        variant = attrs.get("variant", "navigation")
        layout = attrs.get("layout", "default")

        return (
            f'<div class="card-grid" '
            f'data-columns="{columns}" '
            f'data-gap="{gap}" '
            f'data-style="{style}" '
            f'data-variant="{variant}" '
            f'data-layout="{layout}">\n'
            f"{text}"
            f"</div>\n"
        )


# =============================================================================
# Individual Card Directive
# =============================================================================


@dataclass
class CardOptions(DirectiveOptions):
    """
    Options for individual card directive.

    Attributes:
        icon: Icon name
        link: URL or page reference
        color: Color theme (blue, green, red, etc.)
        image: Header image URL
        footer: Footer content
        pull: Fields to pull from linked page (comma-separated)
        layout: Layout override (default, horizontal, portrait, compact)
    """

    icon: str = ""
    link: str = ""
    color: str = ""
    image: str = ""
    footer: str = ""
    pull: str = ""
    layout: str = ""

    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "color": list(VALID_COLORS),
        "layout": [""] + list(VALID_LAYOUTS),  # Empty string allowed
    }


class CardDirective(BengalDirective):
    """
    Individual card directive (nested in cards).

    Syntax:
        :::{card} Card Title
        :icon: book
        :link: /docs/
        :color: blue
        :image: /hero.jpg
        :footer: Updated 2025
        :pull: title, description

        Card content with **markdown** support.
        :::

    Footer separator:
        :::{card} Title
        Body content
        +++
        Footer content
        :::

    Contract:
        Typically nested inside :::{cards}, but can be standalone.
    """

    NAMES: ClassVar[list[str]] = ["card"]
    TOKEN_TYPE: ClassVar[str] = "card"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = CardOptions

    # Contract: card should be inside cards_grid (soft validation)
    CONTRACT: ClassVar[DirectiveContract] = CARD_CONTRACT

    DIRECTIVE_NAMES: ClassVar[list[str]] = ["card"]

    def parse_directive(
        self,
        title: str,
        options: CardOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build card token, handling footer separator."""
        # Check for +++ footer separator
        footer = options.footer
        if not footer and ("+++" in content):
            parts = content.split("+++", 1)
            # Reparse children without footer
            # Note: children already parsed, so we record footer separately
            footer = parts[1].strip() if len(parts) > 1 else ""

        # Parse pull fields
        pull_fields = [f.strip() for f in options.pull.split(",") if f.strip()]

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "title": title or "",
                "icon": options.icon,
                "link": options.link,
                "color": options.color if options.color in VALID_COLORS else "",
                "image": options.image,
                "footer": footer,
                "pull": pull_fields,
                "layout": options.layout if options.layout in VALID_LAYOUTS else "",
            },
            children=children,
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render individual card to HTML."""
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
            if "title" in pull_fields and not title:
                title = pulled.get("title", "")
            if "description" in pull_fields and not text.strip():
                text = f"<p>{self.escape_html(pulled.get('description', ''))}</p>"
            if "icon" in pull_fields and not icon:
                icon = pulled.get("icon", "")
            if "image" in pull_fields and not image:
                image = pulled.get("image", "")

        # Resolve link URL
        resolved_link = _resolve_link_url(renderer, link) if link else ""

        # Card wrapper
        if resolved_link:
            card_tag = "a"
            card_attrs_str = f' href="{self.escape_html(resolved_link)}"'
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

        # Header image
        if image:
            parts.append(
                f'  <img class="card-image" src="{self.escape_html(image)}" '
                f'alt="{self.escape_html(title)}" loading="lazy">'
            )

        # Card header
        if icon or title:
            parts.append('  <div class="card-header">')
            if icon:
                rendered_icon = _render_icon(icon)
                if rendered_icon:
                    parts.append(
                        f'    <span class="card-icon" data-icon="{self.escape_html(icon)}">'
                    )
                    parts.append(rendered_icon)
                    parts.append("    </span>")
            if title:
                parts.append(f'    <div class="card-title">{self.escape_html(title)}</div>')
            parts.append("  </div>")

        # Card content
        if text:
            parts.append('  <div class="card-content">')
            parts.append(f"    {text}")
            parts.append("  </div>")

        # Footer
        if footer:
            parts.append('  <div class="card-footer">')
            parts.append(f"    {footer}")
            parts.append("  </div>")

        parts.append(f"</{card_tag}>")

        return "\n".join(parts) + "\n"


# =============================================================================
# Legacy Grid Directive (backward compatibility)
# =============================================================================


class GridDirective(DirectivePlugin):
    """
    Grid layout compatibility layer.

    Converts legacy grid syntax to modern cards syntax.
    Not migrated to BengalDirective since it's a compatibility shim.

    Old syntax:
        ::::{grid} 1 2 2 2
        :gutter: 1
        ::::
    """

    DIRECTIVE_NAMES: ClassVar[list[str]] = ["grid"]

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
        """Parse grid directive (compatibility mode)."""
        title = self.parse_title(m)
        options = dict(self.parse_options(m))

        columns = _convert_legacy_columns(title)
        gap = _convert_legacy_gutter(options.get("gutter", ""))

        content = self.parse_content(m)
        children = self.parse_tokens(block, content, state)

        return {
            "type": "cards_grid",
            "attrs": {
                "columns": columns,
                "gap": gap,
                "style": "default",
                "variant": "navigation",
                "layout": "default",
            },
            "children": children,
        }

    def __call__(self, directive: Any, md: Any) -> None:
        """Register the directive with mistune."""
        directive.register("grid", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("cards_grid", render_cards_grid)


class GridItemCardDirective(DirectivePlugin):
    """
    Grid item card compatibility layer.

    Converts old syntax to modern card syntax.
    Not migrated to BengalDirective since it's a compatibility shim.
    """

    DIRECTIVE_NAMES: ClassVar[list[str]] = ["grid-item-card"]

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
        """Parse grid-item-card directive (compatibility mode)."""
        title = self.parse_title(m)
        options = dict(self.parse_options(m))
        raw_content = self.parse_content(m)

        # Check for +++ footer separator
        footer_text = ""
        if "\n+++\n" in raw_content or "\n+++" in raw_content:
            parts = raw_content.split("+++", 1)
            content = parts[0].strip()
            footer_text = parts[1].strip() if len(parts) > 1 else ""
        else:
            content = raw_content

        children = self.parse_tokens(block, content, state)

        # Extract icon from octicon syntax
        icon, clean_title = _extract_octicon(title)

        return {
            "type": "card",
            "attrs": {
                "title": clean_title,
                "icon": icon,
                "link": options.get("link", "").strip(),
                "color": "",
                "image": "",
                "footer": footer_text,
                "pull": [],
                "layout": "",
            },
            "children": children,
        }

    def __call__(self, directive: Any, md: Any) -> None:
        """Register the directive with mistune."""
        directive.register("grid-item-card", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("card", render_card)


# =============================================================================
# Child Cards Directive
# =============================================================================


@dataclass
class ChildCardsOptions(DirectiveOptions):
    """
    Options for child-cards directive.

    Attributes:
        columns: Column layout
        gap: Grid gap
        include: What to include (sections, pages, all)
        fields: Fields to pull (comma-separated)
        layout: Card layout
        style: Visual style
    """

    columns: str = "auto"
    gap: str = "medium"
    include: str = "all"
    fields: str = "title, description"
    layout: str = "default"
    style: str = "default"

    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "gap": list(VALID_GAPS),
        "include": ["sections", "pages", "all"],
        "layout": list(VALID_LAYOUTS),
        "style": list(VALID_STYLES),
    }


class ChildCardsDirective(BengalDirective):
    """
    Auto-generate cards from current page's child sections/pages.

    Syntax:
        :::{child-cards}
        :columns: 3
        :include: sections
        :fields: title, description, icon
        :::
    """

    NAMES: ClassVar[list[str]] = ["child-cards"]
    TOKEN_TYPE: ClassVar[str] = "child_cards"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = ChildCardsOptions

    DIRECTIVE_NAMES: ClassVar[list[str]] = ["child-cards"]

    def parse_directive(
        self,
        title: str,
        options: ChildCardsOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build child-cards token."""
        fields = [f.strip() for f in options.fields.split(",") if f.strip()]

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "columns": options.columns,
                "gap": options.gap,
                "include": options.include,
                "fields": fields,
                "layout": options.layout,
                "style": options.style,
            },
            children=[],
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render child cards by walking the page object tree."""
        columns = attrs.get("columns", "auto")
        gap = attrs.get("gap", "medium")
        include = attrs.get("include", "all")
        fields = attrs.get("fields", ["title", "description"])
        layout = attrs.get("layout", "default")
        style = attrs.get("style", "default")

        current_page = getattr(renderer, "_current_page", None)
        if not current_page:
            logger.debug("child_cards_no_current_page")
            return '<div class="card-grid" data-columns="auto"><p><em>No page context available</em></p></div>'

        section = getattr(current_page, "_section", None)
        if not section:
            logger.debug("child_cards_no_section", page=str(current_page.source_path))
            return '<div class="card-grid" data-columns="auto"><p><em>Page has no section</em></p></div>'

        children_items = _collect_children(section, current_page, include)

        if not children_items:
            logger.debug("child_cards_no_children", page=str(current_page.source_path))
            return '<div class="card-grid" data-columns="auto"><p><em>No child content found</em></p></div>'

        # Generate card HTML
        cards_html = []
        for child in children_items:
            card_html = _render_child_card(child, fields, layout, self.escape_html)
            cards_html.append(card_html)

        return (
            f'<div class="card-grid" '
            f'data-columns="{columns}" '
            f'data-gap="{gap}" '
            f'data-style="{style}" '
            f'data-variant="navigation" '
            f'data-layout="{layout}">\n'
            f"{''.join(cards_html)}"
            f"</div>\n"
        )


# =============================================================================
# Helper Functions
# =============================================================================


def _normalize_columns(columns: str) -> str:
    """Normalize columns specification."""
    columns = str(columns).strip()

    if columns in ("auto", ""):
        return "auto"

    if columns.isdigit():
        num = int(columns)
        return str(num) if 1 <= num <= 6 else "auto"

    if "-" in columns:
        parts = columns.split("-")
        if all(p.isdigit() and 1 <= int(p) <= 6 for p in parts) and len(parts) in (2, 3, 4):
            return columns

    return "auto"


def _convert_legacy_columns(title: str) -> str:
    """Convert legacy column breakpoints to our format."""
    if not title:
        return "auto"

    parts = title.strip().split()

    if len(parts) == 1 and parts[0].isdigit():
        return parts[0]

    if len(parts) >= 2:
        valid_parts = [p for p in parts if p.isdigit() and 1 <= int(p) <= 6]
        if valid_parts:
            return "-".join(valid_parts[:4])

    return "auto"


def _convert_legacy_gutter(gutter: str) -> str:
    """Convert legacy gutter to gap format."""
    if not gutter:
        return "medium"

    parts = str(gutter).strip().split()
    if parts and parts[0].isdigit():
        num = int(parts[0])
        if num <= 1:
            return "small"
        elif num >= 3:
            return "large"

    return "medium"


def _extract_octicon(title: str) -> tuple[str, str]:
    """Extract octicon from title."""
    pattern = r"\{octicon\}`([^;`]+)(?:;[^`]*)?`\s*"
    match = re.search(pattern, title)

    if match:
        icon_name = match.group(1).strip()
        clean_title = re.sub(pattern, "", title).strip()
        return icon_name, clean_title

    return "", title


def _pull_from_linked_page(renderer: Any, link: str, fields: list[str]) -> dict[str, Any]:
    """Pull metadata from a linked page."""
    page = None

    # Object tree for relative paths
    if link.startswith("./"):
        current_page = getattr(renderer, "_current_page", None)
        if current_page:
            section = getattr(current_page, "_section", None)
            if section:
                child_name = link[2:].rstrip("/").split("/")[0]

                for subsection in getattr(section, "subsections", []):
                    if getattr(subsection, "name", "") == child_name:
                        page = getattr(subsection, "index_page", None)
                        if page:
                            break

                if not page:
                    for p in getattr(section, "pages", []):
                        source_str = str(getattr(p, "source_path", ""))
                        if f"/{child_name}." in source_str or f"/{child_name}/" in source_str:
                            page = p
                            break

    # Fall back to xref_index
    if not page:
        xref_index = getattr(renderer, "_xref_index", None)
        current_page_dir = getattr(renderer, "_current_page_dir", None)
        if xref_index:
            page = _resolve_page(xref_index, link, current_page_dir)

    if not page:
        return {}

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
        elif field == "icon":
            result["icon"] = page.metadata.get("icon", "") if hasattr(page, "metadata") else ""
        elif field == "image":
            result["image"] = page.metadata.get("image", "") if hasattr(page, "metadata") else ""

    return result


def _resolve_page(
    xref_index: dict[str, Any], link: str, current_page_dir: str | None = None
) -> Any:
    """Resolve a link to a page object."""
    # Relative path
    if link.startswith("./") or link.startswith("../"):
        if current_page_dir:
            clean_link = link.replace(".md", "").rstrip("/")
            if clean_link.startswith("./"):
                resolved_path = f"{current_page_dir}/{clean_link[2:]}"
            else:
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

            page = xref_index.get("by_path", {}).get(resolved_path)
            if page:
                return page
        return None

    # Custom ID
    if link.startswith("id:"):
        return xref_index.get("by_id", {}).get(link[3:])

    # Path lookup
    if "/" in link or link.endswith(".md"):
        clean_path = link.replace(".md", "").strip("/")
        return xref_index.get("by_path", {}).get(clean_path)

    # Slug lookup
    pages = xref_index.get("by_slug", {}).get(link, [])
    return pages[0] if pages else None


def _resolve_link_url(renderer: Any, link: str) -> str:
    """Resolve a link reference to a URL."""
    if link.startswith("/") or link.startswith("http://") or link.startswith("https://"):
        return link

    xref_index = getattr(renderer, "_xref_index", None)
    if not xref_index:
        return link

    current_page_dir = getattr(renderer, "_current_page_dir", None)
    page = _resolve_page(xref_index, link, current_page_dir)

    if page and hasattr(page, "url"):
        return page.url

    return link


def _render_icon(icon_name: str) -> str:
    """Render icon using Bengal SVG icons."""
    from bengal.rendering.plugins.directives._icons import render_icon

    return render_icon(icon_name, size=20)


def _collect_children(
    section: Any, current_page: Any, include: str
) -> list[dict[str, Any]]:
    """Collect child sections/pages from section."""
    children: list[dict[str, Any]] = []

    if include in ("sections", "all"):
        for subsection in getattr(section, "subsections", []):
            children.append({
                "type": "section",
                "title": getattr(subsection, "title", subsection.name),
                "description": (
                    subsection.metadata.get("description", "")
                    if hasattr(subsection, "metadata")
                    else ""
                ),
                "icon": (
                    subsection.metadata.get("icon", "")
                    if hasattr(subsection, "metadata")
                    else ""
                ),
                "url": _get_section_url(subsection),
                "weight": (
                    subsection.metadata.get("weight", 0)
                    if hasattr(subsection, "metadata")
                    else 0
                ),
            })

    if include in ("pages", "all"):
        for page in getattr(section, "pages", []):
            source_str = str(getattr(page, "source_path", ""))
            if source_str.endswith("_index.md") or source_str.endswith("index.md"):
                continue
            if (
                hasattr(current_page, "source_path")
                and hasattr(page, "source_path")
                and page.source_path == current_page.source_path
            ):
                continue
            children.append({
                "type": "page",
                "title": getattr(page, "title", ""),
                "description": (
                    page.metadata.get("description", "")
                    if hasattr(page, "metadata")
                    else ""
                ),
                "icon": page.metadata.get("icon", "") if hasattr(page, "metadata") else "",
                "url": getattr(page, "url", ""),
                "weight": page.metadata.get("weight", 0) if hasattr(page, "metadata") else 0,
            })

    # Sort by weight, then title
    children.sort(key=lambda c: (c.get("weight", 0), c.get("title", "").lower()))
    return children


def _get_section_url(section: Any) -> str:
    """Get URL for a section."""
    if hasattr(section, "index_page") and section.index_page:
        return getattr(section.index_page, "url", "/")
    path = getattr(section, "path", None)
    if path:
        return f"/{path}/"
    return "/"


def _render_child_card(
    child: dict[str, Any],
    fields: list[str],
    layout: str,
    escape_html: Any,
) -> str:
    """Render a single card for a child section/page."""
    title = child.get("title", "") if "title" in fields else ""
    description = child.get("description", "") if "description" in fields else ""
    icon = child.get("icon", "") if "icon" in fields else ""
    url = child.get("url", "")
    child_type = child.get("type", "page")

    # Fallback icon
    if not icon and "icon" in fields:
        icon = "folder" if child_type == "section" else "file"

    classes = ["card"]
    if layout:
        classes.append(f"card-layout-{layout}")
    class_str = " ".join(classes)

    parts = [f'<a class="{class_str}" href="{escape_html(url)}">']

    if icon or title:
        parts.append('  <div class="card-header">')
        if icon:
            rendered_icon = _render_icon(icon)
            if rendered_icon:
                parts.append(f'    <span class="card-icon" data-icon="{escape_html(icon)}">')
                parts.append(f"      {rendered_icon}")
                parts.append("    </span>")
        if title:
            parts.append(f'    <div class="card-title">{escape_html(title)}</div>')
        parts.append("  </div>")

    if description:
        parts.append('  <div class="card-content">')
        parts.append(f"    <p>{escape_html(description)}</p>")
        parts.append("  </div>")

    parts.append("</a>")

    return "\n".join(parts) + "\n"


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
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
# Backward Compatibility Render Functions
# =============================================================================


def render_cards_grid(renderer: Any, text: str, **attrs: Any) -> str:
    """Legacy render function for backward compatibility."""
    return CardsDirective().render(renderer, text, **attrs)


def render_card(renderer: Any, text: str, **attrs: Any) -> str:
    """Legacy render function for backward compatibility."""
    return CardDirective().render(renderer, text, **attrs)


def render_child_cards(renderer: Any, text: str, **attrs: Any) -> str:
    """Legacy render function for backward compatibility."""
    return ChildCardsDirective().render(renderer, text, **attrs)
