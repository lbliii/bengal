"""
Directive system for Bengal templates.

Implements lazy-loading to prevent performance regression when extracting
directives from the rendering package.

This package provides:
    - Lazy-loading registry for directive classes
    - Base directive class with contract validation
    - All standard Bengal directives (admonitions, tabs, cards, etc.)
    - Factory function for creating Mistune plugin

Architecture:
    Directives are loaded lazily via `get_directive()` to avoid importing
    all directive implementations at package import time. This maintains
    fast startup times while allowing the full directive library to be
    available on demand.

    Note: `create_documentation_directives` is also lazy-loaded to avoid
    circular imports with bengal.rendering.plugins.

Usage:
    from bengal.directives import get_directive, register_all

    # Get a specific directive (lazy-loaded)
    DropdownDirective = get_directive("dropdown")

    # Pre-load all directives (for testing/inspection)
    register_all()

    # Create Mistune plugin with all directives
    from bengal.directives import create_documentation_directives
    md = mistune.create_markdown(plugins=[create_documentation_directives()])

Related:
    - bengal/rendering/plugins/directives/: Original directive location (deprecated)
    - plan/ready/plan-architecture-refactoring.md: Migration plan
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.directives.admonitions import ADMONITION_TYPES
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
from bengal.directives.fenced import FencedDirective
from bengal.directives.registry import (
    KNOWN_DIRECTIVE_NAMES,
    get_directive,
    get_directive_classes,
    get_known_directive_names,
    register_all,
)
from bengal.directives.tokens import DirectiveToken as _DirectiveToken  # noqa: F811

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

# Code-related directives (can use backtick fences)
CODE_BLOCK_DIRECTIVES: frozenset[str] = frozenset(
    {
        "code-tabs",
        "literalinclude",
    }
)

# DIRECTIVE_CLASSES needs to be a property that actually calls the lazy loader
# We can't use module-level __getattr__ because this module already has the attribute
# So we use a lazy-evaluated approach
_directive_classes_cache: list[type] | None = None


def _get_directive_classes() -> list[type]:
    """Get all directive classes, loading them if needed."""
    global _directive_classes_cache
    if _directive_classes_cache is None:
        _directive_classes_cache = get_directive_classes()
    return _directive_classes_cache


# Note: DIRECTIVE_CLASSES is not defined here directly; it's accessed via
# module-level __getattr__ which lazily loads all directive classes.

__all__ = [
    # Factory function for Mistune plugin (lazy-loaded)
    "create_documentation_directives",
    # Registry API
    "DIRECTIVE_CLASSES",
    "KNOWN_DIRECTIVE_NAMES",
    "ADMONITION_TYPES",
    "CODE_BLOCK_DIRECTIVES",
    "get_directive",
    "get_known_directive_names",
    "register_all",
    # Base classes
    "BengalDirective",
    "DirectiveToken",
    "DirectiveOptions",
    "DirectiveContract",
    "ContractValidator",
    "ContractViolation",
    "FencedDirective",
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
    # Error handling
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

# Lazy loading for create_documentation_directives to avoid circular imports
_factory_func: Callable[[], Callable[[Any], None]] | None = None


def create_documentation_directives() -> Callable[[Any], None]:
    """
    Create documentation directives plugin for Mistune.

    Returns a function that can be passed to mistune.create_markdown(plugins=[...]).

    This is a thin wrapper that lazy-loads the actual factory function to avoid
    circular imports between bengal.directives and bengal.rendering.plugins.

    Usage:
        from bengal.directives import create_documentation_directives

        md = mistune.create_markdown(
            plugins=[create_documentation_directives()]
        )
    """
    global _factory_func
    if _factory_func is None:
        from bengal.directives.factory import (
            create_documentation_directives as _create,
        )

        _factory_func = _create
    return _factory_func()


def __getattr__(name: str) -> list[type]:
    """Module-level attribute access for lazy DIRECTIVE_CLASSES."""
    if name == "DIRECTIVE_CLASSES":
        return _get_directive_classes()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
