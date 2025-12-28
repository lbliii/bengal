"""Hand-written Nim lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    BINARY_DIGITS,
    DIGITS,
    HEX_DIGITS,
    OCTAL_DIGITS,
    HashCommentsMixin,
    scan_string,
    scan_triple_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["NimStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "addr",
        "and",
        "as",
        "asm",
        "bind",
        "block",
        "break",
        "case",
        "cast",
        "concept",
        "const",
        "continue",
        "converter",
        "defer",
        "discard",
        "distinct",
        "div",
        "do",
        "elif",
        "else",
        "end",
        "enum",
        "except",
        "export",
        "finally",
        "for",
        "from",
        "func",
        "if",
        "import",
        "in",
        "include",
        "interface",
        "is",
        "isnot",
        "iterator",
        "let",
        "macro",
        "method",
        "mixin",
        "mod",
        "nil",
        "not",
        "notin",
        "object",
        "of",
        "or",
        "out",
        "proc",
        "ptr",
        "raise",
        "ref",
        "return",
        "shl",
        "shr",
        "static",
        "template",
        "try",
        "tuple",
        "type",
        "using",
        "var",
        "when",
        "while",
        "xor",
        "yield",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "int",
        "int8",
        "int16",
        "int32",
        "int64",
        "uint",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "float",
        "float32",
        "float64",
        "bool",
        "char",
        "string",
        "cstring",
        "pointer",
        "typedesc",
        "void",
        "auto",
        "any",
        "untyped",
        "typed",
        "range",
        "array",
        "openArray",
        "seq",
        "set",
        "ptr",
        "ref",
        "Table",
        "OrderedTable",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "echo",
        "assert",
        "doAssert",
        "quit",
        "repr",
        "len",
        "low",
        "high",
        "sizeof",
        "succ",
        "pred",
        "inc",
        "dec",
        "abs",
        "min",
        "max",
        "add",
        "del",
        "pop",
        "insert",
        "contains",
        "find",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"true", "false", "nil"})


class NimStateMachineLexer(
    HashCommentsMixin,
    StateMachineLexer,
):
    """Nim lexer."""

    name = "nim"
    aliases = ("nimrod",)
    filenames = ("*.nim", "*.nims", "*.nimble")
    mimetypes = ("text/x-nim",)

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
        line_start = starttart

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

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

            # Block comments #[ ... ]# (nestable)
            if char == "#" and pos + 1 < length and code[pos + 1] == "[":
                start = pos
                pos += 2
                depth = 1
                start_line = line
                while pos < length and depth > 0:
                    if code[pos : pos + 2] == "#[":
                        depth += 1
                        pos += 2
                        continue
                    if code[pos : pos + 2] == "]#":
                        depth -= 1
                        pos += 2
                        continue
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.COMMENT_MULTILINE, code[start:pos], start_line, col)
                continue

            # Doc comments ##
            if char == "#" and pos + 1 < length and code[pos + 1] == "#":
                start = pos
                while pos < length and code[pos] != "\n":
                    pos += 1
                yield Token(TokenType.COMMENT_DOC, code[start:pos], line, col)
                continue

            # Line comments
            token, new_pos = self._try_hash_comment(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Pragmas {. ... .}
            if char == "{" and pos + 1 < length and code[pos + 1] == ".":
                start = pos
                pos += 2
                while pos < length:
                    if code[pos : pos + 2] == ".}":
                        pos += 2
                        break
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.COMMENT_PREPROC, code[start:pos], line, col)
                continue

            # Triple-quoted strings
            if char == '"' and pos + 2 < length and code[pos : pos + 3] == '"""':
                start = pos
                pos += 3
                pos, newlines = scan_triple_string(code, pos, '"')
                yield Token(TokenType.STRING, code[start:pos], line, col)
                if newlines:
                    line += newlines
                    line_start = start + code[start:pos].rfind("\n") + 1
                continue

            # Raw strings r"..."
            if char == "r" and pos + 1 < length and code[pos + 1] == '"':
                start = pos
                pos += 2
                while pos < length and code[pos] != '"':
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Regular strings
            if char == '"':
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, '"')
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Character literals
            if char == "'":
                start = pos
                pos += 1
                if pos < length and code[pos] == "\\":
                    pos += 2
                elif pos < length:
                    pos += 1
                if pos < length and code[pos] == "'":
                    pos += 1
                yield Token(TokenType.STRING_CHAR, code[start:pos], line, col)
                continue

            # Numbers
            if char in DIGITS:
                start = pos
                if code[pos] == "0" and pos + 1 < length:
                    next_char = code[pos + 1]
                    if next_char in "xX":
                        pos += 2
                        while pos < length and (code[pos] in HEX_DIGITS or code[pos] == "_"):
                            pos += 1
                        yield Token(TokenType.NUMBER_HEX, code[start:pos], line, col)
                        continue
                    if next_char in "oO":
                        pos += 2
                        while pos < length and (code[pos] in OCTAL_DIGITS or code[pos] == "_"):
                            pos += 1
                        yield Token(TokenType.NUMBER_OCT, code[start:pos], line, col)
                        continue
                    if next_char in "bB":
                        pos += 2
                        while pos < length and (code[pos] in BINARY_DIGITS or code[pos] == "_"):
                            pos += 1
                        yield Token(TokenType.NUMBER_BIN, code[start:pos], line, col)
                        continue

                while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                    pos += 1
                if pos < length and code[pos] == ".":
                    if pos + 1 < length and code[pos + 1] in DIGITS:
                        pos += 1
                        while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                            pos += 1
                if pos < length and code[pos] in "eE":
                    pos += 1
                    if pos < length and code[pos] in "+-":
                        pos += 1
                    while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                        pos += 1
                # Type suffixes
                if pos < length and code[pos] == "'":
                    pos += 1
                    while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                        pos += 1
                value = code[start:pos]
                token_type = (
                    TokenType.NUMBER_FLOAT
                    if "." in value or "e" in value.lower()
                    else TokenType.NUMBER_INTEGER
                )
                yield Token(token_type, value, line, col)
                continue

            # Keywords and identifiers (Nim is case-insensitive for keywords)
            if char.isalpha() or char == "_":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                word = code[start:pos]
                word_lower = word.lower().replace("_", "")
                if word_lower in _CONSTANTS or word in _CONSTANTS:
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif word_lower in (
                    "proc",
                    "func",
                    "method",
                    "iterator",
                    "macro",
                    "template",
                    "converter",
                    "type",
                    "enum",
                    "object",
                    "tuple",
                ):
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word_lower in ("import", "export", "include", "from"):
                    yield Token(TokenType.KEYWORD_NAMESPACE, word, line, col)
                elif word_lower in _KEYWORDS or word in _KEYWORDS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif word in _TYPES:
                    yield Token(TokenType.KEYWORD_TYPE, word, line, col)
                elif word in _BUILTINS:
                    yield Token(TokenType.NAME_BUILTIN, word, line, col)
                elif word and word[0].isupper():
                    yield Token(TokenType.NAME_CLASS, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Operators
            if char in "=<>!&|+-*/%^@$~`:":
                start = pos
                if pos + 1 < length and code[pos : pos + 2] in (
                    "==",
                    "!=",
                    "<=",
                    ">=",
                    "&&",
                    "||",
                    "+=",
                    "-=",
                    "*=",
                    "/=",
                    "->",
                    "=>",
                    "..",
                ):
                    pos += 2
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            # Punctuation
            if char in "()[]{},.;":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
