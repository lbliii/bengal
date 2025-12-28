"""Hand-written HCL/Terraform lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    DIGITS,
    CStyleCommentsMixin,
    HashCommentsMixin,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["HclStateMachineLexer"]


_BLOCK_TYPES: frozenset[str] = frozenset(
    {
        "data",
        "locals",
        "module",
        "output",
        "provider",
        "resource",
        "terraform",
        "variable",
        "moved",
        "import",
        "check",
        "removed",
    }
)

_KEYWORDS: frozenset[str] = frozenset(
    {
        "for",
        "for_each",
        "if",
        "in",
        "dynamic",
        "content",
        "each",
        "self",
        "count",
        "depends_on",
        "lifecycle",
        "connection",
        "provisioner",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "bool",
        "list",
        "map",
        "number",
        "object",
        "set",
        "string",
        "tuple",
        "any",
    }
)

_FUNCTIONS: frozenset[str] = frozenset(
    {
        "abs",
        "ceil",
        "floor",
        "log",
        "max",
        "min",
        "pow",
        "signum",
        "chomp",
        "format",
        "formatlist",
        "indent",
        "join",
        "lower",
        "regex",
        "regexall",
        "replace",
        "split",
        "strrev",
        "substr",
        "title",
        "trim",
        "trimprefix",
        "trimsuffix",
        "trimspace",
        "upper",
        "alltrue",
        "anytrue",
        "chunklist",
        "coalesce",
        "coalescelist",
        "compact",
        "concat",
        "contains",
        "distinct",
        "element",
        "flatten",
        "index",
        "keys",
        "length",
        "list",
        "lookup",
        "map",
        "matchkeys",
        "merge",
        "one",
        "range",
        "reverse",
        "setintersection",
        "setproduct",
        "setsubtract",
        "setunion",
        "slice",
        "sort",
        "sum",
        "transpose",
        "values",
        "zipmap",
        "base64decode",
        "base64encode",
        "csvdecode",
        "jsondecode",
        "jsonencode",
        "yamldecode",
        "yamlencode",
        "file",
        "fileexists",
        "fileset",
        "templatefile",
        "formatdate",
        "timeadd",
        "timestamp",
        "md5",
        "sha1",
        "sha256",
        "uuid",
        "can",
        "nonsensitive",
        "sensitive",
        "tobool",
        "tolist",
        "tomap",
        "tonumber",
        "toset",
        "tostring",
        "try",
        "type",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"true", "false", "null"})


class HclStateMachineLexer(
    CStyleCommentsMixin,
    HashCommentsMixin,
    StateMachineLexer,
):
    """HCL/Terraform lexer."""

    name = "hcl"
    aliases = ("terraform", "tf")
    filenames = ("*.tf", "*.tfvars", "*.hcl")
    mimetypes = ("text/x-hcl", "application/x-terraform")

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

            # Hash comments
            token, new_pos = self._try_hash_comment(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
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

            # Heredoc <<EOF or <<-EOF
            if char == "<" and pos + 1 < length and code[pos + 1] == "<":
                start = pos
                pos += 2
                strip_indent = False
                if pos < length and code[pos] == "-":
                    strip_indent = True
                    pos += 1
                # Get delimiter
                delim_start = pos
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                delim = code[delim_start:pos]
                if delim:
                    start_line = line
                    while pos < length and code[pos] != "\n":
                        pos += 1
                    if pos < length:
                        pos += 1
                        line += 1
                        line_start = pos
                    # Find end delimiter
                    while pos < length:
                        if strip_indent:
                            while pos < length and code[pos] in " \t":
                                pos += 1
                        if code[pos : pos + len(delim)] == delim:
                            temp = pos + len(delim)
                            if temp >= length or code[temp] == "\n":
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

            # Variable interpolation ${...} or %{...}
            if char in "$%" and pos + 1 < length and code[pos + 1] == "{":
                start = pos
                pos += 2
                depth = 1
                while pos < length and depth > 0:
                    if code[pos] == "{":
                        depth += 1
                    elif code[pos] == "}":
                        depth -= 1
                    elif code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.STRING_INTERPOL, code[start:pos], line, col)
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

            # Numbers
            if char in DIGITS or (char == "-" and pos + 1 < length and code[pos + 1] in DIGITS):
                start = pos
                if char == "-":
                    pos += 1
                while pos < length and code[pos] in DIGITS:
                    pos += 1
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
                while pos < length and (code[pos].isalnum() or code[pos] in "_-"):
                    pos += 1
                word = code[start:pos]
                if word in _CONSTANTS:
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif word in _BLOCK_TYPES:
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word in _KEYWORDS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif word in _TYPES:
                    yield Token(TokenType.KEYWORD_TYPE, word, line, col)
                elif word in _FUNCTIONS:
                    yield Token(TokenType.NAME_FUNCTION, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Operators
            if char in "=<>!&|+-*/%?":
                start = pos
                if pos + 2 < length and code[pos : pos + 3] in ("...",):
                    pos += 3
                elif pos + 1 < length and code[pos : pos + 2] in (
                    "=>",
                    "->",
                    "&&",
                    "||",
                    "==",
                    "!=",
                    "<=",
                    ">=",
                ):
                    pos += 2
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            # Splat operator
            if char == "*":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                continue

            # Dot (attribute access)
            if char == ".":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                continue

            # Punctuation
            if char in "()[]{}:,":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.ERROR, char, line, col)
            pos += 1
