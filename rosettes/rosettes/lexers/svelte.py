"""Svelte component lexer for Rosettes.

Thread-safe regex-based tokenizer for Svelte single-file components.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["SvelteLexer"]


class SvelteLexer(PatternLexer):
    """Svelte component lexer. Thread-safe.

    Note: This is a simplified lexer for Svelte template syntax.
    For full SFC support, consider using embedded lexers.
    """

    name = "svelte"
    aliases = ("svelte-html",)
    filenames = ("*.svelte",)
    mimetypes = ("text/x-svelte",)

    rules = (
        # Script and style blocks
        Rule(re.compile(r"<script[^>]*>", re.IGNORECASE), TokenType.NAME_TAG),
        Rule(re.compile(r"</script>", re.IGNORECASE), TokenType.NAME_TAG),
        Rule(re.compile(r"<style[^>]*>", re.IGNORECASE), TokenType.NAME_TAG),
        Rule(re.compile(r"</style>", re.IGNORECASE), TokenType.NAME_TAG),
        # HTML comments
        Rule(re.compile(r"<!--.*?-->", re.DOTALL), TokenType.COMMENT_MULTILINE),
        # Svelte special elements
        Rule(
            re.compile(
                r"<(?:svelte:head|svelte:window|svelte:body|svelte:document|svelte:component|svelte:self|svelte:fragment|svelte:options|svelte:element)\b"
            ),
            TokenType.KEYWORD,
        ),
        Rule(
            re.compile(
                r"</(?:svelte:head|svelte:window|svelte:body|svelte:document|svelte:component|svelte:self|svelte:fragment)>"
            ),
            TokenType.KEYWORD,
        ),
        # Control flow blocks
        Rule(re.compile(r"\{#if\b"), TokenType.KEYWORD),
        Rule(re.compile(r"\{:else if\b"), TokenType.KEYWORD),
        Rule(re.compile(r"\{:else\}"), TokenType.KEYWORD),
        Rule(re.compile(r"\{/if\}"), TokenType.KEYWORD),
        Rule(re.compile(r"\{#each\b"), TokenType.KEYWORD),
        Rule(re.compile(r"\{:then\b"), TokenType.KEYWORD),
        Rule(re.compile(r"\{:catch\b"), TokenType.KEYWORD),
        Rule(re.compile(r"\{/each\}"), TokenType.KEYWORD),
        Rule(re.compile(r"\{#await\b"), TokenType.KEYWORD),
        Rule(re.compile(r"\{/await\}"), TokenType.KEYWORD),
        Rule(re.compile(r"\{#key\b"), TokenType.KEYWORD),
        Rule(re.compile(r"\{/key\}"), TokenType.KEYWORD),
        Rule(re.compile(r"\{#snippet\b"), TokenType.KEYWORD),
        Rule(re.compile(r"\{/snippet\}"), TokenType.KEYWORD),
        Rule(re.compile(r"\{@render\b"), TokenType.KEYWORD),
        Rule(re.compile(r"\{@html\b"), TokenType.KEYWORD),
        Rule(re.compile(r"\{@debug\b"), TokenType.KEYWORD),
        Rule(re.compile(r"\{@const\b"), TokenType.KEYWORD),
        # Expression braces
        Rule(re.compile(r"\{"), TokenType.PUNCTUATION),
        Rule(re.compile(r"\}"), TokenType.PUNCTUATION),
        # Directives: on:, bind:, class:, style:, use:, transition:, animate:, in:, out:
        Rule(
            re.compile(
                r"\b(?:on|bind|class|style|use|transition|animate|in|out|let):[a-zA-Z_][a-zA-Z0-9_]*"
            ),
            TokenType.NAME_DECORATOR,
        ),
        # Shorthand directives
        Rule(
            re.compile(r"\b(?:on|bind|class|style|use|transition|animate|in|out|let):"),
            TokenType.NAME_DECORATOR,
        ),
        # HTML tags
        Rule(re.compile(r"</[a-zA-Z][a-zA-Z0-9-]*>"), TokenType.NAME_TAG),
        Rule(re.compile(r"<[a-zA-Z][a-zA-Z0-9-]*"), TokenType.NAME_TAG),
        Rule(re.compile(r"/>"), TokenType.NAME_TAG),
        Rule(re.compile(r">"), TokenType.NAME_TAG),
        # Attributes
        Rule(re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_-]*(?==)"), TokenType.NAME_ATTRIBUTE),
        # Strings
        Rule(re.compile(r'"[^"]*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^']*'"), TokenType.STRING_SINGLE),
        # Template literals (basic)
        Rule(re.compile(r"`[^`]*`"), TokenType.STRING_BACKTICK),
        # Numbers
        Rule(re.compile(r"-?\d+\.?\d*"), TokenType.NUMBER),
        # Operators
        Rule(re.compile(r"[=+\-*/%!<>&|?:]"), TokenType.OPERATOR),
        # Identifiers
        Rule(re.compile(r"\$[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_VARIABLE),  # Stores
        Rule(re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"), TokenType.NAME),
        # Punctuation
        Rule(re.compile(r"[(),;\[\]]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
        # Text
        Rule(re.compile(r"[^\s<>{}\[\]()]+"), TokenType.TEXT),
    )
