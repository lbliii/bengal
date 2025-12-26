"""Reusable scanner components for state machine lexers.

These mixins provide common scanning patterns that can be composed
into language-specific lexers, dramatically reducing code duplication.

Usage:
    class MyLexer(
        CStyleCommentsMixin,
        CStyleNumbersMixin,
        CStyleStringsMixin,
        StateMachineLexer,
    ):
        # Just define keywords and operators
        pass
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bengal.rendering.rosettes._types import Token, TokenType

if TYPE_CHECKING:
    pass

__all__ = [
    # Configuration dataclasses
    "NumberConfig",
    "StringConfig",
    "CommentConfig",
    "OperatorConfig",
    # Mixin classes
    "WhitespaceMixin",
    "CStyleCommentsMixin",
    "HashCommentsMixin",
    "CStyleNumbersMixin",
    "CStyleStringsMixin",
    "CStyleOperatorsMixin",
    # Standalone scanners
    "scan_c_style_number",
    "scan_identifier",
    "scan_operators",
]


# =============================================================================
# Configuration dataclasses for customizable scanning
# =============================================================================


@dataclass(frozen=True, slots=True)
class NumberConfig:
    """Configuration for number scanning.

    Attributes:
        hex_prefix: Prefix for hex numbers (e.g., "0x").
        octal_prefix: Prefix for octal numbers (e.g., "0o").
        binary_prefix: Prefix for binary numbers (e.g., "0b").
        allow_underscores: Whether underscores are allowed in numbers.
        integer_suffixes: Valid suffixes for integers (e.g., ("n",) for BigInt).
        float_suffixes: Valid suffixes for floats (e.g., ("f32", "f64")).
        imaginary_suffix: Suffix for imaginary numbers (e.g., "j" for Python).
    """

    hex_prefix: tuple[str, ...] = ("0x", "0X")
    octal_prefix: tuple[str, ...] = ("0o", "0O")
    binary_prefix: tuple[str, ...] = ("0b", "0B")
    allow_underscores: bool = True
    integer_suffixes: tuple[str, ...] = ()
    float_suffixes: tuple[str, ...] = ()
    imaginary_suffix: str | None = None


@dataclass(frozen=True, slots=True)
class StringConfig:
    """Configuration for string scanning.

    Attributes:
        single_quote: Whether single-quoted strings are allowed.
        double_quote: Whether double-quoted strings are allowed.
        backtick: Whether backtick strings are allowed (template literals).
        triple_quote: Whether triple-quoted strings are allowed.
        escape_char: The escape character (usually backslash).
        prefixes: Valid string prefixes (e.g., "frb" for Python).
        raw_string_marker: Marker for raw strings (e.g., "r" for Python).
    """

    single_quote: bool = True
    double_quote: bool = True
    backtick: bool = False
    triple_quote: bool = False
    escape_char: str = "\\"
    prefixes: frozenset[str] = frozenset()
    raw_string_marker: str | None = None


@dataclass(frozen=True, slots=True)
class CommentConfig:
    """Configuration for comment scanning.

    Attributes:
        line_comment: Line comment marker (e.g., "//", "#").
        block_start: Block comment start (e.g., "/*").
        block_end: Block comment end (e.g., "*/").
        doc_line: Documentation comment line marker (e.g., "///").
        doc_block_start: Documentation block start (e.g., "/**").
    """

    line_comment: str | None = "//"
    block_start: str | None = "/*"
    block_end: str | None = "*/"
    doc_line: str | None = None
    doc_block_start: str | None = None


@dataclass(frozen=True, slots=True)
class OperatorConfig:
    """Configuration for operator scanning.

    Operators are scanned longest-first. Group by length for efficiency.
    """

    three_char: frozenset[str] = frozenset()
    two_char: frozenset[str] = frozenset()
    one_char: frozenset[str] = frozenset()


# =============================================================================
# Character sets (shared across all scanners)
# =============================================================================

DIGITS: frozenset[str] = frozenset("0123456789")
HEX_DIGITS: frozenset[str] = frozenset("0123456789abcdefABCDEF")
OCTAL_DIGITS: frozenset[str] = frozenset("01234567")
BINARY_DIGITS: frozenset[str] = frozenset("01")
WHITESPACE: frozenset[str] = frozenset(" \t\n\r\f\v")
IDENT_START: frozenset[str] = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
IDENT_CONT: frozenset[str] = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789"
)
# JavaScript/PHP allow $ in identifiers
IDENT_START_DOLLAR: frozenset[str] = IDENT_START | frozenset("$")
IDENT_CONT_DOLLAR: frozenset[str] = IDENT_CONT | frozenset("$")


# =============================================================================
# Standalone scanner functions
# =============================================================================


def scan_whitespace(code: str, pos: int) -> tuple[int, int]:
    """Scan whitespace, returning (new_pos, newline_count).

    Returns:
        Tuple of (position after whitespace, number of newlines encountered).
    """
    length = len(code)
    newlines = 0
    while pos < length and code[pos] in WHITESPACE:
        if code[pos] == "\n":
            newlines += 1
        pos += 1
    return pos, newlines


def scan_line_comment(code: str, pos: int) -> int:
    """Scan to end of line (for line comments).

    Args:
        pos: Position after comment marker (e.g., after "//").

    Returns:
        Position at end of line (before newline) or end of input.
    """
    length = len(code)
    while pos < length and code[pos] != "\n":
        pos += 1
    return pos


def scan_block_comment(code: str, pos: int, end_marker: str = "*/") -> int:
    """Scan block comment until end marker.

    Args:
        pos: Position after opening marker.
        end_marker: The closing marker (e.g., "*/").

    Returns:
        Position after closing marker (or end of input if unterminated).
    """
    length = len(code)
    marker_len = len(end_marker)

    while pos < length:
        if code[pos : pos + marker_len] == end_marker:
            return pos + marker_len
        pos += 1

    return pos


def scan_identifier(
    code: str,
    pos: int,
    *,
    allow_dollar: bool = False,
) -> int:
    """Scan an identifier.

    Args:
        pos: Position at start of identifier.
        allow_dollar: Whether $ is allowed in identifiers (JavaScript).

    Returns:
        Position after identifier.
    """
    length = len(code)
    cont_chars = IDENT_CONT_DOLLAR if allow_dollar else IDENT_CONT

    pos += 1  # Skip first character (already validated)
    while pos < length and code[pos] in cont_chars:
        pos += 1

    return pos


def scan_string(
    code: str,
    pos: int,
    quote: str,
    *,
    escape_char: str = "\\",
    allow_multiline: bool = False,
) -> tuple[int, int]:
    """Scan a string literal using C-optimized str.find().

    Args:
        pos: Position after opening quote.
        quote: The quote character.
        escape_char: The escape character.
        allow_multiline: Whether newlines are allowed.

    Returns:
        Tuple of (position after closing quote, newline count).
    """
    length = len(code)
    start = pos

    while True:
        # Use C-level str.find() for fast quote scanning
        quote_pos = code.find(quote, pos)

        if quote_pos == -1:
            # Unterminated string - count newlines and return end
            if allow_multiline:
                return length, code.count("\n", start, length)
            # For single-line, find first newline
            newline_pos = code.find("\n", start)
            if newline_pos != -1 and newline_pos < length:
                return newline_pos, 0
            return length, 0

        # Check for newline before quote (single-line mode)
        if not allow_multiline:
            newline_pos = code.find("\n", pos, quote_pos)
            if newline_pos != -1:
                return newline_pos, 0

        # Count preceding backslashes to check if escaped
        num_backslashes = 0
        check = quote_pos - 1
        while check >= start and code[check] == escape_char:
            num_backslashes += 1
            check -= 1

        if num_backslashes % 2 == 0:
            # Even backslashes = not escaped, this is the closing quote
            newlines = code.count("\n", start, quote_pos) if allow_multiline else 0
            return quote_pos + 1, newlines

        # Odd backslashes = escaped quote, continue searching
        pos = quote_pos + 1


def scan_triple_string(code: str, pos: int, quote: str) -> tuple[int, int]:
    """Scan a triple-quoted string using C-optimized str.find().

    Args:
        pos: Position after opening triple quote.
        quote: The quote character.

    Returns:
        Tuple of (position after closing triple quote, newline count).
    """
    length = len(code)
    triple = quote * 3
    start = pos

    while True:
        # Use C-level str.find() for fast triple-quote scanning
        triple_pos = code.find(triple, pos)

        if triple_pos == -1:
            # Unterminated string
            return length, code.count("\n", start, length)

        # Check if escaped (count preceding backslashes)
        num_backslashes = 0
        check = triple_pos - 1
        while check >= start and code[check] == "\\":
            num_backslashes += 1
            check -= 1

        if num_backslashes % 2 == 0:
            # Not escaped, this is the closing triple quote
            newlines = code.count("\n", start, triple_pos)
            return triple_pos + 3, newlines

        # Escaped, continue searching after this position
        pos = triple_pos + 1

    return pos, newlines


def scan_c_style_number(
    code: str,
    pos: int,
    config: NumberConfig | None = None,
) -> tuple[TokenType, int]:
    """Scan a C-style number literal.

    Handles:
    - Hex: 0x1a2b
    - Octal: 0o755
    - Binary: 0b1010
    - Float: 3.14, 1e10, 3.14e-10
    - Integer: 42

    Args:
        pos: Position at first digit or dot.
        config: Number scanning configuration.

    Returns:
        Tuple of (token_type, position after number).
    """
    if config is None:
        config = NumberConfig()

    length = len(code)

    # Leading dot (e.g., .5)
    if code[pos] == ".":
        pos += 1
        pos = _scan_digits(code, pos, DIGITS, config.allow_underscores)
        pos = _scan_exponent(code, pos, config.allow_underscores)
        pos = _scan_suffix(code, pos, config.float_suffixes)
        return TokenType.NUMBER_FLOAT, pos

    # Check for prefixes (hex, octal, binary)
    if code[pos] == "0" and pos + 1 < length:
        two_char = code[pos : pos + 2]

        if two_char in config.hex_prefix:
            pos += 2
            pos = _scan_digits(code, pos, HEX_DIGITS, config.allow_underscores)
            pos = _scan_suffix(code, pos, config.integer_suffixes)
            return TokenType.NUMBER_HEX, pos

        if two_char in config.octal_prefix:
            pos += 2
            pos = _scan_digits(code, pos, OCTAL_DIGITS, config.allow_underscores)
            pos = _scan_suffix(code, pos, config.integer_suffixes)
            return TokenType.NUMBER_OCT, pos

        if two_char in config.binary_prefix:
            pos += 2
            pos = _scan_digits(code, pos, BINARY_DIGITS, config.allow_underscores)
            pos = _scan_suffix(code, pos, config.integer_suffixes)
            return TokenType.NUMBER_BIN, pos

    # Decimal number
    pos = _scan_digits(code, pos, DIGITS, config.allow_underscores)

    # Check for decimal point
    if pos < length and code[pos] == ".":
        # Make sure it's not a method call like 1.toString()
        if pos + 1 < length and code[pos + 1] in IDENT_START:
            pos = _scan_suffix(code, pos, config.integer_suffixes)
            return TokenType.NUMBER_INTEGER, pos

        pos += 1
        pos = _scan_digits(code, pos, DIGITS, config.allow_underscores)
        pos = _scan_exponent(code, pos, config.allow_underscores)
        pos = _scan_suffix(code, pos, config.float_suffixes)

        # Check for imaginary suffix
        if config.imaginary_suffix and pos < length:
            if code[pos] == config.imaginary_suffix:
                pos += 1

        return TokenType.NUMBER_FLOAT, pos

    # Check for exponent without decimal point
    if pos < length and code[pos] in "eE":
        pos = _scan_exponent(code, pos, config.allow_underscores)
        pos = _scan_suffix(code, pos, config.float_suffixes)
        return TokenType.NUMBER_FLOAT, pos

    # Check for imaginary suffix (Python: 1j)
    if config.imaginary_suffix and pos < length:
        if code[pos] == config.imaginary_suffix:
            pos += 1
            return TokenType.NUMBER_FLOAT, pos

    # Integer with optional suffix
    pos = _scan_suffix(code, pos, config.integer_suffixes)
    return TokenType.NUMBER_INTEGER, pos


def _scan_digits(
    code: str,
    pos: int,
    digit_set: frozenset[str],
    allow_underscores: bool,
) -> int:
    """Scan digits, optionally with underscores."""
    length = len(code)
    while pos < length:
        char = code[pos]
        if char in digit_set or (allow_underscores and char == "_"):
            pos += 1
        else:
            break
    return pos


def _scan_exponent(code: str, pos: int, allow_underscores: bool) -> int:
    """Scan optional exponent (e.g., e10, E-5)."""
    length = len(code)

    if pos >= length or code[pos] not in "eE":
        return pos

    pos += 1

    if pos < length and code[pos] in "+-":
        pos += 1

    return _scan_digits(code, pos, DIGITS, allow_underscores)


def _scan_suffix(code: str, pos: int, suffixes: tuple[str, ...]) -> int:
    """Scan optional type suffix (e.g., u32, f64, n)."""
    if not suffixes:
        return pos

    # Check suffixes longest-first
    for suffix in sorted(suffixes, key=len, reverse=True):
        if code[pos : pos + len(suffix)] == suffix:
            return pos + len(suffix)

    return pos


def scan_operators(
    code: str,
    pos: int,
    config: OperatorConfig,
) -> tuple[str | None, int]:
    """Scan operators using longest-match.

    Returns:
        Tuple of (operator string or None, new position).
    """
    # Check 3-char operators first
    if config.three_char and pos + 2 < len(code):
        three = code[pos : pos + 3]
        if three in config.three_char:
            return three, pos + 3

    # Check 2-char operators
    if config.two_char and pos + 1 < len(code):
        two = code[pos : pos + 2]
        if two in config.two_char:
            return two, pos + 2

    # Check 1-char operators
    if config.one_char:
        one = code[pos]
        if one in config.one_char:
            return one, pos + 1

    return None, pos


# =============================================================================
# Mixin classes for common patterns
# =============================================================================


class WhitespaceMixin:
    """Mixin for whitespace scanning. All languages use this."""

    WHITESPACE = WHITESPACE

    def _scan_whitespace(self, code: str, pos: int) -> tuple[int, int]:
        """Scan whitespace, returning (new_pos, newline_count)."""
        return scan_whitespace(code, pos)


class CStyleCommentsMixin:
    """Mixin for C-style comments (// and /* */).

    Used by: JavaScript, TypeScript, C, C++, Java, Go, Rust, etc.
    """

    def _scan_line_comment(self, code: str, pos: int) -> int:
        """Scan // comment to end of line."""
        return scan_line_comment(code, pos)

    def _scan_block_comment(self, code: str, pos: int) -> int:
        """Scan /* */ block comment."""
        return scan_block_comment(code, pos, "*/")

    def _try_comment(self, code: str, pos: int, line: int, col: int) -> tuple[Token | None, int]:
        """Try to scan a C-style comment.

        Returns (token, new_pos) or (None, pos) if not a comment.
        """
        if pos >= len(code) or code[pos] != "/":
            return None, pos

        if pos + 1 >= len(code):
            return None, pos

        next_char = code[pos + 1]

        if next_char == "/":
            # Line comment
            end_pos = scan_line_comment(code, pos + 2)
            return Token(TokenType.COMMENT_SINGLE, code[pos:end_pos], line, col), end_pos

        if next_char == "*":
            # Block comment
            end_pos = scan_block_comment(code, pos + 2, "*/")
            return (
                Token(TokenType.COMMENT_MULTILINE, code[pos:end_pos], line, col),
                end_pos,
            )

        return None, pos


class HashCommentsMixin:
    """Mixin for hash comments (#).

    Used by: Python, Ruby, Bash, Perl, YAML, etc.
    """

    def _scan_hash_comment(self, code: str, pos: int) -> int:
        """Scan # comment to end of line."""
        return scan_line_comment(code, pos)

    def _try_hash_comment(
        self, code: str, pos: int, line: int, col: int
    ) -> tuple[Token | None, int]:
        """Try to scan a hash comment."""
        if pos >= len(code) or code[pos] != "#":
            return None, pos

        end_pos = scan_line_comment(code, pos + 1)
        return Token(TokenType.COMMENT_SINGLE, code[pos:end_pos], line, col), end_pos


class CStyleNumbersMixin:
    """Mixin for C-style numbers.

    Used by: Most languages (Python, JavaScript, C, C++, Java, Go, Rust, etc.)
    """

    # Override in subclass to customize
    NUMBER_CONFIG: NumberConfig = NumberConfig()

    def _try_number(self, code: str, pos: int, line: int, col: int) -> tuple[Token | None, int]:
        """Try to scan a number literal."""
        char = code[pos]

        # Must start with digit or dot followed by digit
        if char not in DIGITS:
            if char != "." or pos + 1 >= len(code) or code[pos + 1] not in DIGITS:
                return None, pos

        start = pos
        token_type, pos = scan_c_style_number(code, pos, self.NUMBER_CONFIG)
        return Token(token_type, code[start:pos], line, col), pos


class CStyleStringsMixin:
    """Mixin for C-style strings (" and ').

    Used by: Most languages.
    """

    # Override in subclass to customize
    STRING_CONFIG: StringConfig = StringConfig()

    def _try_string(
        self, code: str, pos: int, line: int, col: int
    ) -> tuple[Token | None, int, int]:
        """Try to scan a string literal.

        Returns (token, new_pos, newline_count) or (None, pos, 0).
        """
        char = code[pos]

        if char == '"' and self.STRING_CONFIG.double_quote:
            start = pos
            pos += 1
            pos, newlines = scan_string(code, pos, '"', escape_char=self.STRING_CONFIG.escape_char)
            return Token(TokenType.STRING, code[start:pos], line, col), pos, newlines

        if char == "'" and self.STRING_CONFIG.single_quote:
            start = pos
            pos += 1
            pos, newlines = scan_string(code, pos, "'", escape_char=self.STRING_CONFIG.escape_char)
            return Token(TokenType.STRING, code[start:pos], line, col), pos, newlines

        if char == "`" and self.STRING_CONFIG.backtick:
            start = pos
            pos += 1
            pos, newlines = scan_string(
                code, pos, "`", escape_char=self.STRING_CONFIG.escape_char, allow_multiline=True
            )
            return Token(TokenType.STRING, code[start:pos], line, col), pos, newlines

        return None, pos, 0


class CStyleOperatorsMixin:
    """Mixin for scanning operators longest-first.

    Configure via OPERATOR_CONFIG in subclass.
    """

    OPERATOR_CONFIG: OperatorConfig = OperatorConfig()

    def _try_operator(self, code: str, pos: int, line: int, col: int) -> tuple[Token | None, int]:
        """Try to scan an operator."""
        op, new_pos = scan_operators(code, pos, self.OPERATOR_CONFIG)
        if op:
            return Token(TokenType.OPERATOR, op, line, col), new_pos
        return None, pos


# =============================================================================
# Pre-configured operator sets for common language families
# =============================================================================

# C-family operators (C, C++, Java, JavaScript, etc.)
C_FAMILY_OPERATORS = OperatorConfig(
    three_char=frozenset({">>>=", ">>=", "<<=", "**=", "//=", "&&=", "||=", "??="}),
    two_char=frozenset(
        {
            "==",
            "!=",
            "<=",
            ">=",
            "&&",
            "||",
            "++",
            "--",
            "+=",
            "-=",
            "*=",
            "/=",
            "%=",
            "&=",
            "|=",
            "^=",
            "<<",
            ">>",
            "->",
            "=>",
            "::",
            "??",
            "?.",
            "**",
            "//",
        }
    ),
    one_char=frozenset("+-*/%&|^~!<>=?:."),
)

# Python operators
PYTHON_OPERATORS = OperatorConfig(
    three_char=frozenset({"**=", "//=", ">>=", "<<="}),
    two_char=frozenset(
        {
            "==",
            "!=",
            "<=",
            ">=",
            "**",
            "//",
            "<<",
            ">>",
            "+=",
            "-=",
            "*=",
            "/=",
            "%=",
            "@=",
            "&=",
            "|=",
            "^=",
            ":=",
            "->",
        }
    ),
    one_char=frozenset("+-*/%@&|^~<>=!"),
)

# Rust operators
RUST_OPERATORS = OperatorConfig(
    three_char=frozenset({"..=", ">>=", "<<="}),
    two_char=frozenset(
        {
            "==",
            "!=",
            "<=",
            ">=",
            "&&",
            "||",
            "<<",
            ">>",
            "+=",
            "-=",
            "*=",
            "/=",
            "%=",
            "&=",
            "|=",
            "^=",
            "->",
            "=>",
            "::",
            "..",
        }
    ),
    one_char=frozenset("+-*/%&|^~!<>=?"),
)

# Go operators
GO_OPERATORS = OperatorConfig(
    three_char=frozenset({"<<=", ">>=", "&^="}),
    two_char=frozenset(
        {
            "==",
            "!=",
            "<=",
            ">=",
            "&&",
            "||",
            "<<",
            ">>",
            "++",
            "--",
            "+=",
            "-=",
            "*=",
            "/=",
            "%=",
            "&=",
            "|=",
            "^=",
            ":=",
            "<-",
            "&^",
        }
    ),
    one_char=frozenset("+-*/%&|^~!<>="),
)
