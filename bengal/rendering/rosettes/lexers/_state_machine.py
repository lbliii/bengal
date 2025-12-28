"""Base class for hand-written state machine lexers.

Thread-safe, O(n) guaranteed, zero regex.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from bengal.rendering.rosettes._config import LexerConfig
from bengal.rendering.rosettes._types import Token, TokenType

if TYPE_CHECKING:
    pass

__all__ = [
    "StateMachineLexer",
    "scan_while",
    "scan_until",
    "scan_string",
    "scan_triple_string",
]


class StateMachineLexer:
    """Base class for hand-written state machine lexers.

    Thread-safe: tokenize() uses only local variables.
    O(n) guaranteed: single pass, no backtracking.

    Subclasses implement language-specific tokenization by overriding
    the tokenize() method with character-by-character logic.

    Design Principles:
        1. No regex — character matching only
        2. Explicit state — no hidden backtracking
        3. Local variables only — thread-safe by design
        4. Single pass — O(n) guaranteed
    """

    name: str = "base"
    aliases: tuple[str, ...] = ()
    filenames: tuple[str, ...] = ()
    mimetypes: tuple[str, ...] = ()

    # Shared character class sets (frozen for thread safety)
    DIGITS: frozenset[str] = frozenset("0123456789")
    HEX_DIGITS: frozenset[str] = frozenset("0123456789abcdefABCDEF")
    OCTAL_DIGITS: frozenset[str] = frozenset("01234567")
    BINARY_DIGITS: frozenset[str] = frozenset("01")
    LETTERS: frozenset[str] = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
    IDENT_START: frozenset[str] = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
    IDENT_CONT: frozenset[str] = frozenset(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789"
    )
    WHITESPACE: frozenset[str] = frozenset(" \t\n\r\f\v")

    def tokenize(
        self,
        code: str,
        config: LexerConfig | None = None,
        start: int = 0,
        end: int | None = None,
    ) -> Iterator[Token]:
        """Tokenize source code.

        Subclasses override this with language-specific logic.

        Args:
            code: The source code to tokenize.
            config: Optional lexer configuration.
            start: Starting index in the source string.
            end: Optional ending index in the source string.

        Yields:
            Token objects in order of appearance.
        """
        raise NotImplementedError("Subclasses must implement tokenize()")

    def tokenize_fast(
        self,
        code: str,
        start: int = 0,
        end: int | None = None,
    ) -> Iterator[tuple[TokenType, str]]:
        """Fast tokenization without position tracking.

        Default implementation strips position info from tokenize().
        Subclasses may override for further optimization.

        Args:
            code: The source code to tokenize.
            start: Starting index in the source string.
            end: Optional ending index in the source string.

        Yields:
            (TokenType, value) tuples.
        """
        for token in self.tokenize(code, start=start, end=end):
            yield (token.type, token.value)


# =============================================================================
# Helper functions for common scanning patterns
# =============================================================================


def scan_while(code: str, pos: int, char_set: frozenset[str]) -> int:
    """Advance position while characters are in char_set.

    Args:
        code: Source code string.
        pos: Starting position.
        char_set: Set of characters to match.

    Returns:
        The new position (may be unchanged if no match).
    """
    length = len(code)
    while pos < length and code[pos] in char_set:
        pos += 1
    return pos


def scan_until(code: str, pos: int, char_set: frozenset[str]) -> int:
    """Advance position until a character in char_set is found.

    Args:
        code: Source code string.
        pos: Starting position.
        char_set: Set of characters to stop at.

    Returns:
        The new position (may be end of string).
    """
    length = len(code)
    while pos < length and code[pos] not in char_set:
        pos += 1
    return pos


def scan_string(
    code: str,
    pos: int,
    quote: str,
    *,
    allow_escape: bool = True,
    allow_multiline: bool = False,
) -> int:
    """Scan a string literal, handling escapes.

    Args:
        code: Source code.
        pos: Position after opening quote.
        quote: The quote character (' or ").
        allow_escape: Whether backslash escapes are allowed.
        allow_multiline: Whether newlines are allowed.

    Returns:
        Position after closing quote (or end of string/line if unterminated).
    """
    length = len(code)

    while pos < length:
        char = code[pos]

        if char == quote:
            return pos + 1  # Include closing quote

        if char == "\\" and allow_escape and pos + 1 < length:
            pos += 2  # Skip escape sequence
            continue

        if char == "\n" and not allow_multiline:
            return pos  # Unterminated string

        pos += 1

    return pos  # End of input (unterminated)


def scan_triple_string(code: str, pos: int, quote: str) -> int:
    """Scan a triple-quoted string.

    Args:
        code: Source code.
        pos: Position after opening triple quote.
        quote: The quote character (' or ").

    Returns:
        Position after closing triple quote (or end of input).
    """
    length = len(code)
    triple = quote * 3

    while pos < length:
        if code[pos : pos + 3] == triple:
            return pos + 3

        if code[pos] == "\\" and pos + 1 < length:
            pos += 2  # Skip escape
            continue

        pos += 1

    return pos  # End of input (unterminated)


def scan_line_comment(code: str, pos: int) -> int:
    """Scan to end of line (for line comments).

    Args:
        code: Source code.
        pos: Starting position (after comment marker).

    Returns:
        Position at end of line (before newline) or end of input.
    """
    length = len(code)
    while pos < length and code[pos] != "\n":
        pos += 1
    return pos


def scan_block_comment(code: str, pos: int, end_marker: str) -> int:
    """Scan a block comment until end marker.

    Args:
        code: Source code.
        pos: Position after opening marker.
        end_marker: The closing marker (e.g., "*/" or "-->").

    Returns:
        Position after closing marker (or end of input).
    """
    length = len(code)
    marker_len = len(end_marker)

    while pos < length:
        if code[pos : pos + marker_len] == end_marker:
            return pos + marker_len
        pos += 1

    return pos  # End of input (unterminated)
