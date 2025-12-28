"""Built-in directive handlers.

Provides commonly-used directives out of the box:
    - Admonitions: note, warning, tip, danger, error, info, example, success, caution, seealso
    - Dropdown: collapsible content with icons, badges, colors
    - Tabs: tab-set and tab-item with sync and CSS state machine modes
    - Container: generic wrapper div with custom classes
    - Steps: numbered step-by-step guides with contracts
    - Cards: grid layout with card, cards, and child-cards directives
    - Checklist: styled lists with progress tracking
    - Media: figure, audio, and gallery directives
    - Tables: list-table directive for MyST-style tables
"""

from __future__ import annotations

from bengal.rendering.parsers.patitas.directives.builtins.admonition import (
    AdmonitionDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.cards import (
    CardDirective,
    CardsDirective,
    ChildCardsDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.checklist import (
    ChecklistDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.container import (
    ContainerDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.dropdown import (
    DropdownDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.media import (
    AudioDirective,
    FigureDirective,
    GalleryDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.steps import (
    StepDirective,
    StepsDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.tables import (
    ListTableDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.tabs import (
    TabItemDirective,
    TabSetDirective,
)

__all__ = [
    "AdmonitionDirective",
    "AudioDirective",
    "CardDirective",
    "CardsDirective",
    "ChecklistDirective",
    "ChildCardsDirective",
    "ContainerDirective",
    "DropdownDirective",
    "FigureDirective",
    "GalleryDirective",
    "ListTableDirective",
    "StepDirective",
    "StepsDirective",
    "TabItemDirective",
    "TabSetDirective",
]
