"""HTML lexer for Rosettes.

Thread-safe regex-based tokenizer for HTML markup.
Note: This is a simplified lexer that doesn't handle nested languages.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["HtmlLexer"]


class HtmlLexer(PatternLexer):
    """HTML lexer.

    Handles HTML5 syntax including tags, attributes, comments, and entities.
    Does NOT highlight embedded CSS/JS (falls back to plain text for those).
    Thread-safe: all state is immutable.
    """

    name = "html"
    aliases = ("htm", "xhtml")
    filenames = ("*.html", "*.htm", "*.xhtml")
    mimetypes = ("text/html", "application/xhtml+xml")

    rules = (
        # Comments
        Rule(re.compile(r"<!--[\s\S]*?-->"), TokenType.COMMENT_MULTILINE),
        # DOCTYPE
        Rule(re.compile(r"<!DOCTYPE[^>]*>", re.IGNORECASE), TokenType.COMMENT_PREPROC),
        # CDATA
        Rule(re.compile(r"<!\[CDATA\[[\s\S]*?\]\]>"), TokenType.COMMENT_PREPROC),
        # Script and style tags (simplified - content as raw text)
        Rule(
            re.compile(r"<(script|style)\b[^>]*>[\s\S]*?</\1>", re.IGNORECASE),
            TokenType.STRING_OTHER,
        ),
        # End tags
        Rule(re.compile(r"</[a-zA-Z][a-zA-Z0-9-]*\s*>"), TokenType.NAME_TAG),
        # Opening tag start (just the < and tag name)
        Rule(re.compile(r"<[a-zA-Z][a-zA-Z0-9-]*"), TokenType.NAME_TAG),
        # Tag close (including self-closing)
        Rule(re.compile(r"/?>"), TokenType.NAME_TAG),
        # Attribute values (quoted) - these can appear anywhere after tag open
        Rule(re.compile(r'"[^"]*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^']*'"), TokenType.STRING_SINGLE),
        # Attribute names
        Rule(re.compile(r"[a-zA-Z_:][a-zA-Z0-9_:.-]*"), TokenType.NAME_ATTRIBUTE),
        # Equals sign
        Rule(re.compile(r"="), TokenType.PUNCTUATION),
        # Entity references
        Rule(re.compile(r"&[a-zA-Z]+;"), TokenType.NAME_ENTITY),
        Rule(re.compile(r"&#[0-9]+;"), TokenType.NAME_ENTITY),
        Rule(re.compile(r"&#x[0-9a-fA-F]+;"), TokenType.NAME_ENTITY),
        # Whitespace (must come before text to be more specific)
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
        # Text content (between tags) - less greedy, stops at special chars
        Rule(re.compile(r"[^<>&\s\"'=/]+"), TokenType.TEXT),
    )
