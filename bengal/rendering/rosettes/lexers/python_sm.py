"""Hand-written Python lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._config import LexerConfig
from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._state_machine import (
    StateMachineLexer,
    scan_triple_string,
)

__all__ = ["PythonStateMachineLexer"]


# =============================================================================
# Keyword and builtin lookup tables (frozen for thread safety)
# =============================================================================

_KEYWORDS: frozenset[str] = frozenset(
    {
        "False",
        "None",
        "True",
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield",
        # Python 3.10+
        "match",
        "case",
        # Python 3.12+
        "type",
    }
)

_KEYWORD_CONSTANTS: frozenset[str] = frozenset({"True", "False", "None"})
_KEYWORD_DECLARATIONS: frozenset[str] = frozenset({"def", "class", "lambda"})
_KEYWORD_NAMESPACE: frozenset[str] = frozenset({"import", "from"})

_BUILTINS: frozenset[str] = frozenset(
    {
        "abs",
        "aiter",
        "all",
        "anext",
        "any",
        "ascii",
        "bin",
        "bool",
        "breakpoint",
        "bytearray",
        "bytes",
        "callable",
        "chr",
        "classmethod",
        "compile",
        "complex",
        "delattr",
        "dict",
        "dir",
        "divmod",
        "enumerate",
        "eval",
        "exec",
        "filter",
        "float",
        "format",
        "frozenset",
        "getattr",
        "globals",
        "hasattr",
        "hash",
        "help",
        "hex",
        "id",
        "input",
        "int",
        "isinstance",
        "issubclass",
        "iter",
        "len",
        "list",
        "locals",
        "map",
        "max",
        "memoryview",
        "min",
        "next",
        "object",
        "oct",
        "open",
        "ord",
        "pow",
        "print",
        "property",
        "range",
        "repr",
        "reversed",
        "round",
        "set",
        "setattr",
        "slice",
        "sorted",
        "staticmethod",
        "str",
        "sum",
        "super",
        "tuple",
        "type",
        "vars",
        "zip",
        "__import__",
    }
)

_PSEUDO_BUILTINS: frozenset[str] = frozenset(
    {
        "self",
        "cls",
        "__name__",
        "__doc__",
        "__package__",
        "__loader__",
        "__spec__",
        "__path__",
        "__file__",
        "__cached__",
        "__builtins__",
    }
)

_EXCEPTIONS: frozenset[str] = frozenset(
    {
        "ArithmeticError",
        "AssertionError",
        "AttributeError",
        "BaseException",
        "BaseExceptionGroup",
        "BlockingIOError",
        "BrokenPipeError",
        "BufferError",
        "BytesWarning",
        "ChildProcessError",
        "ConnectionAbortedError",
        "ConnectionError",
        "ConnectionRefusedError",
        "ConnectionResetError",
        "DeprecationWarning",
        "EOFError",
        "EnvironmentError",
        "Exception",
        "ExceptionGroup",
        "FileExistsError",
        "FileNotFoundError",
        "FloatingPointError",
        "FutureWarning",
        "GeneratorExit",
        "IOError",
        "ImportError",
        "ImportWarning",
        "IndentationError",
        "IndexError",
        "InterruptedError",
        "IsADirectoryError",
        "KeyError",
        "KeyboardInterrupt",
        "LookupError",
        "MemoryError",
        "ModuleNotFoundError",
        "NameError",
        "NotADirectoryError",
        "NotImplemented",
        "NotImplementedError",
        "OSError",
        "OverflowError",
        "PendingDeprecationWarning",
        "PermissionError",
        "ProcessLookupError",
        "RecursionError",
        "ReferenceError",
        "ResourceWarning",
        "RuntimeError",
        "RuntimeWarning",
        "StopAsyncIteration",
        "StopIteration",
        "SyntaxError",
        "SyntaxWarning",
        "SystemError",
        "SystemExit",
        "TabError",
        "TimeoutError",
        "TypeError",
        "UnboundLocalError",
        "UnicodeDecodeError",
        "UnicodeEncodeError",
        "UnicodeError",
        "UnicodeTranslateError",
        "UnicodeWarning",
        "UserWarning",
        "ValueError",
        "Warning",
        "ZeroDivisionError",
    }
)

# String prefix characters
_STRING_PREFIXES: frozenset[str] = frozenset("fFrRbBuU")

# Two-character operators
_TWO_CHAR_OPS: frozenset[str] = frozenset(
    {
        ":=",
        "->",
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
    }
)

# Three-character operators
_THREE_CHAR_OPS: frozenset[str] = frozenset({"**=", "//=", ">>=", "<<="})


class PythonStateMachineLexer(StateMachineLexer):
    """Hand-written Python 3 lexer.

    O(n) guaranteed, zero regex, thread-safe.
    Handles all Python 3.x syntax including f-strings, type hints, walrus operator.
    """

    name = "python"
    aliases = ("py", "python3", "py3")
    filenames = ("*.py", "*.pyw", "*.pyi")
    mimetypes = ("text/x-python", "application/x-python")

    def tokenize(
        self,
        code: str,
        config: LexerConfig | None = None,
        *,
        start: int = 0,
        end: int | None = None,
    ) -> Iterator[Token]:
        """Tokenize Python source code.

        Single-pass, character-by-character. O(n) guaranteed.
        """
        pos = start
        length = end if end is not None else len(code)
        line = 1
        line_start = start

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

            # -----------------------------------------------------------------
            # Whitespace
            # -----------------------------------------------------------------
            if char in self.WHITESPACE:
                start = pos
                start_line = line
                while pos < length and code[pos] in self.WHITESPACE:
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.WHITESPACE, code[start:pos], start_line, col)
                continue

            # -----------------------------------------------------------------
            # Comments
            # -----------------------------------------------------------------
            if char == "#":
                start = pos
                while pos < length and code[pos] != "\n":
                    pos += 1
                yield Token(TokenType.COMMENT_SINGLE, code[start:pos], line, col)
                continue

            # -----------------------------------------------------------------
            # String literals (including prefixed)
            # -----------------------------------------------------------------
            if char in "\"'":
                # Direct string (no prefix)
                start = pos
                start_line = line
                token_type, pos, newlines = self._scan_string_literal(code, pos)

                if newlines:
                    line += newlines
                    value = code[start:pos]
                    line_start = start + value.rfind("\n") + 1

                yield Token(token_type, code[start:pos], start_line, col)
                continue

            if char in _STRING_PREFIXES:
                # Check if this is actually a string prefix (followed by quote)
                # Look ahead past any additional prefix chars to find a quote
                lookahead = pos + 1
                while lookahead < length and code[lookahead] in _STRING_PREFIXES:
                    lookahead += 1
                if lookahead < length and code[lookahead] in "\"'":
                    # It's a prefixed string
                    start = pos
                    start_line = line
                    token_type, pos, newlines = self._scan_string_literal(code, pos)

                    if newlines:
                        line += newlines
                        value = code[start:pos]
                        line_start = start + value.rfind("\n") + 1

                    yield Token(token_type, code[start:pos], start_line, col)
                    continue
                # Otherwise, fall through to identifier handling

            # -----------------------------------------------------------------
            # Numbers
            # -----------------------------------------------------------------
            if char in self.DIGITS or (
                char == "." and pos + 1 < length and code[pos + 1] in self.DIGITS
            ):
                start = pos
                token_type, pos = self._scan_number(code, pos)
                yield Token(token_type, code[start:pos], line, col)
                continue

            # -----------------------------------------------------------------
            # Identifiers, keywords, builtins
            # Python 3 allows Unicode identifiers (PEP 3131)
            # -----------------------------------------------------------------
            if char in self.IDENT_START or char.isidentifier():
                start = pos
                pos += 1
                # Scan identifier: ASCII fast path, then Unicode fallback
                while pos < length:
                    next_char = code[pos]
                    if next_char in self.IDENT_CONT:
                        # Fast path: ASCII continuation character
                        pos += 1
                    elif next_char.isidentifier() or next_char.isdigit():
                        # Unicode identifier or digit continuation
                        pos += 1
                    else:
                        break
                word = code[start:pos]
                token_type = self._classify_word(word)
                yield Token(token_type, word, line, col)
                continue

            # -----------------------------------------------------------------
            # Decorators
            # -----------------------------------------------------------------
            if char == "@":
                start = pos
                pos += 1
                if pos < length:
                    next_char = code[pos]
                    if next_char in self.IDENT_START or next_char.isidentifier():
                        pos += 1
                        # Scan identifier: ASCII fast path, then Unicode fallback
                        while pos < length:
                            char_at_pos = code[pos]
                            if (
                                char_at_pos in self.IDENT_CONT
                                or char_at_pos.isidentifier()
                                or char_at_pos.isdigit()
                            ):
                                pos += 1
                            else:
                                break
                        # Handle dotted decorators
                        while pos < length and code[pos] == ".":
                            pos += 1
                            if pos < length:
                                char_at_pos = code[pos]
                                if char_at_pos in self.IDENT_CONT or char_at_pos.isidentifier():
                                    pos += 1
                                    while pos < length:
                                        cont_char = code[pos]
                                        if (
                                            cont_char in self.IDENT_CONT
                                            or cont_char.isidentifier()
                                            or cont_char.isdigit()
                                        ):
                                            pos += 1
                                        else:
                                            break
                yield Token(TokenType.NAME_DECORATOR, code[start:pos], line, col)
                continue

            # -----------------------------------------------------------------
            # Multi-character operators (check 3-char first, then 2-char)
            # -----------------------------------------------------------------
            if pos + 2 < length:
                three_char = code[pos : pos + 3]
                if three_char in _THREE_CHAR_OPS:
                    yield Token(TokenType.OPERATOR, three_char, line, col)
                    pos += 3
                    continue

            if pos + 1 < length:
                two_char = code[pos : pos + 2]
                if two_char in _TWO_CHAR_OPS:
                    yield Token(TokenType.OPERATOR, two_char, line, col)
                    pos += 2
                    continue

            # -----------------------------------------------------------------
            # Single-character operators
            # -----------------------------------------------------------------
            if char in "+-*/%@&|^~<>=!":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                continue

            # -----------------------------------------------------------------
            # Punctuation
            # -----------------------------------------------------------------
            if char in "()[]{}:;.,\\":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            # -----------------------------------------------------------------
            # Unknown character — emit as error and continue
            # -----------------------------------------------------------------
            yield Token(TokenType.ERROR, char, line, col)
            pos += 1

    def _scan_string_literal(
        self,
        code: str,
        pos: int,
    ) -> tuple[TokenType, int, int]:
        """Scan a string literal with optional prefix.

        Returns (token_type, end_position, newline_count).
        """
        length = len(code)

        # Handle string prefixes (f, r, b, u, combinations like fr, rf, br, etc.)
        while pos < length and code[pos] in _STRING_PREFIXES:
            pos += 1

        if pos >= length or code[pos] not in "\"'":
            # Not actually a string (shouldn't happen if called correctly)
            return TokenType.ERROR, pos, 0

        quote = code[pos]
        pos += 1

        # Check for triple quote
        if pos + 1 < length and code[pos : pos + 2] == quote * 2:
            pos += 2  # Skip the other two quotes
            start_pos = pos
            pos = scan_triple_string(code, pos, quote)
            # Count newlines in the string
            newlines = code[start_pos:pos].count("\n")
            return TokenType.STRING_DOC, pos, newlines

        # Single-quoted string
        newlines = 0
        while pos < length:
            char = code[pos]

            if char == quote:
                return TokenType.STRING, pos + 1, newlines

            if char == "\\" and pos + 1 < length:
                # Skip escape sequence
                if code[pos + 1] == "\n":
                    newlines += 1
                pos += 2
                continue

            if char == "\n":
                # Unterminated string (newline in single-quoted string)
                return TokenType.STRING, pos, newlines

            pos += 1

        # End of input (unterminated)
        return TokenType.STRING, pos, newlines

    def _scan_number(self, code: str, pos: int) -> tuple[TokenType, int]:
        """Scan a numeric literal.

        Returns (token_type, end_position).
        """
        length = len(code)

        # Leading dot (e.g., .5)
        if code[pos] == ".":
            pos += 1
            pos = self._scan_digits_with_underscore(code, pos)
            pos = self._scan_exponent(code, pos)
            return TokenType.NUMBER_FLOAT, pos

        # 0x, 0o, 0b prefixes
        if code[pos] == "0" and pos + 1 < length:
            next_char = code[pos + 1]

            if next_char in "xX":
                pos += 2
                pos = self._scan_hex_digits(code, pos)
                return TokenType.NUMBER_HEX, pos

            if next_char in "oO":
                pos += 2
                pos = self._scan_octal_digits(code, pos)
                return TokenType.NUMBER_OCT, pos

            if next_char in "bB":
                pos += 2
                pos = self._scan_binary_digits(code, pos)
                return TokenType.NUMBER_BIN, pos

        # Decimal integer or float
        pos = self._scan_digits_with_underscore(code, pos)

        # Decimal point
        if pos < length and code[pos] == ".":
            # Check it's not a method call like 1.real
            if pos + 1 < length and code[pos + 1] in self.IDENT_START:
                return TokenType.NUMBER_INTEGER, pos
            pos += 1
            pos = self._scan_digits_with_underscore(code, pos)
            pos = self._scan_exponent(code, pos)
            return TokenType.NUMBER_FLOAT, pos

        # Exponent without decimal point (e.g., 1e10)
        if pos < length and code[pos] in "eE":
            pos = self._scan_exponent(code, pos)
            return TokenType.NUMBER_FLOAT, pos

        # Complex number suffix
        if pos < length and code[pos] in "jJ":
            pos += 1
            return TokenType.NUMBER_FLOAT, pos

        return TokenType.NUMBER_INTEGER, pos

    def _scan_digits_with_underscore(self, code: str, pos: int) -> int:
        """Scan digits with optional underscores."""
        length = len(code)
        while pos < length and (code[pos] in self.DIGITS or code[pos] == "_"):
            pos += 1
        return pos

    def _scan_hex_digits(self, code: str, pos: int) -> int:
        """Scan hex digits with optional underscores."""
        length = len(code)
        while pos < length and (code[pos] in self.HEX_DIGITS or code[pos] == "_"):
            pos += 1
        return pos

    def _scan_octal_digits(self, code: str, pos: int) -> int:
        """Scan octal digits with optional underscores."""
        length = len(code)
        while pos < length and (code[pos] in self.OCTAL_DIGITS or code[pos] == "_"):
            pos += 1
        return pos

    def _scan_binary_digits(self, code: str, pos: int) -> int:
        """Scan binary digits with optional underscores."""
        length = len(code)
        while pos < length and (code[pos] in self.BINARY_DIGITS or code[pos] == "_"):
            pos += 1
        return pos

    def _scan_exponent(self, code: str, pos: int) -> int:
        """Scan optional exponent part of number."""
        length = len(code)

        if pos >= length or code[pos] not in "eE":
            return pos

        pos += 1

        if pos < length and code[pos] in "+-":
            pos += 1

        return self._scan_digits_with_underscore(code, pos)

    def _classify_word(self, word: str) -> TokenType:
        """Classify an identifier into the appropriate token type."""
        if word in _KEYWORDS:
            if word in _KEYWORD_CONSTANTS:
                return TokenType.KEYWORD_CONSTANT
            if word in _KEYWORD_DECLARATIONS:
                return TokenType.KEYWORD_DECLARATION
            if word in _KEYWORD_NAMESPACE:
                return TokenType.KEYWORD_NAMESPACE
            return TokenType.KEYWORD

        if word in _BUILTINS:
            return TokenType.NAME_BUILTIN

        if word in _PSEUDO_BUILTINS:
            return TokenType.NAME_BUILTIN_PSEUDO

        if word in _EXCEPTIONS:
            return TokenType.NAME_EXCEPTION

        return TokenType.NAME
