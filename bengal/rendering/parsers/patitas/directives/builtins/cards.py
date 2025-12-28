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
from typing import TYPE_CHECKING, ClassVar

from bengal.rendering.parsers.patitas.directives.contracts import (
    CARD_CONTRACT,
    CARDS_CONTRACT,
    DirectiveContract,
)
from bengal.rendering.parsers.patitas.directives.options import StyledOptions
from bengal.rendering.parsers.patitas.nodes import Directive

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation
    from bengal.rendering.parsers.patitas.nodes import Block
    from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder

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
        from bengal.directives._icons import render_icon, warn_missing_icon

        icon_html = render_icon(icon_name, size=20)

        if not icon_html and icon_name:
            warn_missing_icon(icon_name, directive="card", context=card_title)

        return icon_html or ""
    except ImportError:
        return ""  # Graceful fallback if icons not available


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
    ) -> None:
        """Render individual card to HTML."""
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

        # Card wrapper (link or div)
        if link:
            card_tag = "a"
            card_attrs_str = f' href="{html_escape(link)}"'
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
    ) -> None:
        """Render child cards by walking the page object tree.

        Note: This requires render context with current_page and section
        information. Without it, renders an empty placeholder.
        """
        opts = node.options  # Direct typed access!

        columns = opts.columns
        gap = opts.gap
        style = opts.style
        layout = opts.layout

        # Placeholder - actual child page discovery requires render context
        # which is injected by the renderer when available
        sb.append(
            f'<div class="card-grid" '
            f'data-columns="{html_escape(columns)}" '
            f'data-gap="{html_escape(gap)}" '
            f'data-style="{html_escape(style)}" '
            f'data-variant="navigation" '
            f'data-layout="{html_escape(layout)}">\n'
        )
        sb.append("  <p><em>Child cards will be generated at build time.</em></p>\n")
        sb.append("</div>\n")
