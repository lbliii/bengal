"""Cards directive system for grid layouts.

Provides:
- cards: Container grid for card elements
- card: Individual card with link, icon, badge, etc.
- child-cards: Auto-generate cards from child pages

Use cases:
- Navigation card grids (documentation landing pages)
- Feature showcases
- Auto-generated section indexes

Example:
::::{cards}
:columns: 3

:::{card} Getting Started
:icon: rocket
:link: /docs/quickstart/

Quick introduction to the platform.
:::

:::{card} API Reference
:icon: book
:link: /docs/api/

Complete API documentation.
:::
::::

Thread Safety:
Stateless handlers. Safe for concurrent use across threads.

HTML Output:
Matches Bengal's cards directive exactly for parity.

"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape as html_escape
from typing import TYPE_CHECKING, Any, ClassVar

from patitas.nodes import Directive

from bengal.parsing.backends.patitas.directives.contracts import (
    CARD_CONTRACT,
    CARDS_CONTRACT,
    DirectiveContract,
)
from bengal.parsing.backends.patitas.directives.options import StyledOptions

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder

__all__ = [
    "CardDirective",
    "CardOptions",
    "CardsDirective",
    "CardsOptions",
    "ChildCardsDirective",
    "ChildCardsOptions",
]


# =============================================================================
# Valid option values
# =============================================================================

VALID_LAYOUTS = frozenset(["default", "horizontal", "portrait", "compact"])
VALID_GAPS = frozenset(["small", "medium", "large"])
VALID_STYLES = frozenset(["default", "minimal", "bordered"])
VALID_COLORS = frozenset(
    [
        "blue",
        "green",
        "red",
        "yellow",
        "orange",
        "purple",
        "gray",
        "pink",
        "indigo",
        "teal",
        "cyan",
        "violet",
    ]
)


# =============================================================================
# Utility functions
# =============================================================================


def normalize_columns(columns: str) -> str:
    """Normalize columns specification.

    Args:
        columns: Raw columns value (auto, 1-6, or responsive like 1-2-3)

    Returns:
        Normalized columns string

    """
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


def _render_icon(icon_name: str, card_title: str = "") -> str:
    """Render icon using Bengal SVG icons.

    Args:
        icon_name: Name of the icon to render
        card_title: Title of the card (for warning context)

    Returns:
        SVG HTML string, or empty string if not found

    """
    try:
        from bengal.icons.svg import render_icon, warn_missing_icon

        icon_html = render_icon(icon_name, size=20)

        if not icon_html and icon_name:
            warn_missing_icon(icon_name, directive="card", context=card_title)

        return icon_html or ""
    except ImportError:
        return ""


def _resolve_link(
    link: str,
    xref_index: dict[str, Any],
    current_page_dir: str | None = None,
) -> tuple[str, Any]:
    """Resolve a link reference to a URL and page object.

    Handles explicit prefixes:
    - id:page-id -> Look up by page ID in xref_index["by_id"]
    - path:/docs/page/ -> Look up by path in xref_index["by_path"]
    - slug:page-slug -> Look up by slug in xref_index["by_slug"]

    And implicit resolution (no prefix):
    - ./ and ../ -> resolve via resolve_page with current_page_dir
    - Links containing "/" but not starting with "http" -> try by_path
    - Other links -> try by_slug

    Args:
        link: Link string (may include id:, path:, or slug: prefix)
        xref_index: Cross-reference index with by_id, by_path, by_slug dicts
        current_page_dir: Content-relative directory for resolving ./ and ../

    Returns:
        Tuple of (resolved_url, page_object or None)
    """
    if not link:
        return "", None

    # Relative paths (./ and ../) require current_page_dir
    if link.startswith(("./", "../")) and current_page_dir:
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
                parent = (
                    "/".join(parts[:-up_count]) if up_count > 0 else current_page_dir
                )
                resolved_path = f"{parent}/{remaining}" if remaining else parent
            else:
                resolved_path = remaining
        page = xref_index.get("by_path", {}).get(resolved_path)
        if page:
            url = getattr(page, "href", None) or getattr(page, "url", "")
            return url, page

    # Check for explicit prefixes
    if link.startswith("id:"):
        page_id = link[3:]
        by_id = xref_index.get("by_id", {})
        page = by_id.get(page_id)
        if page:
            # Get URL from page object - try href first (canonical), then url
            url = getattr(page, "href", None) or getattr(page, "url", "")
            return url, page
        return link, None  # Return original if not found

    if link.startswith("path:"):
        page_path = link[5:]
        by_path = xref_index.get("by_path", {})
        page = by_path.get(page_path)
        if page:
            url = getattr(page, "href", None) or getattr(page, "url", "")
            return url, page
        return link, None

    if link.startswith("slug:"):
        page_slug = link[5:]
        by_slug = xref_index.get("by_slug", {})
        pages = by_slug.get(page_slug, [])
        if pages:
            page = pages[0] if isinstance(pages, list) else pages
            url = getattr(page, "href", None) or getattr(page, "url", "")
            return url, page
        return link, None

    # Skip external URLs (http://, https://, //, etc.)
    if link.startswith(("http://", "https://", "//", "mailto:", "tel:")):
        return link, None

    # Skip absolute URLs that start with /
    if link.startswith("/"):
        return link, None

    # Implicit resolution: try path first for links containing "/"
    if "/" in link:
        by_path = xref_index.get("by_path", {})
        page = by_path.get(link)
        if page:
            url = getattr(page, "href", None) or getattr(page, "url", "")
            return url, page

    # Implicit resolution: try slug for simple strings
    by_slug = xref_index.get("by_slug", {})
    pages = by_slug.get(link, [])
    if pages:
        page = pages[0] if isinstance(pages, list) else pages
        url = getattr(page, "href", None) or getattr(page, "url", "")
        return url, page

    # Return original link if no resolution found
    return link, None


def _pull_from_page(
    page: Any, pull_fields: list[str], title: str, description: str, icon: str
) -> tuple[str, str, str]:
    """Pull data from a linked page based on pull_fields.

    Args:
        page: Page object to pull data from
        pull_fields: List of fields to pull (title, description, icon)
        title: Current title (may be overwritten)
        description: Current description (may be overwritten)
        icon: Current icon (may be overwritten)

    Returns:
        Tuple of (title, description, icon) with pulled values
    """
    for field in pull_fields:
        field = field.lower().strip()

        if field == "title" and not title:
            # Pull title from page
            pulled_title = getattr(page, "title", "")
            if pulled_title:
                title = pulled_title

        elif field == "description" and not description:
            # Pull description from page metadata
            metadata = getattr(page, "metadata", {})
            if isinstance(metadata, dict):
                pulled_desc = metadata.get("description", "")
                if pulled_desc:
                    description = pulled_desc

        elif field == "icon" and not icon:
            # Pull icon from page metadata
            metadata = getattr(page, "metadata", {})
            if isinstance(metadata, dict):
                pulled_icon = metadata.get("icon", "")
                if pulled_icon:
                    icon = pulled_icon

    return title, description, icon


# =============================================================================
# Options classes
# =============================================================================


@dataclass(frozen=True, slots=True)
class CardsOptions(StyledOptions):
    """Options for cards grid directive.

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


