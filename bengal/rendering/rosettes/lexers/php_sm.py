"""Hand-written PHP lexer using composable scanner mixins.

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
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["PhpStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "abstract",
        "and",
        "array",
        "as",
        "break",
        "callable",
        "case",
        "catch",
        "class",
        "clone",
        "const",
        "continue",
        "declare",
        "default",
        "die",
        "do",
        "echo",
        "else",
        "elseif",
        "empty",
        "enddeclare",
        "endfor",
        "endforeach",
        "endif",
        "endswitch",
        "endwhile",
        "enum",
        "eval",
        "exit",
        "extends",
        "final",
        "finally",
        "fn",
        "for",
        "foreach",
        "function",
        "global",
        "goto",
        "if",
        "implements",
        "include",
        "include_once",
        "instanceof",
        "insteadof",
        "interface",
        "isset",
        "list",
        "match",
        "namespace",
        "new",
        "or",
        "print",
        "private",
        "protected",
        "public",
        "readonly",
        "require",
        "require_once",
        "return",
        "static",
        "switch",
        "throw",
        "trait",
        "try",
        "unset",
        "use",
        "var",
        "while",
        "xor",
        "yield",
        "yield from",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "array",
        "bool",
        "callable",
        "float",
        "int",
        "iterable",
        "mixed",
        "never",
        "null",
        "object",
        "string",
        "void",
        "false",
        "true",
        "self",
        "parent",
    }
)

_CONSTANTS: frozenset[str] = frozenset(
    {
        "true",
        "false",
        "null",
        "TRUE",
        "FALSE",
        "NULL",
        "__CLASS__",
        "__DIR__",
        "__FILE__",
        "__FUNCTION__",
        "__LINE__",
        "__METHOD__",
        "__NAMESPACE__",
        "__TRAIT__",
    }
)


class PhpStateMachineLexer(
    CStyleCommentsMixin,
    CStyleNumbersMixin,
    CStyleOperatorsMixin,
    StateMachineLexer,
):
    """PHP lexer using composable mixins."""

    name = "php"
    aliases = ("php3", "php4", "php5", "php7", "php8")
    filenames = ("*.php", "*.php3", "*.php4", "*.php5", "*.phtml")
    mimetypes = ("text/x-php", "application/x-php")

    NUMBER_CONFIG = NumberConfig()

    OPERATOR_CONFIG = OperatorConfig(
        three_char=frozenset({"===", "!==", "<=>", "**=", "??="}),
        two_char=frozenset(
            {
                "==",
                "!=",
                "<=",
                ">=",
                "&&",
                "||",
                "++",
                "--",
                "+=",
                "-=",
                "*=",
                "/=",
                "%=",
                ".=",
                "&=",
                "|=",
                "^=",
                "=>",
                "->",
                "::",
                "??",
                "**",
                "<>",
                "<<",
                ">>",
            }
        ),
        one_char=frozenset("+-*/%&|^~!<>=?@."),
    )

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = start
        in_php = False

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

            # PHP open tags
            if not in_php:
                if code[pos : pos + 5] == "<?php":
                    yield Token(TokenType.COMMENT_PREPROC, "<?php", line, col)
                    pos += 5
                    in_php = True
                    continue
                if code[pos : pos + 3] == "<?=":
                    yield Token(TokenType.COMMENT_PREPROC, "<?=", line, col)
                    pos += 3
                    in_php = True
                    continue
                if code[pos : pos + 2] == "<?":
                    yield Token(TokenType.COMMENT_PREPROC, "<?", line, col)
                    pos += 2
                    in_php = True
                    continue
                # HTML mode
                start = pos
                while pos < length and code[pos : pos + 2] != "<?":
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                if pos > start:
                    yield Token(TokenType.TEXT, code[start:pos], line, col)
                continue

            # PHP close tag
            if code[pos : pos + 2] == "?>":
                yield Token(TokenType.COMMENT_PREPROC, "?>", line, col)
                pos += 2
                in_php = False
                continue

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

            # Hash comments
            if char == "#":
                start = pos
                while pos < length and code[pos] != "\n":
                    pos += 1
                yield Token(TokenType.COMMENT_SINGLE, code[start:pos], line, col)
                continue

            # C-style comments
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

            # Variables $var
            if char == "$":
                start = pos
                pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                yield Token(TokenType.NAME_VARIABLE, code[start:pos], line, col)
                continue

            # Heredoc/Nowdoc
            if code[pos : pos + 3] == "<<<":
                start = pos
                pos += 3
                while pos < length and code[pos] in " \t":
                    pos += 1
                quoted = False
                if pos < length and code[pos] in "\"'":
                    quoted = True
                    quote = code[pos]
                    pos += 1
                delim_start = pos
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                delim = code[delim_start:pos]
                if quoted and pos < length and code[pos] == quote:
                    pos += 1
                # Skip to newline
                while pos < length and code[pos] != "\n":
                    pos += 1
                if pos < length:
                    pos += 1
                    line += 1
                    line_start = pos
                # Find end delimiter
                start_line = line
                while pos < length:
                    while pos < length and code[pos] in " \t":
                        pos += 1
                    if code[pos : pos + len(delim)] == delim:
                        temp = pos + len(delim)
                        if temp >= length or code[temp] in ";\n":
                            pos = temp
                            break
                    while pos < length and code[pos] != "\n":
                        pos += 1
                    if pos < length:
                        pos += 1
                        line += 1
                        line_start = pos
                yield Token(TokenType.STRING_HEREDOC, code[start:pos], start_line, col)
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

            if char == "'":
                start = pos
                pos += 1
                while pos < length and code[pos] != "'":
                    if code[pos] == "\\" and pos + 1 < length and code[pos + 1] in "\\'":
                        pos += 2
                        continue
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Numbers
            token, new_pos = self._try_number(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Identifiers
            if char in IDENT_START or char == "\\":
                start = pos
                if char == "\\":
                    pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] in "_\\"):
                    pos += 1
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
            if char in "()[]{}:;,":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.ERROR, char, line, col)
            pos += 1

    def _classify_word(self, word: str) -> TokenType:
        base = word.lstrip("\\").split("\\")[-1]  # Get last part of namespace
        if base in _CONSTANTS:
            return TokenType.KEYWORD_CONSTANT
        if base in ("class", "interface", "trait", "enum", "function", "fn", "const"):
            return TokenType.KEYWORD_DECLARATION
        if base in ("namespace", "use"):
            return TokenType.KEYWORD_NAMESPACE
        if base.lower() in {k.lower() for k in _KEYWORDS}:
            return TokenType.KEYWORD
        if base in _TYPES:
            return TokenType.KEYWORD_TYPE
        if base and base[0].isupper():
            return TokenType.NAME_CLASS
        return TokenType.NAME
