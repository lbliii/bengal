"""
Type definitions for Bengal directives.

This module provides TypedDict definitions for directive attributes and
Protocol definitions for mistune parser types. These enable type-safe
directive development without depending on mistune internals.

Shadow Protocols:
Mistune's internal types (BlockParser, BlockState) are not exported.
This module defines matching protocols that allow type checking without
coupling to mistune's implementation details.

Example:
    >>> from bengal.directives.types import DirectiveAttrs, DirectiveToken
    >>> attrs: DirectiveAttrs = {"class_": "highlight", "id": "my-directive"}

See Also:
- :mod:`bengal.directives.base`: BengalDirective base class
- :mod:`bengal.directives.tokens`: DirectiveToken dataclass
- :mod:`bengal.parsing.ast.types`: AST node types

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Protocol, TypedDict, runtime_checkable

if TYPE_CHECKING:
    pass


# =============================================================================
# Mistune Shadow Protocols
# =============================================================================
# These protocols match mistune's internal types without depending on them.
# This allows type checking while maintaining loose coupling.


@runtime_checkable
class MistuneBlockState(Protocol):
    """
    Protocol matching mistune's BlockState interface.

    BlockState manages parser state during block-level parsing, including
    cursor position, token buffer, and nesting depth tracking.

    """

    @property
    def cursor(self) -> int:
        """Current position in the source text."""
        ...

    @property
    def tokens(self) -> list[dict[str, object]]:
        """Accumulated tokens from parsing."""
        ...

    @property
    def env(self) -> dict[str, object]:
        """Environment dict for storing state."""
        ...

    @env.setter
    def env(self, value: dict[str, object]) -> None:
        """Set environment dict."""
        ...

    def depth(self) -> int:
        """Current nesting depth."""
        ...

    def child_state(self, text: str) -> MistuneBlockState:
        """Create a child state for nested parsing."""
        ...

    def append_token(self, token: dict[str, object]) -> None:
        """Add a token to the buffer."""
        ...


@runtime_checkable
class MistuneBlockParser(Protocol):
    """
    Protocol matching mistune's BlockParser interface.

    BlockParser handles block-level markdown parsing, including paragraphs,
    headings, code blocks, and directives.

    """

    @property
    def max_nested_level(self) -> int:
        """Maximum nesting depth for recursive parsing."""
        ...

    @property
    def rules(self) -> list[str]:
        """Active parsing rules."""
        ...

    def parse(
        self,
        state: MistuneBlockState,
        rules: list[str] | None = None,
    ) -> list[dict[str, object]]:
        """Parse text into tokens."""
        ...


@runtime_checkable
class MistuneRenderer(Protocol):
    """Protocol matching mistune's renderer interface."""

    NAME: str

    def register(self, name: str, method: object) -> None:
        """Register a render method for a token type."""
        ...


@runtime_checkable
class MistuneMarkdown(Protocol):
    """
    Protocol matching mistune's Markdown interface.

    Used for directive registration and renderer access.

    """

    @property
    def block(self) -> MistuneBlockParser:
        """Block parser instance."""
        ...

    @property
    def renderer(self) -> MistuneRenderer | None:
        """HTML renderer instance."""
        ...

    def __call__(self, text: str) -> str:
        """Render markdown to HTML."""
        ...


# =============================================================================
# Directive Parse Result Types
# =============================================================================


class DirectiveToken(TypedDict, total=False):
    """Token structure returned by directive parsing."""

    type: str
    raw: str
    attrs: dict[str, object]
    children: list[dict[str, object]]
    text: str


class DirectiveParseResult(TypedDict, total=False):
    """Extended parse result with metadata."""

    type: str
    raw: str
    attrs: dict[str, object]
    children: list[dict[str, object]]
    source_file: str | None
    source_line: int | None


# =============================================================================
# Common Directive Attributes
# =============================================================================


class DirectiveAttrs(TypedDict, total=False):
    """Common attributes for all directives."""

    class_: str  # CSS class (use class_ to avoid Python keyword)
    id: str  # HTML id attribute
    title: str  # Title/caption


class StyledAttrs(DirectiveAttrs, total=False):
    """Attributes for styled directives."""

    style: str  # Inline CSS style


class TitledAttrs(DirectiveAttrs, total=False):
    """Attributes for titled directives (admonitions, dropdowns).

    Note: title is inherited from DirectiveAttrs.
    """

    icon: str | None
    collapsible: bool
    open: bool


# =============================================================================
# Specific Directive Attribute Types
# =============================================================================


class CodeBlockAttrs(DirectiveAttrs, total=False):
    """Attributes for code block directives."""

    language: str
    filename: str | None
    linenos: bool
    hl_lines: list[int]
    start_line: int
    emphasize_lines: str  # Line spec like "1,3-5"
    caption: str | None
    dedent: int


class AdmonitionAttrs(DirectiveAttrs, total=False):
    """Attributes for admonition directives."""

    type: Literal["note", "warning", "tip", "danger", "info", "caution", "important"]
    collapsible: bool
    open: bool
    icon: str | None


