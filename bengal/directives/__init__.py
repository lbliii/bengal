"""Public API for Bengal directives.

Re-exports from the Patitas directive system. Use `DirectiveHandler` (or its
alias `BengalDirective`) to implement custom directives.

Plan: plan-production-maturity.md Phase 0B — unify naming (BengalDirective = DirectiveHandler).
"""

from __future__ import annotations

from bengal.parsing.backends.patitas.directives import (
    DirectiveContract,
    DirectiveHandler,
    DirectiveOptions,
    DirectiveParseOnly,
    DirectiveRegistry,
    DirectiveRegistryBuilder,
    DirectiveRenderOnly,
    create_default_registry,
)

# Alias for documentation and backward compatibility — docs historically used "BengalDirective"
BengalDirective = DirectiveHandler

_DEFAULT_REGISTRY: DirectiveRegistry | None = None


def get_directive(name: str) -> type[DirectiveHandler] | None:
    """Get the handler class for a directive name from the default registry.

    Returns the handler instance's class for testing or inspection.
    For a handler instance, use create_default_registry().get(name) instead.
    """
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = create_default_registry()
    handler = _DEFAULT_REGISTRY.get(name)
    return type(handler) if handler is not None else None


__all__ = [
    "BengalDirective",
    "DirectiveContract",
    "DirectiveHandler",
    "DirectiveOptions",
    "DirectiveParseOnly",
    "DirectiveRegistry",
    "DirectiveRegistryBuilder",
    "DirectiveRenderOnly",
    "create_default_registry",
    "get_directive",
]
