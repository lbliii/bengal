"""reStructuredText (RST) lexer for Rosettes.

Thread-safe regex-based tokenizer for reStructuredText markup.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["RstLexer"]

# Common RST directives
_DIRECTIVES = frozenset(
    (
        # Admonitions
        "attention",
        "caution",
        "danger",
        "error",
        "hint",
        "important",
        "note",
        "tip",
        "warning",
        "admonition",
        # Body elements
        "topic",
        "sidebar",
        "line-block",
        "parsed-literal",
        "code",
        "code-block",
        "sourcecode",
        "math",
        "rubric",
        "epigraph",
        "highlights",
        "pull-quote",
        "compound",
        "container",
        # Tables
        "table",
        "csv-table",
        "list-table",
        # Includes
        "contents",
        "include",
        "raw",
        # Images
        "image",
        "figure",
        # Special
        "default-role",
        "role",
        "toctree",
        "index",
        "glossary",
        "only",
        "seealso",
        "versionadded",
        "versionchanged",
        "deprecated",
        # Sphinx-specific
        "module",
        "function",
        "class",
        "method",
        "attribute",
        "data",
        "exception",
        "py:function",
        "py:class",
        "py:method",
        "py:module",
        "literalinclude",
        "automodule",
        "autoclass",
        "autofunction",
    )
)


class RstLexer(PatternLexer):
    """reStructuredText lexer. Thread-safe."""

    name = "rst"
    aliases = ("restructuredtext", "rest", "restx")
    filenames = ("*.rst", "*.rest", "*.restx")
    mimetypes = ("text/x-rst", "text/prs.fallenstein.rst")

    rules = (
        # Comments (lines starting with ..)
        Rule(re.compile(r"^\.\.\s+[^:\n]+$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Directives: .. directive::
        Rule(re.compile(r"^\.\.\s+[a-zA-Z][a-zA-Z0-9_-]*::", re.MULTILINE), TokenType.KEYWORD),
        # Directive options: :option:
        Rule(re.compile(r"^\s+:[a-zA-Z][a-zA-Z0-9_-]*:", re.MULTILINE), TokenType.NAME_ATTRIBUTE),
        # Substitution definitions: |name|
        Rule(re.compile(r"\|[^|]+\|"), TokenType.NAME_VARIABLE),
        # Roles: :role:`text`
        Rule(re.compile(r":[a-zA-Z][a-zA-Z0-9_-]*:`[^`]+`"), TokenType.NAME_FUNCTION),
        # Default role: `text`
        Rule(re.compile(r"`[^`]+`"), TokenType.STRING_BACKTICK),
        # Internal targets: _`target`
        Rule(re.compile(r"_`[^`]+`"), TokenType.NAME_LABEL),
        # Hyperlink targets: .. _name:
        Rule(re.compile(r"^\.\.\s+_[^:]+:", re.MULTILINE), TokenType.NAME_LABEL),
        # Anonymous hyperlinks: __
        Rule(re.compile(r"__\b"), TokenType.NAME_LABEL),
        # Footnotes: [#name]_ or [1]_
        Rule(re.compile(r"\[[#\*]?[a-zA-Z0-9_]*\]_"), TokenType.NAME_TAG),
        # Citations: [name]_
        Rule(re.compile(r"\[[a-zA-Z][a-zA-Z0-9_]*\]_"), TokenType.NAME_TAG),
        # Section titles (underlines)
        Rule(re.compile(r"^[=\-`:'\"~^_*+#<>]{2,}\s*$", re.MULTILINE), TokenType.GENERIC_HEADING),
        # Inline literals: ``text``
        Rule(re.compile(r"``[^`]+``"), TokenType.STRING_BACKTICK),
        # Strong emphasis: **text**
        Rule(re.compile(r"\*\*[^*]+\*\*"), TokenType.GENERIC_STRONG),
        # Emphasis: *text*
        Rule(re.compile(r"\*[^*\n]+\*"), TokenType.GENERIC_EMPH),
        # Bullet lists
        Rule(re.compile(r"^[ \t]*[-*+•‣⁃]\s+", re.MULTILINE), TokenType.PUNCTUATION),
        # Enumerated lists
        Rule(
            re.compile(r"^[ \t]*(?:\d+\.|[a-zA-Z]\.|[ivxIVX]+\.|#\.)\s+", re.MULTILINE),
            TokenType.PUNCTUATION,
        ),
        # Field lists: :field:
        Rule(re.compile(r"^:[a-zA-Z][a-zA-Z0-9_ ]*:", re.MULTILINE), TokenType.NAME_ATTRIBUTE),
        # Option lists
        Rule(re.compile(r"^-{1,2}[a-zA-Z][a-zA-Z0-9-]*", re.MULTILINE), TokenType.NAME),
        # Literal blocks indicator
        Rule(re.compile(r"::\s*$", re.MULTILINE), TokenType.PUNCTUATION),
        # Regular text
        Rule(re.compile(r"[^\s*_`:\[\]|]+"), TokenType.TEXT),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
