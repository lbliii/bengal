"""Diff/Patch lexer for Rosettes.

Thread-safe regex-based tokenizer for unified diff format.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["DiffLexer"]


class DiffLexer(PatternLexer):
    """Unified diff lexer.

    Handles unified diff format as produced by `diff -u` or `git diff`.
    Thread-safe: all state is immutable.
    """

    name = "diff"
    aliases = ("patch", "udiff")
    filenames = ("*.diff", "*.patch")
    mimetypes = ("text/x-diff", "text/x-patch")

    rules = (
        # File headers
        Rule(re.compile(r"^---.*$", re.MULTILINE), TokenType.GENERIC_DELETED),
        Rule(re.compile(r"^\+\+\+.*$", re.MULTILINE), TokenType.GENERIC_INSERTED),
        # Index and diff command lines
        Rule(re.compile(r"^diff\s.*$", re.MULTILINE), TokenType.GENERIC_HEADING),
        Rule(re.compile(r"^index\s.*$", re.MULTILINE), TokenType.GENERIC_SUBHEADING),
        Rule(re.compile(r"^new file mode.*$", re.MULTILINE), TokenType.GENERIC_SUBHEADING),
        Rule(re.compile(r"^deleted file mode.*$", re.MULTILINE), TokenType.GENERIC_SUBHEADING),
        Rule(re.compile(r"^similarity index.*$", re.MULTILINE), TokenType.GENERIC_SUBHEADING),
        Rule(re.compile(r"^rename from.*$", re.MULTILINE), TokenType.GENERIC_SUBHEADING),
        Rule(re.compile(r"^rename to.*$", re.MULTILINE), TokenType.GENERIC_SUBHEADING),
        Rule(re.compile(r"^copy from.*$", re.MULTILINE), TokenType.GENERIC_SUBHEADING),
        Rule(re.compile(r"^copy to.*$", re.MULTILINE), TokenType.GENERIC_SUBHEADING),
        # Hunk headers
        Rule(re.compile(r"^@@.*@@.*$", re.MULTILINE), TokenType.GENERIC_SUBHEADING),
        # Added lines
        Rule(re.compile(r"^\+.*$", re.MULTILINE), TokenType.GENERIC_INSERTED),
        # Removed lines
        Rule(re.compile(r"^-.*$", re.MULTILINE), TokenType.GENERIC_DELETED),
        # Context lines
        Rule(re.compile(r"^ .*$", re.MULTILINE), TokenType.TEXT),
        # No newline at end of file
        Rule(re.compile(r"^\\ No newline.*$", re.MULTILINE), TokenType.GENERIC_STRONG),
        # Binary file indicators
        Rule(re.compile(r"^Binary files.*$", re.MULTILINE), TokenType.GENERIC_OUTPUT),
        # Whitespace and other
        Rule(re.compile(r"\n"), TokenType.WHITESPACE),
        Rule(re.compile(r".+"), TokenType.TEXT),
    )
