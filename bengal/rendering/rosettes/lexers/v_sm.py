"""Hand-written V lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
V is a simple, fast systems programming language.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    BINARY_DIGITS,
    DIGITS,
    HEX_DIGITS,
    OCTAL_DIGITS,
    CStyleCommentsMixin,
    scan_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["VStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "as",
        "asm",
        "assert",
        "atomic",
        "break",
        "const",
        "continue",
        "defer",
        "else",
        "enum",
        "false",
        "fn",
        "for",
        "go",
        "goto",
        "if",
        "import",
        "in",
        "interface",
        "is",
        "isreftype",
        "lock",
        "match",
        "module",
        "mut",
        "none",
        "or",
        "pub",
        "return",
        "rlock",
        "select",
        "shared",
        "sizeof",
        "spawn",
        "static",
        "struct",
        "true",
        "type",
        "typeof",
        "union",
        "unsafe",
        "volatile",
        "while",
        "__global",
        "__offsetof",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "bool",
        "byte",
        "char",
        "f32",
        "f64",
        "i8",
        "i16",
        "i32",
        "i64",
        "i128",
        "int",
        "isize",
        "rune",
        "string",
        "u8",
        "u16",
        "u32",
        "u64",
        "u128",
        "usize",
        "voidptr",
        "charptr",
        "byteptr",
        "any",
        "none",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "print",
        "println",
        "eprint",
        "eprintln",
        "dump",
        "panic",
        "assert",
        "error",
        "typeof",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"true", "false", "none"})


class VStateMachineLexer(
    CStyleCommentsMixin,
    StateMachineLexer,
):
    """V language lexer."""

    name = "vlang"
    aliases = ("v",)
    filenames = ("*.v", "*.vv")
    mimetypes = ("text/x-v",)

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

            # Compiler directives $if etc
            if char == "$":
                start = pos
                pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                yield Token(TokenType.COMMENT_PREPROC, code[start:pos], line, col)
                continue

            # Attributes [inline] etc
            if char == "[":
                start = pos
                pos += 1
                depth = 1
                while pos < length and depth > 0:
                    if code[pos] == "[":
                        depth += 1
                    elif code[pos] == "]":
                        depth -= 1
                    pos += 1
                # Check if it's an attribute (alphanumeric content)
                content = code[start + 1 : pos - 1]
                if content and (content[0].isalpha() or content[0] == "_"):
                    yield Token(TokenType.NAME_DECORATOR, code[start:pos], line, col)
                else:
                    # Regular brackets - backtrack
                    pos = start + 1
                    yield Token(TokenType.PUNCTUATION, "[", line, col)
                continue

            # Raw strings r'...' or r"..."
            if char == "r" and pos + 1 < length and code[pos + 1] in "\"'":
                start = pos
                quote = code[pos + 1]
                pos += 2
                while pos < length and code[pos] != quote:
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # C-interop strings c'...' or c"..."
            if char == "c" and pos + 1 < length and code[pos + 1] in "\"'":
                start = pos
                quote = code[pos + 1]
                pos += 2
                pos, _ = scan_string(code, pos, quote)
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Strings with interpolation
            if char == '"' or char == "'":
                quote = char
                start = pos
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
                continue

            # Backtick strings (raw)
            if char == "`":
                start = pos
                pos += 1
                while pos < length and code[pos] != "`":
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                if pos < length:
                    pos += 1
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
                if (
                    pos < length
                    and code[pos] == "."
                    and pos + 1 < length
                    and code[pos + 1] in DIGITS
                ):
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
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                word = code[start:pos]
                if word in _CONSTANTS:
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif word in ("fn", "struct", "enum", "interface", "union", "type", "const"):
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word in ("import", "module", "pub"):
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
            if char in "=<>!&|+-*/%^~:":
                start = pos
                if pos + 1 < length and code[pos : pos + 2] in (
                    "==",
                    "!=",
                    "<=",
                    ">=",
                    "&&",
                    "||",
                    "<<",
                    ">>",
                    "+=",
                    "-=",
                    "*=",
                    "/=",
                    "%=",
                    ":=",
                    "->",
                    "..",
                ):
                    pos += 2
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            # Dot and range
            if char == ".":
                if pos + 1 < length and code[pos + 1] == ".":
                    yield Token(TokenType.OPERATOR, "..", line, col)
                    pos += 2
                else:
                    yield Token(TokenType.OPERATOR, ".", line, col)
                    pos += 1
                continue

            # Punctuation
            if char in "()[]{},.;#@?":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