class TabSetAttrs(DirectiveAttrs, total=False):
    """Attributes for tab-set directives."""

    sync: str | None  # Sync group name
    selected: int  # Default selected tab index


class TabItemAttrs(DirectiveAttrs, total=False):
    """Attributes for tab-item directives."""

    label: str
    sync: str | None  # Sync key for cross-tab-set sync
    selected: bool


class DropdownAttrs(DirectiveAttrs, total=False):
    """Attributes for dropdown/details directives.

    Note: title is inherited from DirectiveAttrs.
    """

    open: bool
    icon: str | None


class ImageAttrs(DirectiveAttrs, total=False):
    """Attributes for image directives."""

    src: str
    alt: str
    width: str | int | None
    height: str | int | None
    align: Literal["left", "center", "right"]
    caption: str | None


class IncludeAttrs(DirectiveAttrs, total=False):
    """Attributes for include directives."""

    file: str
    lines: str  # Line spec like "1-10" or "5,"
    start_after: str  # Marker text
    end_before: str  # Marker text
    dedent: int
    language: str  # For literalinclude


class CardAttrs(DirectiveAttrs, total=False):
    """Attributes for card directives.

    Note: title is inherited from DirectiveAttrs.
    """

    link: str | None
    image: str | None
    footer: str | None


class GridAttrs(DirectiveAttrs, total=False):
    """Attributes for grid layout directives."""

    columns: int | str  # Can be "1 2 3 4" for responsive
    gutter: int
    margin: int
    padding: int


class StepAttrs(DirectiveAttrs, total=False):
    """Attributes for step directives.

    Note: title is inherited from DirectiveAttrs.
    """

    number: int | None


class GlossaryAttrs(DirectiveAttrs, total=False):
    """Attributes for glossary directives."""

    sorted: bool


class MermaidAttrs(DirectiveAttrs, total=False):
    """Attributes for mermaid diagram directives."""

    caption: str | None
    align: Literal["left", "center", "right"]


class EmbedAttrs(DirectiveAttrs, total=False):
    """Attributes for embed directives."""

    url: str
    type: Literal["youtube", "vimeo", "codepen", "gist", "twitter", "iframe"]
    width: str | int | None
    height: str | int | None
    aspect_ratio: str  # e.g., "16:9"


# =============================================================================
# Directive Options Types (parsed from :option: lines)
# =============================================================================


class DirectiveOptionsDict(TypedDict, total=False):
    """Raw directive options as parsed from markup."""

    # Common options (any directive)
    class_: str
    name: str  # For cross-references

    # Code options
    language: str
    linenos: bool
    lineno_start: int
    emphasize_lines: str
    caption: str
    dedent: int

    # Admonition options
    collapsible: bool
    open: bool

    # Grid/layout options
    columns: str
    gutter: int
    margin: int

    # Include options
    lines: str
    start_after: str
    end_before: str


# =============================================================================
# Renderer Protocol
# =============================================================================


@runtime_checkable
class DirectiveRenderer(Protocol):
    """
    Protocol for directive renderers.

    Renderers convert parsed directive tokens to HTML output.

    """

    def render_children(self, token: dict[str, object]) -> str:
        """Render child tokens to HTML."""
        ...

    def __call__(self, tokens: list[dict[str, object]], state: object) -> str:
        """Render a list of tokens to HTML."""
        ...


# =============================================================================
# Contract Types
# =============================================================================


class ContractViolationDict(TypedDict):
    """Serialized contract violation for logging/reporting."""

    violation_type: str
    directive: str
    parent: str | None
    expected: list[str]
    source_file: str | None
    source_line: int | None
    message: str


# =============================================================================
# Exports
# =============================================================================

@runtime_checkable
class MistuneDirectiveRegistry(Protocol):
    """Protocol matching mistune's BaseDirective registry interface."""

    def register(self, name: str, parse_method: object) -> None:
        """Register a directive parse method."""
        ...


__all__ = [
    "AdmonitionAttrs",
    "CardAttrs",
    # Specific directive attributes
    "CodeBlockAttrs",
    # Contract
    "ContractViolationDict",
    # Base attributes
    "DirectiveAttrs",
    # Options
    "DirectiveOptionsDict",
    "DirectiveParseResult",
    # Renderer
    "DirectiveRenderer",
    # Token types
    "DirectiveToken",
    "DropdownAttrs",
    "EmbedAttrs",
    "GlossaryAttrs",
    "GridAttrs",
    "ImageAttrs",
    "IncludeAttrs",
    "MermaidAttrs",
    # Mistune protocols
    "MistuneBlockParser",
    "MistuneBlockState",
    "MistuneDirectiveRegistry",
    "MistuneMarkdown",
    "MistuneRenderer",
    "StepAttrs",
    "StyledAttrs",
    "TabItemAttrs",
    "TabSetAttrs",
    "TitledAttrs",
]
