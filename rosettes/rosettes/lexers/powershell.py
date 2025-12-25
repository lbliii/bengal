"""PowerShell lexer for Rosettes.

Thread-safe regex-based tokenizer for PowerShell scripts.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["PowerShellLexer"]

_KEYWORDS = (
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
    "while",
    "workflow",
)

_OPERATORS = (
    "-and",
    "-as",
    "-band",
    "-bnot",
    "-bor",
    "-bxor",
    "-contains",
    "-eq",
    "-f",
    "-ge",
    "-gt",
    "-icontains",
    "-ieq",
    "-ige",
    "-igt",
    "-ile",
    "-ilike",
    "-ilt",
    "-imatch",
    "-in",
    "-ine",
    "-inotcontains",
    "-inotlike",
    "-inotmatch",
    "-ireplace",
    "-is",
    "-isnot",
    "-isplit",
    "-join",
    "-le",
    "-like",
    "-lt",
    "-match",
    "-ne",
    "-not",
    "-notcontains",
    "-notin",
    "-notlike",
    "-notmatch",
    "-or",
    "-replace",
    "-shl",
    "-shr",
    "-split",
    "-xor",
)

_CONSTANTS = ("$true", "$false", "$null")


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0).lower()
    if word in ("function", "filter", "class", "enum", "param"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("using",):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    return TokenType.NAME


class PowerShellLexer(PatternLexer):
    """PowerShell lexer. Thread-safe."""

    name = "powershell"
    aliases = ("posh", "ps1", "psm1", "pwsh")
    filenames = ("*.ps1", "*.psm1", "*.psd1")
    mimetypes = ("text/x-powershell",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_-]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"<#[\s\S]*?#>"), TokenType.COMMENT_MULTILINE),
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Here-strings
        Rule(re.compile(r"@\"[\s\S]*?\"@"), TokenType.STRING_HEREDOC),
        Rule(re.compile(r"@'[\s\S]*?'@"), TokenType.STRING_HEREDOC),
        # Strings
        Rule(re.compile(r'"[^"]*(?:""[^"]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^']*(?:''[^']*)*'"), TokenType.STRING_SINGLE),
        # Special variables
        Rule(re.compile(r"\$(?:true|false|null)\b", re.IGNORECASE), TokenType.KEYWORD_CONSTANT),
        Rule(re.compile(r"\$\$|\$\?|\$\^"), TokenType.NAME_VARIABLE_MAGIC),
        Rule(re.compile(r"\$_|\$PSItem"), TokenType.NAME_VARIABLE_MAGIC),
        # Variables
        Rule(re.compile(r"\$\{[^}]+\}"), TokenType.NAME_VARIABLE),
        Rule(
            re.compile(r"\$[a-zA-Z_][a-zA-Z0-9_]*(?::[a-zA-Z_][a-zA-Z0-9_]*)?"),
            TokenType.NAME_VARIABLE,
        ),
        # Cmdlet names (Verb-Noun pattern)
        Rule(re.compile(r"\b[A-Z][a-z]+(?:-[A-Z][a-zA-Z0-9]+)+\b"), TokenType.NAME_FUNCTION),
        # Comparison/logical operators
        Rule(
            re.compile(
                r"-(?:eq|ne|lt|le|gt|ge|like|notlike|match|notmatch|contains|notcontains|in|notin|replace|split|join|and|or|not|band|bor|bxor|bnot|shl|shr|is|isnot|as|f)\b",
                re.IGNORECASE,
            ),
            TokenType.OPERATOR,
        ),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F]+[lL]?"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"\d+\.\d*(?:[eE][+-]?\d+)?[dD]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+[eE][+-]?\d+[dD]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+[lLdD]?(?:kb|mb|gb|tb|pb)?", re.IGNORECASE), TokenType.NUMBER_INTEGER),
        # Keywords
        Rule(
            re.compile(
                r"\b(?:begin|break|catch|class|continue|data|define|do|dynamicparam|else|elseif|end|enum|exit|filter|finally|for|foreach|from|function|hidden|if|in|inlinescript|parallel|param|process|return|sequence|static|switch|throw|trap|try|until|using|while|workflow)\b",
                re.IGNORECASE,
            ),
            _classify_word,
        ),
        # Names
        Rule(re.compile(_WORD_PATTERN), TokenType.NAME),
        # Operators
        Rule(re.compile(r"=>|->|\.\.|::"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|%="), TokenType.OPERATOR),
        Rule(re.compile(r"\+\+|--"), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%=!<>|&]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}@;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
