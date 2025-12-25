"""Vue Single File Component lexer for Rosettes.

Thread-safe regex-based tokenizer for Vue SFC templates.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["VueLexer"]


class VueLexer(PatternLexer):
    """Vue Single File Component lexer. Thread-safe.

    Note: This is a simplified lexer for Vue template syntax.
    For full SFC support with embedded CSS/JS, consider using embedded lexers.
    """

    name = "vue"
    aliases = ("vuejs", "vue-html", "vue-template")
    filenames = ("*.vue",)
    mimetypes = ("text/x-vue", "application/x-vue")

    rules = (
        # Template, script, style blocks
        Rule(re.compile(r"<template[^>]*>", re.IGNORECASE), TokenType.NAME_TAG),
        Rule(re.compile(r"</template>", re.IGNORECASE), TokenType.NAME_TAG),
        Rule(re.compile(r"<script[^>]*>", re.IGNORECASE), TokenType.NAME_TAG),
        Rule(re.compile(r"</script>", re.IGNORECASE), TokenType.NAME_TAG),
        Rule(re.compile(r"<style[^>]*>", re.IGNORECASE), TokenType.NAME_TAG),
        Rule(re.compile(r"</style>", re.IGNORECASE), TokenType.NAME_TAG),
        # HTML comments
        Rule(re.compile(r"<!--.*?-->", re.DOTALL), TokenType.COMMENT_MULTILINE),
        # Vue directives: v-if, v-for, v-bind, v-on, v-model, v-slot, v-show, etc.
        Rule(re.compile(r"v-[a-zA-Z][a-zA-Z0-9-]*"), TokenType.NAME_DECORATOR),
        # Shorthand for v-bind: :prop
        Rule(re.compile(r":[a-zA-Z][a-zA-Z0-9-]*"), TokenType.NAME_DECORATOR),
        # Shorthand for v-on: @event
        Rule(re.compile(r"@[a-zA-Z][a-zA-Z0-9-]*(?:\.[a-zA-Z]+)*"), TokenType.NAME_DECORATOR),
        # Shorthand for v-slot: #slot
        Rule(re.compile(r"#[a-zA-Z][a-zA-Z0-9-]*"), TokenType.NAME_DECORATOR),
        # Modifiers: .prevent, .stop, .native
        Rule(re.compile(r"\.[a-zA-Z][a-zA-Z0-9]*(?=[\s=>])"), TokenType.NAME_ATTRIBUTE),
        # Mustache interpolation: {{ expression }}
        Rule(re.compile(r"\{\{"), TokenType.PUNCTUATION),
        Rule(re.compile(r"\}\}"), TokenType.PUNCTUATION),
        # HTML tags
        Rule(re.compile(r"</[a-zA-Z][a-zA-Z0-9-]*>"), TokenType.NAME_TAG),
        Rule(re.compile(r"<[a-zA-Z][a-zA-Z0-9-]*"), TokenType.NAME_TAG),
        Rule(re.compile(r"/>"), TokenType.NAME_TAG),
        Rule(re.compile(r">"), TokenType.NAME_TAG),
        # HTML/component attributes
        Rule(re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_-]*(?==)"), TokenType.NAME_ATTRIBUTE),
        # Strings
        Rule(re.compile(r'"[^"]*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^']*'"), TokenType.STRING_SINGLE),
        # Template literals
        Rule(re.compile(r"`[^`]*`"), TokenType.STRING_BACKTICK),
        # Numbers
        Rule(re.compile(r"-?\d+\.?\d*"), TokenType.NUMBER),
        # JavaScript keywords (commonly used in templates)
        Rule(
            re.compile(r"\b(?:true|false|null|undefined|this|new|typeof|instanceof|in|of)\b"),
            TokenType.KEYWORD,
        ),
        # Operators
        Rule(re.compile(r"===|!==|==|!=|<=|>=|&&|\|\||[+\-*/%<>=!?:]"), TokenType.OPERATOR),
        # Identifiers
        Rule(re.compile(r"\$[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_VARIABLE),  # $refs, $emit
        Rule(re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"), TokenType.NAME),
        # Punctuation
        Rule(re.compile(r"[(),;\[\].]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
        # Text
        Rule(re.compile(r"[^\s<>{}\[\]()]+"), TokenType.TEXT),
    )
