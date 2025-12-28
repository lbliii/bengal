"""Hand-written Lua lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    DIGITS,
    HEX_DIGITS,
    scan_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["LuaStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "and",
        "break",
        "do",
        "else",
        "elseif",
        "end",
        "for",
        "function",
        "goto",
        "if",
        "in",
        "local",
        "not",
        "or",
        "repeat",
        "return",
        "then",
        "until",
        "while",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"true", "false", "nil"})

_BUILTINS: frozenset[str] = frozenset(
    {
        "assert",
        "collectgarbage",
        "dofile",
        "error",
        "getfenv",
        "getmetatable",
        "ipairs",
        "load",
        "loadfile",
        "loadstring",
        "module",
        "next",
        "pairs",
        "pcall",
        "print",
        "rawequal",
        "rawget",
        "rawlen",
        "rawset",
        "require",
        "select",
        "setfenv",
        "setmetatable",
        "tonumber",
        "tostring",
        "type",
        "unpack",
        "xpcall",
        "_G",
        "_VERSION",
    }
)


class LuaStateMachineLexer(StateMachineLexer):
    """Lua lexer with -- and --[[ ]] comments."""

    name = "lua"
    aliases = ()
    filenames = ("*.lua", "*.wlua")
    mimetypes = ("text/x-lua", "application/x-lua")

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = start

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

            # Comments -- or --[[ ]]
            if char == "-" and pos + 1 < length and code[pos + 1] == "-":
                start = pos
                pos += 2
                # Check for long comment --[[ or --[=[ etc.
                if pos < length and code[pos] == "[":
                    equals = 0
                    temp = pos + 1
                    while temp < length and code[temp] == "=":
                        equals += 1
                        temp += 1
                    if temp < length and code[temp] == "[":
                        # Long comment
                        pos = temp + 1
                        end_bracket = "]" + "=" * equals + "]"
                        start_line = line
                        while pos < length:
                            if code[pos : pos + len(end_bracket)] == end_bracket:
                                pos += len(end_bracket)
                                break
                            if code[pos] == "\n":
                                line += 1
                                line_start = pos + 1
                            pos += 1
                        yield Token(TokenType.COMMENT_MULTILINE, code[start:pos], start_line, col)
                        continue
                # Short comment
                while pos < length and code[pos] != "\n":
                    pos += 1
                yield Token(TokenType.COMMENT_SINGLE, code[start:pos], line, col)
                continue

            # Long strings [[ ]] or [=[ ]=]
            if char == "[":
                equals = 0
                temp = pos + 1
                while temp < length and code[temp] == "=":
                    equals += 1
                    temp += 1
                if temp < length and code[temp] == "[":
                    start = pos
                    pos = temp + 1
                    end_bracket = "]" + "=" * equals + "]"
                    start_line = line
                    while pos < length:
                        if code[pos : pos + len(end_bracket)] == end_bracket:
                            pos += len(end_bracket)
                            break
                        if code[pos] == "\n":
                            line += 1
                            line_start = pos + 1
                        pos += 1
                    yield Token(TokenType.STRING, code[start:pos], start_line, col)
                    continue

            # Regular strings
            if char in "\"'":
                start = pos
                quote = char
                pos += 1
                pos, _ = scan_string(code, pos, quote)
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Numbers
            if char in DIGITS or (char == "." and pos + 1 < length and code[pos + 1] in DIGITS):
                start = pos
                if char == "0" and pos + 1 < length and code[pos + 1] in "xX":
                    pos += 2
                    while pos < length and (code[pos] in HEX_DIGITS or code[pos] == "."):
                        pos += 1
                    if pos < length and code[pos] in "pP":
                        pos += 1
                        if pos < length and code[pos] in "+-":
                            pos += 1
                        while pos < length and code[pos] in DIGITS:
                            pos += 1
                    yield Token(TokenType.NUMBER_HEX, code[start:pos], line, col)
                    continue

                if char == ".":
                    pos += 1
                while pos < length and code[pos] in DIGITS:
                    pos += 1
                if pos < length and code[pos] == ".":
                    pos += 1
                    while pos < length and code[pos] in DIGITS:
                        pos += 1
                if pos < length and code[pos] in "eE":
                    pos += 1
                    if pos < length and code[pos] in "+-":
                        pos += 1
                    while pos < length and code[pos] in DIGITS:
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
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                word = code[start:pos]
                if word in _CONSTANTS:
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif word in ("function", "local"):
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word in _KEYWORDS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif word in _BUILTINS:
                    yield Token(TokenType.NAME_BUILTIN, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Operators
            if char == "." and pos + 2 < length and code[pos : pos + 3] == "...":
                yield Token(TokenType.OPERATOR, "...", line, col)
                pos += 3
                continue
            if char == "." and pos + 1 < length and code[pos + 1] == ".":
                yield Token(TokenType.OPERATOR, "..", line, col)
                pos += 2
                continue

            if char in "=<>~":
                start = pos
                if pos + 1 < length and code[pos + 1] == "=":
                    pos += 2
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            if char in "+-*/%^#":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                continue

            # Punctuation
            if char in "()[]{}.,;:":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.ERROR, char, line, col)
            pos += 1
