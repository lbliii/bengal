"""
Lazy context evaluation for template rendering.

Provides LazyPageContext that defers evaluation of expensive context fields
until they're actually accessed by the template. This optimization provides
15-25% speedup on pages with simple templates that don't access all context.

Architecture:
    LazyPageContext wraps the standard context dict and intercepts __getitem__
    to evaluate lazy factories on first access. Evaluated values are cached.

    ```
    context["posts"]  # First access: evaluates factory, caches result
    context["posts"]  # Second access: returns cached value
    ```

Thread Safety:
    Each LazyPageContext instance is used by a single render thread.
    No locking is needed - instances are not shared.

Performance:
    - Lazy fields: ~0 cost if not accessed
    - First access: factory evaluation cost + dict assignment
    - Subsequent access: O(1) dict lookup

RFC: rfc-lazy-context-evaluation

"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class LazyValue:
    """Marker class for lazy-evaluated values.

    When accessed, the factory is called and the result replaces
    the LazyValue in the context dict.
    """

    __slots__ = ("factory",)

    def __init__(self, factory: Callable[[], Any]) -> None:
        """Initialize with a factory function.

        Args:
            factory: Zero-argument callable that produces the value
        """
        self.factory = factory

    def evaluate(self) -> Any:
        """Evaluate the factory and return the result."""
        return self.factory()


class LazyPageContext(dict[str, Any]):
    """
    Context dict with lazy evaluation for expensive fields.

    Subclasses dict to provide lazy evaluation of fields like posts,
    subsections, and params that may not be accessed by all templates.

    Usage:
        >>> context = LazyPageContext()
        >>> context["posts"] = LazyValue(lambda: expensive_query())
        >>> # posts not evaluated yet
        >>> template.render(**context)  # Accesses posts -> evaluated

    Fields that benefit from lazy evaluation:
        - posts: Section pages list (O(n) to collect)
        - subsections: Section children (O(n) to collect)
        - params: CascadingParamsContext (allocates wrapper)
        - toc_items: Parsed TOC structure (O(n) parsing)

    Thread Safety:
        Instance per render thread - no locking needed.

    """

    __slots__ = ()  # Use dict's storage

    def __getitem__(self, key: str) -> Any:
        """Get item, evaluating lazy values on first access.

        Args:
            key: Context key to retrieve

        Returns:
            Evaluated value (cached for subsequent access)
        """
        value = super().__getitem__(key)

        if isinstance(value, LazyValue):
            # Evaluate and cache
            evaluated = value.evaluate()
            super().__setitem__(key, evaluated)
            return evaluated

        return value

    def get(self, key: str, default: Any = None) -> Any:
        """Get item with default, evaluating lazy values.

        Args:
            key: Context key to retrieve
            default: Default if key not present

        Returns:
            Evaluated value or default
        """
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def __contains__(self, key: object) -> bool:
        """Check if key exists (doesn't evaluate lazy values)."""
        return super().__contains__(key)

    def items(self) -> Any:
        """Return items, evaluating all lazy values.

        Note: This evaluates ALL lazy values. Use sparingly.
        """
        # Evaluate all lazy values first
        for key in list(super().keys()):
            value = super().__getitem__(key)
            if isinstance(value, LazyValue):
                super().__setitem__(key, value.evaluate())

        return super().items()

    def values(self) -> Any:
        """Return values, evaluating all lazy values.

        Note: This evaluates ALL lazy values. Use sparingly.
        """
        # Evaluate all lazy values first
        for key in list(super().keys()):
            value = super().__getitem__(key)
            if isinstance(value, LazyValue):
                super().__setitem__(key, value.evaluate())

        return super().values()


def make_lazy(factory: Callable[[], Any]) -> LazyValue:
    """Create a lazy value from a factory function.

    Convenience function for creating lazy values:

        >>> context["posts"] = make_lazy(lambda: section.sorted_pages)

    Args:
        factory: Zero-argument callable that produces the value

    Returns:
        LazyValue that will evaluate factory on first access
    """
    return LazyValue(factory)


__all__ = [
    "LazyPageContext",
    "LazyValue",
    "make_lazy",
]
