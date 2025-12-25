"""AsciiDoc lexer for Rosettes.

Thread-safe regex-based tokenizer for AsciiDoc markup.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["AsciidocLexer"]


class AsciidocLexer(PatternLexer):
    """AsciiDoc lexer. Thread-safe."""

    name = "asciidoc"
    aliases = ("adoc", "asc")
    filenames = ("*.adoc", "*.asciidoc", "*.asc")
    mimetypes = ("text/x-asciidoc",)

    rules = (
        # Comments
        Rule(re.compile(r"^//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(
            re.compile(r"^////\n.*?\n////\s*$", re.MULTILINE | re.DOTALL),
            TokenType.COMMENT_MULTILINE,
        ),
        # Document title (level 0)
        Rule(re.compile(r"^=\s+.+$", re.MULTILINE), TokenType.GENERIC_HEADING),
        # Section titles
        Rule(re.compile(r"^={2,6}\s+.+$", re.MULTILINE), TokenType.GENERIC_HEADING),
        # Alternate section syntax (underlines)
        Rule(re.compile(r"^[=\-~^+]{4,}\s*$", re.MULTILINE), TokenType.GENERIC_HEADING),
        # Block titles: .Title
        Rule(re.compile(r"^\.[^\s].*$", re.MULTILINE), TokenType.NAME_LABEL),
        # Attributes: :name: value
        Rule(re.compile(r"^:[a-zA-Z][a-zA-Z0-9_-]*!?:", re.MULTILINE), TokenType.NAME_ATTRIBUTE),
        # Attribute references: {name}
        Rule(re.compile(r"\{[a-zA-Z][a-zA-Z0-9_-]*\}"), TokenType.NAME_VARIABLE),
        # Anchors: [[id]] or [#id]
        Rule(re.compile(r"\[\[[^\]]+\]\]"), TokenType.NAME_LABEL),
        Rule(re.compile(r"\[#[^\]]+\]"), TokenType.NAME_LABEL),
        # Block delimiters
        Rule(re.compile(r"^[-=*_+/.]{4,}\s*$", re.MULTILINE), TokenType.PUNCTUATION),
        # Admonition labels
        Rule(
            re.compile(r"^(?:NOTE|TIP|IMPORTANT|WARNING|CAUTION):", re.MULTILINE), TokenType.KEYWORD
        ),
        # Inline macros: macro:target[attrs]
        Rule(re.compile(r"[a-zA-Z]+:[^\s\[]+\[[^\]]*\]"), TokenType.NAME_FUNCTION),
        # Block macros: macro::target[attrs]
        Rule(re.compile(r"^[a-zA-Z]+::[^\s\[]*\[[^\]]*\]", re.MULTILINE), TokenType.NAME_FUNCTION),
        # Image/Include: image::, include::
        Rule(
            re.compile(r"^(?:image|include|video|audio)::[^\s\[]+\[[^\]]*\]", re.MULTILINE),
            TokenType.KEYWORD,
        ),
        # Source blocks: [source,lang]
        Rule(re.compile(r"^\[source[^\]]*\]", re.MULTILINE), TokenType.KEYWORD),
        # Other block attributes: [name]
        Rule(re.compile(r"^\[[^\]]+\]\s*$", re.MULTILINE), TokenType.NAME_ATTRIBUTE),
        # Strong: *text* or **text**
        Rule(re.compile(r"\*\*[^*]+\*\*"), TokenType.GENERIC_STRONG),
        Rule(re.compile(r"(?<!\*)\*[^*\s][^*]*[^*\s]\*(?!\*)"), TokenType.GENERIC_STRONG),
        # Emphasis: _text_ or __text__
        Rule(re.compile(r"__[^_]+__"), TokenType.GENERIC_EMPH),
        Rule(re.compile(r"(?<!_)_[^_\s][^_]*[^_\s]_(?!_)"), TokenType.GENERIC_EMPH),
        # Monospace: `text` or ``text``
        Rule(re.compile(r"``[^`]+``"), TokenType.STRING_BACKTICK),
        Rule(re.compile(r"`[^`\n]+`"), TokenType.STRING_BACKTICK),
        # Inline literal: +text+
        Rule(re.compile(r"\+[^+\n]+\+"), TokenType.STRING_BACKTICK),
        # Superscript: ^text^
        Rule(re.compile(r"\^[^^]+\^"), TokenType.GENERIC_EMPH),
        # Subscript: ~text~
        Rule(re.compile(r"~[^~]+~"), TokenType.GENERIC_EMPH),
        # Links: link:url[text], http://...
        Rule(re.compile(r"(?:https?|ftp|irc)://[^\s\[\]]+"), TokenType.NAME_ATTRIBUTE),
        Rule(re.compile(r"link:[^\s\[]+\[[^\]]*\]"), TokenType.NAME_ATTRIBUTE),
        # Cross-references: <<id>> or <<id,text>>
        Rule(re.compile(r"<<[^>]+>>"), TokenType.NAME_TAG),
        # Footnotes: footnote:[text]
        Rule(re.compile(r"footnote(?:ref)?:\[[^\]]+\]"), TokenType.NAME_TAG),
        # Lists
        Rule(re.compile(r"^[ \t]*[*\-]+ ", re.MULTILINE), TokenType.PUNCTUATION),
        Rule(re.compile(r"^[ \t]*\.+ ", re.MULTILINE), TokenType.PUNCTUATION),
        Rule(re.compile(r"^[ \t]*\d+\. ", re.MULTILINE), TokenType.PUNCTUATION),
        # Callouts: <1>, <2>
        Rule(re.compile(r"<\d+>"), TokenType.NAME_TAG),
        # Text
        Rule(re.compile(r"[^\s*_`+\^~<>\[\]{:]+"), TokenType.TEXT),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
