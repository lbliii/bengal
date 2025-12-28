"""Hand-written Dockerfile lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    DIGITS,
    HashCommentsMixin,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["DockerfileStateMachineLexer"]


_INSTRUCTIONS: frozenset[str] = frozenset(
    {
        "FROM",
        "MAINTAINER",
        "RUN",
        "CMD",
        "LABEL",
        "EXPOSE",
        "ENV",
        "ADD",
        "COPY",
        "ENTRYPOINT",
        "VOLUME",
        "USER",
        "WORKDIR",
        "ARG",
        "ONBUILD",
        "STOPSIGNAL",
        "HEALTHCHECK",
        "SHELL",
    }
)


class DockerfileStateMachineLexer(
    HashCommentsMixin,
    StateMachineLexer,
):
    """Dockerfile lexer."""

    name = "dockerfile"
    aliases = ("docker",)
    filenames = ("Dockerfile", "*.dockerfile", "Dockerfile.*")
    mimetypes = ("text/x-dockerfile",)

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

            # Instructions (at line start)
            if at_line_start and char.isalpha():
                start = pos
                while pos < length and code[pos].isalpha():
                    pos += 1
                word = code[start:pos]
                if word.upper() in _INSTRUCTIONS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
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
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                at_line_start = False
                continue

            # Variables $VAR or ${VAR}
            if char == "$":
                start = pos
                pos += 1
                if pos < length and code[pos] == "{":
                    pos += 1
                    while pos < length and code[pos] != "}":
                        pos += 1
                    if pos < length:
                        pos += 1
                elif pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                        pos += 1
                yield Token(TokenType.NAME_VARIABLE, code[start:pos], line, col)
                at_line_start = False
                continue

            # Numbers
            if char in DIGITS:
                start = pos
                while pos < length and code[pos] in DIGITS:
                    pos += 1
                yield Token(TokenType.NUMBER_INTEGER, code[start:pos], line, col)
                at_line_start = False
                continue

            # Identifiers/paths
            if char.isalpha() or char in "/_.-":
                start = pos
                while pos < length and code[pos] not in " \t\n#\"'$=[]":
                    pos += 1
                yield Token(TokenType.TEXT, code[start:pos], line, col)
                at_line_start = False
                continue

            # Operators
            if char == "=":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                at_line_start = False
                continue

            # Brackets
            if char in "[]":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                at_line_start = False
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
            at_line_start = False
