"""Fish shell lexer for Rosettes.

Thread-safe regex-based tokenizer for Fish shell scripts.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["FishLexer"]

# Fish keywords
_KEYWORDS = frozenset(
    (
        "if",
        "else",
        "switch",
        "case",
        "for",
        "in",
        "while",
        "begin",
        "end",
        "function",
        "return",
        "break",
        "continue",
        "and",
        "or",
        "not",
        "time",
        "builtin",
        "command",
        "exec",
        "set",
        "argparse",
    )
)

# Fish builtins
_BUILTINS = frozenset(
    (
        "abbr",
        "alias",
        "bg",
        "bind",
        "block",
        "breakpoint",
        "cd",
        "cdh",
        "complete",
        "contains",
        "count",
        "dirh",
        "dirs",
        "disown",
        "echo",
        "emit",
        "eval",
        "exit",
        "false",
        "fg",
        "fish_add_path",
        "fish_breakpoint_prompt",
        "fish_config",
        "fish_git_prompt",
        "fish_greeting",
        "fish_indent",
        "fish_is_root_user",
        "fish_key_reader",
        "fish_mode_prompt",
        "fish_opt",
        "fish_prompt",
        "fish_right_prompt",
        "fish_status_to_signal",
        "fish_svn_prompt",
        "fish_title",
        "fish_update_completions",
        "fish_vcs_prompt",
        "funced",
        "funcsave",
        "functions",
        "help",
        "history",
        "isatty",
        "jobs",
        "math",
        "nextd",
        "open",
        "path",
        "popd",
        "prevd",
        "printf",
        "prompt_hostname",
        "prompt_login",
        "prompt_pwd",
        "psub",
        "pushd",
        "pwd",
        "random",
        "read",
        "realpath",
        "set_color",
        "source",
        "status",
        "string",
        "suspend",
        "test",
        "trap",
        "true",
        "type",
        "ulimit",
        "umask",
        "vared",
        "wait",
    )
)


def _classify_word(match: re.Match[str]) -> TokenType:
    """Classify Fish identifiers."""
    word = match.group(0)
    if word in ("true", "false"):
        return TokenType.KEYWORD_CONSTANT
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    return TokenType.NAME


class FishLexer(PatternLexer):
    """Fish shell lexer. Thread-safe."""

    name = "fish"
    aliases = ("fishshell",)
    filenames = ("*.fish",)
    mimetypes = ("application/x-fish",)

    rules = (
        # Comments
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^']*'"), TokenType.STRING_SINGLE),
        # Variable expansion: $var, $var[1], (command)
        Rule(re.compile(r"\$[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_VARIABLE),
        Rule(re.compile(r"\$\{[^}]+\}"), TokenType.NAME_VARIABLE),
        # Command substitution
        Rule(re.compile(r"\("), TokenType.PUNCTUATION),
        Rule(re.compile(r"\)"), TokenType.PUNCTUATION),
        # Status variable
        Rule(re.compile(r"\$status|\$pipestatus|\$argv|\$fish_pid"), TokenType.NAME_BUILTIN_PSEUDO),
        # Redirections
        Rule(re.compile(r"\d*>>?\+?|<|\^"), TokenType.OPERATOR),
        # Pipes and background
        Rule(re.compile(r"\||&"), TokenType.OPERATOR),
        # Options: -o, --option
        Rule(re.compile(r"--?[a-zA-Z][a-zA-Z0-9_-]*"), TokenType.NAME_ATTRIBUTE),
        # Numbers
        Rule(re.compile(r"-?\d+\.\d+"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"-?\d+"), TokenType.NUMBER_INTEGER),
        # Keywords and identifiers
        Rule(re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_-]*\b"), _classify_word),
        # Semicolons
        Rule(re.compile(r";"), TokenType.PUNCTUATION),
        # Array indexing
        Rule(re.compile(r"\[|\]"), TokenType.PUNCTUATION),
        # Globbing
        Rule(re.compile(r"\*\*|\*|\?"), TokenType.OPERATOR),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
        # Other
        Rule(re.compile(r"[^\s\[\](){}|&;$\"'#]+"), TokenType.TEXT),
    )
