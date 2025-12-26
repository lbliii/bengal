"""Hand-written Elixir lexer using state machine approach.

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

__all__ = ["ElixirStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "after",
        "and",
        "case",
        "catch",
        "cond",
        "do",
        "else",
        "end",
        "fn",
        "for",
        "if",
        "in",
        "not",
        "or",
        "raise",
        "receive",
        "rescue",
        "try",
        "unless",
        "when",
        "with",
    }
)

_DECLARATIONS: frozenset[str] = frozenset(
    {
        "def",
        "defp",
        "defmacro",
        "defmacrop",
        "defmodule",
        "defprotocol",
        "defimpl",
        "defstruct",
        "defexception",
        "defdelegate",
        "defguard",
        "defguardp",
        "defoverridable",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "alias",
        "import",
        "require",
        "use",
        "is_atom",
        "is_binary",
        "is_bitstring",
        "is_boolean",
        "is_float",
        "is_function",
        "is_integer",
        "is_list",
        "is_map",
        "is_nil",
        "is_number",
        "is_pid",
        "is_port",
        "is_reference",
        "is_tuple",
        "abs",
        "binary_part",
        "bit_size",
        "byte_size",
        "div",
        "elem",
        "hd",
        "length",
        "map_size",
        "max",
        "min",
        "node",
        "rem",
        "round",
        "self",
        "tl",
        "trunc",
        "tuple_size",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"true", "false", "nil"})


class ElixirStateMachineLexer(
    HashCommentsMixin,
    StateMachineLexer,
):
    """Elixir lexer."""

    name = "elixir"
    aliases = ("ex", "exs")
    filenames = ("*.ex", "*.exs")
    mimetypes = ("text/x-elixir",)

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = 0

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

            # Comments
            token, new_pos = self._try_hash_comment(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Attributes @name
            if char == "@":
                start = pos
                pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] in "_?!"):
                    pos += 1
                yield Token(TokenType.NAME_DECORATOR, code[start:pos], line, col)
                continue

            # Atoms :name or :"name"
            if char == ":":
                if pos + 1 < length:
                    next_char = code[pos + 1]
                    if next_char == '"':
                        start = pos
                        pos += 2
                        pos, _ = scan_string(code, pos, '"')
                        yield Token(TokenType.STRING_SYMBOL, code[start:pos], line, col)
                        continue
                    if next_char.isalpha() or next_char == "_":
                        start = pos
                        pos += 1
                        while pos < length and (code[pos].isalnum() or code[pos] in "_?!@"):
                            pos += 1
                        yield Token(TokenType.STRING_SYMBOL, code[start:pos], line, col)
                        continue
                yield Token(TokenType.PUNCTUATION, ":", line, col)
                pos += 1
                continue

            # Sigils ~r/.../ ~s"..." etc.
            if char == "~" and pos + 1 < length and code[pos + 1].isalpha():
                start = pos
                pos += 2
                sigil_type = code[pos - 1]
                if pos < length:
                    delim = code[pos]
                    close_delim = {"(": ")", "[": "]", "{": "}", "<": ">"}.get(delim, delim)
                    pos += 1
                    while pos < length and code[pos] != close_delim:
                        if code[pos] == "\\" and pos + 1 < length:
                            pos += 2
                            continue
                        if code[pos] == "\n":
                            line += 1
                            line_start = pos + 1
                        pos += 1
                    if pos < length:
                        pos += 1
                    # Modifiers
                    while pos < length and code[pos].isalpha():
                        pos += 1
                token_type = TokenType.STRING_REGEX if sigil_type in "rR" else TokenType.STRING
                yield Token(token_type, code[start:pos], line, col)
                continue

            # Heredocs """...""" or '''...'''
            if char == '"' and pos + 2 < length and code[pos : pos + 3] == '"""':
                start = pos
                pos += 3
                pos, newlines = scan_triple_string(code, pos, '"')
                yield Token(TokenType.STRING_DOC, code[start:pos], line, col)
                if newlines:
                    line += newlines
                    line_start = start + code[start:pos].rfind("\n") + 1
                continue

            if char == "'" and pos + 2 < length and code[pos : pos + 3] == "'''":
                start = pos
                pos += 3
                while pos < length:
                    if code[pos : pos + 3] == "'''":
                        pos += 3
                        break
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
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

            # Charlists
            if char == "'":
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, "'")
                yield Token(TokenType.STRING, code[start:pos], line, col)
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
                value = code[start:pos]
                token_type = (
                    TokenType.NUMBER_FLOAT
                    if "." in value or "e" in value.lower()
                    else TokenType.NUMBER_INTEGER
                )
                yield Token(token_type, value, line, col)
                continue

            # Keywords and identifiers
            if char.isalpha() or char == "_":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] in "_?!"):
                    pos += 1
                word = code[start:pos]
                if word in _CONSTANTS:
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif word in _DECLARATIONS:
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word in _BUILTINS:
                    yield Token(TokenType.NAME_BUILTIN, word, line, col)
                elif word in _KEYWORDS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif word and word[0].isupper():
                    yield Token(TokenType.NAME_CLASS, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Operators
            if char in "=<>!&|+-*/%^~":
                start = pos
                if pos + 2 < length and code[pos : pos + 3] in (
                    "===",
                    "!==",
                    "|||",
                    "&&&",
                    "<<<",
                    ">>>",
                    "~>>",
                    "<<~",
                    "|>",
                    "<>",
                    "++",
                    "--",
                    "..",
                ):
                    pos += (
                        3
                        if code[pos : pos + 3]
                        in ("===", "!==", "|||", "&&&", "<<<", ">>>", "~>>", "<<~")
                        else 2
                    )
                elif pos + 1 < length and code[pos : pos + 2] in (
                    "==",
                    "!=",
                    "<=",
                    ">=",
                    "&&",
                    "||",
                    "++",
                    "--",
                    "<>",
                    "|>",
                    "->",
                    "<-",
                    "=>",
                    "::",
                    "..",
                    "~~",
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
