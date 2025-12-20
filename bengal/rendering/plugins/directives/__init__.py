"""
Mistune directives package.

DEPRECATED: All directive implementations have moved to bengal.directives.
This module re-exports for backwards compatibility.

Import directly from bengal.directives for new code:
    from bengal.directives import create_documentation_directives
    from bengal.directives import BengalDirective, DirectiveToken
"""

from __future__ import annotations

# Re-export everything from the new location
from bengal.directives import (
    DIRECTIVE_CLASSES,
    KNOWN_DIRECTIVE_NAMES,
    create_documentation_directives,
    get_directive,
    get_known_directive_names,
    register_all,
)

# Directive classes
from bengal.directives.admonitions import AdmonitionDirective
from bengal.directives.badge import BadgeDirective
from bengal.directives.base import (
    CARD_CONTRACT,
    CARDS_CONTRACT,
    CODE_TABS_CONTRACT,
    STEP_CONTRACT,
    STEPS_CONTRACT,
    TAB_ITEM_CONTRACT,
    TAB_SET_CONTRACT,
    BengalDirective,
    ContainerOptions,
    ContractValidator,
    ContractViolation,
    DirectiveContract,
    DirectiveError,
    DirectiveOptions,
    DirectiveToken,
    StyledOptions,
    TitledOptions,
    attr_str,
    bool_attr,
    build_class_string,
    class_attr,
    data_attrs,
    escape_html,
    format_directive_error,
)
from bengal.directives.build import BuildDirective
from bengal.directives.button import ButtonDirective
from bengal.directives.cache import (
    DirectiveCache,
    clear_cache,
    configure_cache,
    get_cache,
    get_cache_stats,
)
from bengal.directives.cards import (
    CardDirective,
    CardsDirective,
    ChildCardsDirective,
    GridDirective,
    GridItemCardDirective,
)
from bengal.directives.checklist import ChecklistDirective
from bengal.directives.code_tabs import CodeTabsDirective
from bengal.directives.container import ContainerDirective
from bengal.directives.data_table import DataTableDirective
from bengal.directives.dropdown import DropdownDirective
from bengal.directives.embed import (
    CodePenDirective,
    CodeSandboxDirective,
    GistDirective,
    StackBlitzDirective,
)
from bengal.directives.example_label import ExampleLabelDirective
from bengal.directives.fenced import FencedDirective
from bengal.directives.figure import AudioDirective, FigureDirective
from bengal.directives.glossary import GlossaryDirective
from bengal.directives.icon import IconDirective
from bengal.directives.include import IncludeDirective
from bengal.directives.list_table import ListTableDirective
from bengal.directives.literalinclude import LiteralIncludeDirective
from bengal.directives.marimo import MarimoCellDirective
from bengal.directives.navigation import (
    BreadcrumbsDirective,
    PrevNextDirective,
    RelatedDirective,
    SiblingsDirective,
)
from bengal.directives.rubric import RubricDirective
from bengal.directives.steps import StepDirective, StepsDirective
from bengal.directives.tabs import TabItemDirective, TabSetDirective
from bengal.directives.target import TargetDirective
from bengal.directives.terminal import AsciinemaDirective
from bengal.directives.validator import DirectiveSyntaxValidator
from bengal.directives.versioning import (
    ChangedDirective,
    DeprecatedDirective,
    SinceDirective,
)
from bengal.directives.video import (
    SelfHostedVideoDirective,
    VimeoDirective,
    YouTubeDirective,
)

# Admonition types subset (for type-specific validation)
ADMONITION_TYPES: frozenset[str] = frozenset(
    {
        "note",
        "tip",
        "warning",
        "danger",
        "error",
        "info",
        "example",
        "success",
        "caution",
        "seealso",
    }
)

# Code-related directives (can use backtick fences)
CODE_BLOCK_DIRECTIVES: frozenset[str] = frozenset(
    {
        "code-tabs",
        "literalinclude",
    }
)

__all__ = [
    # Factory function
    "create_documentation_directives",
    # Registry constants and functions
    "DIRECTIVE_CLASSES",
    "KNOWN_DIRECTIVE_NAMES",
    "get_directive",
    "get_known_directive_names",
    "register_all",
    "ADMONITION_TYPES",
    "CODE_BLOCK_DIRECTIVES",
    # Directive System v2 - Foundation Classes
    "BengalDirective",
    "DirectiveToken",
    "DirectiveOptions",
    "DirectiveContract",
    "ContractValidator",
    "ContractViolation",
    # Preset Options
    "StyledOptions",
    "ContainerOptions",
    "TitledOptions",
    # Preset Contracts
    "STEPS_CONTRACT",
    "STEP_CONTRACT",
    "TAB_SET_CONTRACT",
    "TAB_ITEM_CONTRACT",
    "CARDS_CONTRACT",
    "CARD_CONTRACT",
    "CODE_TABS_CONTRACT",
    # Utilities
    "escape_html",
    "build_class_string",
    "bool_attr",
    "data_attrs",
    "attr_str",
    "class_attr",
    # Cache
    "DirectiveCache",
    "clear_cache",
    "configure_cache",
    "get_cache",
    "get_cache_stats",
    # Fenced
    "FencedDirective",
    # Validator
    "DirectiveSyntaxValidator",
    # Error handling
    "DirectiveError",
    "format_directive_error",
    # All directive classes
    "AdmonitionDirective",
    "BadgeDirective",
    "BuildDirective",
    "ButtonDirective",
    "CardDirective",
    "CardsDirective",
    "ChildCardsDirective",
    "GridDirective",
    "GridItemCardDirective",
    "ChecklistDirective",
    "CodeTabsDirective",
    "ContainerDirective",
    "DataTableDirective",
    "DropdownDirective",
    "CodePenDirective",
    "CodeSandboxDirective",
    "GistDirective",
    "StackBlitzDirective",
    "ExampleLabelDirective",
    "AudioDirective",
    "FigureDirective",
    "GlossaryDirective",
    "IconDirective",
    "IncludeDirective",
    "ListTableDirective",
    "LiteralIncludeDirective",
    "MarimoCellDirective",
    "BreadcrumbsDirective",
    "PrevNextDirective",
    "RelatedDirective",
    "SiblingsDirective",
    "RubricDirective",
    "StepDirective",
    "StepsDirective",
    "TabItemDirective",
    "TabSetDirective",
    "TargetDirective",
    "AsciinemaDirective",
    "ChangedDirective",
    "DeprecatedDirective",
    "SinceDirective",
    "SelfHostedVideoDirective",
    "VimeoDirective",
    "YouTubeDirective",
]
