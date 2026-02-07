"""
Generic ContextVar management for thread-safe context storage.

Provides a reusable pattern for ContextVar-based context management,
eliminating boilerplate across multiple modules.

Thread Safety (Free-Threading / PEP 703):
    ContextVars are thread-local by design (PEP 567).
    Each thread/async task has independent storage - no locks needed.
    ~8M ops/sec throughput (benchmarked).

Usage:
    # Define a manager for your context type
    _tracker_ctx = ContextVarManager[EffectTracer]("effect_tracer")

    # Get/set/reset
    tracker = _tracker_ctx.get()
    token = _tracker_ctx.set(my_tracker)
    _tracker_ctx.reset(token)

    # Or use as context manager
    with _tracker_ctx(my_tracker) as tracker:
        # tracker is active in this scope
        pass

Related Modules:
    - bengal.rendering.assets: Uses for AssetManifestContext
    - bengal.rendering.asset_tracking: Uses for AssetTracker
    - bengal.rendering.context.data_tracking: Uses for EffectTracer integration
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Generic, TypeVar

T = TypeVar("T")


class ContextVarManager(Generic[T]):
    """
    Generic manager for ContextVar-based thread-local storage.

    Encapsulates the common pattern of:
    - get_current_X() -> X | None
    - set_current_X(x: X) -> Token
    - reset_current_X(token: Token | None) -> None
    - X_context(x: X) -> ContextManager[X]

    Thread Safety:
        ContextVars are thread-local by design (PEP 567).
        Each thread has independent storage - no locks needed.

    Example:
        # Define manager
        _tracker = ContextVarManager[MyTracker]("my_tracker")

        # Use get/set/reset
        current = _tracker.get()
        token = _tracker.set(new_tracker)
        _tracker.reset(token)

        # Or use context manager
        with _tracker(my_instance) as instance:
            # instance is available via _tracker.get()
            do_work()

    """

    __slots__ = ("_var", "_name")

    def __init__(self, name: str, *, default: T | None = None) -> None:
        """
        Initialize the ContextVar manager.

        Args:
            name: Name for the ContextVar (for debugging)
            default: Default value when not set (typically None)
        """
        self._name = name
        self._var: ContextVar[T | None] = ContextVar(name, default=default)

    @property
    def name(self) -> str:
        """Get the ContextVar name."""
        return self._name

    def get(self) -> T | None:
        """
        Get current value for this thread/context.

        Returns:
            Current value if set, None otherwise.

        Thread Safety:
            Uses ContextVar - each thread/async task has independent storage.
        """
        return self._var.get()

    def set(self, value: T) -> Token[T | None]:
        """
        Set value for current context.

        Args:
            value: Value to set

        Returns:
            Token that can be used to restore the previous value via reset().

        Note:
            Always use with try/finally or the context manager for proper cleanup.
        """
        return self._var.set(value)

    def reset(self, token: Token[T | None] | None = None) -> None:
        """
        Reset to previous value.

        Args:
            token: Token from set() for proper nesting support.
                   If None, sets value to None.
        """
        if token is not None:
            self._var.reset(token)
        else:
            self._var.set(None)

    @contextmanager
    def __call__(self, value: T) -> Iterator[T]:
        """
        Context manager for scoped value usage.

        Properly restores previous value on exit (supports nesting).

        Usage:
            with manager(my_value) as val:
                # val is available via manager.get()
                do_work()
            # Previous value is restored

        Args:
            value: Value to use within the context

        Yields:
            The value that was set (same as input)
        """
        token = self.set(value)
        try:
            yield value
        finally:
            self.reset(token)

    def __repr__(self) -> str:
        return f"ContextVarManager({self._name!r})"
