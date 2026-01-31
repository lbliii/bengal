"""
AST utilities for tree walking and extraction.

This module provides utilities for working with markdown AST nodes:
- walk_ast: Recursive generator over all nodes
- extract_toc_from_ast: Extract TOC structure from headings
- extract_links_from_ast: Extract all link URLs
- extract_plain_text: Extract plain text for search/LLM

These utilities enable O(n) traversal operations that replace regex-based
extraction on rendered HTML.

Performance:
AST walks have better constant factors than regex:
- No regex compilation overhead
- No string allocation from re.sub
- Cache-friendly sequential access

Related:
- bengal/parsing/ast/types.py: ASTNode type definitions
- bengal/core/page/content.py: PageContentMixin uses these utilities
- bengal/parsing/backends/mistune/ast.py: AST parsing

See Also:
- plan/drafted/rfc-ast-content-pipeline.md: RFC for AST-based pipeline

"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from bengal.parsing.ast.types import ASTNode, is_heading, is_link, is_text
from bengal.utils.primitives.text import slugify


def walk_ast(ast: list[ASTNode]) -> Iterator[ASTNode]:
    """
    Recursively walk all nodes in an AST.

    Yields each node in depth-first order, enabling O(n) traversal
    for extraction operations.

    Args:
        ast: Root-level AST nodes

    Yields:
        Each ASTNode in the tree

    Example:
            >>> ast = [{"type": "heading", "level": 1, "children": [{"type": "text", "raw": "Hello"}]}]
            >>> nodes = list(walk_ast(ast))
            >>> len(nodes)
        2

    """
    for node in ast:
        yield node
        # Check for children in various formats
        children = node.get("children")
        if children and isinstance(children, list):
            yield from walk_ast(children)


def generate_heading_id(node: ASTNode) -> str:
    """
    Generate a URL-friendly ID from a heading node.

    Extracts text content and converts to a slug suitable for anchor links.
    Uses the shared slugify utility from bengal.utils.primitives.text.

    Args:
        node: A heading node

    Returns:
        URL-friendly slug (e.g., "getting-started")

    Example:
            >>> node = {"type": "heading", "level": 1, "children": [{"type": "text", "raw": "Getting Started!"}]}
            >>> generate_heading_id(node)
            'getting-started'

    """
    text = extract_text_from_node(node)
    return slugify(text, unescape_html=True, max_length=100)


def extract_text_from_node(node: ASTNode) -> str:
    """
    Extract all text content from a single node and its children.

    Args:
        node: AST node to extract text from

    Returns:
        Concatenated text content

    """
    parts: list[str] = []

    if "raw" in node:
        parts.append(node["raw"])  # type: ignore[typeddict-item]

    children = node.get("children")
    if children and isinstance(children, list):
        for child in children:
            parts.append(extract_text_from_node(child))

    return "".join(parts)


def extract_toc_from_ast(ast: list[ASTNode]) -> list[dict[str, Any]]:
    """
    Extract TOC structure from AST (replaces HTMLParser in toc.py).

    Walks the AST and extracts all heading nodes, building a structured
    table of contents.

    Args:
        ast: Root-level AST nodes

    Returns:
        List of TOC items with id, title, and level

    Example:
            >>> ast = [
            ...     {"type": "heading", "level": 2, "children": [{"type": "text", "raw": "Introduction"}]},
            ...     {"type": "heading", "level": 3, "children": [{"type": "text", "raw": "Background"}]},
            ... ]
            >>> toc = extract_toc_from_ast(ast)
            >>> toc[0]
        {'id': 'introduction', 'title': 'Introduction', 'level': 1}

    """
    toc_items: list[dict[str, Any]] = []

    for node in walk_ast(ast):
        if is_heading(node):
            # Get level from node or attrs
            level = node.get("level")
            if level is None:
                attrs = node.get("attrs", {})
                level = attrs.get("level", 1)

            title = extract_text_from_node(node)
            heading_id = generate_heading_id(node)

            # Level mapping: H2 -> level 1, H3 -> level 2, etc.
            # (H1 is typically page title, excluded from TOC)
            toc_level = max(1, level - 1)

            toc_items.append(
                {
                    "id": heading_id,
                    "title": title,
                    "level": toc_level,
                }
            )

    return toc_items


def extract_links_from_ast(ast: list[ASTNode]) -> list[str]:
    """
    Extract all links from AST.

    Args:
        ast: Root-level AST nodes

    Returns:
        List of link URLs

    Example:
            >>> ast = [
            ...     {"type": "paragraph", "children": [
            ...         {"type": "link", "url": "/docs/", "children": [{"type": "text", "raw": "Docs"}]}
            ...     ]}
            ... ]
            >>> links = extract_links_from_ast(ast)
            >>> links
        ['/docs/']

    """
    links: list[str] = []

    for node in walk_ast(ast):
        if is_link(node):
            # Try direct url field first (our typed LinkNode)
            url = node.get("url")

            # Fallback: Mistune 3.x stores URL in attrs.url
            if not url:
                attrs = node.get("attrs", {})
                if isinstance(attrs, dict):
                    url = attrs.get("url", "")

            if url:
                links.append(url)

    return links


def extract_plain_text(ast: list[ASTNode]) -> str:
    """
    Extract plain text for search indexing (replaces regex strip in content.py).

    Walks the AST and concatenates all text content, adding appropriate
    spacing for block elements.

    Args:
        ast: Root-level AST nodes

    Returns:
        Plain text content

    Example:
            >>> ast = [
            ...     {"type": "heading", "level": 1, "children": [{"type": "text", "raw": "Hello"}]},
            ...     {"type": "paragraph", "children": [{"type": "text", "raw": "World"}]},
            ... ]
            >>> text = extract_plain_text(ast)
            >>> text
            'Hello\nWorld'

    """
    parts: list[str] = []

    def _walk_for_text(nodes: list[ASTNode]) -> None:
        for node in nodes:
            node_type = node.get("type", "")

            # Extract raw text
            if is_text(node) or node_type == "codespan":
                raw = node.get("raw", "")
                if raw:
                    parts.append(raw)
            elif node_type == "block_code":
                # Include code block content for search
                raw = node.get("raw", "")
                if raw:
                    parts.append(raw)

            # Recurse into children
            children = node.get("children")
            if children and isinstance(children, list):
                _walk_for_text(children)

            # Add spacing for block elements
            if node_type in ("paragraph", "heading", "list", "block_code", "block_quote"):
                parts.append("\n")

    _walk_for_text(ast)

    # Join and normalize whitespace
    text = "".join(parts)
    # Collapse multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
