"""
Extraction utilities for Patitas Document ASTs.

Provides plain text, link, and TOC extraction from Patitas frozen
dataclass ASTs using the BaseVisitor pattern. These replace the
TypedDict-based extraction in utils.py when the page carries a
Patitas Document as its canonical AST.

Thread Safety:
    Each visitor instance accumulates mutable state. Create a new
    instance per extraction call (not shared across threads).

"""

from __future__ import annotations

import re
from typing import Any

from bengal.utils.primitives.text import slugify_id

__all__ = [
    "extract_links_from_document",
    "extract_plain_text_from_document",
    "extract_toc_from_document",
    "render_document_to_html",
]


def _is_patitas_document(obj: Any) -> bool:
    """Check if an object is a Patitas Document without importing at module level."""
    return type(obj).__name__ == "Document" and hasattr(obj, "children") and hasattr(obj, "location")


def extract_plain_text_from_document(doc: Any) -> str:
    """Extract plain text from a Patitas Document AST.

    Walks the AST tree and concatenates all text content, adding
    appropriate spacing for block elements.

    Args:
        doc: Patitas Document (frozen dataclass)

    Returns:
        Plain text content suitable for search indexing
    """
    if not _is_patitas_document(doc):
        return ""

    try:
        from patitas.nodes import (
            BlockQuote,
            CodeSpan,
            Document,
            Emphasis,
            FencedCode,
            Heading,
            IndentedCode,
            Link,
            List,
            ListItem,
            Paragraph,
            SoftBreak,
            Strikethrough,
            Strong,
            Table,
            TableCell,
            TableRow,
            Text,
        )
    except ImportError:
        return ""

    parts: list[str] = []

    def _walk(node: Any) -> None:
        match node:
            case Text(content=content):
                parts.append(content)
            case CodeSpan(code=code):
                parts.append(code)
            case SoftBreak():
                parts.append(" ")
            case FencedCode():
                # Include code content for search indexing
                if hasattr(node, "content_override") and node.content_override:
                    parts.append(node.content_override)
                parts.append("\n")
            case IndentedCode(code=code):
                parts.append(code)
                parts.append("\n")
            case Document(children=children) | Paragraph(children=children) | Heading(children=children) | BlockQuote(children=children) | ListItem(children=children):
                for child in children:
                    _walk(child)
                parts.append("\n")
            case Emphasis(children=children) | Strong(children=children) | Strikethrough(children=children) | Link(children=children):
                for child in children:
                    _walk(child)
            case List(items=items):
                for item in items:
                    _walk(item)
                parts.append("\n")
            case Table(head=head, body=body):
                for row in head:
                    _walk(row)
                for row in body:
                    _walk(row)
                parts.append("\n")
            case TableRow(cells=cells):
                for cell in cells:
                    _walk(cell)
                    parts.append(" ")
            case TableCell(children=children):
                for child in children:
                    _walk(child)
            case _:
                # Leaf nodes or unknown — skip
                pass

    _walk(doc)

    text = "".join(parts)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_links_from_document(doc: Any) -> list[str]:
    """Extract all link URLs from a Patitas Document AST.

    Args:
        doc: Patitas Document (frozen dataclass)

    Returns:
        List of link URL strings
    """
    if not _is_patitas_document(doc):
        return []

    try:
        from patitas.nodes import (
            BlockQuote,
            Document,
            Emphasis,
            Heading,
            Link,
            List,
            ListItem,
            Paragraph,
            Strikethrough,
            Strong,
            Table,
            TableCell,
            TableRow,
        )
    except ImportError:
        return []

    links: list[str] = []

    def _walk(node: Any) -> None:
        match node:
            case Link(url=url, children=children):
                if url:
                    links.append(url)
                for child in children:
                    _walk(child)
            case Document(children=children) | Paragraph(children=children) | Heading(children=children) | BlockQuote(children=children) | ListItem(children=children):
                for child in children:
                    _walk(child)
            case Emphasis(children=children) | Strong(children=children) | Strikethrough(children=children):
                for child in children:
                    _walk(child)
            case List(items=items):
                for item in items:
                    _walk(item)
            case Table(head=head, body=body):
                for row in head:
                    _walk(row)
                for row in body:
                    _walk(row)
            case TableRow(cells=cells):
                for cell in cells:
                    _walk(cell)
            case TableCell(children=children):
                for child in children:
                    _walk(child)
            case _:
                pass

    _walk(doc)
    return links


def extract_toc_from_document(doc: Any) -> list[dict[str, Any]]:
    """Extract TOC structure from a Patitas Document AST.

    Args:
        doc: Patitas Document (frozen dataclass)

    Returns:
        List of TOC items: [{"id": str, "title": str, "level": int}, ...]
    """
    if not _is_patitas_document(doc):
        return []

    try:
        from patitas.nodes import (
            CodeSpan,
            Emphasis,
            Heading,
            Link,
            Strikethrough,
            Strong,
            Text,
        )
    except ImportError:
        return []

    toc_items: list[dict[str, Any]] = []

    def _text_of(node: Any) -> str:
        """Extract text content from an inline node tree."""
        match node:
            case Text(content=content):
                return content
            case CodeSpan(code=code):
                return code
            case Emphasis(children=children) | Strong(children=children) | Strikethrough(children=children) | Link(children=children):
                return "".join(_text_of(c) for c in children)
            case _:
                return ""

    for child in doc.children:
        if isinstance(child, Heading):
            title = "".join(_text_of(c) for c in child.children)
            heading_id = child.explicit_id or slugify_id(title)
            # Level mapping: H2 -> level 1, H3 -> level 2, etc.
            toc_level = max(1, child.level - 1)
            toc_items.append({
                "id": heading_id,
                "title": title,
                "level": toc_level,
            })

    return toc_items


def render_document_to_html(doc: Any, source: str = "") -> str:
    """Render a Patitas Document AST to HTML.

    Uses Patitas' own HtmlRenderer for correct output.

    Args:
        doc: Patitas Document (frozen dataclass)
        source: Original source text (for zero-copy code extraction)

    Returns:
        HTML string
    """
    if not _is_patitas_document(doc):
        return ""

    try:
        from patitas import render
    except ImportError:
        return ""

    return render(doc, source=source)
