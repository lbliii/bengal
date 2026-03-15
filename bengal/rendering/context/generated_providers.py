"""
Generated page context provider registry.

Maps PageKind to context-building callables. Replaces string-based
dispatch in Renderer with extensible registry pattern.

RFC: rfc-generated-page-context-protocol
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from bengal.core.page.kind import PageKind

if TYPE_CHECKING:
    from bengal.protocols import PageLike

# Registry: PageKind -> (renderer, page) -> dict
# Callable[[Any, PageLike], dict[str, Any]]
GENERATED_CONTEXT_REGISTRY: dict[PageKind, Callable[[Any, PageLike], dict[str, Any]]] = {}


def register_provider(
    kind: PageKind,
    provider: Callable[[Any, PageLike], dict[str, Any]],
) -> None:
    """Register a context provider for a PageKind."""
    GENERATED_CONTEXT_REGISTRY[kind] = provider


def get_generated_context(renderer: Any, page: PageLike) -> dict[str, Any] | None:
    """
    Get template context for a generated page via registry dispatch.

    Returns:
        Context dict to merge, or None if no provider registered
    """
    kind = PageKind.from_page(page)
    provider = GENERATED_CONTEXT_REGISTRY.get(kind)
    if provider is None:
        return None
    return provider(renderer, page)
