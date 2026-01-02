"""Lexer operating modes and constants.

This module defines the finite state machine modes for the lexer
and constant sets used for HTML block classification.
"""

from __future__ import annotations

from enum import Enum, auto


class LexerMode(Enum):
    """Lexer operating modes.

    The lexer switches between modes based on context:
    - BLOCK: Between blocks, scanning for block starts
    - CODE_FENCE: Inside fenced code block
    - DIRECTIVE: Inside directive block
    - HTML_BLOCK: Inside HTML block (types 1-7)
    """

    BLOCK = auto()  # Between blocks
    CODE_FENCE = auto()  # Inside fenced code block
    DIRECTIVE = auto()  # Inside directive block
    HTML_BLOCK = auto()  # Inside HTML block


# CommonMark HTML block type 1 tags (case-insensitive)
HTML_BLOCK_TYPE1_TAGS = frozenset({"pre", "script", "style", "textarea"})

# CommonMark HTML block type 6 tags (case-insensitive)
# These are "block-level" HTML tags that end on blank line
HTML_BLOCK_TYPE6_TAGS = frozenset(
    {
        "address",
        "article",
        "aside",
        "base",
        "basefont",
        "blockquote",
        "body",
        "caption",
        "center",
        "col",
        "colgroup",
        "dd",
        "details",
        "dialog",
        "dir",
        "div",
        "dl",
        "dt",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "frame",
        "frameset",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "head",
        "header",
        "hr",
        "html",
        "iframe",
        "legend",
        "li",
        "link",
        "main",
        "menu",
        "menuitem",
        "nav",
        "noframes",
        "ol",
        "optgroup",
        "option",
        "p",
        "param",
        "search",
        "section",
        "summary",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "title",
        "tr",
        "track",
        "ul",
    }
)
