"""Hand-written Groovy lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    IDENT_CONT,
    IDENT_START,
    CStyleCommentsMixin,
    CStyleNumbersMixin,
    CStyleOperatorsMixin,
    NumberConfig,
    OperatorConfig,
    scan_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer, scan_triple_string

__all__ = ["GroovyStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "abstract",
        "assert",
        "break",
        "case",
        "catch",
        "class",
        "const",
        "continue",
        "def",
        "default",
        "do",
        "else",
        "enum",
        "extends",
        "final",
        "finally",
        "for",
        "goto",
        "if",
        "implements",
        "import",
        "in",
        "instanceof",
        "interface",
        "native",
        "new",
        "package",
        "private",
        "protected",
        "public",
        "return",
        "static",
        "strictfp",
        "super",
        "switch",
        "synchronized",
        "this",
        "throw",
        "throws",
        "trait",
        "transient",
        "try",
        "volatile",
        "while",
        "with",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "void",
        "boolean",
        "byte",
        "char",
        "short",
        "int",
        "long",
        "float",
        "double",
        "Boolean",
        "Byte",
        "Character",
        "Short",
        "Integer",
        "Long",
        "Float",
        "Double",
        "String",
        "Object",
        "List",
        "Map",
        "Set",
        "Array",
        "Closure",
        "Range",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "println",
        "print",
        "sprintf",
        "printf",
        "each",
        "collect",
        "find",
        "findAll",
        "grep",
        "inject",
        "any",
        "every",
        "sort",
        "unique",
        "reverse",
        "join",
        "split",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"true", "false", "null"})


class GroovyStateMachineLexer(
    CStyleCommentsMixin,
    CStyleNumbersMixin,
    CStyleOperatorsMixin,
    StateMachineLexer,
):
    """Groovy lexer."""

    name = "groovy"
    aliases = ("gvy",)
    filenames = ("*.groovy", "*.gradle")
    mimetypes = ("text/x-groovy",)

    NUMBER_CONFIG = NumberConfig(
        integer_suffixes=("l", "L", "g", "G"),
        float_suffixes=("f", "F", "d", "D", "g", "G"),
    )

    OPERATOR_CONFIG = OperatorConfig(
        three_char=frozenset({"<=>", "...", "**=", "?:.", "*."}),
        two_char=frozenset(
            {
                "++",
                "--",
                "**",
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
                "?:",
                "?.",
                "->",
                "=~",
                "==~",
                "..",
                "<:",
                ">:",
            }
        ),
        one_char=frozenset("+-*/%&|^~!<>=?:"),
    )

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

            # Annotations @Name
            if char == "@":
                start = pos
                pos += 1
                while pos < length and (code[pos] in IDENT_CONT):
                    pos += 1
                yield Token(TokenType.NAME_DECORATOR, code[start:pos], line, col)
                continue

            # Triple-quoted strings (GString)
            if char == '"' and pos + 2 < length and code[pos : pos + 3] == '"""':
                start = pos
                pos += 3
                pos, newlines = scan_triple_string(code, pos, '"')
                yield Token(TokenType.STRING, code[start:pos], line, col)
                if newlines:
                    line += newlines
                    line_start = start + code[start:pos].rfind("\n") + 1
                continue

            if char == "'" and pos + 2 < length and code[pos : pos + 3] == "'''":
                start = pos
                pos += 3
                while pos < length:
                    if code[pos : pos + 3] == "'''":
                        pos += 3
                        break
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Regular strings
            if char == '"':
                start = pos
                pos += 1
                while pos < length and code[pos] != '"':
                    if code[pos] == "\\" and pos + 1 < length:
                        pos += 2
                        continue
                    if code[pos] == "$" and pos + 1 < length:
                        # GString interpolation
                        pass
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            if char == "'":
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, "'")
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Slashy strings /regex/
            if char == "/" and pos + 1 < length and code[pos + 1] not in "/=*":
                # Check if this looks like a regex context
                start = pos
                pos += 1
                while pos < length and code[pos] != "/":
                    if code[pos] == "\\" and pos + 1 < length:
                        pos += 2
                        continue
                    if code[pos] == "\n":
                        # Not a regex, backtrack
                        pos = start
                        break
                    pos += 1
                else:
                    if pos < length:
                        pos += 1
                    yield Token(TokenType.STRING_REGEX, code[start:pos], line, col)
                    continue
                # If we broke out, fall through to operators
                pass

            # Numbers
            token, new_pos = self._try_number(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Keywords and identifiers
            if char in IDENT_START:
                start = pos
                while pos < length and code[pos] in IDENT_CONT:
                    pos += 1
                word = code[start:pos]
                if word in _CONSTANTS:
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif word in ("class", "interface", "enum", "trait", "def"):
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word in ("import", "package"):
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
            token, new_pos = self._try_operator(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Punctuation
            if char in "()[]{},.;":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
