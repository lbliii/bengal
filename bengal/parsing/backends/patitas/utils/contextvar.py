"""Generic ContextVar management utilities.

Provides a reusable pattern for ContextVar-based thread-local state.
Eliminates duplication across config.py, render_config.py, accumulator.py,
and request_context.py.

Thread Safety:
    ContextVars are thread-local by design (PEP 567).
    Each thread has independent storage - no locks needed.

Usage:
    from bengal.parsing.backends.patitas.utils.contextvar import ContextVarManager

    # Create a manager for your config type
    _manager: ContextVarManager[MyConfig] = ContextVarManager(
        "my_config",
        default=MyConfig(),
    )

    # Use the manager
    def get_my_config() -> MyConfig:
        return _manager.get()

    def set_my_config(config: MyConfig) -> Token[MyConfig]:
        return _manager.set(config)

    # Or use the context manager
    with _manager.context(MyConfig(option=True)) as cfg:
        ...

"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import overload


class ContextVarManager[T]:
    """Generic manager for ContextVar-based thread-local state.

    Provides a consistent get/set/reset/context pattern for any type T.

    Type Parameters:
        T: The type of value stored in the ContextVar

    Thread Safety:
        ContextVars are thread-local by design (PEP 567).
        Also async-safe (each task gets its own context).

    Attributes:
        _var: The underlying ContextVar
        _default: Default value (None for optional types)
        _name: Name for debugging/introspection
    """

    __slots__ = ("_default", "_name", "_var")

    @overload
    def __init__(
        self,
        name: str,
        *,
        default: T,
    ) -> None: ...

    @overload
    def __init__(
        self,
        name: str,
        *,
        default: None = None,
    ) -> None: ...

    def __init__(
        self,
        name: str,
        *,
        default: T | None = None,
    ) -> None:
        """Initialize the ContextVar manager.

        Args:
            name: Name for the ContextVar (for debugging)
            default: Default value when not set (None for optional types)
        """
        self._name = name
        self._default = default
        self._var: ContextVar[T | None] = ContextVar(name, default=default)

    @property
    def name(self) -> str:
        """Get the ContextVar name."""
        return self._name

    def get(self) -> T | None:
        """Get the current value (thread-local).

        Returns:
            The current value or None if not set and no default.
        """
        return self._var.get()

    def get_or_raise(self, error_class: type[Exception], message: str) -> T:
        """Get the current value or raise an exception if not set.

        Args:
            error_class: Exception class to raise
            message: Error message

        Returns:
            The current value

        Raises:
            error_class: If no value is set (value is None)
        """
        value = self._var.get()
        if value is None:
            raise error_class(message)
        return value

    def set(self, value: T) -> Token[T | None]:
        """Set the value for the current context.

        Returns a token that can be used to restore the previous value.

        Args:
            value: The value to set

        Returns:
            Token that can be passed to reset() for proper nesting
        """
        return self._var.set(value)

    def reset(self, token: Token[T | None] | None = None) -> None:
        """Reset to previous value or default.

        If token is provided, restores to the previous value (proper nesting).
        Otherwise, resets to the default value.

        Args:
            token: Optional token from set() for proper nesting support
        """
        if token is not None:
            self._var.reset(token)
        else:
            self._var.set(self._default)

    @contextmanager
    def context(self, value: T) -> Iterator[T]:
        """Context manager for scoped value.

        Properly restores previous value on exit (supports nesting).

        Args:
            value: The value to use within the context

        Yields:
            The value that was set (same as input)
        """
        token = self.set(value)
        try:
            yield value
        finally:
            self.reset(token)


def create_contextvar_manager[T](
    name: str,
    default: T | None = None,
) -> ContextVarManager[T]:
    """Factory function to create a ContextVarManager.

    Args:
        name: Name for the ContextVar (for debugging)
        default: Default value when not set

    Returns:
        Configured ContextVarManager instance
    """
    return ContextVarManager(name, default=default)
