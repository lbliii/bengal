"""XML lexer for Rosettes.

Thread-safe regex-based tokenizer for XML documents.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["XmlLexer"]


class XmlLexer(PatternLexer):
    """XML lexer. Thread-safe."""

    name = "xml"
    aliases = ("xsl", "xslt", "rss", "svg")
    filenames = ("*.xml", "*.xsl", "*.xslt", "*.rss", "*.svg", "*.plist")
    mimetypes = ("text/xml", "application/xml", "image/svg+xml")

    rules = (
        # Comments
        Rule(re.compile(r"<!--[\s\S]*?-->"), TokenType.COMMENT_MULTILINE),
        # CDATA
        Rule(re.compile(r"<!\[CDATA\[[\s\S]*?\]\]>"), TokenType.STRING),
        # DOCTYPE
        Rule(re.compile(r"<!DOCTYPE[^>]*>", re.IGNORECASE), TokenType.COMMENT_PREPROC),
        # XML declaration
        Rule(re.compile(r"<\?xml[^?]*\?>"), TokenType.COMMENT_PREPROC),
        # Processing instructions
        Rule(re.compile(r"<\?[^?]*\?>"), TokenType.COMMENT_PREPROC),
        # End tags
        Rule(re.compile(r"</[a-zA-Z_:][\w:.-]*\s*>"), TokenType.NAME_TAG),
        # Start/empty tags
        Rule(re.compile(r"<[a-zA-Z_:][\w:.-]*"), TokenType.NAME_TAG),
        Rule(re.compile(r"/>"), TokenType.NAME_TAG),
        Rule(re.compile(r">"), TokenType.NAME_TAG),
        # Attributes
        Rule(re.compile(r"[a-zA-Z_:][\w:.-]*(?=\s*=)"), TokenType.NAME_ATTRIBUTE),
        # Attribute values
        Rule(re.compile(r'"[^"]*"'), TokenType.STRING),
        Rule(re.compile(r"'[^']*'"), TokenType.STRING),
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
