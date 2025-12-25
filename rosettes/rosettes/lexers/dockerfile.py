"""Dockerfile lexer for Rosettes.

Thread-safe regex-based tokenizer for Dockerfiles.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["DockerfileLexer"]

_INSTRUCTIONS = (
    "ADD",
    "ARG",
    "CMD",
    "COPY",
    "ENTRYPOINT",
    "ENV",
    "EXPOSE",
    "FROM",
    "HEALTHCHECK",
    "LABEL",
    "MAINTAINER",
    "ONBUILD",
    "RUN",
    "SHELL",
    "STOPSIGNAL",
    "USER",
    "VOLUME",
    "WORKDIR",
)


def _classify_instruction(match: re.Match[str]) -> TokenType:
    word = match.group(0).upper()
    if word in _INSTRUCTIONS:
        return TokenType.KEYWORD
    return TokenType.NAME


class DockerfileLexer(PatternLexer):
    """Dockerfile lexer. Thread-safe."""

    name = "dockerfile"
    aliases = ("docker",)
    filenames = ("Dockerfile", "Dockerfile.*", "*.dockerfile")
    mimetypes = ("text/x-dockerfile",)

    rules = (
        # Comments
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Parser directives (must be at start)
        Rule(re.compile(r"^#\s*(?:syntax|escape)=.*$", re.MULTILINE), TokenType.COMMENT_PREPROC),
        # Instructions (case-insensitive)
        Rule(
            re.compile(
                r"^(?:ADD|ARG|CMD|COPY|ENTRYPOINT|ENV|EXPOSE|FROM|HEALTHCHECK|LABEL|MAINTAINER|ONBUILD|RUN|SHELL|STOPSIGNAL|USER|VOLUME|WORKDIR)\b",
                re.MULTILINE | re.IGNORECASE,
            ),
            TokenType.KEYWORD,
        ),
        # AS keyword in FROM
        Rule(re.compile(r"\bAS\b", re.IGNORECASE), TokenType.KEYWORD),
        # Variables
        Rule(re.compile(r"\$\{[^}]+\}"), TokenType.NAME_VARIABLE),
        Rule(re.compile(r"\$[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_VARIABLE),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^']*'"), TokenType.STRING_SINGLE),
        # JSON arrays (for CMD, ENTRYPOINT)
        Rule(re.compile(r"\["), TokenType.PUNCTUATION),
        Rule(re.compile(r"\]"), TokenType.PUNCTUATION),
        # Flags (--flag=value)
        Rule(re.compile(r"--[a-zA-Z][-a-zA-Z0-9]*"), TokenType.NAME_ATTRIBUTE),
        # Numbers
        Rule(re.compile(r"\d+"), TokenType.NUMBER_INTEGER),
        # Image names/tags
        Rule(re.compile(r"[a-zA-Z0-9][-a-zA-Z0-9_./:]*"), TokenType.NAME),
        # Operators
        Rule(re.compile(r"[=:]"), TokenType.OPERATOR),
        # Line continuation
        Rule(re.compile(r"\\$", re.MULTILINE), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[,]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
