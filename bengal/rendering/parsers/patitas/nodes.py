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

from bengal.rendering.parsers.patitas.directives.options import DirectiveOptions
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
    
    Markdown: ``\\`` at end of line or two trailing spaces
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


# =============================================================================
# Plugin Inline Nodes
# =============================================================================


@dataclass(frozen=True, slots=True)
class Strikethrough(Node):
    """Strikethrough (deleted) text.
    
    Markdown: ~~deleted~~
    HTML: <del>deleted</del>
        
    """

    children: tuple[Inline, ...]


@dataclass(frozen=True, slots=True)
class Math(Node):
    """Inline math expression.
    
    Markdown: $E = mc^2$
    HTML: <span class="math">E = mc^2</span>
        
    """

    content: str


@dataclass(frozen=True, slots=True)
class FootnoteRef(Node):
    """Footnote reference.
    
    Markdown: [^1] or [^note]
    HTML: <sup><a href="#fn-1">1</a></sup>
        
    """

    identifier: str


# PEP 695 type alias for inline elements
type Inline = (
    Text
    | Emphasis
    | Strong
    | Strikethrough
    | Link
    | Image
    | CodeSpan
    | LineBreak
    | SoftBreak
    | HtmlInline
    | Role
    | Math
    | FootnoteRef
)


# =============================================================================
# Block Nodes
# =============================================================================


@dataclass(frozen=True, slots=True)
class Heading(Node):
    """ATX or setext heading.
    
    Markdown: # Heading or Heading\n======
    HTML: <h1>Heading</h1>
    
    Supports MyST-compatible explicit anchor syntax: ## Title {#custom-id}
    The {#id} is parsed during lexing and stored in explicit_id.
        
    """

    level: Literal[1, 2, 3, 4, 5, 6]
    children: tuple[Inline, ...]
    style: Literal["atx", "setext"] = "atx"
    explicit_id: str | None = None  # MyST {#custom-id} syntax


@dataclass(frozen=True, slots=True)
class Paragraph(Node):
    """Paragraph block.
    
    Markdown: Text separated by blank lines
    HTML: <p>text</p>
        
    """

    children: tuple[Inline, ...]


@dataclass(frozen=True, slots=True)
class FencedCode(Node):
    """Fenced code block with zero-copy source reference.
    
    BREAKING CHANGE (v0.4.0):
        Previous: code: str (extracted content)
        Current:  source_start/source_end indices into original source
    
    Migration:
        Old: block.code
        New: block.get_code(source)
    
    For nested contexts (e.g., fenced code inside block quotes), the
    content_override field stores the actual code content directly
    since the source offsets would be relative to a sub-parser's source.
        
    """

    source_start: int
    source_end: int
    info: str | None = None
    marker: Literal["`", "~"] = "`"
    fence_indent: int = 0  # Leading spaces on opening fence line
    content_override: str | None = None  # Direct content for nested contexts

    def get_code(self, source: str) -> str:
        """Extract code content (creates new string).

        CommonMark: strips up to fence_indent spaces from each content line.
        """
        # Use content_override if available (for nested contexts)
        if self.content_override is not None:
            code = self.content_override
        else:
            code = source[self.source_start : self.source_end]

        # CommonMark: strip up to fence_indent spaces from each line
        if self.fence_indent > 0:
            lines = code.split("\n")
            stripped_lines = []
            for line in lines:
                # Count leading spaces
                spaces = 0
                while spaces < len(line) and line[spaces] == " ":
                    spaces += 1
                # Strip up to fence_indent spaces
                strip_count = min(spaces, self.fence_indent)
                stripped_lines.append(line[strip_count:])
            code = "\n".join(stripped_lines)

        return code

    def code_length(self) -> int:
        """Length of code content without allocation."""
        if self.content_override is not None:
            return len(self.content_override)
        return self.source_end - self.source_start


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
class Directive[TOptions: DirectiveOptions](Node):
    """Block directive (MyST syntax).
    
    Markdown: :::{name} title\n:option: value\ncontent\n:::
    
    Generic over options type for full type safety. Use Directive[YourOptions]
    to get typed options access in handlers.
    
    PEP 695 Note:
        Uses Python 3.12+ type parameter syntax: `class Directive[TOptions: DirectiveOptions]`
        instead of the older `class Directive(Node, Generic[TOptions])` with TypeVar.
        
    """

    name: str
    title: str | None
    options: TOptions  # Typed options object — IDE knows the exact type!
    children: tuple[Block, ...]
    raw_content: str | None = None  # For directives needing unparsed content


@dataclass(frozen=True, slots=True)
class Document(Node):
    """Root document node.
    
    Contains all top-level blocks in the document.
        
    """

    children: tuple[Block, ...]


# =============================================================================
# Plugin Block Nodes
# =============================================================================


@dataclass(frozen=True, slots=True)
class TableCell(Node):
    """Table cell (th or td).
    
    Markdown: | cell content |
    HTML: <td>cell content</td> or <th>cell content</th>
        
    """

    children: tuple[Inline, ...]
    is_header: bool = False
    align: Literal["left", "center", "right"] | None = None


@dataclass(frozen=True, slots=True)
class TableRow(Node):
    """Table row.
    
    Markdown: | cell1 | cell2 |
    HTML: <tr><td>cell1</td><td>cell2</td></tr>
        
    """

    cells: tuple[TableCell, ...]
    is_header: bool = False


@dataclass(frozen=True, slots=True)
class Table(Node):
    """Table (GFM-style).
    
    Markdown:
        | A | B |
        |---|---|
        | 1 | 2 |
    
    HTML: <table>...</table>
        
    """

    head: tuple[TableRow, ...]  # Header rows (usually 1)
    body: tuple[TableRow, ...]  # Body rows
    alignments: tuple[Literal["left", "center", "right"] | None, ...]


@dataclass(frozen=True, slots=True)
class MathBlock(Node):
    """Block math expression.
    
    Markdown:
        $$
        E = mc^2
        $$
    
    HTML: <div class="math-block">E = mc^2</div>
        
    """

    content: str


@dataclass(frozen=True, slots=True)
class FootnoteDef(Node):
    """Footnote definition.
    
    Markdown: [^1]: Footnote content here.
    HTML: (rendered in footnotes section)
        
    """

    identifier: str
    children: tuple[Block, ...]


# PEP 695 type alias for block elements
type Block = (
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
    | Table
    | MathBlock
    | FootnoteDef
)
