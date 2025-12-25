"""Hand-written Haskell lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    DIGITS,
    HEX_DIGITS,
    OCTAL_DIGITS,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["HaskellStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "as",
        "case",
        "class",
        "data",
        "default",
        "deriving",
        "do",
        "else",
        "family",
        "forall",
        "foreign",
        "hiding",
        "if",
        "import",
        "in",
        "infix",
        "infixl",
        "infixr",
        "instance",
        "let",
        "mdo",
        "module",
        "newtype",
        "of",
        "proc",
        "qualified",
        "rec",
        "then",
        "type",
        "where",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "Bool",
        "Char",
        "Double",
        "Either",
        "Float",
        "Int",
        "Integer",
        "IO",
        "Maybe",
        "Ordering",
        "String",
        "Word",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"True", "False", "Nothing", "Just", "Left", "Right"})


class HaskellStateMachineLexer(StateMachineLexer):
    """Haskell lexer with -- and {- -} comments."""

    name = "haskell"
    aliases = ("hs",)
    filenames = ("*.hs", "*.lhs")
    mimetypes = ("text/x-haskell",)

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

            # Line comments --
            if char == "-" and pos + 1 < length and code[pos + 1] == "-":
                start = pos
                while pos < length and code[pos] != "\n":
                    pos += 1
                yield Token(TokenType.COMMENT_SINGLE, code[start:pos], line, col)
                continue

            # Block comments {- -} (nested)
            if char == "{" and pos + 1 < length and code[pos + 1] == "-":
                start = pos
                pos += 2
                depth = 1
                start_line = line
                while pos < length and depth > 0:
                    if code[pos : pos + 2] == "{-":
                        depth += 1
                        pos += 2
                        continue
                    if code[pos : pos + 2] == "-}":
                        depth -= 1
                        pos += 2
                        continue
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.COMMENT_MULTILINE, code[start:pos], start_line, col)
                continue

            # Pragma {-# ... #-}
            if char == "{" and pos + 2 < length and code[pos : pos + 3] == "{-#":
                start = pos
                pos += 3
                start_line = line
                while pos < length:
                    if code[pos : pos + 3] == "#-}":
                        pos += 3
                        break
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.COMMENT_PREPROC, code[start:pos], start_line, col)
                continue

            # Strings
            if char == '"':
                start = pos
                pos += 1
                while pos < length and code[pos] != '"':
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
                        while pos < length and code[pos] in HEX_DIGITS:
                            pos += 1
                        yield Token(TokenType.NUMBER_HEX, code[start:pos], line, col)
                        continue
                    if next_char in "oO":
                        pos += 2
                        while pos < length and code[pos] in OCTAL_DIGITS:
                            pos += 1
                        yield Token(TokenType.NUMBER_OCT, code[start:pos], line, col)
                        continue

                while pos < length and code[pos] in DIGITS:
                    pos += 1
                is_float = False
                if pos < length and code[pos] == ".":
                    if pos + 1 < length and code[pos + 1] in DIGITS:
                        is_float = True
                        pos += 1
                        while pos < length and code[pos] in DIGITS:
                            pos += 1
                if pos < length and code[pos] in "eE":
                    is_float = True
                    pos += 1
                    if pos < length and code[pos] in "+-":
                        pos += 1
                    while pos < length and code[pos] in DIGITS:
                        pos += 1
                yield Token(
                    TokenType.NUMBER_FLOAT if is_float else TokenType.NUMBER_INTEGER,
                    code[start:pos],
                    line,
                    col,
                )
                continue

            # Identifiers (lowercase start = variable, uppercase start = constructor/type)
            if char.isalpha() or char == "_":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] in "_'"):
                    pos += 1
                word = code[start:pos]
                if word in _CONSTANTS:
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif word in ("data", "newtype", "type", "class", "instance"):
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word in ("module", "import", "qualified", "as", "hiding"):
                    yield Token(TokenType.KEYWORD_NAMESPACE, word, line, col)
                elif word in _KEYWORDS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif word in _TYPES:
                    yield Token(TokenType.KEYWORD_TYPE, word, line, col)
                elif word and word[0].isupper():
                    yield Token(TokenType.NAME_CLASS, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Operators (symbolic)
            if char in "!#$%&*+./<=>?@\\^|-~:":
                start = pos
                while pos < length and code[pos] in "!#$%&*+./<=>?@\\^|-~:":
                    pos += 1
                op = code[start:pos]
                if op in ("::", "->", "<-", "=>", "|", "\\", "=", "@"):
                    yield Token(TokenType.OPERATOR, op, line, col)
                else:
                    yield Token(TokenType.OPERATOR, op, line, col)
                continue

            # Backtick operators `func`
            if char == "`":
                start = pos
                pos += 1
                while pos < length and code[pos] != "`":
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            # Punctuation
            if char in "()[]{},:;":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.ERROR, char, line, col)
            pos += 1
