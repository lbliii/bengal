"""Typed AST nodes for Patitas.

All AST nodes are frozen dataclasses with slots for:
- Type safety: IDE autocomplete, catch errors at dev time
- Immutability: Safe sharing across threads (Python 3.14t ready)
- Memory efficiency: __slots__ reduces memory footprint
- Pattern matching: Python 3.10+ match statements work naturally

Node Hierarchy:
    Node (base)
    ├── Block (block-level elements)
    │   ├── Document
    │   ├── Heading
    │   ├── Paragraph
    │   ├── FencedCode
    │   ├── IndentedCode
    │   ├── BlockQuote
    │   ├── List
    │   ├── ListItem
    │   ├── ThematicBreak
    │   ├── HtmlBlock
    │   └── Directive
    └── Inline (inline elements)
        ├── Text
        ├── Emphasis
        ├── Strong
        ├── Link
        ├── Image
        ├── CodeSpan
        ├── LineBreak
        ├── HtmlInline
        └── Role

Thread Safety:
    All nodes are frozen (immutable) and safe to share across threads.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from bengal.rendering.parsers.patitas.location import SourceLocation

# =============================================================================
# Base Node
# =============================================================================


@dataclass(frozen=True, slots=True)
class Node:
    """Base class for all AST nodes.

    All nodes track their source location for error messages and debugging.
    """

    location: SourceLocation


# =============================================================================
# Inline Nodes
# =============================================================================


@dataclass(frozen=True, slots=True)
class Text(Node):
    """Plain text content.

    The most common inline node, representing literal text.
    """

    content: str


@dataclass(frozen=True, slots=True)
class Emphasis(Node):
    """Emphasized (italic) text.

    Markdown: *text* or _text_
    HTML: <em>text</em>
    """

    children: tuple[Inline, ...]


@dataclass(frozen=True, slots=True)
class Strong(Node):
    """Strong (bold) text.

    Markdown: **text** or __text__
    HTML: <strong>text</strong>
    """

    children: tuple[Inline, ...]


@dataclass(frozen=True, slots=True)
class Link(Node):
    """Hyperlink.

    Markdown: [text](url "title") or [text][ref]
    HTML: <a href="url" title="title">text</a>
    """

    url: str
    title: str | None
    children: tuple[Inline, ...]


@dataclass(frozen=True, slots=True)
class Image(Node):
    """Image.

    Markdown: ![alt](url "title")
    HTML: <img src="url" alt="alt" title="title">
    """

    url: str
    alt: str
    title: str | None = None


@dataclass(frozen=True, slots=True)
class CodeSpan(Node):
    """Inline code.

    Markdown: `code`
    HTML: <code>code</code>
    """

    code: str


@dataclass(frozen=True, slots=True)
class LineBreak(Node):
    """Hard line break.

    Markdown: \\ at end of line or two trailing spaces
    HTML: <br />
    """

    pass


@dataclass(frozen=True, slots=True)
class SoftBreak(Node):
    """Soft line break (single newline in paragraph).

    Typically rendered as a space or newline depending on renderer settings.
    """

    pass


@dataclass(frozen=True, slots=True)
class HtmlInline(Node):
    """Inline raw HTML.

    Markdown: <span>text</span>
    HTML: passed through unchanged
    """

    html: str


@dataclass(frozen=True, slots=True)
class Role(Node):
    """Inline role (MyST syntax).

    Markdown: {role}`content`
    Example: {ref}`target`, {kbd}`Ctrl+C`
    """

    name: str
    content: str
    target: str | None = None


# Type alias for inline elements
Inline = (
    Text | Emphasis | Strong | Link | Image | CodeSpan | LineBreak | SoftBreak | HtmlInline | Role
)


# =============================================================================
# Block Nodes
# =============================================================================


@dataclass(frozen=True, slots=True)
class Heading(Node):
    """ATX or setext heading.

    Markdown: # Heading or Heading\\n======
    HTML: <h1>Heading</h1>
    """

    level: Literal[1, 2, 3, 4, 5, 6]
    children: tuple[Inline, ...]
    style: Literal["atx", "setext"] = "atx"


@dataclass(frozen=True, slots=True)
class Paragraph(Node):
    """Paragraph block.

    Markdown: Text separated by blank lines
    HTML: <p>text</p>
    """

    children: tuple[Inline, ...]


@dataclass(frozen=True, slots=True)
class FencedCode(Node):
    """Fenced code block.

    Markdown: ```lang\\ncode\\n```
    HTML: <pre><code class="language-lang">code</code></pre>
    """

    code: str
    info: str | None = None
    marker: Literal["`", "~"] = "`"


@dataclass(frozen=True, slots=True)
class IndentedCode(Node):
    """Indented code block (4+ spaces).

    Markdown: ····code
    HTML: <pre><code>code</code></pre>
    """

    code: str


@dataclass(frozen=True, slots=True)
class BlockQuote(Node):
    """Block quote.

    Markdown: > quoted text
    HTML: <blockquote>text</blockquote>
    """

    children: tuple[Block, ...]


@dataclass(frozen=True, slots=True)
class ListItem(Node):
    """List item.

    Markdown: - item or 1. item
    HTML: <li>item</li>
    """

    children: tuple[Block, ...]
    checked: bool | None = None  # For task lists: True/False/None


@dataclass(frozen=True, slots=True)
class List(Node):
    """Ordered or unordered list.

    Markdown: - item or 1. item
    HTML: <ul>/<ol> with <li> children
    """

    items: tuple[ListItem, ...]
    ordered: bool = False
    start: int = 1  # Starting number for ordered lists
    tight: bool = True  # Tight vs loose list


@dataclass(frozen=True, slots=True)
class ThematicBreak(Node):
    """Thematic break (horizontal rule).

    Markdown: --- or *** or ___
    HTML: <hr />
    """

    pass


@dataclass(frozen=True, slots=True)
class HtmlBlock(Node):
    """Raw HTML block.

    Markdown: HTML that starts a block
    HTML: passed through unchanged
    """

    html: str


@dataclass(frozen=True, slots=True)
class Directive(Node):
    """Block directive (MyST syntax).

    Markdown: :::{name} title\\n:option: value\\ncontent\\n:::
    """

    name: str
    title: str | None
    options: frozenset[tuple[str, str]]
    children: tuple[Block, ...]
    raw_content: str | None = None  # For directives needing unparsed content


@dataclass(frozen=True, slots=True)
class Document(Node):
    """Root document node.

    Contains all top-level blocks in the document.
    """

    children: tuple[Block, ...]


# Type alias for block elements
Block = (
    Document
    | Heading
    | Paragraph
    | FencedCode
    | IndentedCode
    | BlockQuote
    | List
    | ListItem
    | ThematicBreak
    | HtmlBlock
    | Directive
)
