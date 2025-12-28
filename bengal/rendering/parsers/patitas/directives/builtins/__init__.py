"""Built-in directive handlers.

Provides commonly-used directives out of the box:
    - Admonitions: note, warning, tip, danger, error, info, example, success, caution, seealso
    - Dropdown: collapsible content with icons, badges, colors
    - Tabs: tab-set and tab-item with sync and CSS state machine modes
    - Container: generic wrapper div with custom classes
    - Steps: numbered step-by-step guides with contracts
"""

from __future__ import annotations

from bengal.rendering.parsers.patitas.directives.builtins.admonition import (
    AdmonitionDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.container import (
    ContainerDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.dropdown import (
    DropdownDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.steps import (
    StepDirective,
    StepsDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.tabs import (
    TabItemDirective,
    TabSetDirective,
)

__all__ = [
    "AdmonitionDirective",
    "ContainerDirective",
    "DropdownDirective",
    "StepDirective",
    "StepsDirective",
    "TabItemDirective",
    "TabSetDirective",
]
