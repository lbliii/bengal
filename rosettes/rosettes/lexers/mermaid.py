"""Mermaid diagram lexer for Rosettes.

Thread-safe regex-based tokenizer for Mermaid diagram-as-code syntax.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["MermaidLexer"]

# Mermaid diagram types
_DIAGRAM_TYPES = frozenset(
    (
        "graph",
        "flowchart",
        "sequenceDiagram",
        "classDiagram",
        "stateDiagram",
        "stateDiagram-v2",
        "erDiagram",
        "journey",
        "gantt",
        "pie",
        "quadrantChart",
        "requirementDiagram",
        "gitGraph",
        "mindmap",
        "timeline",
        "zenuml",
        "sankey-beta",
        "xychart-beta",
        "block-beta",
    )
)

# Mermaid keywords
_KEYWORDS = frozenset(
    (
        # Directions
        "TB",
        "TD",
        "BT",
        "RL",
        "LR",
        # Sequence diagram
        "participant",
        "actor",
        "activate",
        "deactivate",
        "Note",
        "note",
        "over",
        "right",
        "left",
        "of",
        "loop",
        "alt",
        "else",
        "opt",
        "par",
        "and",
        "critical",
        "option",
        "break",
        "rect",
        "end",
        "autonumber",
        "off",
        # Class diagram
        "class",
        "namespace",
        "callback",
        "link",
        "click",
        "cssClass",
        "direction",
        # State diagram
        "state",
        "as",
        # ER diagram
        "erDiagram",
        # Gantt
        "dateFormat",
        "axisFormat",
        "todayMarker",
        "title",
        "excludes",
        "includes",
        "section",
        "done",
        "active",
        "crit",
        "milestone",
        "after",
        # Pie
        "showData",
        # Git
        "commit",
        "branch",
        "checkout",
        "merge",
        "cherry-pick",
        # General
        "subgraph",
        "style",
        "classDef",
        "linkStyle",
        "accTitle",
        "accDescr",
        "init",
        "theme",
    )
)


def _classify_word(match: re.Match[str]) -> TokenType:
    """Classify Mermaid identifiers."""
    word = match.group(0)
    if word in _DIAGRAM_TYPES:
        return TokenType.KEYWORD_DECLARATION
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    return TokenType.NAME


class MermaidLexer(PatternLexer):
    """Mermaid diagram lexer. Thread-safe."""

    name = "mermaid"
    aliases = ("mmd",)
    filenames = ("*.mmd", "*.mermaid")
    mimetypes = ("text/x-mermaid",)

    rules = (
        # Comments
        Rule(re.compile(r"%%.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Directive: %%{init: ...}%%
        Rule(re.compile(r"%%\{.*?\}%%", re.DOTALL), TokenType.COMMENT_PREPROC),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_SINGLE),
        # Node text in brackets/parens: [text], (text), {text}, ((text)), [[text]]
        Rule(re.compile(r"\[\[[^\]]+\]\]"), TokenType.STRING),  # Subroutine
        Rule(re.compile(r"\(\([^)]+\)\)"), TokenType.STRING),  # Circle
        Rule(re.compile(r"\[\([^)]+\)\]"), TokenType.STRING),  # Stadium
        Rule(re.compile(r"\(\[[^\]]+\]\)"), TokenType.STRING),  # Cylinder
        Rule(re.compile(r"\[\{[^}]+\}\]"), TokenType.STRING),  # Hexagon
        Rule(re.compile(r"\{\{[^}]+\}\}"), TokenType.STRING),  # Rhombus
        Rule(re.compile(r"\[/[^/]+/\]"), TokenType.STRING),  # Parallelogram
        Rule(re.compile(r"\[\\[^\\]+\\\]"), TokenType.STRING),  # Parallelogram alt
        Rule(re.compile(r">\s*[^\]]+\s*\]"), TokenType.STRING),  # Asymmetric
        Rule(re.compile(r"\[[^\]]+\]"), TokenType.STRING),  # Rectangle
        Rule(re.compile(r"\([^)]+\)"), TokenType.STRING),  # Rounded
        Rule(re.compile(r"\{[^}]+\}"), TokenType.STRING),  # Diamond
        # Arrow/edge definitions
        Rule(
            re.compile(r"-->|==>|-.->|---->|====|---|===|~~~|--x|--o|<-->|o--o|x--x"),
            TokenType.OPERATOR,
        ),
        Rule(re.compile(r"-\.->|===>|-->>|<<--"), TokenType.OPERATOR),
        # Pipe for edge labels: |text|
        Rule(re.compile(r"\|[^|]+\|"), TokenType.STRING),
        # Class/style definitions: :::className
        Rule(re.compile(r":::[a-zA-Z][a-zA-Z0-9_-]*"), TokenType.NAME_CLASS),
        # IDs and node names
        Rule(re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*"), _classify_word),
        # Numbers (for Gantt dates, etc.)
        Rule(re.compile(r"\d{4}-\d{2}-\d{2}"), TokenType.LITERAL_DATE),
        Rule(re.compile(r"\d+[dwmyhms]?"), TokenType.NUMBER),
        # Punctuation
        Rule(re.compile(r"[;:,]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
        # Other
        Rule(re.compile(r"[^\s\[\](){}<>|:;,\"']+"), TokenType.TEXT),
    )
