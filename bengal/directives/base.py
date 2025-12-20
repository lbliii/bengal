"""
Base class for Bengal directives.

Re-exports from the original location for backwards compatibility.
This module will contain the actual implementation after the full migration.

Related:
    - bengal/rendering/plugins/directives/base.py: Original implementation
    - bengal/directives/registry.py: Lazy-loading registry
"""

from __future__ import annotations

# Re-export from original location during migration
from bengal.rendering.plugins.directives.base import BengalDirective
from bengal.rendering.plugins.directives.contracts import (
    CARD_CONTRACT,
    CARDS_CONTRACT,
    CODE_TABS_CONTRACT,
    STEP_CONTRACT,
    STEPS_CONTRACT,
    TAB_ITEM_CONTRACT,
    TAB_SET_CONTRACT,
    ContractValidator,
    ContractViolation,
    DirectiveContract,
)
from bengal.rendering.plugins.directives.errors import (
    DirectiveError,
    format_directive_error,
)
from bengal.rendering.plugins.directives.options import (
    ContainerOptions,
    DirectiveOptions,
    StyledOptions,
    TitledOptions,
)
from bengal.rendering.plugins.directives.tokens import DirectiveToken
from bengal.rendering.plugins.directives.utils import (
    attr_str,
    bool_attr,
    build_class_string,
    class_attr,
    data_attrs,
    escape_html,
)

__all__ = [
    # Base class
    "BengalDirective",
    # Tokens
    "DirectiveToken",
    # Options
    "DirectiveOptions",
    "StyledOptions",
    "ContainerOptions",
    "TitledOptions",
    # Contracts
    "DirectiveContract",
    "ContractValidator",
    "ContractViolation",
    "STEPS_CONTRACT",
    "STEP_CONTRACT",
    "TAB_SET_CONTRACT",
    "TAB_ITEM_CONTRACT",
    "CARDS_CONTRACT",
    "CARD_CONTRACT",
    "CODE_TABS_CONTRACT",
    # Errors
    "DirectiveError",
    "format_directive_error",
    # Utilities
    "escape_html",
    "build_class_string",
    "bool_attr",
    "data_attrs",
    "attr_str",
    "class_attr",
]
