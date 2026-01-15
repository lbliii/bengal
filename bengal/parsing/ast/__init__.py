"""
AST types and utilities for Bengal parsing.

Exports commonly used AST node types, helpers, and transforms.
"""

from __future__ import annotations

from bengal.parsing.ast.transforms import (
    add_baseurl_to_ast,
    normalize_md_links_in_ast,
    transform_links_in_ast,
)
from bengal.parsing.ast.types import (
    ASTNode,
    BaseNode,
    BlockquoteNode,
    CodeBlockNode,
    CodeSpanNode,
    EmphasisNode,
    HardBreakNode,
    HeadingNode,
    ImageNode,
    LinkNode,
    ListItemNode,
    ListNode,
    ParagraphNode,
    RawHTMLNode,
    SoftBreakNode,
    StrongNode,
    TextNode,
    ThematicBreakNode,
    get_heading_level,
    get_node_text,
    is_code_block,
    is_heading,
    is_image,
    is_link,
    is_raw_html,
    is_text,
)
from bengal.parsing.ast.utils import (
    extract_links_from_ast,
    extract_plain_text,
    extract_toc_from_ast,
    generate_heading_id,
    walk_ast,
)

__all__ = [
    "ASTNode",
    "BaseNode",
    "BlockquoteNode",
    "CodeBlockNode",
    "CodeSpanNode",
    "EmphasisNode",
    "HardBreakNode",
    "HeadingNode",
    "ImageNode",
    "LinkNode",
    "ListItemNode",
    "ListNode",
    "ParagraphNode",
    "RawHTMLNode",
    "SoftBreakNode",
    "StrongNode",
    "TextNode",
    "ThematicBreakNode",
    "add_baseurl_to_ast",
    "extract_links_from_ast",
    "extract_plain_text",
    "extract_toc_from_ast",
    "generate_heading_id",
    "get_heading_level",
    "get_node_text",
    "is_code_block",
    "is_heading",
    "is_image",
    "is_link",
    "is_raw_html",
    "is_text",
    "normalize_md_links_in_ast",
    "transform_links_in_ast",
    "walk_ast",
]