@dataclass(frozen=True, slots=True)
class CardOptions(StyledOptions):
    """Options for individual card directive.

    Attributes:
        icon: Icon name
        link: URL or page reference
        description: Brief summary shown below the title
        badge: Badge text (e.g., "New", "Beta", "Pro")
        color: Color theme (blue, green, red, etc.)
        image: Header image URL
        footer: Footer content
        pull: Fields to pull from linked page (comma-separated)
        layout: Layout override (default, horizontal, portrait, compact)

    """

    icon: str = ""
    link: str = ""
    description: str = ""
    badge: str = ""
    color: str = ""
    image: str = ""
    footer: str = ""
    pull: str = ""
    layout: str = ""


@dataclass(frozen=True, slots=True)
class ChildCardsOptions(StyledOptions):
    """Options for child-cards directive.

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


# =============================================================================
# Cards grid directive
# =============================================================================


class CardsDirective:
    """Handler for cards grid container directive.

    Creates a responsive grid of cards with sensible defaults.

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    names: ClassVar[tuple[str, ...]] = ("cards",)
    token_type: ClassVar[str] = "cards_grid"
    contract: ClassVar[DirectiveContract | None] = CARDS_CONTRACT
    options_class: ClassVar[type[CardsOptions]] = CardsOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: CardsOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build cards grid AST node."""
        # Normalize and validate options
        normalized_opts = CardsOptions(
            columns=normalize_columns(options.columns),
            gap=options.gap if options.gap in VALID_GAPS else "medium",
            style=options.style if options.style in VALID_STYLES else "default",
            variant=options.variant,
            layout=options.layout if options.layout in VALID_LAYOUTS else "default",
            class_=options.class_,
        )

        return Directive(
            location=location,
            name=name,
            title=title,
            options=normalized_opts,  # Pass typed options directly
            children=tuple(children),
        )

    def render(
        self,
        node: Directive[CardsOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render cards grid container to HTML."""
        opts = node.options  # Direct typed access!

        columns = opts.columns
        gap = opts.gap
        style = opts.style
        variant = opts.variant
        layout = opts.layout

        sb.append(
            f'<div class="card-grid" '
            f'data-columns="{html_escape(columns)}" '
            f'data-gap="{html_escape(gap)}" '
            f'data-style="{html_escape(style)}" '
            f'data-variant="{html_escape(variant)}" '
            f'data-layout="{html_escape(layout)}">\n'
        )
        sb.append(rendered_children)
        sb.append("</div>\n")


