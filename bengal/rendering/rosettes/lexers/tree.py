"""Tree/Directory structure lexer for Rosettes.

Thread-safe regex-based tokenizer for ASCII directory tree output.
Highlights directories, files, extensions, and tree structure characters.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["TreeLexer"]


class TreeLexer(PatternLexer):
    """Directory tree lexer.

    Handles ASCII tree output like `tree` command or hand-drawn structures.
    Thread-safe: all state is immutable.

    Example::

        config/
        ├── _default/
        │   ├── site.yaml
        │   └── theme.yaml
        └── environments/
            └── production.yaml
    """

    name = "tree"
    aliases = ("directory", "filetree", "dirtree")
    filenames = ()  # Not typically a file format
    mimetypes = ()

    rules = (
        # Comments at end of line
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Ellipsis for truncated content (before tree chars)
        Rule(re.compile(r"\.\.\."), TokenType.COMMENT_SINGLE),
        # Tree structure characters (box-drawing)
        Rule(re.compile(r"[├└│─┬┼┤┴╭╮╰╯┌┐└┘]+"), TokenType.PUNCTUATION),
        # ASCII tree alternatives
        Rule(re.compile(r"[\|`+\-]+(?=\s)"), TokenType.PUNCTUATION),
        # Directory names (end with /)
        Rule(re.compile(r"[a-zA-Z0-9_\-\.]+/"), TokenType.NAME_CLASS),
        # Hidden directories (start with . and end with /)
        Rule(re.compile(r"\.[a-zA-Z0-9_\-]+/"), TokenType.NAME_CLASS),
        # Files with common config extensions (use lookahead to prevent partial match)
        Rule(
            re.compile(r"[a-zA-Z0-9_\-]+\.(?:ya?ml|toml|json|ini|conf|cfg)(?=\s|$)"),
            TokenType.NAME_ATTRIBUTE,
        ),
        # Files with doc/markup extensions (before code, since html > h, rst > rs)
        Rule(
            re.compile(r"[a-zA-Z0-9_\-]+\.(?:md|rst|txt|html|css|htm|xml|svg)(?=\s|$)"),
            TokenType.STRING,
        ),
        # Files with common code extensions
        Rule(
            re.compile(
                r"[a-zA-Z0-9_\-]+\.(?:py|pyi|js|jsx|ts|tsx|rs|go|c|cpp|h|hpp|java|rb|sh|lua|pl|php|swift|kt|scala|ex|exs|zig|nim|v|mojo)(?=\s|$)"
            ),
            TokenType.NAME_FUNCTION,
        ),
        # Hidden files (dotfiles)
        Rule(re.compile(r"\.[a-zA-Z0-9_\-]+(?:\.[a-zA-Z0-9]+)?(?=\s|$)"), TokenType.NAME_DECORATOR),
        # Other files with extensions (catch-all)
        Rule(re.compile(r"[a-zA-Z0-9_\-]+\.[a-zA-Z0-9]+(?=\s|$)"), TokenType.NAME),
        # Files without extensions
        Rule(re.compile(r"[a-zA-Z0-9_\-]+(?=\s|$)"), TokenType.NAME),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
        # Any remaining characters
        Rule(re.compile(r"."), TokenType.TEXT),
    )
