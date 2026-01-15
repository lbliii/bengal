"""
AST-level transformations for link manipulation.

This module provides type-safe AST transformations that replace regex-based
HTML manipulation:

- transform_links_in_ast: Generic link transformer
- normalize_md_links_in_ast: Convert .md links to clean URLs
- add_baseurl_to_ast: Prepend baseurl to internal links

Benefits over regex:
- No risk of matching href inside code blocks
- Handles edge cases (quotes, escapes) correctly
- Type-safe: operates on structured data
- Better constant factors (no regex compilation)

Related:
- bengal/rendering/link_transformer.py: Legacy regex-based transforms
- bengal/parsing/ast/types.py: ASTNode type definitions
- bengal/parsing/ast/utils.py: AST walking utilities

See Also:
- plan/drafted/rfc-ast-content-pipeline.md: RFC for AST-based pipeline

"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from bengal.parsing.ast.types import ASTNode


def transform_links_in_ast(
    ast: list[ASTNode],
    transformer: Callable[[str], str],
) -> list[ASTNode]:
    """
    Transform links at AST level (replaces regex in link_transformer.py).
    
    Benefits over regex:
    - No risk of matching href inside code blocks
    - Handles edge cases (quotes, escapes) correctly
    - Type-safe: operates on structured data
    
    Args:
        ast: Root-level AST nodes
        transformer: Function that takes a URL and returns transformed URL
    
    Returns:
        New AST with transformed links
    
    Example:
            >>> def add_prefix(url: str) -> str:
            ...     return f"/prefix{url}" if url.startswith("/") else url
            >>> ast = [{"type": "link", "url": "/docs/", "children": []}]
            >>> transformed = transform_links_in_ast(ast, add_prefix)
            >>> transformed[0]["url"]
            '/prefix/docs/'
        
    """

    def transform_node(node: ASTNode) -> ASTNode:
        node_type = node.get("type", "")

        # Transform link nodes
        if node_type == "link":
            # Get URL from direct field or attrs
            url = node.get("url")  # type: ignore[union-attr]
            if url is None:
                attrs = node.get("attrs", {})
                if isinstance(attrs, dict):
                    url = attrs.get("url", "")

            if url:
                new_url = transformer(url)
                # Create new node with transformed URL
                new_node: dict[str, Any] = dict(node)
                if "url" in node:
                    new_node["url"] = new_url
                else:
                    # Handle attrs.url format
                    new_attrs = dict(node.get("attrs", {}))
                    new_attrs["url"] = new_url
                    new_node["attrs"] = new_attrs

                # Transform children if present
                children = node.get("children")
                if children and isinstance(children, list):
                    new_node["children"] = [transform_node(c) for c in children]

                return new_node  # type: ignore[return-value]

        # Transform image src
        if node_type == "image":
            src = node.get("src")  # type: ignore[union-attr]
            if src:
                new_src = transformer(src)
                new_node = dict(node)
                new_node["src"] = new_src
                return new_node  # type: ignore[return-value]

        # Recurse into children for other node types
        children = node.get("children")
        if children and isinstance(children, list):
            new_node = dict(node)
            new_node["children"] = [transform_node(c) for c in children]
            return new_node  # type: ignore[return-value]

        return node

    return [transform_node(n) for n in ast]


def normalize_md_links_in_ast(ast: list[ASTNode]) -> list[ASTNode]:
    """
    Convert .md links to clean URLs at AST level.
    
    Transforms:
    - ./folder-mode.md  ->  ./folder-mode/
    - ../other.md       ->  ../other/
    - sibling.md        ->  sibling/
    - ./_index.md       ->  ./
    - path/page.md      ->  path/page/
    
    Args:
        ast: Root-level AST nodes
    
    Returns:
        New AST with normalized links
    
    Example:
            >>> ast = [{"type": "link", "url": "./guide.md", "children": []}]
            >>> transformed = normalize_md_links_in_ast(ast)
            >>> transformed[0]["url"]
            './guide/'
        
    """

    def normalize(url: str) -> str:
        if not url.endswith(".md"):
            return url

        # Handle _index.md -> parent directory
        if url.endswith("/_index.md"):
            clean_path = url[:-10] + "/"  # Strip /_index.md, add /
            if clean_path == "/":
                clean_path = "./"
            return clean_path
        if url.endswith("_index.md"):
            # Just "_index.md" with no path prefix
            return "./"
        if url.endswith("/index.md"):
            clean_path = url[:-9] + "/"  # Strip /index.md, add /
            return clean_path
        if url.endswith("index.md"):
            # Just "index.md" with no path prefix
            return "./"

        # Regular .md file -> strip extension, add trailing slash
        return url[:-3] + "/"

    return transform_links_in_ast(ast, normalize)


def add_baseurl_to_ast(ast: list[ASTNode], baseurl: str) -> list[ASTNode]:
    """
    Prepend baseurl to internal links at AST level.
    
    Only transforms:
    - Links starting with "/" (internal absolute paths)
    - Does NOT transform external URLs (http://, https://)
    - Does NOT transform anchors (#section)
    - Does NOT transform relative paths (../other, ./sibling)
    - Does NOT transform links that already have baseurl
    
    Args:
        ast: Root-level AST nodes
        baseurl: Base URL prefix (e.g., "/bengal")
    
    Returns:
        New AST with baseurl-prefixed internal links
    
    Example:
            >>> ast = [{"type": "link", "url": "/docs/guide/", "children": []}]
            >>> transformed = add_baseurl_to_ast(ast, "/bengal")
            >>> transformed[0]["url"]
            '/bengal/docs/guide/'
        
    """
    if not baseurl:
        return ast

    # Normalize baseurl (strip trailing slash)
    baseurl = baseurl.rstrip("/")

    def add_base(url: str) -> str:
        # Skip if not internal absolute path
        if not url.startswith("/"):
            return url

        # Skip external URLs (shouldn't happen for /-prefixed, but be safe)
        if url.startswith(("//", "http://", "https://")):
            return url

        # Skip if already has baseurl
        if url.startswith(baseurl + "/") or url == baseurl:
            return url

        return f"{baseurl}{url}"

    return transform_links_in_ast(ast, add_base)


def transform_ast_for_output(
    ast: list[ASTNode],
    baseurl: str | None = None,
    normalize_md: bool = True,
) -> list[ASTNode]:
    """
    Apply all output transformations to AST.
    
    Convenience function that applies:
    1. .md link normalization (if normalize_md=True)
    2. baseurl prefixing (if baseurl provided)
    
    Args:
        ast: Root-level AST nodes
        baseurl: Optional base URL prefix
        normalize_md: Whether to normalize .md links (default True)
    
    Returns:
        Transformed AST ready for rendering
        
    """
    result = ast

    if normalize_md:
        result = normalize_md_links_in_ast(result)

    if baseurl:
        result = add_baseurl_to_ast(result, baseurl)

    return result
