"""Bash/Shell lexer for Rosettes.

Thread-safe regex-based tokenizer for shell scripts.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["BashLexer"]

# Shell keywords
_KEYWORDS = (
    "if",
    "then",
    "else",
    "elif",
    "fi",
    "for",
    "while",
    "until",
    "do",
    "done",
    "case",
    "esac",
    "in",
    "function",
    "select",
    "time",
    "coproc",
)

# Shell builtins
_BUILTINS = (
    "alias",
    "bg",
    "bind",
    "break",
    "builtin",
    "caller",
    "cd",
    "command",
    "compgen",
    "complete",
    "compopt",
    "continue",
    "declare",
    "dirs",
    "disown",
    "echo",
    "enable",
    "eval",
    "exec",
    "exit",
    "export",
    "false",
    "fc",
    "fg",
    "getopts",
    "hash",
    "help",
    "history",
    "jobs",
    "kill",
    "let",
    "local",
    "logout",
    "mapfile",
    "popd",
    "printf",
    "pushd",
    "pwd",
    "read",
    "readarray",
    "readonly",
    "return",
    "set",
    "shift",
    "shopt",
    "source",
    "suspend",
    "test",
    "times",
    "trap",
    "true",
    "type",
    "typeset",
    "ulimit",
    "umask",
    "unalias",
    "unset",
    "wait",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    """Classify a word token."""
    word = match.group(0)
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    return TokenType.NAME


class BashLexer(PatternLexer):
    """Bash/Shell lexer.

    Handles Bash/sh/zsh syntax including variable expansion, here-documents,
    and command substitution markers.
    Thread-safe: all state is immutable.
    """

    name = "bash"
    aliases = ("sh", "shell", "zsh", "ksh")
    filenames = ("*.sh", "*.bash", "*.zsh", "*.ksh", ".bashrc", ".zshrc", ".profile")
    mimetypes = ("text/x-shellscript", "application/x-sh")

    rules = (
        # Shebang
        Rule(re.compile(r"^#!.*$", re.MULTILINE), TokenType.COMMENT_HASHBANG),
        # Comments
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Here-documents (simplified - just the markers)
        Rule(re.compile(r"<<-?'?(\w+)'?"), TokenType.STRING_HEREDOC),
        # Double-quoted strings (may contain variables)
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        # Single-quoted strings (literal)
        Rule(re.compile(r"'[^']*'"), TokenType.STRING_SINGLE),
        # ANSI-C quoting
        Rule(re.compile(r"\$'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING),
        # Variable expansion
        Rule(re.compile(r"\$\{[^}]+\}"), TokenType.NAME_VARIABLE),
        Rule(re.compile(r"\$[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_VARIABLE),
        Rule(re.compile(r"\$[0-9@#?$!*-]"), TokenType.NAME_VARIABLE),
        # Command substitution
        Rule(re.compile(r"\$\([^)]*\)"), TokenType.STRING_INTERPOL),
        Rule(re.compile(r"`[^`]*`"), TokenType.STRING_BACKTICK),
        # Options: -o, --option (must come before operators)
        Rule(re.compile(r"--?[a-zA-Z][a-zA-Z0-9_-]*"), TokenType.NAME_ATTRIBUTE),
        # Numbers
        Rule(re.compile(r"\b\d+\b"), TokenType.NUMBER_INTEGER),
        # Keywords and builtins (includes hyphenated commands like my-script)
        Rule(re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_-]*\b"), _classify_word),
        # Operators
        Rule(re.compile(r"&&|\|\|"), TokenType.OPERATOR),
        Rule(re.compile(r"\|&|&>|>>|>|<|2>&1|&"), TokenType.OPERATOR),
        Rule(re.compile(r";;|;&|;;&"), TokenType.OPERATOR),  # Case terminators
        Rule(re.compile(r"[|!]"), TokenType.OPERATOR),
        # Comparison operators
        Rule(re.compile(r"-(?:eq|ne|lt|le|gt|ge|z|n|f|d|e|r|w|x|s)\b"), TokenType.OPERATOR_WORD),
        # Punctuation
        Rule(re.compile(r"[()[\]{};<>=]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
        # Catch-all for any remaining text (paths, filenames, etc.)
        Rule(re.compile(r"[^\s\[\](){}|&;$\"'#<>=]+"), TokenType.TEXT),
    )
