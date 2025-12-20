"""Card directives for card grids and layouts."""

from __future__ import annotations

from bengal.rendering.plugins.directives.cards import (
    CardDirective,
    CardsDirective,
    ChildCardsDirective,
    GridDirective,
    GridItemCardDirective,
)

__all__ = [
    "CardsDirective",
    "CardDirective",
    "ChildCardsDirective",
    "GridDirective",
    "GridItemCardDirective",
]

# Combined directive names from all card-related directives
DIRECTIVE_NAMES = (
    CardsDirective.DIRECTIVE_NAMES
    + CardDirective.DIRECTIVE_NAMES
    + ChildCardsDirective.DIRECTIVE_NAMES
    + GridDirective.DIRECTIVE_NAMES
    + GridItemCardDirective.DIRECTIVE_NAMES
)