# =============================================================================
# Card directive
# =============================================================================


class CardDirective:
    """Handler for individual card directive.

    Renders a single card with optional link, icon, badge, etc.

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    names: ClassVar[tuple[str, ...]] = ("card",)
    token_type: ClassVar[str] = "card"
    contract: ClassVar[DirectiveContract | None] = CARD_CONTRACT
    options_class: ClassVar[type[CardOptions]] = CardOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: CardOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build card AST node."""
        # Check for +++ footer separator in content
        footer = options.footer
        if not footer and ("+++" in content):
            parts = content.split("+++", 1)
            footer = parts[1].strip() if len(parts) > 1 else ""

        # Parse pull fields
        pull_fields = [f.strip() for f in options.pull.split(",") if f.strip()]

        # Validate color and layout, create normalized options
        from dataclasses import replace

        normalized_opts = replace(
            options,
            color=options.color if options.color in VALID_COLORS else "",
            layout=options.layout if options.layout in VALID_LAYOUTS else "",
            footer=footer,
            pull=",".join(pull_fields),
        )

        return Directive(
            location=location,
            name=name,
            title=title,
            options=normalized_opts,  # Pass typed options directly
            children=tuple(children),
        )

    def render(
        self,
        node: Directive[CardOptions],
        rendered_children: str,
        sb: StringBuilder,
        *,
        xref_index: dict[str, Any] | None = None,
        current_page_dir: str | None = None,
    ) -> None:
        """Render individual card to HTML.

        Args:
            node: The card directive AST node
            rendered_children: Pre-rendered child content
            sb: StringBuilder to append output
            xref_index: Optional cross-reference index for link resolution
            current_page_dir: Content-relative directory for resolving ./ and ../
        """
        opts = node.options  # Direct typed access!

        # Title comes from node.title (directive title)
        title = node.title or ""
        icon = opts.icon
        link = opts.link
        description = opts.description
        badge = opts.badge
        color = opts.color
        image = opts.image
        footer = opts.footer
        layout = opts.layout
        pull_fields = [f.strip() for f in opts.pull.split(",") if f.strip()]

        # Resolve link and pull data from linked page if xref_index is available
        resolved_link = link
        linked_page = None
        if link and xref_index:
            resolved_link, linked_page = _resolve_link(
                link, xref_index, current_page_dir
            )

        # Pull data from linked page
        if linked_page and pull_fields:
            title, description, icon = _pull_from_page(
                linked_page, pull_fields, title, description, icon
            )

        # Card wrapper (link or div)
        if resolved_link:
            card_tag = "a"
            card_attrs_str = f' href="{html_escape(resolved_link)}"'
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
        sb.append(f'<{card_tag} class="{class_str}"{card_attrs_str}>\n')

        # Header image
        if image:
            sb.append(
                f'  <img class="card-image" src="{html_escape(image)}" '
                f'alt="{html_escape(title)}" loading="lazy">\n'
            )

        # Card header with optional badge
        if icon or title or badge:
            sb.append('  <div class="card-header">\n')
            if icon:
                rendered_icon = _render_icon(icon, card_title=title)
                if rendered_icon:
                    sb.append(f'    <span class="card-icon" data-icon="{html_escape(icon)}">\n')
                    sb.append(f"      {rendered_icon}\n")
                    sb.append("    </span>\n")
            if title:
                sb.append(f'    <div class="card-title">{html_escape(title)}</div>\n')
            if badge:
                sb.append(f'    <span class="card-badge">{html_escape(badge)}</span>\n')
            sb.append("  </div>\n")

        # Description (brief summary below header)
        if description:
            sb.append(f'  <div class="card-description">{html_escape(description)}</div>\n')

        # Card content
        if rendered_children.strip():
            sb.append('  <div class="card-content">\n')
            sb.append(f"    {rendered_children}")
            sb.append("  </div>\n")

        # Footer
        if footer:
            sb.append('  <div class="card-footer">\n')
            sb.append(f"    {footer}\n")
            sb.append("  </div>\n")

        sb.append(f"</{card_tag}>\n")


