"""LaTeX/TeX lexer for Rosettes.

Thread-safe regex-based tokenizer for LaTeX and TeX documents.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["LatexLexer"]


class LatexLexer(PatternLexer):
    """LaTeX/TeX lexer. Thread-safe."""

    name = "latex"
    aliases = ("tex", "latex", "context")
    filenames = ("*.tex", "*.latex", "*.ltx", "*.sty", "*.cls")
    mimetypes = ("text/x-tex", "text/x-latex", "application/x-tex", "application/x-latex")

    rules = (
        # Comments
        Rule(re.compile(r"%.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Math modes: $...$ and $$...$$
        Rule(re.compile(r"\$\$[^$]+\$\$", re.DOTALL), TokenType.STRING),
        Rule(re.compile(r"\$[^$\n]+\$"), TokenType.STRING),
        # Math environments: \[...\] and \(...\)
        Rule(re.compile(r"\\\[[^\]]+\\\]", re.DOTALL), TokenType.STRING),
        Rule(re.compile(r"\\\([^)]+\\\)"), TokenType.STRING),
        # Commands with arguments: \command{arg}
        Rule(re.compile(r"\\[a-zA-Z@]+\*?"), TokenType.KEYWORD),
        # Special characters
        Rule(re.compile(r"\\[^a-zA-Z\s]"), TokenType.STRING_ESCAPE),
        # Environment names in begin/end
        Rule(re.compile(r"(?<=\\begin\{)[a-zA-Z*]+(?=\})"), TokenType.NAME_CLASS),
        Rule(re.compile(r"(?<=\\end\{)[a-zA-Z*]+(?=\})"), TokenType.NAME_CLASS),
        # Groups/arguments
        Rule(re.compile(r"[{}]"), TokenType.PUNCTUATION),
        # Optional arguments
        Rule(re.compile(r"[\[\]]"), TokenType.PUNCTUATION),
        # Ampersand (table separator)
        Rule(re.compile(r"&"), TokenType.OPERATOR),
        # Newline commands
        Rule(re.compile(r"\\\\"), TokenType.OPERATOR),
        # Active characters
        Rule(re.compile(r"[~^_]"), TokenType.OPERATOR),
        # Numbers
        Rule(re.compile(r"-?\d+\.?\d*(?:pt|pc|in|bp|cm|mm|dd|cc|sp|ex|em)?"), TokenType.NUMBER),
        # Text
        Rule(re.compile(r"[a-zA-Z]+"), TokenType.TEXT),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
        # Other punctuation
        Rule(re.compile(r"[.,;:!?'\"()/-]"), TokenType.PUNCTUATION),
    )
