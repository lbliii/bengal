"""Makefile lexer for Rosettes.

Thread-safe regex-based tokenizer for Makefiles.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["MakefileLexer"]

_FUNCTIONS = (
    "abspath",
    "addprefix",
    "addsuffix",
    "and",
    "basename",
    "call",
    "dir",
    "error",
    "eval",
    "file",
    "filter",
    "filter-out",
    "findstring",
    "firstword",
    "flavor",
    "foreach",
    "if",
    "info",
    "join",
    "lastword",
    "notdir",
    "or",
    "origin",
    "patsubst",
    "realpath",
    "shell",
    "sort",
    "strip",
    "subst",
    "suffix",
    "value",
    "warning",
    "wildcard",
    "word",
    "wordlist",
    "words",
)


class MakefileLexer(PatternLexer):
    """Makefile lexer. Thread-safe."""

    name = "makefile"
    aliases = ("make", "mf", "bsdmake")
    filenames = ("Makefile", "makefile", "GNUmakefile", "*.mk", "*.mak")
    mimetypes = ("text/x-makefile",)

    rules = (
        # Comments
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Directives
        Rule(
            re.compile(
                r"^\.(?:PHONY|SUFFIXES|DEFAULT|PRECIOUS|INTERMEDIATE|SECONDARY|SECONDEXPANSION|DELETE_ON_ERROR|IGNORE|LOW_RESOLUTION_TIME|SILENT|EXPORT_ALL_VARIABLES|NOTPARALLEL|ONESHELL|POSIX)\b",
                re.MULTILINE,
            ),
            TokenType.KEYWORD,
        ),
        # Conditionals
        Rule(
            re.compile(r"^\s*(?:ifeq|ifneq|ifdef|ifndef|else|endif)\b", re.MULTILINE),
            TokenType.KEYWORD,
        ),
        # Include/export
        Rule(
            re.compile(
                r"^\s*(?:include|sinclude|-include|export|unexport|override|define|endef|undefine)\b",
                re.MULTILINE,
            ),
            TokenType.KEYWORD,
        ),
        # Automatic variables
        Rule(re.compile(r"\$[@%<?\^+*]|\$\([@%<?\^+*][DF]?\)"), TokenType.NAME_VARIABLE_MAGIC),
        # Variable references $(VAR) or ${VAR}
        Rule(re.compile(r"\$\([^)]+\)|\$\{[^}]+\}"), TokenType.NAME_VARIABLE),
        # Simple variable reference $X
        Rule(re.compile(r"\$[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_VARIABLE),
        # Escaped dollar
        Rule(re.compile(r"\$\$"), TokenType.STRING_ESCAPE),
        # Targets (at start of line, before colon)
        Rule(re.compile(r"^[a-zA-Z0-9_./-]+(?=\s*:)", re.MULTILINE), TokenType.NAME_FUNCTION),
        # Assignment operators
        Rule(re.compile(r":=|\?=|\+=|!=|::=|="), TokenType.OPERATOR),
        # Rule separator
        Rule(re.compile(r":"), TokenType.PUNCTUATION),
        # Recipe prefix (tab at start of line)
        Rule(re.compile(r"^\t", re.MULTILINE), TokenType.WHITESPACE),
        # Continuation
        Rule(re.compile(r"\\$", re.MULTILINE), TokenType.OPERATOR),
        # Strings (in shell commands)
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^']*'"), TokenType.STRING_SINGLE),
        # Shell commands/text
        Rule(re.compile(r"[a-zA-Z0-9_./-]+"), TokenType.NAME),
        # Operators
        Rule(re.compile(r"[|&;<>]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\],]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
