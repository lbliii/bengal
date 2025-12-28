"""Hand-written PowerShell lexer using state machine approach.

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

__all__ = ["PowershellStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "begin",
        "break",
        "catch",
        "class",
        "continue",
        "data",
        "define",
        "do",
        "dynamicparam",
        "else",
        "elseif",
        "end",
        "enum",
        "exit",
        "filter",
        "finally",
        "for",
        "foreach",
        "from",
        "function",
        "hidden",
        "if",
        "in",
        "inlinescript",
        "parallel",
        "param",
        "process",
        "return",
        "sequence",
        "static",
        "switch",
        "throw",
        "trap",
        "try",
        "until",
        "using",
        "var",
        "while",
        "workflow",
    }
)

_OPERATORS: frozenset[str] = frozenset(
    {
        "-eq",
        "-ne",
        "-gt",
        "-ge",
        "-lt",
        "-le",
        "-like",
        "-notlike",
        "-match",
        "-notmatch",
        "-contains",
        "-notcontains",
        "-in",
        "-notin",
        "-replace",
        "-split",
        "-join",
        "-and",
        "-or",
        "-xor",
        "-not",
        "-band",
        "-bor",
        "-bxor",
        "-bnot",
        "-shl",
        "-shr",
        "-is",
        "-isnot",
        "-as",
        "-f",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "Add-Content",
        "Clear-Content",
        "Clear-Host",
        "Compare-Object",
        "ConvertFrom-Json",
        "ConvertTo-Json",
        "Copy-Item",
        "Export-Csv",
        "ForEach-Object",
        "Format-List",
        "Format-Table",
        "Get-ChildItem",
        "Get-Command",
        "Get-Content",
        "Get-Date",
        "Get-Help",
        "Get-Item",
        "Get-Location",
        "Get-Member",
        "Get-Process",
        "Get-Service",
        "Import-Csv",
        "Import-Module",
        "Invoke-Command",
        "Invoke-Expression",
        "Invoke-RestMethod",
        "Invoke-WebRequest",
        "Measure-Object",
        "Move-Item",
        "New-Item",
        "New-Object",
        "Out-File",
        "Out-Null",
        "Read-Host",
        "Remove-Item",
        "Rename-Item",
        "Select-Object",
        "Select-String",
        "Set-Content",
        "Set-Item",
        "Set-Location",
        "Sort-Object",
        "Split-Path",
        "Start-Process",
        "Start-Service",
        "Stop-Process",
        "Stop-Service",
        "Test-Path",
        "Where-Object",
        "Write-Error",
        "Write-Host",
        "Write-Output",
        "Write-Verbose",
        "Write-Warning",
    }
)


class PowershellStateMachineLexer(StateMachineLexer):
    """PowerShell lexer with # and <# #> comments."""

    name = "powershell"
    aliases = ("posh", "ps1", "psm1")
    filenames = ("*.ps1", "*.psm1", "*.psd1")
    mimetypes = ("text/x-powershell",)

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = start

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

            # Block comments <# ... #>
            if char == "<" and pos + 1 < length and code[pos + 1] == "#":
                start = pos
                pos += 2
                start_line = line
                while pos < length:
                    if code[pos : pos + 2] == "#>":
                        pos += 2
                        break
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.COMMENT_MULTILINE, code[start:pos], start_line, col)
                continue

            # Line comments #
            if char == "#":
                start = pos
                while pos < length and code[pos] != "\n":
                    pos += 1
                yield Token(TokenType.COMMENT_SINGLE, code[start:pos], line, col)
                continue

            # Variables $var, $env:var, $script:var
            if char == "$":
                start = pos
                pos += 1
                if pos < length and code[pos] in "({":
                    # Complex variable $(expr) or ${name}
                    open_char = code[pos]
                    close_char = ")" if open_char == "(" else "}"
                    depth = 1
                    pos += 1
                    while pos < length and depth > 0:
                        if code[pos] == open_char:
                            depth += 1
                        elif code[pos] == close_char:
                            depth -= 1
                        pos += 1
                else:
                    while pos < length and (code[pos].isalnum() or code[pos] in "_:"):
                        pos += 1
                yield Token(TokenType.NAME_VARIABLE, code[start:pos], line, col)
                continue

            # Strings
            if char in "\"'":
                start = pos
                quote = char
                pos += 1
                while pos < length:
                    if code[pos] == quote:
                        if pos + 1 < length and code[pos + 1] == quote:
                            pos += 2  # Escaped quote
                            continue
                        pos += 1
                        break
                    if code[pos] == "`" and pos + 1 < length:
                        pos += 2  # Backtick escape
                        continue
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Here-strings @"..."@ or @'...'@
            if char == "@" and pos + 1 < length and code[pos + 1] in "\"'":
                start = pos
                quote = code[pos + 1]
                pos += 2
                start_line = line
                # Skip to end of line
                while pos < length and code[pos] != "\n":
                    pos += 1
                if pos < length:
                    pos += 1
                    line += 1
                    line_start = pos
                # Find closing
                end_marker = quote + "@"
                while pos < length:
                    if code[pos : pos + 2] == end_marker:
                        pos += 2
                        break
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.STRING_HEREDOC, code[start:pos], start_line, col)
                continue

            # Numbers
            if char in DIGITS or (char == "-" and pos + 1 < length and code[pos + 1] in DIGITS):
                start = pos
                if char == "-":
                    pos += 1
                if code[pos] == "0" and pos + 1 < length and code[pos + 1] in "xX":
                    pos += 2
                    while pos < length and code[pos] in HEX_DIGITS:
                        pos += 1
                    yield Token(TokenType.NUMBER_HEX, code[start:pos], line, col)
                    continue
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
                # Type suffixes
                if pos < length and code[pos] in "dDlLkbmbgbKBMBGB":
                    while pos < length and code[pos].isalpha():
                        pos += 1
                value = code[start:pos]
                token_type = (
                    TokenType.NUMBER_FLOAT
                    if "." in value or "e" in value.lower()
                    else TokenType.NUMBER_INTEGER
                )
                yield Token(token_type, value, line, col)
                continue

            # Operators starting with -
            if char == "-" and pos + 1 < length and code[pos + 1].isalpha():
                start = pos
                pos += 1
                while pos < length and code[pos].isalpha():
                    pos += 1
                word = code[start:pos].lower()
                if word in _OPERATORS:
                    yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                else:
                    yield Token(TokenType.NAME, code[start:pos], line, col)
                continue

            # Keywords and cmdlets
            if char.isalpha() or char == "_":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] in "_-"):
                    pos += 1
                word = code[start:pos]
                lower = word.lower()
                if lower in ("true", "false", "null"):
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif lower in ("function", "class", "enum", "param"):
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif lower in ("using", "import-module"):
                    yield Token(TokenType.KEYWORD_NAMESPACE, word, line, col)
                elif lower in _KEYWORDS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif any(word.lower() == b.lower() for b in _BUILTINS):
                    yield Token(TokenType.NAME_BUILTIN, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Operators
            if char in "=<>!&|+-*/%":
                start = pos
                if pos + 1 < length and code[pos : pos + 2] in (
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
                ):
                    pos += 2
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            # Punctuation
            if char in "()[]{}:;,.@":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
