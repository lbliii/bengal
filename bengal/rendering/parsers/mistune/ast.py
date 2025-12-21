"""
AST parsing and rendering support for Mistune.

Provides true AST output via Mistune's built-in AST support:
- parse_to_ast: Parse markdown to AST tokens
- render_ast: Render AST tokens to HTML
- parse_with_ast: Get AST, HTML, and TOC together
"""

from __future__ import annotations

from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def create_ast_parser(mistune_module: Any, base_plugins: list[Any] | None) -> Any:
    """
    Create an AST parser instance.

    IMPORTANT: Uses the same plugin set as the HTML parser so directive tokens
    are present in the returned token stream.

    Args:
        mistune_module: The imported mistune module
        base_plugins: List of base plugins to include

    Returns:
        Mistune markdown instance configured for AST output
    """
    plugins = list(base_plugins) if isinstance(base_plugins, list) else []
    return mistune_module.create_markdown(
        renderer=None,  # None means AST output
        plugins=plugins,
    )


def parse_to_ast(
    content: str,
    ast_parser: Any,
) -> list[dict[str, Any]]:
    """
    Parse Markdown content to AST tokens.

    Uses Mistune's built-in AST support by parsing with renderer=None.
    The AST is a list of token dictionaries representing the document structure.

    Performance:
        - Parsing cost is similar to parse() (same tokenization)
        - AST is more memory-efficient than HTML for caching
        - Multiple outputs can be generated from single AST

    Args:
        content: Raw Markdown content
        ast_parser: Pre-configured AST parser instance

    Returns:
        List of AST token dictionaries

    Example:
        >>> parse_to_ast("# Hello\\n\\nWorld", ast_parser)
        [
            {'type': 'heading', 'attrs': {'level': 1}, 'children': [...]},
            {'type': 'paragraph', 'children': [{'type': 'text', 'raw': 'World'}]}
        ]
    """
    if not content:
        return []

    try:
        # Parse returns AST when renderer=None
        ast = ast_parser(content)
        return ast if ast else []
    except Exception as e:
        logger.warning(
            "mistune_ast_parsing_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        return []


def render_ast(ast: list[dict[str, Any]]) -> str:
    """
    Render AST tokens to HTML.

    Uses Mistune's renderer to convert AST tokens back to HTML.
    This enables parse-once, render-many patterns.

    Args:
        ast: List of AST token dictionaries from parse_to_ast()

    Returns:
        Rendered HTML string

    Example:
        >>> ast = parse_to_ast("# Hello", ast_parser)
        >>> html = render_ast(ast)
        >>> print(html)
        '<h1>Hello</h1>'
    """
    if not ast:
        return ""

    try:
        # Mistune 3.x requires HTMLRenderer instance and BlockState
        from mistune.core import BlockState
        from mistune.renderers.html import HTMLRenderer

        renderer = HTMLRenderer()
        state = BlockState()
        return renderer(ast, state)
    except Exception as e:
        logger.warning(
            "mistune_ast_rendering_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        return ""