# =============================================================================
# Child cards directive
# =============================================================================


class ChildCardsDirective:
    """Handler for child-cards directive.

    Auto-generates cards from current page's child sections/pages.
    Requires render context with current page information.

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    names: ClassVar[tuple[str, ...]] = ("child-cards",)
    token_type: ClassVar[str] = "child_cards"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[ChildCardsOptions]] = ChildCardsOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: ChildCardsOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build child-cards AST node."""
        fields = [f.strip() for f in options.fields.split(",") if f.strip()]

        # Normalize and validate options
        from dataclasses import replace

        normalized_opts = replace(
            options,
            gap=options.gap if options.gap in VALID_GAPS else "medium",
            include=options.include if options.include in ("sections", "pages", "all") else "all",
            fields=",".join(fields),
            layout=options.layout if options.layout in VALID_LAYOUTS else "default",
            style=options.style if options.style in VALID_STYLES else "default",
        )

        return Directive(
            location=location,
            name=name,
            title=title,
            options=normalized_opts,  # Pass typed options directly
            children=(),  # No children - auto-generated at render time
        )

    def render(
        self,
        node: Directive[ChildCardsOptions],
        rendered_children: str,
        sb: StringBuilder,
        *,
        page_context: Any | None = None,
    ) -> None:
        """Render child cards by walking the page object tree.

        Args:
            node: Directive AST node with options
            rendered_children: Pre-rendered children HTML (unused)
            sb: StringBuilder for output
            page_context: Page object from renderer (for section/children access)
        """
        from bengal.parsing.backends.patitas.directives.builtins.cards_utils import (
            collect_children,
            render_child_card,
        )

        opts = node.options  # Direct typed access!

        columns = opts.columns
        gap = opts.gap
        style = opts.style
        layout = opts.layout
        include = opts.include
        fields = [f.strip() for f in opts.fields.split(",") if f.strip()]

        def no_content(message: str) -> None:
            """Render empty state with message."""
            sb.append(
                f'<div class="card-grid" '
                f'data-columns="{html_escape(columns)}" '
                f'data-gap="{html_escape(gap)}" '
                f'data-style="{html_escape(style)}" '
                f'data-variant="navigation" '
                f'data-layout="{html_escape(layout)}">\n'
            )
            sb.append(f"  <p><em>{html_escape(message)}</em></p>\n")
            sb.append("</div>\n")

        # Check for page context
        if not page_context:
            no_content("No page context available")
            return

        # Get section from page
        section = getattr(page_context, "_section", None)
        if not section:
            no_content("Page has no section")
            return

        # Collect children from section
        children_items = collect_children(section, page_context, include)

        if not children_items:
            no_content("No child content found")
            return

        # Start card grid
        sb.append(
            f'<div class="card-grid" '
            f'data-columns="{html_escape(columns)}" '
            f'data-gap="{html_escape(gap)}" '
            f'data-style="{html_escape(style)}" '
            f'data-variant="navigation" '
            f'data-layout="{html_escape(layout)}">\n'
        )

        # Generate cards
        for child in children_items:
            card_html = render_child_card(child, fields, layout, html_escape)
            sb.append(card_html)

        sb.append("</div>\n")
