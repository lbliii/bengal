"""
Cards directive for Bengal SSG.

DEPRECATED: This module has moved to bengal.directives.cards.
Import from bengal.directives.cards instead:

    from bengal.directives.cards import CardsDirective, CardDirective

This module re-exports from the new location for backwards compatibility.
"""

from __future__ import annotations

# Re-export from new location
from bengal.directives.cards import (
    VALID_COLORS,
    VALID_GAPS,
    VALID_LAYOUTS,
    VALID_STYLES,
    CardDirective,
    CardOptions,
    CardsDirective,
    CardsOptions,
    ChildCardsDirective,
    ChildCardsOptions,
    GridDirective,
    GridItemCardDirective,
    render_card,
    render_cards_grid,
    render_child_cards,
)

__all__ = [
    "CardDirective",
    "CardsDirective",
    "ChildCardsDirective",
    "GridDirective",
    "GridItemCardDirective",
    "CardsOptions",
    "CardOptions",
    "ChildCardsOptions",
    "VALID_COLORS",
    "VALID_GAPS",
    "VALID_LAYOUTS",
    "VALID_STYLES",
    "render_card",
    "render_cards_grid",
    "render_child_cards",
]


def __getattr__(name: str) -> object:
    """Emit deprecation warning on attribute access."""
    import warnings

    warnings.warn(
        "bengal.rendering.plugins.directives.cards is deprecated. "
        "Import from bengal.directives.cards instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
