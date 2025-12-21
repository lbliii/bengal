"""
Legacy grid directive compatibility layer.

Converts old grid and grid-item-card syntax to modern cards syntax.
"""

from __future__ import annotations

from re import Match
from typing import Any, ClassVar

from mistune.directives import DirectivePlugin

from bengal.directives.cards.card import CardDirective
from bengal.directives.cards.cards_grid import CardsDirective
from bengal.directives.cards.utils import (
    convert_legacy_columns,
    convert_legacy_gutter,
    extract_octicon,
)

__all__ = ["GridDirective", "GridItemCardDirective"]


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

        columns = convert_legacy_columns(title)
        gap = convert_legacy_gutter(options.get("gutter", ""))

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
            md.renderer.register("cards_grid", CardsDirective().render)


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
        icon, clean_title = extract_octicon(title)

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
            md.renderer.register("card", CardDirective().render)
