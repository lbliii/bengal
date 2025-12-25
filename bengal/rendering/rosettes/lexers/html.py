"""HTML lexer for Rosettes.

Thread-safe regex-based tokenizer for HTML markup.
Note: This is a simplified lexer that doesn't handle nested languages.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

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
        # Self-closing tags
        Rule(re.compile(r"<[a-zA-Z][a-zA-Z0-9-]*(?:\s+[^>]*)?/>"), TokenType.NAME_TAG),
        # Opening tags with attributes
        Rule(re.compile(r"<[a-zA-Z][a-zA-Z0-9-]*"), TokenType.NAME_TAG),
        Rule(re.compile(r">"), TokenType.NAME_TAG),
        # Attribute names
        Rule(re.compile(r"[a-zA-Z_:][a-zA-Z0-9_:.-]*(?=\s*=)"), TokenType.NAME_ATTRIBUTE),
        Rule(re.compile(r"[a-zA-Z_:][a-zA-Z0-9_:.-]*(?=[\s/>])"), TokenType.NAME_ATTRIBUTE),
        # Attribute values
        Rule(re.compile(r'"[^"]*"'), TokenType.STRING),
        Rule(re.compile(r"'[^']*'"), TokenType.STRING),
        # Unquoted attribute values
        Rule(re.compile(r"=[^\s/>]+"), TokenType.STRING),
        # Entity references
        Rule(re.compile(r"&[a-zA-Z]+;"), TokenType.NAME_ENTITY),
        Rule(re.compile(r"&#[0-9]+;"), TokenType.NAME_ENTITY),
        Rule(re.compile(r"&#x[0-9a-fA-F]+;"), TokenType.NAME_ENTITY),
        # Text content
        Rule(re.compile(r"[^<>&]+"), TokenType.TEXT),
        # Punctuation
        Rule(re.compile(r"[=]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
