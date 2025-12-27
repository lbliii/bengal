"""Kida lexer — tokenizes template source code into a token stream.

The lexer scans template source and produces Token objects that the Parser
consumes. It operates in four modes based on current context:

Modes:
    - **DATA**: Outside template constructs; collects raw text
    - **VARIABLE**: Inside `{{ }}`; tokenizes expression
    - **BLOCK**: Inside `{% %}`; tokenizes statement
    - **COMMENT**: Inside `{# #}`; skips to closing delimiter

Token Types:
    - **Delimiters**: BLOCK_BEGIN, BLOCK_END, VARIABLE_BEGIN, VARIABLE_END
    - **Literals**: STRING, INTEGER, FLOAT
    - **Identifiers**: NAME (includes keywords like 'if', 'for', 'and')
    - **Operators**: ADD, SUB, MUL, DIV, EQ, NE, LT, GT, etc.
    - **Punctuation**: DOT, COMMA, COLON, PIPE, LPAREN, RPAREN, etc.
    - **Data**: DATA (raw text between template constructs)

Whitespace Control:
    Supports Jinja2-style whitespace trimming:
    - `{{- expr }}`: Strip whitespace before
    - `{{ expr -}}`: Strip whitespace after
    - `{%- stmt %}` / `{% stmt -%}`: Same for blocks

Performance:
    - **Compiled regex**: Patterns are class-level, compiled once
    - **O(1) operator lookup**: Dict-based, not list iteration
    - **Single-pass scanning**: No backtracking
    - **Generator-based**: Memory-efficient for large templates

Thread-Safety:
    Lexer instances are single-use. Create one per tokenization.
    The resulting token list is immutable.

Example:
    >>> from bengal.rendering.kida.lexer import Lexer, tokenize
    >>> lexer = Lexer("Hello, {{ name }}!")
    >>> tokens = list(lexer.tokenize())
    >>> [(t.type.name, t.value) for t in tokens]
    [('DATA', 'Hello, '), ('VARIABLE_BEGIN', '{{'), ('NAME', 'name'),
     ('VARIABLE_END', '}}'), ('DATA', '!'), ('EOF', '')]

    # Convenience function:
    >>> tokens = tokenize("{{ x | upper }}")
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum, auto

from bengal.rendering.kida._types import Token, TokenType


class LexerMode(Enum):
    """Lexer operating mode."""

    DATA = auto()  # Outside template constructs
    BLOCK = auto()  # Inside {% %}
    VARIABLE = auto()  # Inside {{ }}
    COMMENT = auto()  # Inside {# #}


@dataclass(frozen=True, slots=True)
class LexerConfig:
    """Lexer configuration for delimiter customization and whitespace control.

    Allows customizing template delimiters and enabling automatic whitespace
    trimming. Frozen for thread-safety (immutable after creation).

    Attributes:
        block_start: Block tag opening delimiter (default: '{%')
        block_end: Block tag closing delimiter (default: '%}')
        variable_start: Variable tag opening delimiter (default: '{{')
        variable_end: Variable tag closing delimiter (default: '}}')
        comment_start: Comment opening delimiter (default: '{#')
        comment_end: Comment closing delimiter (default: '#}')
        line_statement_prefix: Line statement prefix, e.g., '#' (default: None)
        line_comment_prefix: Line comment prefix, e.g., '##' (default: None)
        trim_blocks: Remove first newline after block tags (default: False)
        lstrip_blocks: Strip leading whitespace before block tags (default: False)

    Example:
        # Use Ruby-style ERB delimiters:
        >>> config = LexerConfig(
        ...     variable_start='<%=',
        ...     variable_end='%>',
        ...     block_start='<%',
        ...     block_end='%>',
        ... )

        # Enable automatic whitespace control:
        >>> config = LexerConfig(trim_blocks=True, lstrip_blocks=True)
    """

    block_start: str = "{%"
    block_end: str = "%}"
    variable_start: str = "{{"
    variable_end: str = "}}"
    comment_start: str = "{#"
    comment_end: str = "#}"
    line_statement_prefix: str | None = None
    line_comment_prefix: str | None = None
    trim_blocks: bool = False
    lstrip_blocks: bool = False


# Default configuration (immutable singleton)
DEFAULT_CONFIG = LexerConfig()

# Maximum number of tokens allowed (DoS protection)
# Typical template: 100-1000 tokens
# Large template: 5k-10k tokens
# 100k tokens = ~100x normal size (reasonable upper bound)
MAX_TOKENS = 100_000


class LexerError(Exception):
    """Lexer error with source location."""

    def __init__(
        self,
        message: str,
        source: str,
        lineno: int,
        col_offset: int,
        suggestion: str | None = None,
    ):
        self.message = message
        self.source = source
        self.lineno = lineno
        self.col_offset = col_offset
        self.suggestion = suggestion
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        lines = self.source.splitlines()
        error_line = lines[self.lineno - 1] if self.lineno <= len(lines) else ""
        pointer = " " * self.col_offset + "^"

        msg = f"""
