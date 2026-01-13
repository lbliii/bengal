"""Typed inline tokens for Patitas parser.

Uses NamedTuples for inline token representation, providing:
- Immutability by default (required for external match tracking)
- Tuple unpacking support
- Lower memory footprint (~80 bytes vs ~200 for dict)
- Faster attribute access (tuple index vs hash lookup)
- Full type safety with IDE autocomplete

Thread Safety:
All tokens are immutable and safe to share across threads.

Usage:
from bengal.rendering.parsers.patitas.parsing.inline.tokens import (
    DelimiterToken,
    TextToken,
    InlineToken,
)

    token = DelimiterToken(char="*", count=2, can_open=True, can_close=False)
match token:
    case DelimiterToken(char="*", count=count):
        print(f"Asterisk delimiter with count {count}")

"""

from __future__ import annotations

from typing import Literal, NamedTuple

# PEP 695 type alias for delimiter characters
type DelimiterChar = Literal["*", "_", "~"]


class DelimiterToken(NamedTuple):
    """Delimiter token for emphasis/strikethrough processing.
    
    Immutable by design — match state tracked externally in MatchRegistry.
    
    NamedTuple chosen over dataclass for:
    - Immutability by default (required for external match tracking)
    - Tuple unpacking support
    - Lower memory footprint (~80 bytes vs ~200 for dict)
    - Faster attribute access (tuple index vs hash lookup)
    
    Attributes:
        char: The delimiter character ("*", "_", or "~").
        count: Number of consecutive delimiter characters.
        can_open: Whether this delimiter can open emphasis.
        can_close: Whether this delimiter can close emphasis.
        
    """

    char: DelimiterChar
    count: int
    can_open: bool
    can_close: bool

    @property
    def type(self) -> Literal["delimiter"]:
        """Token type identifier for dispatch."""
        return "delimiter"

    @property
    def original_count(self) -> int:
        """Original count (same as count for immutable tokens)."""
        return self.count


class TextToken(NamedTuple):
    """Plain text token.
    
    Attributes:
        content: The text content.
        
    """

    content: str

    @property
    def type(self) -> Literal["text"]:
        """Token type identifier for dispatch."""
        return "text"


class CodeSpanToken(NamedTuple):
    """Inline code span token.
    
    Attributes:
        code: The code content (already processed per CommonMark rules).
        
    """

    code: str

    @property
    def type(self) -> Literal["code_span"]:
        """Token type identifier for dispatch."""
        return "code_span"


class NodeToken(NamedTuple):
    """Pre-parsed AST node token (links, images, etc.).
    
    Used when inline content is parsed directly into an AST node
    (e.g., links, images, autolinks, roles, math).
    
    Attributes:
        node: The pre-parsed inline AST node.
        
    """

    node: object  # Inline node type

    @property
    def type(self) -> Literal["node"]:
        """Token type identifier for dispatch."""
        return "node"


class HardBreakToken(NamedTuple):
    """Hard line break token.
    
    Represents a hard line break (backslash + newline or two trailing spaces).
        
    """

    @property
    def type(self) -> Literal["hard_break"]:
        """Token type identifier for dispatch."""
        return "hard_break"


class SoftBreakToken(NamedTuple):
    """Soft line break token.
    
    Represents a soft line break (single newline in paragraph).
    Typically rendered as a space or newline depending on settings.
        
    """

    @property
    def type(self) -> Literal["soft_break"]:
        """Token type identifier for dispatch."""
        return "soft_break"


# PEP 695 type alias for all inline tokens
type InlineToken = (
    DelimiterToken | TextToken | CodeSpanToken | NodeToken | HardBreakToken | SoftBreakToken
)


__all__ = [
    "DelimiterChar",
    "DelimiterToken",
    "TextToken",
    "CodeSpanToken",
    "NodeToken",
    "HardBreakToken",
    "SoftBreakToken",
    "InlineToken",
]
