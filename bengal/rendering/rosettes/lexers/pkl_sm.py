"""Hand-written Pkl lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
Pkl is Apple's configuration language.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    DIGITS,
    CStyleCommentsMixin,
    scan_triple_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["PklStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "abstract",
        "amends",
        "as",
        "class",
        "else",
        "extends",
        "external",
        "false",
        "for",
        "function",
        "hidden",
        "if",
        "import",
        "in",
        "is",
        "let",
        "local",
        "module",
        "new",
        "null",
        "open",
        "out",
        "outer",
        "read",
        "super",
        "this",
        "throw",
        "trace",
        "true",
        "typealias",
        "when",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "Any",
        "Boolean",
        "Duration",
        "Dynamic",
        "Float",
        "Int",
        "Int8",
        "Int16",
        "Int32",
        "UInt",
        "UInt8",
        "UInt16",
        "UInt32",
        "Listing",
        "Mapping",
        "Number",
        "Pair",
        "String",
        "Collection",
        "List",
        "Map",
        "Set",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "Regex",
        "Null",
        "Class",
        "Type",
        "Module",
        "Function",
        "IntSeq",
        "base",
        "output",
        "read",
        "import",
    }
)


class PklStateMachineLexer(
    CStyleCommentsMixin,
    StateMachineLexer,
):
    """Pkl lexer."""

    name = "pkl"
    aliases = ()
    filenames = ("*.pkl",)
    mimetypes = ("text/x-pkl",)

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

            # Comments
            token, new_pos = self._try_comment(code, pos, line, col)
            if token:
                if token.type == TokenType.COMMENT_MULTILINE:
                    newlines = token.value.count("\n")
                    if newlines:
                        line += newlines
                        line_start = pos + token.value.rfind("\n") + 1
                yield token
                pos = new_pos
                continue

            # Annotations @name
            if char == "@":
                start = pos
                pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                yield Token(TokenType.NAME_DECORATOR, code[start:pos], line, col)
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

            # Strings with interpolation
            if char == '"':
                start = pos
                pos += 1
                while pos < length and code[pos] != '"':
                    if code[pos] == "\\" and pos + 1 < length:
                        pos += 2
                        continue
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Numbers
            if char in DIGITS or (char == "-" and pos + 1 < length and code[pos + 1] in DIGITS):
                start = pos
                if char == "-":
                    pos += 1
                while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                    pos += 1
                if pos < length and code[pos] == ".":
                    pos += 1
                    while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                        pos += 1
                if pos < length and code[pos] in "eE":
                    pos += 1
                    if pos < length and code[pos] in "+-":
                        pos += 1
                    while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                        pos += 1
                # Duration suffixes
                if pos < length and code[pos : pos + 2] in ("ns", "us", "ms"):
                    pos += 2
                elif pos < length and code[pos] in "smhd":
                    pos += 1
                # Data size suffixes
                elif pos < length and code[pos : pos + 3] in ("kib", "mib", "gib", "tib", "pib"):
                    pos += 3
                elif pos < length and code[pos : pos + 2] in (
                    "kb",
                    "mb",
                    "gb",
                    "tb",
                    "pb",
                    "Ki",
                    "Mi",
                    "Gi",
                    "Ti",
                    "Pi",
                ):
                    pos += 2
                elif pos < length and code[pos] in "bB":
                    pos += 1

                value = code[start:pos]
                token_type = TokenType.NUMBER_FLOAT if "." in value else TokenType.NUMBER_INTEGER
                yield Token(token_type, value, line, col)
                continue

            # Keywords and identifiers
            if char.isalpha() or char == "_":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                word = code[start:pos]
                if word in ("true", "false", "null"):
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif word in ("class", "module", "function", "typealias", "abstract"):
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word in ("import", "amends", "extends"):
                    yield Token(TokenType.KEYWORD_NAMESPACE, word, line, col)
                elif word in _KEYWORDS:
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
            if char in "=<>!&|+-*/%?":
                start = pos
                if pos + 2 < length and code[pos : pos + 3] in (
                    "...",
                    "?.",
                ):
                    pos += min(3, len(code) - pos)
                elif pos + 1 < length and code[pos : pos + 2] in (
                    "==",
                    "!=",
                    "<=",
                    ">=",
                    "&&",
                    "||",
                    "??",
                    "->",
                    "=>",
                    "..",
                ):
                    pos += 2
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            # Dot operators
            if char == ".":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                continue

            # Punctuation
            if char in "()[]{}:,;":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
