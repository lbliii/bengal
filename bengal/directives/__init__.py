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

from bengal.directives.registry import (
    DIRECTIVE_CLASSES,
    KNOWN_DIRECTIVE_NAMES,
    get_directive,
    get_known_directive_names,
    register_all,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

__all__ = [
    # Factory function for Mistune plugin (lazy-loaded)
    "create_documentation_directives",
    # Registry API
    "DIRECTIVE_CLASSES",
    "KNOWN_DIRECTIVE_NAMES",
    "get_directive",
    "get_known_directive_names",
    "register_all",
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
