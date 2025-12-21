"""
Cards directive system for Bengal SSG.

Provides a modern, simple card grid system with auto-layout and responsive columns.

This is a package containing the cards, card, and child-cards directives.

Components:
    - CardsDirective: Grid container for cards
    - CardDirective: Individual card with optional link, icon, image
    - ChildCardsDirective: Auto-generate cards from child sections/pages

Syntax (preferred - named closers):

```markdown
:::{cards}
:columns: 3
:gap: medium

:::{card} Card Title
:icon: book
:link: /docs/
:description: Brief summary shown below the title
:badge: New
Card content with **markdown** support.
:::{/card}
:::{/cards}
```
"""

from __future__ import annotations

from bengal.directives.cards.card import CardDirective, CardOptions
from bengal.directives.cards.cards_grid import CardsDirective, CardsOptions
from bengal.directives.cards.child_cards import ChildCardsDirective, ChildCardsOptions
from bengal.directives.cards.utils import (
    VALID_COLORS,
    VALID_GAPS,
    VALID_LAYOUTS,
    VALID_STYLES,
)

__all__ = [
    # Main directives
    "CardsDirective",
    "CardDirective",
    "ChildCardsDirective",
    # Options classes
    "CardsOptions",
    "CardOptions",
    "ChildCardsOptions",
    # Utilities
    "VALID_COLORS",
    "VALID_GAPS",
    "VALID_LAYOUTS",
    "VALID_STYLES",
]
