"""Hand-written Clojure lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    DIGITS,
    HEX_DIGITS,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["ClojureStateMachineLexer"]


_SPECIAL_FORMS: frozenset[str] = frozenset(
    {
        "def",
        "if",
        "do",
        "let",
        "quote",
        "var",
        "fn",
        "loop",
        "recur",
        "throw",
        "try",
        "catch",
        "finally",
        "monitor-enter",
        "monitor-exit",
        "new",
        "set!",
        ".",
        "defn",
        "defmacro",
        "defonce",
        "ns",
        "require",
        "import",
        "use",
        "refer",
        "in-ns",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "nil",
        "true",
        "false",
        "nil?",
        "true?",
        "false?",
        "not",
        "and",
        "or",
        "cond",
        "when",
        "when-not",
        "when-let",
        "when-first",
        "if-not",
        "if-let",
        "condp",
        "case",
        "for",
        "doseq",
        "dotimes",
        "while",
        "map",
        "filter",
        "reduce",
        "apply",
        "partial",
        "comp",
        "identity",
        "constantly",
        "juxt",
        "first",
        "rest",
        "next",
        "cons",
        "conj",
        "concat",
        "nth",
        "count",
        "empty?",
        "seq",
        "seq?",
        "list",
        "list?",
        "vector",
        "vector?",
        "hash-map",
        "map?",
        "set",
        "set?",
        "get",
        "get-in",
        "assoc",
        "assoc-in",
        "dissoc",
        "update",
        "update-in",
        "merge",
        "keys",
        "vals",
        "contains?",
        "find",
        "str",
        "pr-str",
        "prn-str",
        "print",
        "println",
        "pr",
        "prn",
        "read",
        "read-string",
        "slurp",
        "spit",
        "atom",
        "swap!",
        "reset!",
        "deref",
        "@",
    }
)


class ClojureStateMachineLexer(StateMachineLexer):
    """Clojure lexer with ; comments."""

    name = "clojure"
    aliases = ("clj",)
    filenames = ("*.clj", "*.cljs", "*.cljc", "*.edn")
    mimetypes = ("text/x-clojure", "application/x-clojure")

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = 0

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

            # Whitespace (including commas which are whitespace in Clojure)
            if char in " \t\n\r,":
                start = pos
                start_line = line
                while pos < length and code[pos] in " \t\n\r,":
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.WHITESPACE, code[start:pos], start_line, col)
                continue

            # Comments ;
            if char == ";":
                start = pos
                while pos < length and code[pos] != "\n":
                    pos += 1
                yield Token(TokenType.COMMENT_SINGLE, code[start:pos], line, col)
                continue

            # Discard macro #_
            if char == "#" and pos + 1 < length and code[pos + 1] == "_":
                yield Token(TokenType.COMMENT_SPECIAL, "#_", line, col)
                pos += 2
                continue

            # Reader macros #
            if char == "#":
                start = pos
                pos += 1
                if pos < length:
                    next_char = code[pos]
                    if next_char == "'":  # #'var
                        pos += 1
                        yield Token(TokenType.OPERATOR, "#'", line, col)
                        continue
                    if next_char == "(":  # #() anonymous function
                        yield Token(TokenType.OPERATOR, "#", line, col)
                        continue
                    if next_char == "{":  # #{} set literal
                        yield Token(TokenType.OPERATOR, "#", line, col)
                        continue
                    if next_char == '"':  # #"" regex
                        start = pos - 1
                        pos += 1
                        while pos < length and code[pos] != '"':
                            if code[pos] == "\\" and pos + 1 < length:
                                pos += 2
                                continue
                            pos += 1
                        if pos < length:
                            pos += 1
                        yield Token(TokenType.STRING_REGEX, code[start:pos], line, col)
                        continue
                yield Token(TokenType.OPERATOR, "#", line, col)
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

            # Character literals \c \newline \u0041
            if char == "\\":
                start = pos
                pos += 1
                if pos < length:
                    if code[pos : pos + 7] == "newline":
                        pos += 7
                    elif code[pos : pos + 5] == "space":
                        pos += 5
                    elif code[pos : pos + 3] == "tab":
                        pos += 3
                    elif code[pos : pos + 9] == "backspace":
                        pos += 9
                    elif code[pos : pos + 10] == "formfeed":
                        pos += 10
                    elif code[pos : pos + 6] == "return":
                        pos += 6
                    elif code[pos] == "u" and pos + 5 <= length:
                        pos += 5  # Unicode \u0041
                    else:
                        pos += 1  # Single char
                yield Token(TokenType.STRING_CHAR, code[start:pos], line, col)
                continue

            # Keywords :keyword
            if char == ":":
                start = pos
                pos += 1
                if pos < length and code[pos] == ":":  # Namespaced keyword ::
                    pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] in "_-?!*+/<>=."):
                    pos += 1
                yield Token(TokenType.STRING_SYMBOL, code[start:pos], line, col)
                continue

            # Numbers
            if char in DIGITS or (char == "-" and pos + 1 < length and code[pos + 1] in DIGITS):
                start = pos
                if char == "-":
                    pos += 1
                # Hex
                if code[pos] == "0" and pos + 1 < length and code[pos + 1] in "xX":
                    pos += 2
                    while pos < length and code[pos] in HEX_DIGITS:
                        pos += 1
                    yield Token(TokenType.NUMBER_HEX, code[start:pos], line, col)
                    continue
                # Ratio or decimal
                while pos < length and code[pos] in DIGITS:
                    pos += 1
                if pos < length and code[pos] == "/":  # Ratio
                    pos += 1
                    while pos < length and code[pos] in DIGITS:
                        pos += 1
                    yield Token(TokenType.NUMBER_INTEGER, code[start:pos], line, col)
                    continue
                if pos < length and code[pos] == ".":
                    pos += 1
                    while pos < length and code[pos] in DIGITS:
                        pos += 1
                if pos < length and code[pos] in "eE":
                    pos += 1
                    if pos < length and code[pos] in "+-":
                        pos += 1
                    while pos < length and code[pos] in DIGITS:
                        pos += 1
                if pos < length and code[pos] in "MN":  # BigDecimal/BigInt
                    pos += 1
                value = code[start:pos]
                token_type = (
                    TokenType.NUMBER_FLOAT
                    if "." in value or "e" in value.lower()
                    else TokenType.NUMBER_INTEGER
                )
                yield Token(token_type, value, line, col)
                continue

            # Symbols and special forms
            if char.isalpha() or char in "_*+-/<>=!?":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] in "_*+-/<>=!?.'"):
                    pos += 1
                word = code[start:pos]
                if word in ("nil", "true", "false"):
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif word in ("def", "defn", "defmacro", "defonce", "fn", "let"):
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word in ("ns", "require", "import", "use", "refer"):
                    yield Token(TokenType.KEYWORD_NAMESPACE, word, line, col)
                elif word in _SPECIAL_FORMS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif word in _BUILTINS:
                    yield Token(TokenType.NAME_BUILTIN, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Quote, syntax quote, unquote
            if char in "'`~@":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                continue

            # Deref @
            if char == "@":
                yield Token(TokenType.OPERATOR, "@", line, col)
                pos += 1
                continue

            # Metadata ^
            if char == "^":
                yield Token(TokenType.OPERATOR, "^", line, col)
                pos += 1
                continue

            # Punctuation
            if char in "()[]{}":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.ERROR, char, line, col)
            pos += 1
