"""Hand-written Tree-sitter query lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
Tree-sitter is a parser generator tool and incremental parsing library.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import scan_string
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["TreeStateMachineLexer"]


_PREDICATES: frozenset[str] = frozenset(
    {
        "eq?",
        "not-eq?",
        "match?",
        "not-match?",
        "any-of?",
        "not-any-of?",
        "is?",
        "is-not?",
        "set!",
        "select-adjacent!",
    }
)


class TreeStateMachineLexer(StateMachineLexer):
    """Tree-sitter query language lexer."""

    name = "tree-sitter-query"
    aliases = ("tree", "scm", "treesitter")
    filenames = ("*.scm",)
    mimetypes = ("text/x-tree-sitter-query",)

    WHITESPACE = frozenset(" \t\n\r")

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = 0

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

            # Comments (semicolon to end of line)
            if char == ";":
                start = pos
                while pos < length and code[pos] != "\n":
                    pos += 1
                yield Token(TokenType.COMMENT_SINGLE, code[start:pos], line, col)
                continue

            # Capture names @name
            if char == "@":
                start = pos
                pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] in "_.-"):
                    pos += 1
                yield Token(TokenType.NAME_VARIABLE, code[start:pos], line, col)
                continue

            # Predicates #eq? etc or #set!
            if char == "#":
                start = pos
                pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] in "_-!?"):
                    pos += 1
                word = code[start + 1 : pos]
                if word in _PREDICATES or word.endswith("?") or word.endswith("!"):
                    yield Token(TokenType.NAME_BUILTIN, code[start:pos], line, col)
                else:
                    yield Token(TokenType.NAME_FUNCTION, code[start:pos], line, col)
                continue

            # Strings
            if char == '"':
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, '"')
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Node types (identifiers in query patterns)
            if char.isalpha() or char == "_":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] in "_"):
                    pos += 1
                yield Token(TokenType.NAME_CLASS, code[start:pos], line, col)
                continue

            # Field names with colon suffix: name:
            if char == ":":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            # Anonymous nodes "_"
            if char == "_" and (pos + 1 >= length or not code[pos + 1].isalnum()):
                yield Token(TokenType.KEYWORD, "_", line, col)
                pos += 1
                continue

            # Quantifiers
            if char in "*+?":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                continue

            # Anchor
            if char == ".":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                continue

            # Negation
            if char == "!":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                continue

            # Alternation
            if char == "|":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                continue

            # Grouping and node matching
            if char in "()[]":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
