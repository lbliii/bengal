"""Hand-written C++ lexer using composable scanner mixins.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    IDENT_START,
    CStyleCommentsMixin,
    CStyleNumbersMixin,
    CStyleOperatorsMixin,
    NumberConfig,
    OperatorConfig,
    scan_identifier,
    scan_line_comment,
    scan_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["CppStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        # C keywords
        "auto",
        "break",
        "case",
        "const",
        "continue",
        "default",
        "do",
        "else",
        "enum",
        "extern",
        "for",
        "goto",
        "if",
        "inline",
        "register",
        "return",
        "sizeof",
        "static",
        "struct",
        "switch",
        "typedef",
        "union",
        "volatile",
        "while",
        # C++ keywords
        "alignas",
        "alignof",
        "and",
        "and_eq",
        "asm",
        "bitand",
        "bitor",
        "catch",
        "class",
        "compl",
        "concept",
        "const_cast",
        "consteval",
        "constexpr",
        "constinit",
        "co_await",
        "co_return",
        "co_yield",
        "decltype",
        "delete",
        "dynamic_cast",
        "explicit",
        "export",
        "final",
        "friend",
        "mutable",
        "namespace",
        "new",
        "noexcept",
        "not",
        "not_eq",
        "operator",
        "or",
        "or_eq",
        "override",
        "private",
        "protected",
        "public",
        "reinterpret_cast",
        "requires",
        "static_assert",
        "static_cast",
        "template",
        "this",
        "throw",
        "try",
        "typeid",
        "typename",
        "using",
        "virtual",
        "xor",
        "xor_eq",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "bool",
        "char",
        "char8_t",
        "char16_t",
        "char32_t",
        "double",
        "float",
        "int",
        "long",
        "short",
        "signed",
        "unsigned",
        "void",
        "wchar_t",
        "size_t",
        "string",
        "vector",
        "map",
        "set",
        "list",
        "pair",
        "tuple",
        "unique_ptr",
        "shared_ptr",
        "weak_ptr",
        "optional",
        "variant",
        "any",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"true", "false", "nullptr", "NULL"})


class CppStateMachineLexer(
    CStyleCommentsMixin,
    CStyleNumbersMixin,
    CStyleOperatorsMixin,
    StateMachineLexer,
):
    """C++ lexer using composable mixins."""

    name = "cpp"
    aliases = ("c++", "cxx", "hpp")
    filenames = ("*.cpp", "*.hpp", "*.cc", "*.hh", "*.cxx", "*.hxx")
    mimetypes = ("text/x-c++",)

    NUMBER_CONFIG = NumberConfig(
        allow_underscores=False,  # C++ uses ' as separator
        integer_suffixes=("u", "U", "l", "L", "ul", "UL", "ll", "LL", "ull", "ULL"),
        float_suffixes=("f", "F", "l", "L"),
    )

    OPERATOR_CONFIG = OperatorConfig(
        three_char=frozenset({"...", "<=>", ">>=", "<<="}),
        two_char=frozenset(
            {
                "->",
                "::",
                "++",
                "--",
                "&&",
                "||",
                "==",
                "!=",
                "<=",
                ">=",
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
            }
        ),
        one_char=frozenset("+-*/%&|^!~<>=?:"),
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

            # Preprocessor
            if char == "#":
                start = pos
                pos = scan_line_comment(code, pos)
                yield Token(TokenType.COMMENT_PREPROC, code[start:pos], line, col)
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

            # Raw strings R"delimiter(...)delimiter"
            if char == "R" and pos + 1 < length and code[pos + 1] == '"':
                start = pos
                pos += 2
                # Find delimiter
                delim_start = pos
                while pos < length and code[pos] != "(":
                    pos += 1
                delimiter = code[delim_start:pos] + ")"
                pos += 1  # Skip (
                # Find end
                end_marker = delimiter + '"'
                while pos < length:
                    if code[pos : pos + len(end_marker)] == end_marker:
                        pos += len(end_marker)
                        break
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Strings
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

            # Numbers (with ' separators)
            if char in self.DIGITS or (
                char == "." and pos + 1 < length and code[pos + 1] in self.DIGITS
            ):
                start = pos
                token_type, pos = self._scan_cpp_number(code, pos)
                yield Token(token_type, code[start:pos], line, col)
                continue

            # Identifiers
            if char in IDENT_START:
                start = pos
                pos = scan_identifier(code, pos)
                word = code[start:pos]
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

    def _scan_cpp_number(self, code: str, pos: int) -> tuple[TokenType, int]:
        """Scan C++ number with ' separators."""
        length = len(code)

        if code[pos] == ".":
            pos += 1
            while pos < length and (code[pos] in self.DIGITS or code[pos] == "'"):
                pos += 1
            if pos < length and code[pos] in "eE":
                pos += 1
                if pos < length and code[pos] in "+-":
                    pos += 1
                while pos < length and (code[pos] in self.DIGITS or code[pos] == "'"):
                    pos += 1
            while pos < length and code[pos] in "fFlL":
                pos += 1
            return TokenType.NUMBER_FLOAT, pos

        # Hex/binary/octal
        if code[pos] == "0" and pos + 1 < length:
            next_char = code[pos + 1]
            if next_char in "xX":
                pos += 2
                while pos < length and (code[pos] in self.HEX_DIGITS or code[pos] == "'"):
                    pos += 1
                while pos < length and code[pos] in "uUlL":
                    pos += 1
                return TokenType.NUMBER_HEX, pos
            if next_char in "bB":
                pos += 2
                while pos < length and (code[pos] in self.BINARY_DIGITS or code[pos] == "'"):
                    pos += 1
                while pos < length and code[pos] in "uUlL":
                    pos += 1
                return TokenType.NUMBER_BIN, pos
            if next_char in self.OCTAL_DIGITS:
                while pos < length and (code[pos] in self.OCTAL_DIGITS or code[pos] == "'"):
                    pos += 1
                while pos < length and code[pos] in "uUlL":
                    pos += 1
                return TokenType.NUMBER_OCT, pos

        # Decimal
        while pos < length and (code[pos] in self.DIGITS or code[pos] == "'"):
            pos += 1

        if pos < length and code[pos] == ".":
            pos += 1
            while pos < length and (code[pos] in self.DIGITS or code[pos] == "'"):
                pos += 1
            if pos < length and code[pos] in "eE":
                pos += 1
                if pos < length and code[pos] in "+-":
                    pos += 1
                while pos < length and (code[pos] in self.DIGITS or code[pos] == "'"):
                    pos += 1
            while pos < length and code[pos] in "fFlL":
                pos += 1
            return TokenType.NUMBER_FLOAT, pos

        if pos < length and code[pos] in "eE":
            pos += 1
            if pos < length and code[pos] in "+-":
                pos += 1
            while pos < length and (code[pos] in self.DIGITS or code[pos] == "'"):
                pos += 1
            while pos < length and code[pos] in "fFlL":
                pos += 1
            return TokenType.NUMBER_FLOAT, pos

        while pos < length and code[pos] in "uUlL":
            pos += 1
        return TokenType.NUMBER_INTEGER, pos

    def _classify_word(self, word: str) -> TokenType:
        if word in _CONSTANTS:
            return TokenType.KEYWORD_CONSTANT
        if word in ("class", "struct", "enum", "union", "typedef", "namespace", "template"):
            return TokenType.KEYWORD_DECLARATION
        if word in ("using", "namespace"):
            return TokenType.KEYWORD_NAMESPACE
        if word in _KEYWORDS:
            return TokenType.KEYWORD
        if word in _TYPES:
            return TokenType.KEYWORD_TYPE
        return TokenType.NAME
