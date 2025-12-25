"""Hand-written INI/Config lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import DIGITS, scan_string
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["IniStateMachineLexer"]


_BOOL_VALUES: frozenset[str] = frozenset(
    {
        "true",
        "false",
        "yes",
        "no",
        "on",
        "off",
        "True",
        "False",
        "Yes",
        "No",
        "On",
        "Off",
        "TRUE",
        "FALSE",
        "YES",
        "NO",
        "ON",
        "OFF",
    }
)


class IniStateMachineLexer(StateMachineLexer):
    """INI/Config file lexer."""

    name = "ini"
    aliases = ("cfg", "dosini", "config")
    filenames = ("*.ini", "*.cfg", "*.conf", ".editorconfig", ".gitconfig")
    mimetypes = ("text/x-ini",)

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = 0
        at_line_start = True

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
                at_line_start = True
                continue

            # Comments (# or ;)
            if char in "#;":
                start = pos
                while pos < length and code[pos] != "\n":
                    pos += 1
                yield Token(TokenType.COMMENT_SINGLE, code[start:pos], line, col)
                at_line_start = False
                continue

            # Section headers [section]
            if at_line_start and char == "[":
                start = pos
                pos += 1
                while pos < length and code[pos] != "]" and code[pos] != "\n":
                    pos += 1
                if pos < length and code[pos] == "]":
                    pos += 1
                yield Token(TokenType.NAME_TAG, code[start:pos], line, col)
                at_line_start = False
                continue

            # Keys (at line start, before =)
            if at_line_start and (char.isalpha() or char in "_-"):
                start = pos
                while pos < length and code[pos] not in "=:\n#;":
                    pos += 1
                word = code[start:pos].rstrip()
                yield Token(TokenType.NAME_ATTRIBUTE, word, line, col)
                pos = start + len(word)
                at_line_start = False
                continue

            # Assignment operators
            if char in "=:":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                at_line_start = False
                continue

            # Quoted strings
            if char in "\"'":
                start = pos
                quote = char
                pos += 1
                pos, _ = scan_string(code, pos, quote)
                yield Token(TokenType.STRING, code[start:pos], line, col)
                at_line_start = False
                continue

            # Numbers
            if char in DIGITS or (char == "-" and pos + 1 < length and code[pos + 1] in DIGITS):
                start = pos
                if char == "-":
                    pos += 1
                while pos < length and code[pos] in DIGITS:
                    pos += 1
                if pos < length and code[pos] == ".":
                    pos += 1
                    while pos < length and code[pos] in DIGITS:
                        pos += 1
                yield Token(
                    TokenType.NUMBER_INTEGER
                    if "." not in code[start:pos]
                    else TokenType.NUMBER_FLOAT,
                    code[start:pos],
                    line,
                    col,
                )
                at_line_start = False
                continue

            # Boolean values and other identifiers
            if char.isalpha() or char in "_-":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] in "_-"):
                    pos += 1
                word = code[start:pos]
                if word in _BOOL_VALUES:
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                else:
                    yield Token(TokenType.STRING, word, line, col)
                at_line_start = False
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
            at_line_start = False
