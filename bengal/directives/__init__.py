"""Directive system for Bengal documentation templates.

This package provides the complete directive infrastructure for extending
Markdown with custom block-level elements like admonitions, tabs, cards,
and code snippets. Directives follow the MyST-style ``:::{name}`` syntax.

Key Features:
    - **Lazy Loading**: Directive classes load on-demand for fast startup.
    - **Contract Validation**: Parent-child relationships validated at parse time.
    - **Typed Options**: Automatic parsing and coercion of directive options.
    - **Extensibility**: Subclass ``BengalDirective`` to create custom directives.

Public API:
    Factory:
        - ``create_documentation_directives``: Create Mistune plugin with all directives.

    Registry:
        - ``get_directive``: Lazy-load a directive class by name.
        - ``register_all``: Pre-load all directive classes.
        - ``DIRECTIVE_CLASSES``: List of all directive classes (lazy-loaded).
        - ``KNOWN_DIRECTIVE_NAMES``: Frozenset of registered directive names.

    Base Classes:
        - ``BengalDirective``: Base class for all directives.
        - ``DirectiveToken``: Typed AST token for directive nodes.
        - ``DirectiveOptions``: Base class for typed option parsing.
        - ``DirectiveContract``: Define valid nesting relationships.
        - ``FencedDirective``: Mistune plugin for fence-style parsing.

    Preset Options:
        - ``StyledOptions``: Common options with CSS class support.
        - ``ContainerOptions``: Layout options for container directives.
        - ``TitledOptions``: Options for directives with titles and icons.

    Preset Contracts:
        - ``STEPS_CONTRACT``, ``STEP_CONTRACT``: Steps container validation.
        - ``TAB_SET_CONTRACT``, ``TAB_ITEM_CONTRACT``: Tabs validation.
        - ``CARDS_CONTRACT``, ``CARD_CONTRACT``: Cards container validation.
        - ``CODE_TABS_CONTRACT``: Code tabs validation.

    Utilities:
        - ``escape_html``, ``build_class_string``, ``bool_attr``, etc.

Example:
    Basic usage with Mistune::

        import mistune
        from bengal.directives import create_documentation_directives

        md = mistune.create_markdown(
            plugins=[create_documentation_directives()]
        )
        html = md(":::{note}\\nThis is a note.\\n:::")

    Get a specific directive class::

        from bengal.directives import get_directive

        DropdownDirective = get_directive("dropdown")

Architecture:
    Directives load lazily via ``get_directive()`` to avoid importing all
    implementations at package import time. The ``create_documentation_directives``
    factory is also lazy-loaded to prevent circular imports with
    ``bengal.rendering.plugins``.

See Also:
    - ``bengal.directives.base``: BengalDirective implementation details.
    - ``bengal.directives.registry``: Lazy loading mechanism.
    - ``bengal.directives.contracts``: Contract validation system.
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
from bengal.directives.tokens import DirectiveType

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
    """Return all directive classes, loading them lazily if needed.

    This internal function backs the ``DIRECTIVE_CLASSES`` module attribute,
    caching the result after the first load to avoid repeated imports.

    Returns:
        List of all BengalDirective subclasses.
    """
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
    "DirectiveType",
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
    """Create the documentation directives plugin for Mistune.

    Returns a callable that registers all Bengal directives with a Mistune
    markdown instance. This is the primary entry point for enabling directive
    support in your markdown processing pipeline.

    The actual factory is lazy-loaded on first call to avoid circular imports
    between ``bengal.directives`` and ``bengal.rendering.plugins``.

    Returns:
        A plugin function compatible with ``mistune.create_markdown(plugins=[...])``.

    Example:
        ::

            import mistune
            from bengal.directives import create_documentation_directives

            md = mistune.create_markdown(
                plugins=[create_documentation_directives()]
            )
            html = md(":::{note}\\nImportant information.\\n:::")

    Raises:
        RuntimeError: If directive registration fails.
        ImportError: If required dependencies are not available.

    See Also:
        ``bengal.directives.factory``: Full factory implementation.
    """
    global _factory_func
    if _factory_func is None:
        from bengal.directives.factory import (
            create_documentation_directives as _create,
        )

        _factory_func = _create
    return _factory_func()


def __getattr__(name: str) -> list[type]:
    """Provide lazy access to module-level attributes.

    Implements PEP 562 module ``__getattr__`` to enable lazy loading of
    ``DIRECTIVE_CLASSES``, which triggers import of all directive modules.

    Args:
        name: The attribute name being accessed.

    Returns:
        For ``DIRECTIVE_CLASSES``, returns a list of all directive classes.

    Raises:
        AttributeError: If the requested attribute does not exist.
    """
    if name == "DIRECTIVE_CLASSES":
        return _get_directive_classes()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
