"""Role registry for handler lookup and registration.

The registry maps role names to their handlers, enabling
extensibility and custom role support.

Thread Safety:
RoleRegistry is immutable after creation. Safe to share.
Use RoleRegistryBuilder for mutable construction.

Example:
    >>> builder = RoleRegistryBuilder()
    >>> builder.register(RefRole())
    >>> builder.register(KbdRole())
    >>> registry = builder.build()
    >>> handler = registry.get("ref")

"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.parsing.backends.patitas.roles.protocol import RoleHandler


class RoleRegistry:
    """Immutable registry of role handlers.

    Maps role names to their handlers for lookup during parsing
    and rendering.

    Thread Safety:
        Immutable after creation. Safe to share across threads.

    """

    __slots__ = ("_by_name", "_by_token_type", "_handlers")

    def __init__(
        self,
        handlers: tuple[RoleHandler, ...],
        by_name: dict[str, RoleHandler],
        by_token_type: dict[str, RoleHandler],
    ) -> None:
        """Initialize registry with pre-built mappings.

        Use RoleRegistryBuilder to create instances.
        """
        self._handlers = handlers
        self._by_name = by_name
        self._by_token_type = by_token_type

    def get(self, name: str) -> RoleHandler | None:
        """Get handler for role name.

        Args:
            name: Role name (e.g., "ref", "kbd")

        Returns:
            Handler if registered, None otherwise
        """
        return self._by_name.get(name)

    def get_by_token_type(self, token_type: str) -> RoleHandler | None:
        """Get handler by token type.

        Args:
            token_type: Token type identifier (e.g., "reference")

        Returns:
            Handler if registered, None otherwise
        """
        return self._by_token_type.get(token_type)

    def has(self, name: str) -> bool:
        """Check if role name is registered."""
        return name in self._by_name

    @property
    def names(self) -> frozenset[str]:
        """Get all registered role names."""
        return frozenset(self._by_name.keys())

    @property
    def handlers(self) -> tuple[RoleHandler, ...]:
        """Get all registered handlers."""
        return self._handlers

    def __contains__(self, name: str) -> bool:
        """Support 'name in registry' syntax."""
        return self.has(name)

    def __len__(self) -> int:
        """Number of registered role names."""
        return len(self._by_name)


class RoleRegistryBuilder:
    """Mutable builder for RoleRegistry.

    Use this to register handlers, then call build() to create
    an immutable registry.

    Example:
            >>> builder = RoleRegistryBuilder()
            >>> builder.register(RefRole())
            >>> builder.register(KbdRole())
            >>> registry = builder.build()

    """

    __slots__ = ("_by_name", "_by_token_type", "_handlers")

    def __init__(self) -> None:
        """Initialize empty builder."""
        self._handlers: list[RoleHandler] = []
        self._by_name: dict[str, RoleHandler] = {}
        self._by_token_type: dict[str, RoleHandler] = {}

    def register(self, handler: RoleHandler) -> RoleRegistryBuilder:
        """Register a role handler.

        Args:
            handler: Handler implementing RoleHandler protocol

        Returns:
            Self for chaining

        Raises:
            ValueError: If handler name conflicts with existing registration
        """
        # Validate handler has required attributes
        if not hasattr(handler, "names"):
            msg = f"Handler {type(handler).__name__} missing 'names' attribute"
            raise TypeError(msg)

        if not hasattr(handler, "token_type"):
            msg = f"Handler {type(handler).__name__} missing 'token_type' attribute"
            raise TypeError(msg)

        # Register by all names
        for name in handler.names:
            if name in self._by_name:
                existing = self._by_name[name]
                msg = f"Role '{name}' already registered by {type(existing).__name__}"
                raise ValueError(msg)
            self._by_name[name] = handler

        # Register by token type
        token_type = handler.token_type
        if token_type not in self._by_token_type:
            self._by_token_type[token_type] = handler

        self._handlers.append(handler)
        return self

    def register_all(self, handlers: list[RoleHandler]) -> RoleRegistryBuilder:
        """Register multiple handlers.

        Args:
            handlers: List of handlers to register

        Returns:
            Self for chaining
        """
        for handler in handlers:
            self.register(handler)
        return self

    def build(self) -> RoleRegistry:
        """Build immutable registry from registered handlers.

        Returns:
            Immutable RoleRegistry
        """
        return RoleRegistry(
            handlers=tuple(self._handlers),
            by_name=dict(self._by_name),
            by_token_type=dict(self._by_token_type),
        )

    def __len__(self) -> int:
        """Number of registered handlers."""
        return len(self._handlers)


def create_default_registry() -> RoleRegistry:
    """Create registry with all built-in roles.

    Returns:
        Registry with ref, kbd, abbr, math, icon, etc.

    """
    from bengal.parsing.backends.patitas.roles.builtins import (
        AbbrRole,
        DocRole,
        IconRole,
        KbdRole,
        MathRole,
        RefRole,
        SubRole,
        SupRole,
    )

    builder = RoleRegistryBuilder()
    builder.register(RefRole())
    builder.register(DocRole())
    builder.register(KbdRole())
    builder.register(AbbrRole())
    builder.register(MathRole())
    builder.register(SubRole())
    builder.register(SupRole())
    builder.register(IconRole())

    return builder.build()
