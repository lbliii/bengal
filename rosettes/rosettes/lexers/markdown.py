"""Markdown lexer for Rosettes.

Thread-safe regex-based tokenizer for Markdown documents.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["MarkdownLexer"]


class MarkdownLexer(PatternLexer):
    """Markdown lexer. Thread-safe."""

    name = "markdown"
    aliases = ("md", "mdown")
    filenames = ("*.md", "*.markdown", "*.mdown")
    mimetypes = ("text/markdown", "text/x-markdown")

    rules = (
        # Fenced code blocks
        Rule(re.compile(r"```[^`]*```", re.DOTALL), TokenType.STRING_BACKTICK),
        Rule(re.compile(r"~~~[^~]*~~~", re.DOTALL), TokenType.STRING_BACKTICK),
        # Inline code
        Rule(re.compile(r"`[^`\n]+`"), TokenType.STRING_BACKTICK),
        # Headings
        Rule(re.compile(r"^#{1,6}\s+.*$", re.MULTILINE), TokenType.GENERIC_HEADING),
        Rule(re.compile(r"^[^\n]+\n[=]+\s*$", re.MULTILINE), TokenType.GENERIC_HEADING),
        Rule(re.compile(r"^[^\n]+\n[-]+\s*$", re.MULTILINE), TokenType.GENERIC_SUBHEADING),
        # Blockquotes
        Rule(re.compile(r"^>\s+.*$", re.MULTILINE), TokenType.GENERIC_OUTPUT),
        # Lists
        Rule(re.compile(r"^[ \t]*[-*+]\s+", re.MULTILINE), TokenType.KEYWORD),
        Rule(re.compile(r"^[ \t]*\d+\.\s+", re.MULTILINE), TokenType.KEYWORD),
        # Horizontal rules
        Rule(re.compile(r"^[-*_]{3,}\s*$", re.MULTILINE), TokenType.PUNCTUATION),
        # Links
        Rule(re.compile(r"\[([^\]]+)\]\(([^)]+)\)"), TokenType.NAME_ATTRIBUTE),
        Rule(re.compile(r"\[([^\]]+)\]\[([^\]]*)\]"), TokenType.NAME_ATTRIBUTE),
        Rule(re.compile(r"^\[[^\]]+\]:\s+\S+.*$", re.MULTILINE), TokenType.NAME_LABEL),
        # Images
        Rule(re.compile(r"!\[([^\]]*)\]\(([^)]+)\)"), TokenType.NAME_TAG),
        # Emphasis
        Rule(re.compile(r"\*\*[^*]+\*\*"), TokenType.GENERIC_STRONG),
        Rule(re.compile(r"__[^_]+__"), TokenType.GENERIC_STRONG),
        Rule(re.compile(r"\*[^*\n]+\*"), TokenType.GENERIC_EMPH),
        Rule(re.compile(r"_[^_\n]+_"), TokenType.GENERIC_EMPH),
        Rule(re.compile(r"~~[^~]+~~"), TokenType.GENERIC_DELETED),
        # HTML tags (simplified)
        Rule(re.compile(r"<[^>]+>"), TokenType.NAME_TAG),
        # Autolinks
        Rule(re.compile(r"<https?://[^>]+>"), TokenType.NAME_ATTRIBUTE),
        Rule(re.compile(r"<[^@>]+@[^>]+>"), TokenType.NAME_ATTRIBUTE),
        # Regular text
        Rule(re.compile(r"[^\s*_`#>\[\]!<]+"), TokenType.TEXT),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
