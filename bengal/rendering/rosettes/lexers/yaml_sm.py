"""Hand-written YAML lexer using composable scanner mixins.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    DIGITS,
    IDENT_START,
    CStyleNumbersMixin,
    HashCommentsMixin,
    scan_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["YamlStateMachineLexer"]


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

_NULL_VALUES: frozenset[str] = frozenset({"null", "Null", "NULL", "~"})


class YamlStateMachineLexer(
    HashCommentsMixin,
    CStyleNumbersMixin,
    StateMachineLexer,
):
    """YAML lexer using composable mixins."""

    name = "yaml"
    aliases = ("yml",)
    filenames = ("*.yaml", "*.yml")
    mimetypes = ("text/yaml", "application/x-yaml")

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = start
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

            # Comments
            token, new_pos = self._try_hash_comment(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                at_line_start = False
                continue

            # Document markers
            if at_line_start and pos + 2 < length:
                three = code[pos : pos + 3]
                if three == "---" or three == "...":
                    rest = code[pos + 3 : pos + 4] if pos + 3 < length else ""
                    if rest in ("", " ", "\n", "\t"):
                        yield Token(TokenType.PUNCTUATION_MARKER, three, line, col)
                        pos += 3
                        at_line_start = False
                        continue

            # Directives %YAML, %TAG
            if at_line_start and char == "%":
                start = pos
                while pos < length and code[pos] != "\n":
                    pos += 1
                yield Token(TokenType.COMMENT_PREPROC, code[start:pos], line, col)
                at_line_start = False
                continue

            # Anchors &name
            if char == "&":
                start = pos
                pos += 1
                while (
                    pos < length
                    and code[pos]
                    in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
                ):
                    pos += 1
                yield Token(TokenType.NAME_LABEL, code[start:pos], line, col)
                at_line_start = False
                continue

            # Aliases *name
            if char == "*":
                start = pos
                pos += 1
                while (
                    pos < length
                    and code[pos]
                    in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
                ):
                    pos += 1
                yield Token(TokenType.NAME_VARIABLE, code[start:pos], line, col)
                at_line_start = False
                continue

            # Tags !!type or !custom
            if char == "!":
                start = pos
                pos += 1
                if pos < length and code[pos] == "!":
                    pos += 1
                while (
                    pos < length
                    and code[pos]
                    in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
                ):
                    pos += 1
                yield Token(TokenType.NAME_TAG, code[start:pos], line, col)
                at_line_start = False
                continue

            # Block scalars | or >
            if char in "|>" and (col == 1 or (pos > 0 and code[pos - 1] in " \t:")):
                start = pos
                pos += 1
                while pos < length and code[pos] in "+-0123456789":
                    pos += 1
                yield Token(TokenType.STRING_HEREDOC, code[start:pos], line, col)
                at_line_start = False
                continue

            # Quoted strings
            if char == '"':
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, '"')
                yield Token(TokenType.STRING, code[start:pos], line, col)
                at_line_start = False
                continue

            if char == "'":
                start = pos
                pos += 1
                # YAML single quotes use '' for escaping
                while pos < length:
                    if code[pos] == "'":
                        if pos + 1 < length and code[pos + 1] == "'":
                            pos += 2
                            continue
                        pos += 1
                        break
                    pos += 1
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
                    if pos < length and code[pos] in "eE":
                        pos += 1
                        if pos < length and code[pos] in "+-":
                            pos += 1
                        while pos < length and code[pos] in DIGITS:
                            pos += 1
                    yield Token(TokenType.NUMBER_FLOAT, code[start:pos], line, col)
                elif pos < length and code[pos] in "eE":
                    pos += 1
                    if pos < length and code[pos] in "+-":
                        pos += 1
                    while pos < length and code[pos] in DIGITS:
                        pos += 1
                    yield Token(TokenType.NUMBER_FLOAT, code[start:pos], line, col)
                else:
                    yield Token(TokenType.NUMBER_INTEGER, code[start:pos], line, col)
                at_line_start = False
                continue

            # Keys and identifiers
            if char in IDENT_START or char == "-":
                start = pos
                while pos < length and code[pos] not in ":#\n[]{},'\"":
                    pos += 1
                word = code[start:pos].rstrip()
                if not word:
                    pos = start + 1
                    yield Token(TokenType.PUNCTUATION, char, line, col)
                    at_line_start = False
                    continue

                # Check if it's a key (followed by :)
                temp_pos = pos
                while temp_pos < length and code[temp_pos] in " \t":
                    temp_pos += 1
                if temp_pos < length and code[temp_pos] == ":":
                    yield Token(TokenType.NAME_ATTRIBUTE, word, line, col)
                    pos = start + len(word)
                elif word.lower() in _BOOL_VALUES or word in _NULL_VALUES:
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                    pos = start + len(word)
                else:
                    yield Token(TokenType.STRING, word, line, col)
                    pos = start + len(word)
                at_line_start = False
                continue

            # Punctuation
            if char in "[]{},:":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                at_line_start = False
                continue

            yield Token(TokenType.ERROR, char, line, col)
            pos += 1
            at_line_start = False
