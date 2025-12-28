"""Built-in directive handlers.

Provides commonly-used directives out of the box:
    - Admonitions: note, warning, tip, important, caution, attention, danger, error, hint
    - Dropdown: collapsible content
    - Tabs: tab-set and tab-item
    - Code blocks: code-block with highlighting options
    - Images/Figures: enhanced image and figure support
"""

from __future__ import annotations

from bengal.rendering.parsers.patitas.directives.builtins.admonition import (
    AdmonitionDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.dropdown import (
    DropdownDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.tabs import (
    TabItemDirective,
    TabSetDirective,
)

__all__ = [
    "AdmonitionDirective",
    "DropdownDirective",
    "TabSetDirective",
    "TabItemDirective",
]
