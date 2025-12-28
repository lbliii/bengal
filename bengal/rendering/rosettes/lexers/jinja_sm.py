"""Hand-written Jinja2 lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.

Jinja2 syntax:
    {# ... #}  - Comments
    {{ ... }}  - Variable expressions (output)
    {% ... %}  - Statements (if, for, block, etc.)
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._config import LexerConfig
from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    DIGITS,
    IDENT_CONT,
    IDENT_START,
    CStyleNumbersMixin,
    NumberConfig,
    scan_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["JinjaStateMachineLexer"]


# Jinja2 keywords
_KEYWORDS: frozenset[str] = frozenset(
    {
        # Control flow
        "if",
        "elif",
        "else",
        "endif",
        "for",
        "endfor",
        "break",
        "continue",
        # Blocks and inheritance
        "block",
        "endblock",
        "extends",
        "include",
        "import",
        "from",
        # Macros and calls
        "macro",
        "endmacro",
        "call",
        "endcall",
        # Filters and sets
        "filter",
        "endfilter",
        "set",
        "endset",
        # Scoping
        "with",
        "endwith",
        # Raw (no template processing)
        "raw",
        "endraw",
        # Others
        "autoescape",
        "endautoescape",
        "trans",
        "endtrans",
        "pluralize",
        "do",
        "recursive",
        "scoped",
        "ignore",
        "missing",
        "context",
        "as",
    }
)

# Jinja2 boolean/word operators
_OPERATORS: frozenset[str] = frozenset(
    {
        "and",
        "or",
        "not",
        "in",
        "is",
    }
)

# Jinja2 constants
_CONSTANTS: frozenset[str] = frozenset(
    {
        "true",
        "false",
        "none",
        "True",
        "False",
        "None",
    }
)

# Common built-in tests (is X)
_BUILTIN_TESTS: frozenset[str] = frozenset(
    {
        "defined",
        "undefined",
        "none",
        "divisibleby",
        "even",
        "odd",
        "iterable",
        "mapping",
        "number",
        "sequence",
        "string",
        "callable",
        "sameas",
        "eq",
        "ne",
        "lt",
        "le",
        "gt",
        "ge",
        "escaped",
        "lower",
        "upper",
    }
)

# Common built-in filters
_BUILTIN_FILTERS: frozenset[str] = frozenset(
    {
        # String filters
        "capitalize",
        "center",
        "escape",
        "forceescape",
        "format",
        "indent",
        "join",
        "lower",
        "lstrip",
        "replace",
        "rstrip",
        "safe",
        "striptags",
        "title",
        "trim",
        "truncate",
        "upper",
        "urlencode",
        "urlize",
        "wordcount",
        "wordwrap",
        "e",
        # List filters
        "batch",
        "first",
        "groupby",
        "items",
        "last",
        "length",
        "list",
        "map",
        "max",
        "min",
        "random",
        "reject",
        "rejectattr",
        "reverse",
        "select",
        "selectattr",
        "slice",
        "sort",
        "sum",
        "unique",
        # Number filters
        "abs",
        "filesizeformat",
        "float",
        "int",
        "round",
        # Other
        "attr",
        "default",
        "d",
        "dictsort",
        "pprint",
        "tojson",
        "xmlattr",
    }
)


class JinjaStateMachineLexer(CStyleNumbersMixin, StateMachineLexer):
    """Jinja2 template lexer.

    Tokenizes Jinja2 template syntax including:
    - Comments: {# ... #}
    - Expressions: {{ ... }}
    - Statements: {% ... %}
    - Plain text between template tags
    """

    name = "jinja"
    aliases = ("jinja2", "j2", "django")
    filenames = ("*.jinja", "*.jinja2", "*.j2")
    mimetypes = ("application/x-jinja", "text/x-jinja")

    # Python-style numbers
    NUMBER_CONFIG = NumberConfig(
        allow_underscores=True,
        imaginary_suffix="j",
    )

    def tokenize(
        self,
        code: str,
        config: LexerConfig | None = None,
        *,
        start: int = 0,
        end: int | None = None,
    ) -> Iterator[Token]:
        pos = start
        length = end if end is not None else len(code)
        line = 1
        line_start = start

        while pos < length:
            col = pos - line_start + 1

            # Check for Jinja2 template tags
            if code[pos] == "{":
                # Comment: {# ... #}
                if pos + 1 < length and code[pos + 1] == "#":
                    start = pos
                    start_line = line
                    pos += 2
                    while pos < length:
                        if code[pos : pos + 2] == "#}":
                            pos += 2
                            break
                        if code[pos] == "\n":
                            line += 1
                            line_start = pos + 1
                        pos += 1
                    yield Token(TokenType.COMMENT_MULTILINE, code[start:pos], start_line, col)
                    continue

                # Expression: {{ ... }}
                if pos + 1 < length and code[pos + 1] == "{":
                    yield Token(TokenType.PUNCTUATION_MARKER, "{{", line, col)
                    pos += 2
                    yield from self._tokenize_expression(code, pos, line, line_start)
                    # Update pos and line tracking after expression
                    pos, line, line_start = self._find_closing_braces(code, pos, line, line_start)
                    continue

                # Statement: {% ... %}
                if pos + 1 < length and code[pos + 1] == "%":
                    yield Token(TokenType.PUNCTUATION_MARKER, "{%", line, col)
                    pos += 2
                    yield from self._tokenize_statement(code, pos, line, line_start)
                    pos, line, line_start = self._find_closing_percent(code, pos, line, line_start)
                    continue

            # Plain text (outside template tags)
            start = pos
            start_line = line
            while pos < length:
                char = code[pos]
                if char == "{" and pos + 1 < length and code[pos + 1] in "#%{":
                    break
                if char == "\n":
                    line += 1
                    line_start = pos + 1
                pos += 1

            if pos > start:
                text = code[start:pos]
                if text.strip():
                    yield Token(TokenType.TEXT, text, start_line, col)
                elif text:
                    yield Token(TokenType.WHITESPACE, text, start_line, col)

    def _find_closing_braces(
        self, code: str, pos: int, line: int, line_start: int
    ) -> tuple[int, int, int]:
        """Find closing }} and return updated position and line info."""
        length = len(code)
        while pos < length:
            if code[pos : pos + 2] == "}}":
                return pos + 2, line, line_start
            if code[pos] == "\n":
                line += 1
                line_start = pos + 1
            # Skip strings
            if code[pos] in "\"'":
                quote = code[pos]
                pos += 1
                while pos < length and code[pos] != quote:
                    if code[pos] == "\\" and pos + 1 < length:
                        pos += 2
                        continue
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                if pos < length:
                    pos += 1
                continue
            pos += 1
        return pos, line, line_start

    def _find_closing_percent(
        self, code: str, pos: int, line: int, line_start: int
    ) -> tuple[int, int, int]:
        """Find closing %} and return updated position and line info."""
        length = len(code)
        while pos < length:
            if code[pos : pos + 2] == "%}":
                return pos + 2, line, line_start
            if code[pos] == "\n":
                line += 1
                line_start = pos + 1
            # Skip strings
            if code[pos] in "\"'":
                quote = code[pos]
                pos += 1
                while pos < length and code[pos] != quote:
                    if code[pos] == "\\" and pos + 1 < length:
                        pos += 2
                        continue
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                if pos < length:
                    pos += 1
                continue
            pos += 1
        return pos, line, line_start

    def _tokenize_expression(
        self, code: str, pos: int, line: int, line_start: int
    ) -> Iterator[Token]:
        """Tokenize inside {{ ... }}."""
        yield from self._tokenize_jinja_content(code, pos, line, line_start, "}}")

    def _tokenize_statement(
        self, code: str, pos: int, line: int, line_start: int
    ) -> Iterator[Token]:
        """Tokenize inside {% ... %}."""
        yield from self._tokenize_jinja_content(code, pos, line, line_start, "%}")

    def _tokenize_jinja_content(
        self,
        code: str,
        pos: int,
        line: int,
        line_start: int,
        end_marker: str,
    ) -> Iterator[Token]:
        """Tokenize Jinja2 content (expressions or statements)."""
        length = len(code)
        after_pipe = False

        while pos < length:
            col = pos - line_start + 1
            char = code[pos]

            # Check for end marker
            if code[pos : pos + 2] == end_marker:
                yield Token(TokenType.PUNCTUATION_MARKER, end_marker, line, col)
                return

            # Whitespace
            if char in " \t":
                start = pos
                while pos < length and code[pos] in " \t":
                    pos += 1
                yield Token(TokenType.WHITESPACE, code[start:pos], line, col)
                continue

            if char == "\n":
                yield Token(TokenType.WHITESPACE, char, line, col)
                pos += 1
                line += 1
                line_start = pos
                continue

            # Strings
            if char in "\"'":
                start = pos
                quote = char
                pos += 1
                pos, newlines = scan_string(code, pos, quote)
                yield Token(TokenType.STRING, code[start:pos], line, col)
                line += newlines
                if newlines > 0:
                    last_newline = code.rfind("\n", start, pos)
                    if last_newline != -1:
                        line_start = last_newline + 1
                after_pipe = False
                continue

            # Numbers
            if char in DIGITS or (char == "." and pos + 1 < length and code[pos + 1] in DIGITS):
                token, new_pos = self._try_number(code, pos, line, col)
                if token:
                    yield token
                    pos = new_pos
                    after_pipe = False
                    continue

            # Pipe (filter separator)
            if char == "|":
                yield Token(TokenType.PUNCTUATION, "|", line, col)
                pos += 1
                after_pipe = True
                continue

            # Identifiers, keywords, and operators
            if char in IDENT_START:
                start = pos
                while pos < length and code[pos] in IDENT_CONT:
                    pos += 1
                word = code[start:pos]

                # Classify the identifier
                if after_pipe and word.lower() in _BUILTIN_FILTERS:
                    yield Token(TokenType.NAME_FUNCTION, word, line, col)
                elif word in _KEYWORDS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif word in _OPERATORS:
                    yield Token(TokenType.OPERATOR_WORD, word, line, col)
                elif word in _CONSTANTS or word.lower() in {"true", "false", "none"}:
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif word in _BUILTIN_TESTS:
                    yield Token(TokenType.NAME_BUILTIN, word, line, col)
                elif word in _BUILTIN_FILTERS:
                    yield Token(TokenType.NAME_FUNCTION, word, line, col)
                else:
                    yield Token(TokenType.NAME_VARIABLE, word, line, col)
                after_pipe = False
                continue

            # Multi-character operators
            if pos + 1 < length:
                two_char = code[pos : pos + 2]
                if two_char in {"==", "!=", "<=", ">=", "**", "//", "~="}:
                    yield Token(TokenType.OPERATOR, two_char, line, col)
                    pos += 2
                    after_pipe = False
                    continue

            # Single-character operators and punctuation
            if char in "+-*/%~<>=":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                after_pipe = False
                continue

            if char in "()[]{},:?.":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                after_pipe = False
                continue

            # Unknown character
            yield Token(TokenType.ERROR, char, line, col)
            pos += 1
            after_pipe = False
