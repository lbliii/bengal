"""Hand-written Rust lexer using composable scanner mixins.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    BINARY_DIGITS,
    DIGITS,
    HEX_DIGITS,
    IDENT_START,
    OCTAL_DIGITS,
    CStyleCommentsMixin,
    CStyleOperatorsMixin,
    OperatorConfig,
    scan_identifier,
    scan_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["RustStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "as",
        "async",
        "await",
        "break",
        "const",
        "continue",
        "crate",
        "dyn",
        "else",
        "enum",
        "extern",
        "false",
        "fn",
        "for",
        "if",
        "impl",
        "in",
        "let",
        "loop",
        "match",
        "mod",
        "move",
        "mut",
        "pub",
        "ref",
        "return",
        "self",
        "Self",
        "static",
        "struct",
        "super",
        "trait",
        "true",
        "type",
        "unsafe",
        "use",
        "where",
        "while",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "bool",
        "char",
        "f32",
        "f64",
        "i8",
        "i16",
        "i32",
        "i64",
        "i128",
        "isize",
        "str",
        "u8",
        "u16",
        "u32",
        "u64",
        "u128",
        "usize",
        "Option",
        "Result",
        "String",
        "Vec",
        "Box",
        "Rc",
        "Arc",
        "Cell",
        "RefCell",
    }
)

_TYPE_SUFFIXES: tuple[str, ...] = (
    "i8",
    "i16",
    "i32",
    "i64",
    "i128",
    "isize",
    "u8",
    "u16",
    "u32",
    "u64",
    "u128",
    "usize",
    "f32",
    "f64",
)


class RustStateMachineLexer(
    CStyleCommentsMixin,
    CStyleOperatorsMixin,
    StateMachineLexer,
):
    """Rust lexer using composable mixins."""

    name = "rust"
    aliases = ("rs",)
    filenames = ("*.rs",)
    mimetypes = ("text/rust", "text/x-rust")

    OPERATOR_CONFIG = OperatorConfig(
        three_char=frozenset({"..=", ">>=", "<<="}),
        two_char=frozenset(
            {
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
                "&=",
                "|=",
                "^=",
                "->",
                "=>",
                "::",
                "..",
            }
        ),
        one_char=frozenset("+-*/%&|^~!<>=?"),
    )

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

            # Attributes #[...] or #![...]
            if char == "#" and pos + 1 < length and code[pos + 1] in "[!":
                start = pos
                pos += 1
                if pos < length and code[pos] == "!":
                    pos += 1
                if pos < length and code[pos] == "[":
                    bracket_depth = 1
                    pos += 1
                    while pos < length and bracket_depth > 0:
                        if code[pos] == "[":
                            bracket_depth += 1
                        elif code[pos] == "]":
                            bracket_depth -= 1
                        elif code[pos] == "\n":
                            line += 1
                            line_start = pos + 1
                        pos += 1
                yield Token(TokenType.NAME_DECORATOR, code[start:pos], line, col)
                continue

            # Lifetimes 'a
            if char == "'" and pos + 1 < length and code[pos + 1] in IDENT_START:
                start = pos
                pos += 1
                pos = scan_identifier(code, pos)
                yield Token(TokenType.NAME_LABEL, code[start:pos], line, col)
                continue

            # Raw strings r#"..."# or r"..."
            if char == "r" and pos + 1 < length and code[pos + 1] in '#"':
                start = pos
                pos += 1
                hash_count = 0
                while pos < length and code[pos] == "#":
                    hash_count += 1
                    pos += 1
                if pos < length and code[pos] == '"':
                    pos += 1
                    end_marker = '"' + "#" * hash_count
                    start_line = line
                    while pos < length:
                        if code[pos : pos + len(end_marker)] == end_marker:
                            pos += len(end_marker)
                            break
                        if code[pos] == "\n":
                            line += 1
                            line_start = pos + 1
                        pos += 1
                    yield Token(TokenType.STRING, code[start:pos], start_line, col)
                    continue

            # Byte strings b"..." or b'...'
            if char == "b" and pos + 1 < length and code[pos + 1] in "\"'":
                start = pos
                quote = code[pos + 1]
                pos += 2
                pos, _ = scan_string(code, pos, quote)
                token_type = TokenType.STRING if quote == '"' else TokenType.STRING_CHAR
                yield Token(token_type, code[start:pos], line, col)
                continue

            # Regular strings
            if char == '"':
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, '"')
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Character literals
            if char == "'":
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, "'")
                yield Token(TokenType.STRING_CHAR, code[start:pos], line, col)
                continue

            # Numbers
            if char in DIGITS:
                start = pos
                token_type, pos = self._scan_rust_number(code, pos)
                yield Token(token_type, code[start:pos], line, col)
                continue

            # Macros name!
            if char in IDENT_START:
                start = pos
                pos = scan_identifier(code, pos)
                word = code[start:pos]
                if pos < length and code[pos] == "!":
                    pos += 1
                    yield Token(TokenType.NAME_FUNCTION_MAGIC, code[start:pos], line, col)
                    continue
                token_type = self._classify_word(word)
                yield Token(token_type, word, line, col)
                continue

            # Operators
            token, new_pos = self._try_operator(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Punctuation
            if char in "()[]{}:;,.":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.ERROR, char, line, col)
            pos += 1

    def _scan_rust_number(self, code: str, pos: int) -> tuple[TokenType, int]:
        """Scan Rust number with type suffixes."""
        length = len(code)

        # Hex/octal/binary
        if code[pos] == "0" and pos + 1 < length:
            next_char = code[pos + 1]
            if next_char in "xX":
                pos += 2
                while pos < length and (code[pos] in HEX_DIGITS or code[pos] == "_"):
                    pos += 1
                pos = self._scan_type_suffix(code, pos)
                return TokenType.NUMBER_HEX, pos
            if next_char in "oO":
                pos += 2
                while pos < length and (code[pos] in OCTAL_DIGITS or code[pos] == "_"):
                    pos += 1
                pos = self._scan_type_suffix(code, pos)
                return TokenType.NUMBER_OCT, pos
            if next_char in "bB":
                pos += 2
                while pos < length and (code[pos] in BINARY_DIGITS or code[pos] == "_"):
                    pos += 1
                pos = self._scan_type_suffix(code, pos)
                return TokenType.NUMBER_BIN, pos

        # Decimal
        while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
            pos += 1

        # Float
        if pos < length and code[pos] == "." and pos + 1 < length and code[pos + 1] in DIGITS:
            pos += 1
            while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                pos += 1
            if pos < length and code[pos] in "eE":
                pos += 1
                if pos < length and code[pos] in "+-":
                    pos += 1
                while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                    pos += 1
            pos = self._scan_type_suffix(code, pos)
            return TokenType.NUMBER_FLOAT, pos

        if pos < length and code[pos] in "eE":
            pos += 1
            if pos < length and code[pos] in "+-":
                pos += 1
            while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                pos += 1
            pos = self._scan_type_suffix(code, pos)
            return TokenType.NUMBER_FLOAT, pos

        pos = self._scan_type_suffix(code, pos)
        return TokenType.NUMBER_INTEGER, pos

    def _scan_type_suffix(self, code: str, pos: int) -> int:
        """Scan Rust type suffix (i32, u64, f64, etc.)."""
        for suffix in sorted(_TYPE_SUFFIXES, key=len, reverse=True):
            if code[pos : pos + len(suffix)] == suffix:
                return pos + len(suffix)
        return pos

    def _classify_word(self, word: str) -> TokenType:
        if word in ("true", "false"):
            return TokenType.KEYWORD_CONSTANT
        if word in (
            "fn",
            "struct",
            "enum",
            "trait",
            "type",
            "impl",
            "mod",
            "const",
            "static",
            "let",
        ):
            return TokenType.KEYWORD_DECLARATION
        if word in ("use", "crate", "mod", "super", "self", "Self"):
            return TokenType.KEYWORD_NAMESPACE
        if word in _KEYWORDS:
            return TokenType.KEYWORD
        if word in _TYPES:
            return TokenType.NAME_BUILTIN
        if word and word[0].isupper():
            return TokenType.NAME_CLASS
        return TokenType.NAME
