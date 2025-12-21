"""
Individual card directive.

Provides a single card component that can be nested in a cards container
or used standalone.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.cards.utils import (
    VALID_COLORS,
    VALID_LAYOUTS,
    pull_from_linked_page,
    render_icon,
    resolve_link_url,
)
from bengal.directives.contracts import CARD_CONTRACT, DirectiveContract
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken

__all__ = ["CardDirective", "CardOptions"]


@dataclass
class CardOptions(DirectiveOptions):
    """
    Options for individual card directive.

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

    Example:
        :::{card} Getting Started
        :icon: rocket
        :link: /docs/quickstart/
        :description: Everything you need to get up and running
        :badge: Updated
        Detailed content here.
        :::{/card}
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
                "description": options.description,
                "badge": options.badge,
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
        description = attrs.get("description", "")
        badge = attrs.get("badge", "")
        color = attrs.get("color", "")
        image = attrs.get("image", "")
        footer = attrs.get("footer", "")
        pull_fields = attrs.get("pull", [])
        layout = attrs.get("layout", "")

        # Pull metadata from linked page if requested
        if link and pull_fields:
            pulled = pull_from_linked_page(renderer, link, pull_fields)
            if "title" in pull_fields and not title:
                title = pulled.get("title", "")
            if "description" in pull_fields and not description:
                description = pulled.get("description", "")
            if "icon" in pull_fields and not icon:
                icon = pulled.get("icon", "")
            if "image" in pull_fields and not image:
                image = pulled.get("image", "")

        # Resolve link URL
        resolved_link = resolve_link_url(renderer, link) if link else ""

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

        # Card header with optional badge
        if icon or title or badge:
            parts.append('  <div class="card-header">')
            if icon:
                rendered_icon = render_icon(icon, card_title=title)
                if rendered_icon:
                    parts.append(
                        f'    <span class="card-icon" data-icon="{self.escape_html(icon)}">'
                    )
                    parts.append(rendered_icon)
                    parts.append("    </span>")
            if title:
                parts.append(f'    <div class="card-title">{self.escape_html(title)}</div>')
            if badge:
                parts.append(f'    <span class="card-badge">{self.escape_html(badge)}</span>')
            parts.append("  </div>")

        # Description (brief summary below header)
        if description:
            parts.append(f'  <div class="card-description">{self.escape_html(description)}</div>')

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
