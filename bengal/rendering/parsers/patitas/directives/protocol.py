"""DirectiveHandler protocol for extensible block-level directives.

Directives are the primary extension mechanism for block-level markup.
Implement the DirectiveHandler protocol to create custom directives.

Thread Safety:
Handlers must be stateless. All state should be in the AST node
or passed as arguments. Multiple threads may call the same handler
instance concurrently.

Example:
    >>> class NoteDirective:
    ...     names = ("note",)
    ...
    ...     def parse(self, name, title, options, content, children, location):
    ...         return Directive(location, name, title, options, children)
    ...
    ...     def render(self, node, rendered_children, sb):
    ...         sb.append('<div class="admonition note">')
    ...         sb.append(rendered_children)
    ...         sb.append('</div>')

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.directives.contracts import DirectiveContract
    from bengal.rendering.parsers.patitas.directives.options import DirectiveOptions
    from patitas.location import SourceLocation
    from patitas.nodes import Block, Directive
    from patitas.stringbuilder import StringBuilder


@runtime_checkable
class DirectiveHandler(Protocol):
    """Protocol for directive implementations.
    
    Implement this protocol to create custom directives. The parser calls
    parse() to build the AST node, and the renderer calls render() to
    produce HTML output.
    
    Attributes:
        names: Tuple of directive names this handler responds to.
               Example: ("note", "warning", "tip") for admonitions
        token_type: Token type identifier for the AST. Used for dispatch.
        contract: Optional nesting validation contract.
        options_class: Class for typed options parsing.
    
    Thread Safety:
        Handlers must be stateless. All mutable state must be in the AST
        node (which is immutable) or passed as arguments. Multiple threads
        may call the same handler instance concurrently.
    
    Example:
            >>> class VideoDirective:
            ...     names = ("video",)
            ...     token_type = "video"
            ...     options_class = VideoOptions
            ...
            ...     def parse(self, name, title, options, content, children, location):
            ...         return Directive(location, name, title, options, children)
            ...
            ...     def render(self, node, rendered_children, sb):
            ...         sb.append(f'<video src="{node.title}"></video>')
        
    """

    # Class-level attributes
    names: ClassVar[tuple[str, ...]]
    """Directive names this handler responds to (e.g., ("note", "warning"))."""

    token_type: ClassVar[str]
    """Token type identifier for AST dispatch (e.g., "admonition")."""

    contract: ClassVar[DirectiveContract | None]
    """Optional contract for nesting validation. None means no restrictions."""

    options_class: ClassVar[type[DirectiveOptions]]
    """Class for typed options parsing. Defaults to DirectiveOptions."""

    preserves_raw_content: ClassVar[bool]
    """If True, parser will preserve raw content string in node.raw_content.

    Set this to True for directives that need to parse raw content themselves
    (e.g., gallery parsing image URLs from content).
    """

    def parse(
        self,
        name: str,
        title: str | None,
        options: DirectiveOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build the directive AST node.

        Called by the parser when a directive block is encountered.
        Return a Directive node to include in the AST.

        Args:
            name: The directive name used (e.g., "note" or "warning")
            title: Optional title text after the directive name
            options: Typed options parsed from :key: value lines
            content: Raw content string (prefer children for most cases)
            children: Parsed child nodes from the directive body
            location: Source location for error messages

        Returns:
            A Directive node for the AST

        Thread Safety:
            This method is called from parser context. Must not modify
            any shared state.
        """
        ...

    def render(
        self,
        node: Directive,
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render the directive to HTML.

        Called by the renderer when a Directive node is encountered.
        Append HTML output to the StringBuilder.

        Args:
            node: The Directive AST node to render
            rendered_children: Pre-rendered HTML of child nodes
            sb: StringBuilder to append output to

        Thread Safety:
            This method may be called concurrently from multiple threads.
            Must not modify any shared state.
        """
        ...


@runtime_checkable
class DirectiveParseOnly(Protocol):
    """Protocol for directives that only need custom parsing.
    
    Use this when default rendering is acceptable but you need
    custom AST construction.
        
    """

    names: ClassVar[tuple[str, ...]]
    token_type: ClassVar[str]
    contract: ClassVar[DirectiveContract | None]
    options_class: ClassVar[type[DirectiveOptions]]

    def parse(
        self,
        name: str,
        title: str | None,
        options: DirectiveOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build the directive AST node."""
        ...


@runtime_checkable
class DirectiveRenderOnly(Protocol):
    """Protocol for directives that only need custom rendering.
    
    Use this when default parsing is acceptable but you need
    custom HTML output.
        
    """

    names: ClassVar[tuple[str, ...]]
    token_type: ClassVar[str]

    def render(
        self,
        node: Directive,
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render the directive to HTML."""
        ...
