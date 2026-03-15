"""Public API for Bengal directive system.

Re-exports from the Patitas directive backend for convenient imports.
Use `from bengal.directives import DirectiveHandler` in custom directive code.

Example:
    >>> from bengal.directives import DirectiveHandler, DirectiveOptions, create_default_registry
    >>>
    >>> class AlertDirective:
    ...     names = ("alert",)
    ...     token_type = "alert"
    ...     def parse(self, name, title, options, content, children, location): ...
    ...     def render(self, node, rendered_children, sb): ...
"""

from __future__ import annotations

from bengal.parsing.backends.patitas.directives import (
    DirectiveContract,
    DirectiveHandler,
    DirectiveOptions,
    DirectiveRegistry,
    DirectiveRegistryBuilder,
    create_default_registry,
)

# Alias for documentation (DirectiveHandler is the canonical name)
BengalDirective = DirectiveHandler

__all__ = [
    "BengalDirective",
    "DirectiveContract",
    "DirectiveHandler",
    "DirectiveOptions",
    "DirectiveRegistry",
    "DirectiveRegistryBuilder",
    "create_default_registry",
    "get_directive",
]


def get_directive(name: str) -> DirectiveHandler | None:
    """Get a built-in directive handler by name from the default registry.

    Args:
        name: Directive name (e.g., "note", "dropdown", "warning")

    Returns:
        Handler class if registered, None otherwise.

    Example:
        >>> from bengal.directives import get_directive
        >>> handler_cls = get_directive("dropdown")
        >>> if handler_cls:
        ...     directive = handler_cls()
        ...     # test parse/render
    """
    registry = create_default_registry()
    return registry.get(name)
