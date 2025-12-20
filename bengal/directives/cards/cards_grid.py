"""
Cards grid container directive.

Creates a responsive grid of cards with sensible defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.cards.utils import (
    VALID_GAPS,
    VALID_LAYOUTS,
    VALID_STYLES,
    normalize_columns,
)
from bengal.directives.contracts import CARDS_CONTRACT, DirectiveContract
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken

__all__ = ["CardsDirective", "CardsOptions"]


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
                "columns": normalize_columns(options.columns),
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
