"""Hand-written Ruby lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    BINARY_DIGITS,
    DIGITS,
    HEX_DIGITS,
    OCTAL_DIGITS,
    HashCommentsMixin,
    scan_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["RubyStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "BEGIN",
        "END",
        "alias",
        "and",
        "begin",
        "break",
        "case",
        "class",
        "def",
        "defined?",
        "do",
        "else",
        "elsif",
        "end",
        "ensure",
        "false",
        "for",
        "if",
        "in",
        "module",
        "next",
        "nil",
        "not",
        "or",
        "redo",
        "rescue",
        "retry",
        "return",
        "self",
        "super",
        "then",
        "true",
        "undef",
        "unless",
        "until",
        "when",
        "while",
        "yield",
        "__FILE__",
        "__LINE__",
        "__ENCODING__",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "Array",
        "Float",
        "Integer",
        "String",
        "Hash",
        "Kernel",
        "Object",
        "Class",
        "Module",
        "Proc",
        "Method",
        "Exception",
        "StandardError",
        "RuntimeError",
        "Numeric",
        "Comparable",
        "Enumerable",
        "Regexp",
        "Range",
        "IO",
        "File",
        "Dir",
        "Time",
        "Math",
        "puts",
        "print",
        "gets",
        "require",
        "require_relative",
        "load",
        "include",
        "extend",
        "attr",
        "attr_reader",
        "attr_writer",
        "attr_accessor",
        "private",
        "protected",
        "public",
        "raise",
        "catch",
        "throw",
        "lambda",
        "proc",
    }
)


class RubyStateMachineLexer(
    HashCommentsMixin,
    StateMachineLexer,
):
    """Ruby lexer."""

    name = "ruby"
    aliases = ("rb",)
    filenames = ("*.rb", "*.rake", "*.gemspec", "Rakefile", "Gemfile")
    mimetypes = ("text/x-ruby", "application/x-ruby")

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
                continue

            # Comments
            token, new_pos = self._try_hash_comment(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Multi-line comments =begin ... =end
            if col == 1 and code[pos : pos + 6] == "=begin":
                start = pos
                start_line = line
                while pos < length:
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                        if code[pos + 1 : pos + 5] == "=end":
                            pos = pos + 5
                            while pos < length and code[pos] != "\n":
                                pos += 1
                            break
                    pos += 1
                yield Token(TokenType.COMMENT_MULTILINE, code[start:pos], start_line, 1)
                continue

            # Symbols :name
            if char == ":":
                if pos + 1 < length and (code[pos + 1].isalpha() or code[pos + 1] == "_"):
                    start = pos
                    pos += 1
                    while pos < length and (code[pos].isalnum() or code[pos] in "_?!"):
                        pos += 1
                    yield Token(TokenType.STRING_SYMBOL, code[start:pos], line, col)
                    continue
                if pos + 1 < length and code[pos + 1] == '"':
                    start = pos
                    pos += 2
                    pos, _ = scan_string(code, pos, '"')
                    yield Token(TokenType.STRING_SYMBOL, code[start:pos], line, col)
                    continue
                yield Token(TokenType.PUNCTUATION, ":", line, col)
                pos += 1
                continue

            # Instance variables @var, @@var
            if char == "@":
                start = pos
                pos += 1
                if pos < length and code[pos] == "@":
                    pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                yield Token(TokenType.NAME_VARIABLE, code[start:pos], line, col)
                continue

            # Global variables $var
            if char == "$":
                start = pos
                pos += 1
                if pos < length:
                    if code[pos] in "~&`'+?!@;/\\,.=:<>\"":
                        pos += 1
                    elif code[pos].isalnum() or code[pos] == "_":
                        while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                            pos += 1
                yield Token(TokenType.NAME_VARIABLE, code[start:pos], line, col)
                continue

            # Heredocs <<EOF, <<-EOF, <<~EOF
            if char == "<" and pos + 1 < length and code[pos + 1] == "<":
                temp = pos + 2
                if temp < length and code[temp] in "-~":
                    temp += 1
                if temp < length and (code[temp].isalpha() or code[temp] in "'\"_"):
                    start = pos
                    pos = temp
                    quoted = code[pos] in "'\""
                    if quoted:
                        quote = code[pos]
                        pos += 1
                        while pos < length and code[pos] != quote:
                            pos += 1
                        if pos < length:
                            pos += 1
                    else:
                        while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                            pos += 1
                    yield Token(TokenType.STRING_HEREDOC, code[start:pos], line, col)
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
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Backtick commands
            if char == "`":
                start = pos
                pos += 1
                while pos < length and code[pos] != "`":
                    if code[pos] == "\\" and pos + 1 < length:
                        pos += 2
                        continue
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.STRING_BACKTICK, code[start:pos], line, col)
                continue

            # Regex
            if char == "/" and pos > 0:
                # Simple heuristic: / after operator or keyword
                prev = code[pos - 1]
                if prev in "=([{,;":
                    start = pos
                    pos += 1
                    while pos < length and code[pos] != "/":
                        if code[pos] == "\\" and pos + 1 < length:
                            pos += 2
                            continue
                        if code[pos] == "\n":
                            break
                        pos += 1
                    if pos < length and code[pos] == "/":
                        pos += 1
                        while pos < length and code[pos] in "imxo":
                            pos += 1
                        yield Token(TokenType.STRING_REGEX, code[start:pos], line, col)
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
                    if next_char in "bB":
                        pos += 2
                        while pos < length and (code[pos] in BINARY_DIGITS or code[pos] == "_"):
                            pos += 1
                        yield Token(TokenType.NUMBER_BIN, code[start:pos], line, col)
                        continue
                    if next_char in "oO" or next_char in OCTAL_DIGITS:
                        pos += 1
                        if pos < length and code[pos] in "oO":
                            pos += 1
                        while pos < length and (code[pos] in OCTAL_DIGITS or code[pos] == "_"):
                            pos += 1
                        yield Token(TokenType.NUMBER_OCT, code[start:pos], line, col)
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
                if "." in code[start:pos] or "e" in code[start:pos].lower():
                    yield Token(TokenType.NUMBER_FLOAT, code[start:pos], line, col)
                else:
                    yield Token(TokenType.NUMBER_INTEGER, code[start:pos], line, col)
                continue

            # Keywords and identifiers
            if char.isalpha() or char == "_":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] in "_?!"):
                    pos += 1
                word = code[start:pos]
                if word in ("true", "false", "nil"):
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif word in ("class", "module", "def", "end"):
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word in _KEYWORDS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif word in _BUILTINS:
                    yield Token(TokenType.NAME_BUILTIN, word, line, col)
                elif word and word[0].isupper():
                    yield Token(TokenType.NAME_CLASS, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Operators
            if char in "=<>!&|+-*/%^~":
                start = pos
                if pos + 2 < length and code[pos : pos + 3] in (
                    "===",
                    "<=>",
                    "<=<",
                    ">=>",
                    "&&=",
                    "||=",
                    "**=",
                    "<<=",
                    ">>=",
                ):
                    pos += 3
                elif pos + 1 < length and code[pos : pos + 2] in (
                    "==",
                    "!=",
                    "<=",
                    ">=",
                    "&&",
                    "||",
                    "<<",
                    ">>",
                    "**",
                    "+=",
                    "-=",
                    "*=",
                    "/=",
                    "%=",
                    "&=",
                    "|=",
                    "^=",
                    "=~",
                    "!~",
                    "..",
                ):
                    pos += 2
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            # Punctuation
            if char in "()[]{}.,;?":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
