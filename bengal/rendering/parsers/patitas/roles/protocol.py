"""RoleHandler protocol for extensible inline markup.

Roles are inline directives using MyST syntax: {role}`content`
Implement the RoleHandler protocol to create custom roles.

Thread Safety:
    Handlers must be stateless. All state should be in the AST node
    or passed as arguments. Multiple threads may call the same handler
    instance concurrently.

Example:
    >>> class KbdRole:
    ...     names = ("kbd",)
    ...
    ...     def parse(self, name, content, location):
    ...         return Role(location, name, content)
    ...
    ...     def render(self, node, sb):
    ...         sb.append(f'<kbd>{node.content}</kbd>')
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation
    from bengal.rendering.parsers.patitas.nodes import Role
    from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder


@runtime_checkable
class RoleHandler(Protocol):
    """Protocol for role implementations.

    Roles are inline directives like {ref}`target` or {kbd}`Ctrl+C`.
    They produce inline AST nodes rather than block nodes.

    Attributes:
        names: Tuple of role names this handler responds to.
               Example: ("ref", "doc") for reference roles
        token_type: Token type identifier for the AST.

    Thread Safety:
        Handlers must be stateless. All mutable state must be in the AST
        node or passed as arguments. Multiple threads may call the same
        handler instance concurrently.

    Example:
        >>> class AbbrRole:
        ...     names = ("abbr",)
        ...     token_type = "abbr"
        ...
        ...     def parse(self, name, content, location):
        ...         # Parse "HTML (HyperText Markup Language)"
        ...         parts = content.split("(", 1)
        ...         abbr = parts[0].strip()
        ...         expansion = parts[1].rstrip(")") if len(parts) > 1 else ""
        ...         return Role(location, name, abbr, target=expansion)
        ...
        ...     def render(self, node, sb):
        ...         sb.append(f'<abbr title="{node.target}">{node.content}</abbr>')
    """

    # Class-level attributes
    names: ClassVar[tuple[str, ...]]
    """Role names this handler responds to (e.g., ("ref", "doc"))."""

    token_type: ClassVar[str]
    """Token type identifier for AST dispatch (e.g., "reference")."""

    def parse(
        self,
        name: str,
        content: str,
        location: SourceLocation,
    ) -> Role:
        """Build the role AST node.

        Called by the parser when a role is encountered in inline content.
        Return a Role node to include in the AST.

        Args:
            name: The role name used (e.g., "ref" or "kbd")
            content: The content between backticks
            location: Source location for error messages

        Returns:
            A Role node for the AST

        Thread Safety:
            This method is called from parser context. Must not modify
            any shared state.
        """
        ...

    def render(
        self,
        node: Role,
        sb: StringBuilder,
    ) -> None:
        """Render the role to HTML.

        Called by the renderer when a Role node is encountered.
        Append HTML output to the StringBuilder.

        Args:
            node: The Role AST node to render
            sb: StringBuilder to append output to

        Thread Safety:
            This method may be called concurrently from multiple threads.
            Must not modify any shared state.
        """
        ...


@runtime_checkable
class RoleParseOnly(Protocol):
    """Protocol for roles that only need custom parsing.

    Use this when default rendering is acceptable but you need
    custom AST construction.
    """

    names: ClassVar[tuple[str, ...]]
    token_type: ClassVar[str]

    def parse(
        self,
        name: str,
        content: str,
        location: SourceLocation,
    ) -> Role:
        """Build the role AST node."""
        ...


@runtime_checkable
class RoleRenderOnly(Protocol):
    """Protocol for roles that only need custom rendering.

    Use this when default parsing is acceptable but you need
    custom HTML output.
    """

    names: ClassVar[tuple[str, ...]]
    token_type: ClassVar[str]

    def render(
        self,
        node: Role,
        sb: StringBuilder,
    ) -> None:
        """Render the role to HTML."""
        ...
