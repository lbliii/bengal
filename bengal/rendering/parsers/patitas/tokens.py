"""Token and TokenType definitions for the Patitas lexer.

The lexer produces a stream of Token objects that the parser consumes.
Each Token has a type, value, and source location.

Thread Safety:
    Token is frozen (immutable) and safe to share across threads.
    TokenType is an enum (inherently immutable).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from bengal.rendering.parsers.patitas.location import SourceLocation


class TokenType(Enum):
    """Token types produced by the lexer.

    Organized by category for clarity:
    - Document structure (EOF, BLANK_LINE)
    - Block elements (headings, code blocks, quotes, lists)
    - Inline elements (text, emphasis, links, images)
    - Directives and roles
    """

    # Document structure
    EOF = auto()
    BLANK_LINE = auto()

    # Block elements - headings
    ATX_HEADING = auto()  # # Heading
    SETEXT_HEADING_UNDERLINE = auto()  # === or ---

    # Block elements - code
    FENCED_CODE_START = auto()  # ``` or ~~~
    FENCED_CODE_END = auto()
    FENCED_CODE_CONTENT = auto()
    INDENTED_CODE = auto()  # 4-space indented

    # Block elements - quotes and lists
    BLOCK_QUOTE_MARKER = auto()  # >
    LIST_ITEM_MARKER = auto()  # -, *, +, 1., 1)

    # Block elements - other
    THEMATIC_BREAK = auto()  # ---, ***, ___
    HTML_BLOCK = auto()

    # Paragraph and text
    PARAGRAPH_LINE = auto()  # Regular text line
    TEXT = auto()  # Inline text content

    # Inline elements - emphasis
    EMPHASIS_MARKER = auto()  # * or _
    STRONG_MARKER = auto()  # ** or __

    # Inline elements - code
    CODE_SPAN = auto()  # `code`

    # Inline elements - links and images
    LINK_START = auto()  # [
    LINK_END = auto()  # ]
    LINK_DESTINATION = auto()  # (url "title")
    IMAGE_START = auto()  # ![
    AUTOLINK = auto()  # <url>

    # Inline elements - other
    HARD_BREAK = auto()  # \\ or two trailing spaces
    SOFT_BREAK = auto()  # Single newline in paragraph
    HTML_INLINE = auto()  # Inline HTML

    # Inline elements - escapes
    ESCAPED_CHAR = auto()  # \* \_ etc.

    # Reference definitions
    LINK_REFERENCE_DEF = auto()  # [label]: url "title"

    # Directive system (MyST-compatible)
    DIRECTIVE_OPEN = auto()  # :::
    DIRECTIVE_CLOSE = auto()  # ::: (matching)
    DIRECTIVE_NAME = auto()  # {name}
    DIRECTIVE_TITLE = auto()  # Title text after name
    DIRECTIVE_OPTION = auto()  # :key: value

    # Role system (MyST-compatible)
    ROLE = auto()  # {role}`content`

    # Plugin tokens - Tables (GFM)
    TABLE_ROW = auto()  # | cell | cell |
    TABLE_DELIMITER = auto()  # |---|---|

    # Plugin tokens - Strikethrough
    STRIKETHROUGH_MARKER = auto()  # ~~

    # Plugin tokens - Math
    MATH_INLINE = auto()  # $...$
    MATH_BLOCK_START = auto()  # $$
    MATH_BLOCK_END = auto()  # $$
    MATH_BLOCK_CONTENT = auto()

    # Plugin tokens - Footnotes
    FOOTNOTE_REF = auto()  # [^id]
    FOOTNOTE_DEF = auto()  # [^id]:


@dataclass(frozen=True, slots=True)
class Token:
    """A token produced by the lexer.

    Tokens are the atomic units passed from lexer to parser.
    Each token has a type, string value, and source location.

    Attributes:
        type: The token type (from TokenType enum)
        value: The raw string value from source
        location: Source location for error messages

    Examples:
        >>> tok = Token(TokenType.ATX_HEADING, "## Hello", SourceLocation(1, 1))
        >>> tok.type
        <TokenType.ATX_HEADING: ...>
        >>> tok.value
        '## Hello'

    Thread Safety:
        Frozen dataclass ensures immutability for safe sharing.
    """

    type: TokenType
    value: str
    location: SourceLocation

    def __repr__(self) -> str:
        """Compact repr for debugging."""
        val = self.value
        if len(val) > 20:
            val = val[:17] + "..."
        return f"Token({self.type.name}, {val!r}, {self.location})"

    @property
    def lineno(self) -> int:
        """Line number (convenience accessor)."""
        return self.location.lineno

    @property
    def col(self) -> int:
        """Column offset (convenience accessor)."""
        return self.location.col_offset