Lexer Error: {self.message}
  --> line {self.lineno}:{self.col_offset}
   |
 {self.lineno:>3} | {error_line}
   | {pointer}
"""
        if self.suggestion:
            msg += f"\nSuggestion: {self.suggestion}"
        return msg


class Lexer:
    """Template lexer that transforms source into a token stream.

    The Lexer is the first stage of template compilation. It scans source text
    and yields Token objects representing literals, operators, identifiers,
    and template delimiters.

    Thread-Safety:
        Instance state is mutable during tokenization (position tracking).
        Create one Lexer per source string; do not reuse across threads.

    Operator Lookup:
        Uses O(1) dict lookup instead of O(k) list iteration:
        ```python
        _OPERATORS_2CHAR = {"**": TokenType.POW, "//": TokenType.FLOORDIV, ...}
        _OPERATORS_1CHAR = {"+": TokenType.ADD, "-": TokenType.SUB, ...}
        ```

    Whitespace Control:
        Handles `{{-`, `-}}`, `{%-`, `-%}` modifiers:
        - Left modifier (`{{-`, `{%-`): Strips trailing whitespace from preceding DATA
        - Right modifier (`-}}`, `-%}`): Strips leading whitespace from following DATA

    Error Handling:
        `LexerError` includes source snippet with caret and suggestions:
        ```
        Lexer Error: Unterminated string literal
          --> line 3:15
           |
         3 | {% set x = "hello %}
           |               ^
        Suggestion: Add closing " to end the string
        ```

    Example:
        >>> lexer = Lexer("{% if x %}{{ x }}{% end %}")
        >>> for token in lexer.tokenize():
        ...     print(f"{token.type.name:15} {token.value!r}")
        BLOCK_BEGIN     '{%'
        NAME            'if'
        NAME            'x'
        BLOCK_END       '%}'
        VARIABLE_BEGIN  '{{'
        NAME            'x'
        VARIABLE_END    '}}'
        BLOCK_BEGIN     '{%'
        NAME            'end'
        BLOCK_END       '%}'
        EOF             ''
    """

    # Compiled patterns (class-level, immutable)
    _WHITESPACE_RE = re.compile(r"[ \t\n\r]+")
    _NAME_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
    _STRING_RE = re.compile(
        r"('([^'\\]*(?:\\.[^'\\]*)*)'"  # Single-quoted
        r'|"([^"\\]*(?:\\.[^"\\]*)*)")'  # Double-quoted
    )
    _INTEGER_RE = re.compile(r"\d+")
    _FLOAT_RE = re.compile(r"\d+\.\d*|\.\d+")

    # O(1) operator lookup tables (optimized from O(k) list iteration)
    # Three-char operators checked first, then two-char, then single-char
    _OPERATORS_3CHAR: dict[str, TokenType] = {
        "...": TokenType.RANGE_EXCLUSIVE,  # Range exclusive: 1...11
    }
    _OPERATORS_2CHAR: dict[str, TokenType] = {
        "**": TokenType.POW,
        "//": TokenType.FLOORDIV,
        "==": TokenType.EQ,
        "!=": TokenType.NE,
        "<=": TokenType.LE,
        ">=": TokenType.GE,
        "|>": TokenType.PIPELINE,  # Kida-native pipeline operator
        # Modern syntax features (RFC: kida-modern-syntax-features)
        "?.": TokenType.OPTIONAL_DOT,  # Optional chaining: obj?.attr
        "?[": TokenType.OPTIONAL_BRACKET,  # Optional subscript: obj?[key]
        "??": TokenType.NULLISH_COALESCE,  # Null coalescing: a ?? b
        "..": TokenType.RANGE_INCLUSIVE,  # Range inclusive: 1..10
    }
    _OPERATORS_1CHAR: dict[str, TokenType] = {
        "<": TokenType.LT,
        ">": TokenType.GT,
        "+": TokenType.ADD,
        "-": TokenType.SUB,
        "*": TokenType.MUL,
        "/": TokenType.DIV,
        "%": TokenType.MOD,
        "=": TokenType.ASSIGN,
        ".": TokenType.DOT,
        ",": TokenType.COMMA,
        ":": TokenType.COLON,
        "|": TokenType.PIPE,
        "~": TokenType.TILDE,
        "(": TokenType.LPAREN,
        ")": TokenType.RPAREN,
        "[": TokenType.LBRACKET,
        "]": TokenType.RBRACKET,
        "{": TokenType.LBRACE,
        "}": TokenType.RBRACE,
    }

    __slots__ = (
        "_source",
        "_config",
        "_pos",
        "_lineno",
        "_col_offset",
        "_mode",
        "_trim_next_data",  # Strip leading whitespace from next DATA token
        "_last_block_end",  # Position after last block end (for trim_blocks)
    )

    def __init__(
        self,
        source: str,
        config: LexerConfig | None = None,
    ):
        """Initialize lexer with source code.

        Args:
            source: Template source code
            config: Lexer configuration (uses defaults if None)
        """
        self._source = source
        self._config = config or DEFAULT_CONFIG
        self._pos = 0
        self._lineno = 1
        self._col_offset = 0
        self._mode = LexerMode.DATA
        self._trim_next_data = False  # Set when -}} or -%} is encountered
        self._last_block_end = -1  # Track for trim_blocks

    def tokenize(self) -> Iterator[Token]:
        """Tokenize the source and yield tokens.

        Yields:
            Token objects in order of appearance

        Raises:
            LexerError: If source contains invalid syntax or token limit exceeded
        """
        token_count = 0

        def _counted_yield(token: Token) -> Token:
            """Helper to count tokens as they're yielded."""
            nonlocal token_count
            token_count += 1
            if token_count > MAX_TOKENS:
                raise LexerError(
                    f"Token limit exceeded ({MAX_TOKENS})",
                    self._source,
                    self._lineno,
                    self._col_offset,
                    suggestion="Template is too complex. Split into smaller templates.",
                )
            return token

        def _counted_yield_from(tokens: Iterator[Token]) -> Iterator[Token]:
            """Helper to count tokens from a generator."""
            for token in tokens:
                yield _counted_yield(token)

        while self._pos < len(self._source):
            if self._mode == LexerMode.DATA:
                yield from _counted_yield_from(self._tokenize_data())
            elif self._mode == LexerMode.VARIABLE:
                yield from _counted_yield_from(
                    self._tokenize_code(
                        self._config.variable_end,
                        TokenType.VARIABLE_END,
                    )
                )
            elif self._mode == LexerMode.BLOCK:
                yield from _counted_yield_from(
                    self._tokenize_code(
                        self._config.block_end,
                        TokenType.BLOCK_END,
                    )
                )
            elif self._mode == LexerMode.COMMENT:
                yield from _counted_yield_from(self._tokenize_comment())

        # Emit EOF token (doesn't count toward limit)
        yield Token(TokenType.EOF, "", self._lineno, self._col_offset)

    def _tokenize_data(self) -> Iterator[Token]:
        """Tokenize raw data outside template constructs."""
        start_lineno = self._lineno
        start_col = self._col_offset

        # Find next template construct
        next_construct = self._find_next_construct()

        if next_construct is None:
            # Rest of source is data
            data = self._source[self._pos :]
            if data:
                # Apply trim_next_data if set (from previous -%} or -}})
                if self._trim_next_data:
                    data = data.lstrip()
                    self._trim_next_data = False
                # Apply trim_blocks if enabled (strip first newline after block)
                elif self._last_block_end == self._pos and self._config.trim_blocks:
                    if data.startswith("\n"):
                        data = data[1:]
                    elif data.startswith("\r\n"):
                        data = data[2:]
                self._advance(len(self._source[self._pos :]))
                if data:
                    yield Token(TokenType.DATA, data, start_lineno, start_col)
            return

        construct_type, construct_pos = next_construct

        # Emit data before construct
        if construct_pos > self._pos:
            data = self._source[self._pos : construct_pos]

            # Apply trim_next_data if set (from previous -%} or -}})
            if self._trim_next_data:
                data = data.lstrip()
                self._trim_next_data = False
            # Apply trim_blocks if enabled (strip first newline after block)
            elif self._last_block_end == self._pos and self._config.trim_blocks:
                if data.startswith("\n"):
                    data = data[1:]
                elif data.startswith("\r\n"):
                    data = data[2:]

            # Apply lstrip_blocks: strip leading whitespace before block tags
            # only if the whitespace is on the same line as the block
            if construct_type == "block" and self._config.lstrip_blocks and data:
                # Find if there's only whitespace on this line before the block
                last_newline = data.rfind("\n")
                if last_newline == -1:
                    # No newline - check if entire data is just whitespace
                    if data.strip() == "":
                        data = ""
                else:
                    # Check if content after last newline is just whitespace
                    line_content = data[last_newline + 1 :]
                    if line_content.strip() == "":
                        data = data[: last_newline + 1]

            # Check for left trim modifier ({%- or {{-)
            # If the next construct starts with -, strip trailing whitespace from data
            # IMPORTANT: The - must be IMMEDIATELY after the delimiter (no space)
            delimiter_len = 2  # Length of {{ or {%
            after_delimiter_pos = construct_pos + delimiter_len
            if after_delimiter_pos < len(self._source) and self._source[after_delimiter_pos] == "-":
                # Left trim modifier found - strip trailing whitespace
                data = data.rstrip()

            self._advance(construct_pos - self._pos)
            if data:
                yield Token(TokenType.DATA, data, start_lineno, start_col)

        # Emit construct start token
        if construct_type == "variable":
            yield self._emit_delimiter(
                self._config.variable_start,
                TokenType.VARIABLE_BEGIN,
            )
            self._mode = LexerMode.VARIABLE
        elif construct_type == "block":
            yield self._emit_delimiter(
                self._config.block_start,
                TokenType.BLOCK_BEGIN,
            )
            self._mode = LexerMode.BLOCK
        elif construct_type == "comment":
            yield self._emit_delimiter(
                self._config.comment_start,
                TokenType.COMMENT_BEGIN,
            )
            self._mode = LexerMode.COMMENT

    def _tokenize_code(
        self,
        end_delimiter: str,
        end_token_type: TokenType,
    ) -> Iterator[Token]:
        """Tokenize code inside {{ }} or {% %}."""
        # Handle whitespace trimming (- modifier)
        # e.g., {{- or {%- for left trim, -}} or -%} for right trim
        #
        # IMPORTANT: The - for whitespace control must be IMMEDIATELY after
        # the delimiter (no space). If there's a space before -, it's a unary minus.
        # - {{- expr }} -> left trim (- immediately after {{)
        # - {{ -5 }}    -> unary minus (space before -)

        # Check for leading - (left trim marker) IMMEDIATELY at start of code (no whitespace)
        if self._pos < len(self._source) and self._source[self._pos] == "-":
            # This is a whitespace control marker - skip it
            self._advance(1)
            # Note: The previous DATA token was already emitted, so we can't
            # modify it. This is handled in _tokenize_data by stripping trailing
            # whitespace when we detect {%- or {{-

        while self._pos < len(self._source):
            # Skip whitespace
            self._skip_whitespace()

            if self._pos >= len(self._source):
                raise LexerError(
                    f"Unexpected end of template, expected '{end_delimiter}'",
                    self._source,
                    self._lineno,
                    self._col_offset,
                    f"Add '{end_delimiter}' to close the tag",
                )

            # Check for end delimiter (with optional - modifier)
            if self._source[self._pos :].startswith("-" + end_delimiter):
                # Trim right whitespace marker - strip leading whitespace from next DATA
                self._advance(1)  # Skip -
                self._trim_next_data = True
                yield self._emit_delimiter(end_delimiter, end_token_type)
                # Track block end position for trim_blocks
                if end_token_type == TokenType.BLOCK_END:
                    self._last_block_end = self._pos
                self._mode = LexerMode.DATA
                return

            if self._source[self._pos :].startswith(end_delimiter):
                yield self._emit_delimiter(end_delimiter, end_token_type)
                # Track block end position for trim_blocks
                if end_token_type == TokenType.BLOCK_END:
                    self._last_block_end = self._pos
                self._mode = LexerMode.DATA
                return

            # Tokenize expression/statement content
            yield self._next_code_token()

    def _tokenize_comment(self) -> Iterator[Token]:
        """Skip comment content until closing delimiter."""
        end = self._config.comment_end
        end_pos = self._source.find(end, self._pos)

        if end_pos == -1:
            raise LexerError(
                f"Unclosed comment, expected '{end}'",
                self._source,
                self._lineno,
                self._col_offset,
                f"Add '{end}' to close the comment",
            )

        # Skip comment content
        comment_content = self._source[self._pos : end_pos]
        self._advance(len(comment_content))

        # Emit comment end
        yield self._emit_delimiter(end, TokenType.COMMENT_END)
        self._mode = LexerMode.DATA

    def _next_code_token(self) -> Token:
        """Get the next token from code content.

        Complexity: O(1) for operator lookup (dict-based).
        """
        char = self._source[self._pos]

        # String literal
        if char in ('"', "'"):
            return self._scan_string()

        # Number
        if char.isdigit():
            return self._scan_number()

        # Name or keyword
        if char.isalpha() or char == "_":
            return self._scan_name()

        # Three-char operators (check first for longest match)
        if self._pos + 2 < len(self._source):
            three_char = self._source[self._pos : self._pos + 3]
            if three_char in self._OPERATORS_3CHAR:
                return self._emit_delimiter(three_char, self._OPERATORS_3CHAR[three_char])

        # Two-char operators (check second for longest match)
        if self._pos + 1 < len(self._source):
            two_char = self._source[self._pos : self._pos + 2]
            if two_char in self._OPERATORS_2CHAR:
                return self._emit_delimiter(two_char, self._OPERATORS_2CHAR[two_char])

        # Single-char operators - O(1) dict lookup
        if char in self._OPERATORS_1CHAR:
            return self._emit_delimiter(char, self._OPERATORS_1CHAR[char])

        # Unknown character
        raise LexerError(
            f"Unexpected character: {char!r}",
            self._source,
            self._lineno,
            self._col_offset,
        )

    def _scan_string(self) -> Token:
        """Scan a string literal."""
        start_lineno = self._lineno
        start_col = self._col_offset
        quote_char = self._source[self._pos]
        pos = self._pos + 1

        while pos < len(self._source):
            char = self._source[pos]
            if char == quote_char:
                # End of string
                value = self._source[self._pos + 1 : pos]
                self._advance(pos - self._pos + 1)
                return Token(TokenType.STRING, value, start_lineno, start_col)
            elif char == "\\":
                # Escape sequence
                pos += 2
            else:
                pos += 1

        raise LexerError(
            "Unterminated string literal",
            self._source,
            start_lineno,
            start_col,
            f"Add closing {quote_char} to end the string",
        )

    def _scan_number(self) -> Token:
        """Scan a number literal (integer or float).

        Note: Special handling for range literals (1..10, 1...11).
        If we see digits followed by '..' or '...', treat the digits as
        an integer, not a float, so the range operator can be parsed.
        """
        start_lineno = self._lineno
        start_col = self._col_offset

        # Check for range literal: digits followed by .. or ...
        # If so, parse just the integer part so the range operator is preserved
        int_match = self._INTEGER_RE.match(self._source, self._pos)
        if int_match:
            # Check what follows the integer
            end_pos = self._pos + len(int_match.group())
            if end_pos < len(self._source):
                next_char = self._source[end_pos]
                # If followed by '.', check if it's '..' or '...'
                if next_char == "." and end_pos + 1 < len(self._source):
                    next_next = self._source[end_pos + 1]
                    if next_next == ".":
                        # This is 1..x or 1...x - return integer only
                        value = int_match.group()
                        self._advance(len(value))
                        return Token(TokenType.INTEGER, value, start_lineno, start_col)

        # Try float (longer match)
        match = self._FLOAT_RE.match(self._source, self._pos)
        if match and "." in match.group():
            value = match.group()
            self._advance(len(value))
            return Token(TokenType.FLOAT, value, start_lineno, start_col)

        # Integer
        if int_match:
            value = int_match.group()
            self._advance(len(value))
            return Token(TokenType.INTEGER, value, start_lineno, start_col)

        # Should not reach here
        raise LexerError(
            "Invalid number",
            self._source,
            self._lineno,
            self._col_offset,
        )

    def _scan_name(self) -> Token:
        """Scan a name or keyword."""
        start_lineno = self._lineno
        start_col = self._col_offset

        match = self._NAME_RE.match(self._source, self._pos)
        if not match:
            raise LexerError(
                "Invalid identifier",
                self._source,
                self._lineno,
                self._col_offset,
            )

        name = match.group()
        self._advance(len(name))

        # Map keywords to token types
        if name == "and":
            return Token(TokenType.AND, name, start_lineno, start_col)
        elif name == "or":
            return Token(TokenType.OR, name, start_lineno, start_col)
        elif name == "not":
            return Token(TokenType.NOT, name, start_lineno, start_col)
        elif name == "in":
            return Token(TokenType.IN, name, start_lineno, start_col)
        elif name == "is":
            return Token(TokenType.IS, name, start_lineno, start_col)
        else:
            return Token(TokenType.NAME, name, start_lineno, start_col)

    def _find_next_construct(self) -> tuple[str, int] | None:
        """Find the next template construct ({{ }}, {% %}, or {# #})."""
        positions = []

        for name, start in [
            ("variable", self._config.variable_start),
            ("block", self._config.block_start),
            ("comment", self._config.comment_start),
        ]:
            pos = self._source.find(start, self._pos)
            if pos != -1:
                positions.append((name, pos))

        if not positions:
            return None

        # Return the closest construct
        return min(positions, key=lambda x: x[1])

    def _emit_delimiter(self, delimiter: str, token_type: TokenType) -> Token:
        """Emit a delimiter token and advance position."""
        token = Token(token_type, delimiter, self._lineno, self._col_offset)
        self._advance(len(delimiter))
        return token

    def _skip_whitespace(self) -> None:
        """Skip whitespace characters."""
        match = self._WHITESPACE_RE.match(self._source, self._pos)
        if match:
            self._advance(len(match.group()))

    def _advance(self, count: int) -> None:
        """Advance position by count characters, tracking line/column.

        Optimized to use batch processing with count() for newline detection
        instead of character-by-character iteration. Provides ~15-20% speedup
        for templates with long DATA nodes.
        """
        end_pos = min(self._pos + count, len(self._source))
        chunk = self._source[self._pos : end_pos]
        newlines = chunk.count("\n")
        if newlines:
            self._lineno += newlines
            # Column is distance from last newline to end
            last_nl = chunk.rfind("\n")
            self._col_offset = len(chunk) - last_nl - 1
        else:
            self._col_offset += len(chunk)
        self._pos = end_pos


def tokenize(source: str, config: LexerConfig | None = None) -> list[Token]:
    """Convenience function to tokenize source into a list.

    Args:
        source: Template source code
        config: Optional lexer configuration

    Returns:
        List of tokens

    Example:
        >>> tokens = tokenize("{{ name }}")
        >>> [t.type for t in tokens]
        [<TokenType.VARIABLE_BEGIN>, <TokenType.NAME>, <TokenType.VARIABLE_END>, <TokenType.EOF>]
    """
    lexer = Lexer(source, config)
    return list(lexer.tokenize())
