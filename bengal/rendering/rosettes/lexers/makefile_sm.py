"""Hand-written Makefile lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import HashCommentsMixin
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["MakefileStateMachineLexer"]


_FUNCTIONS: frozenset[str] = frozenset(
    {
        "subst",
        "patsubst",
        "strip",
        "findstring",
        "filter",
        "filter-out",
        "sort",
        "word",
        "wordlist",
        "words",
        "firstword",
        "lastword",
        "dir",
        "notdir",
        "suffix",
        "basename",
        "addsuffix",
        "addprefix",
        "join",
        "wildcard",
        "realpath",
        "abspath",
        "if",
        "or",
        "and",
        "foreach",
        "file",
        "call",
        "value",
        "eval",
        "origin",
        "flavor",
        "error",
        "warning",
        "info",
        "shell",
    }
)

_DIRECTIVES: frozenset[str] = frozenset(
    {
        "include",
        "-include",
        "sinclude",
        "define",
        "endef",
        "undefine",
        "ifdef",
        "ifndef",
        "ifeq",
        "ifneq",
        "else",
        "endif",
        "override",
        "export",
        "unexport",
        "private",
        "vpath",
    }
)


class MakefileStateMachineLexer(
    HashCommentsMixin,
    StateMachineLexer,
):
    """Makefile lexer."""

    name = "makefile"
    aliases = ("make", "mf", "bsdmake")
    filenames = ("Makefile", "makefile", "GNUmakefile", "*.mk", "*.mak")
    mimetypes = ("text/x-makefile",)

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = start
        at_line_start = True

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

            # Tab at line start (recipe)
            if at_line_start and char == "\t":
                yield Token(TokenType.WHITESPACE, char, line, col)
                pos += 1
                # Rest of recipe line
                start = pos
                while pos < length and code[pos] != "\n":
                    if code[pos] == "\\" and pos + 1 < length and code[pos + 1] == "\n":
                        pos += 2
                        line += 1
                        line_start = pos
                        continue
                    pos += 1
                if pos > start:
                    yield Token(TokenType.TEXT, code[start:pos], line, col + 1)
                at_line_start = False
                continue

            # Other whitespace
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

            # Line continuation
            if char == "\\" and pos + 1 < length and code[pos + 1] == "\n":
                yield Token(TokenType.WHITESPACE, "\\\n", line, col)
                pos += 2
                line += 1
                line_start = pos
                continue

            # Comments
            token, new_pos = self._try_hash_comment(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                at_line_start = False
                continue

            # Variables $(VAR) or ${VAR} or $X
            if char == "$":
                start = pos
                pos += 1
                if pos < length:
                    if code[pos] in "({":
                        pos += 1
                        depth = 1
                        while pos < length and depth > 0:
                            if code[pos] in "({":
                                depth += 1
                            elif code[pos] in ")}":
                                depth -= 1
                            pos += 1
                    elif code[pos] not in " \t\n":
                        pos += 1
                yield Token(TokenType.NAME_VARIABLE, code[start:pos], line, col)
                at_line_start = False
                continue

            # Directives (at line start)
            if at_line_start and char.isalpha():
                start = pos
                while pos < length and (code[pos].isalpha() or code[pos] == "-"):
                    pos += 1
                word = code[start:pos]
                if word in _DIRECTIVES:
                    yield Token(TokenType.KEYWORD, word, line, col)
                else:
                    # Could be a target
                    temp = pos
                    while temp < length and code[temp] in " \t":
                        temp += 1
                    if temp < length and code[temp] in ":=":
                        yield Token(TokenType.NAME_LABEL, word, line, col)
                    else:
                        yield Token(TokenType.NAME, word, line, col)
                at_line_start = False
                continue

            # Target/variable definitions
            if char in ":=":
                if char == ":" and pos + 1 < length and code[pos + 1] == "=":
                    yield Token(TokenType.OPERATOR, ":=", line, col)
                    pos += 2
                elif char == ":" and pos + 1 < length and code[pos + 1] == ":":
                    yield Token(TokenType.OPERATOR, "::", line, col)
                    pos += 2
                elif char == "=" and pos + 1 < length and code[pos + 1] == "=":
                    yield Token(TokenType.OPERATOR, "==", line, col)
                    pos += 2
                else:
                    yield Token(TokenType.OPERATOR, char, line, col)
                    pos += 1
                at_line_start = False
                continue

            # Other operators
            if char in "?+!":
                if pos + 1 < length and code[pos + 1] == "=":
                    yield Token(TokenType.OPERATOR, code[pos : pos + 2], line, col)
                    pos += 2
                else:
                    yield Token(TokenType.OPERATOR, char, line, col)
                    pos += 1
                at_line_start = False
                continue

            # Strings
            if char in "\"'":
                start = pos
                quote = char
                pos += 1
                while pos < length and code[pos] != quote:
                    if code[pos] == "\\" and pos + 1 < length:
                        pos += 2
                        continue
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                at_line_start = False
                continue

            # Identifiers and text
            if char.isalpha() or char == "_":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] in "_-."):
                    pos += 1
                word = code[start:pos]
                if word in _FUNCTIONS:
                    yield Token(TokenType.NAME_BUILTIN, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                at_line_start = False
                continue

            # Punctuation
            if char in "(){}[],:;@<>%*":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                at_line_start = False
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
            at_line_start = False
