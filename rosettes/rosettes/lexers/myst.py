"""MyST Markdown lexer for Rosettes.

Thread-safe regex-based tokenizer for MyST-style directive syntax.
Highlights directive fences, options, and known directive names.

Supports both colon-fence (:::{name}) and backtick-fence (```{name}) styles.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["MystLexer"]

# Known directive names (common MyST/Sphinx/Bengal directives)
# Organized by category for maintainability
_DIRECTIVES = frozenset(
    (
        # Admonitions
        "note",
        "tip",
        "warning",
        "danger",
        "error",
        "info",
        "example",
        "success",
        "caution",
        "seealso",
        "attention",
        "hint",
        "important",
        "admonition",
        # Layout
        "cards",
        "card",
        "child-cards",
        "grid",
        "grid-item-card",
        "tab-set",
        "tabs",
        "tab-item",
        "tab",
        "dropdown",
        "details",
        "container",
        "div",
        "sidebar",
        "margin",
        # Content
        "steps",
        "step",
        "checklist",
        "badge",
        "bdg",
        "button",
        "rubric",
        "glossary",
        "figure",
        "image",
        "table",
        "list-table",
        "csv-table",
        "data-table",
        # Code
        "code-block",
        "code",
        "code-tabs",
        "literalinclude",
        "include",
        # Embeds
        "youtube",
        "vimeo",
        "tiktok",
        "video",
        "audio",
        "gist",
        "codepen",
        "codesandbox",
        "stackblitz",
        "spotify",
        "soundcloud",
        "asciinema",
        "gallery",
        "marimo",
        # Versioning
        "since",
        "versionadded",
        "deprecated",
        "versionremoved",
        "changed",
        "versionchanged",
        # Navigation
        "breadcrumbs",
        "siblings",
        "prev-next",
        "related",
        "toctree",
        "contents",
        # Sphinx/RST compatibility
        "math",
        "eval-rst",
        "raw",
        "only",
        "ifconfig",
        "index",
        "glossary",
        "productionlist",
        "highlight",
        "parsed-literal",
        "epigraph",
        "compound",
        "topic",
        "pull-quote",
        "centered",
        "hlist",
    )
)

# Block context keywords (container directives)
_CONTAINERS = frozenset(
    (
        "cards",
        "tab-set",
        "tabs",
        "steps",
        "grid",
        "dropdown",
        "details",
        "container",
        "div",
        "sidebar",
        "margin",
        "code-tabs",
    )
)


def _extract_directive_name(text: str) -> str | None:
    """Extract directive name from {name} pattern in matched text."""
    # Find {name} in the match
    start = text.find("{")
    end = text.find("}")
    if start != -1 and end != -1 and end > start:
        return text[start + 1 : end]
    return None


def _classify_colon_fence(match: re.Match[str]) -> TokenType:
    """Classify a colon-fence directive opener."""
    text = match.group(0)
    name = _extract_directive_name(text)
    if name:
        if name in _CONTAINERS:
            return TokenType.KEYWORD_DECLARATION
        if name in _DIRECTIVES:
            return TokenType.KEYWORD
    return TokenType.NAME_FUNCTION  # Unknown directive, still highlight


def _classify_backtick_fence(match: re.Match[str]) -> TokenType:
    """Classify a backtick-fence directive opener."""
    text = match.group(0)
    name = _extract_directive_name(text)
    if name:
        if name in _CONTAINERS:
            return TokenType.KEYWORD_DECLARATION
        if name in _DIRECTIVES:
            return TokenType.KEYWORD
    return TokenType.NAME_FUNCTION  # Unknown directive, still highlight


class MystLexer(PatternLexer):
    """MyST Markdown lexer. Thread-safe.

    Highlights MyST directive syntax:
        - Colon fences: :::{note} ... :::
        - Backtick fences: ```{note} ... ```
        - Options: :key: value
        - Directive arguments

    Example:
        :::{note} Optional Title
        :class: my-class

        Content here.
        :::
    """

    name = "myst"
    aliases = ("myst-markdown", "mystmd")
    filenames = ("*.myst.md",)
    mimetypes = ("text/x-myst-markdown",)

    rules = (
        # HTML comments (MyST supports these)
        Rule(re.compile(r"<!--.*?-->", re.DOTALL), TokenType.COMMENT_MULTILINE),
        # Colon-fence directive opener: :::{name} or ::::{name} (nested)
        Rule(
            re.compile(r"^:{3,}\{[a-zA-Z][\w-]*\}.*$", re.MULTILINE),
            _classify_colon_fence,
        ),
        # Backtick-fence directive opener: ```{name}
        Rule(
            re.compile(r"^`{3,}\{[a-zA-Z][\w-]*\}.*$", re.MULTILINE),
            _classify_backtick_fence,
        ),
        # Colon-fence closer: ::: or :::: (nested)
        Rule(re.compile(r"^:{3,}\s*$", re.MULTILINE), TokenType.PUNCTUATION),
        # Backtick-fence closer
        Rule(re.compile(r"^`{3,}\s*$", re.MULTILINE), TokenType.PUNCTUATION),
        # Regular code fence with language (not a directive)
        Rule(re.compile(r"^`{3,}[a-zA-Z][\w]*$", re.MULTILINE), TokenType.PUNCTUATION),
        Rule(re.compile(r"^`{3,}$", re.MULTILINE), TokenType.PUNCTUATION),
        # Option lines: :key: value (at start of line or after whitespace)
        Rule(
            re.compile(r"^\s*:[a-zA-Z][\w-]*:\s*.*$", re.MULTILINE),
            TokenType.NAME_ATTRIBUTE,
        ),
        # Role syntax: {role}`text`
        Rule(re.compile(r"\{([a-zA-Z][\w-]*)\}`[^`]+`"), TokenType.NAME_DECORATOR),
        # Target/anchor: (name)=
        Rule(re.compile(r"^\([a-zA-Z][\w-]*\)=\s*$", re.MULTILINE), TokenType.NAME_LABEL),
        # Cross-reference: {ref}`target`
        Rule(re.compile(r"\{ref\}`[^`]+`"), TokenType.NAME_ATTRIBUTE),
        # Inline math: $...$
        Rule(re.compile(r"\$[^$\n]+\$"), TokenType.STRING),
        # Block math: $$...$$
        Rule(re.compile(r"\$\$[^$]+\$\$", re.DOTALL), TokenType.STRING),
        # Headings
        Rule(re.compile(r"^#{1,6}\s+.*$", re.MULTILINE), TokenType.GENERIC_HEADING),
        # Blockquotes
        Rule(re.compile(r"^>\s+.*$", re.MULTILINE), TokenType.GENERIC_OUTPUT),
        # Unordered lists
        Rule(re.compile(r"^[ \t]*[-*+]\s+", re.MULTILINE), TokenType.PUNCTUATION),
        # Ordered lists
        Rule(re.compile(r"^[ \t]*\d+\.\s+", re.MULTILINE), TokenType.PUNCTUATION),
        # Links: [text](url)
        Rule(re.compile(r"\[([^\]]+)\]\(([^)]+)\)"), TokenType.NAME_ATTRIBUTE),
        # Reference links: [text][ref]
        Rule(re.compile(r"\[([^\]]+)\]\[([^\]]*)\]"), TokenType.NAME_ATTRIBUTE),
        # Images: ![alt](url)
        Rule(re.compile(r"!\[([^\]]*)\]\(([^)]+)\)"), TokenType.NAME_TAG),
        # Bold: **text** or __text__
        Rule(re.compile(r"\*\*[^*]+\*\*"), TokenType.GENERIC_STRONG),
        Rule(re.compile(r"__[^_]+__"), TokenType.GENERIC_STRONG),
        # Italic: *text* or _text_
        Rule(re.compile(r"\*[^*\n]+\*"), TokenType.GENERIC_EMPH),
        Rule(re.compile(r"_[^_\n]+_"), TokenType.GENERIC_EMPH),
        # Strikethrough: ~~text~~
        Rule(re.compile(r"~~[^~]+~~"), TokenType.GENERIC_DELETED),
        # Inline code: `code`
        Rule(re.compile(r"`[^`\n]+`"), TokenType.STRING_BACKTICK),
        # HTML tags
        Rule(re.compile(r"<[^>]+>"), TokenType.NAME_TAG),
        # Regular text
        Rule(re.compile(r"[^\s*_`#>\[\]!<:{$]+"), TokenType.TEXT),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
