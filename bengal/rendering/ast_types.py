"""Type definitions for markdown AST nodes (mistune-compatible)."""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


class BaseNode(TypedDict, total=False):
    """Common fields for all AST nodes."""

    children: list[ASTNode]
    attrs: dict[str, str]


class TextNode(TypedDict):
    """Plain text content."""

    type: Literal["text"]
    raw: str


class CodeSpanNode(TypedDict):
    """Inline code."""

    type: Literal["codespan"]
    raw: str


class HeadingNode(TypedDict):
    """Heading (h1-h6)."""

    type: Literal["heading"]
    level: int
    children: list[ASTNode]
    attrs: NotRequired[dict[str, str]]


class ParagraphNode(TypedDict):
    """Paragraph block."""

    type: Literal["paragraph"]
    children: list[ASTNode]


class CodeBlockNode(TypedDict):
    """Fenced code block."""

    type: Literal["block_code"]
    raw: str
    info: str | None  # Language hint


class ListNode(TypedDict):
    """Ordered or unordered list."""

    type: Literal["list"]
    ordered: bool
    children: list[ListItemNode]


class ListItemNode(TypedDict):
    """List item."""

    type: Literal["list_item"]
    children: list[ASTNode]


class BlockquoteNode(TypedDict):
    """Blockquote."""

    type: Literal["block_quote"]
    children: list[ASTNode]


class LinkNode(TypedDict):
    """Hyperlink."""

    type: Literal["link"]
    url: str
    title: str | None
    children: list[ASTNode]


class ImageNode(TypedDict):
    """Image."""

    type: Literal["image"]
    src: str
    alt: str
    title: str | None


class EmphasisNode(TypedDict):
    """Emphasis (italic)."""

    type: Literal["emphasis"]
    children: list[ASTNode]


class StrongNode(TypedDict):
    """Strong (bold)."""

    type: Literal["strong"]
    children: list[ASTNode]


class ThematicBreakNode(TypedDict):
    """Horizontal rule / thematic break."""

    type: Literal["thematic_break"]


class SoftBreakNode(TypedDict):
    """Soft line break."""

    type: Literal["softbreak"]


class HardBreakNode(TypedDict):
    """Hard line break."""

    type: Literal["linebreak"]


# Discriminated union of all node types
type ASTNode = (
    TextNode
    | CodeSpanNode
    | HeadingNode
    | ParagraphNode
    | CodeBlockNode
    | ListNode
    | ListItemNode
    | BlockquoteNode
    | LinkNode
    | ImageNode
    | EmphasisNode
    | StrongNode
    | ThematicBreakNode
    | SoftBreakNode
    | HardBreakNode
)


# Type guards for common patterns
def is_heading(node: ASTNode) -> bool:
    """Type guard for heading nodes."""
    return node.get("type") == "heading"


def is_text(node: ASTNode) -> bool:
    """Type guard for text nodes."""
    return node.get("type") == "text"


def is_code_block(node: ASTNode) -> bool:
    """Type guard for code block nodes."""
    return node.get("type") == "block_code"


def get_heading_level(node: ASTNode) -> int | None:
    """Get heading level if node is a heading."""
    if is_heading(node):
        return node.get("level")  # type: ignore[return-value]
    return None


def get_node_text(node: ASTNode) -> str:
    """Extract text content from a node."""
    if "raw" in node:
        return node["raw"]  # type: ignore[typeddict-item]
    return ""
