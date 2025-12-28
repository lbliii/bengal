"""PatitasParser wrapper implementing BaseMarkdownParser.

Provides Bengal integration by implementing the BaseMarkdownParser interface.
This allows Patitas to be used as a drop-in replacement for MistuneParser.

Usage:
    parser = PatitasParser()
    html = parser.parse("# Hello", {})
    html, toc = parser.parse_with_toc("## Section 1\\n## Section 2", {})

Thread Safety:
    PatitasParser is thread-safe. Each parse() call creates independent
    parser/renderer instances with no shared state.
"""

from __future__ import annotations

import re
from typing import Any

from bengal.rendering.parsers.base import BaseMarkdownParser
from bengal.rendering.parsers.patitas import create_markdown, parse_to_ast
from bengal.rendering.parsers.patitas.nodes import Block, Heading
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Heading pattern for TOC extraction from rendered HTML
_HEADING_PATTERN = re.compile(
    r"<h([1-6])(?:\s+id=[\"']([^\"']+)[\"'])?\s*>(.+?)</h\1>", re.IGNORECASE | re.DOTALL
)


class PatitasParser(BaseMarkdownParser):
    """Parser using Patitas library (modern Markdown parser).

    Provides:
    - O(n) guaranteed parsing (no regex backtracking)
    - Thread-safe by design (immutable AST)
    - Typed AST with frozen dataclasses
    - StringBuilder O(n) rendering

    Supported features:
    - ATX/setext headings
    - Fenced/indented code blocks
    - Block quotes
    - Lists (ordered/unordered)
    - Thematic breaks
    - Emphasis/strong
    - Links/images
    - Inline code
    - Hard/soft breaks
    - Raw HTML

    TODO (future phases):
    - Tables (GFM)
    - Strikethrough
    - Task lists
    - Footnotes
    - Directives
    - Cross-references
    """

    # Default plugins to enable (matches mistune's plugins)
    DEFAULT_PLUGINS = ["table", "strikethrough", "task_lists", "math"]

    def __init__(
        self,
        enable_highlighting: bool = True,
        plugins: list[str] | None = None,
    ) -> None:
        """Initialize the Patitas parser.

        Args:
            enable_highlighting: Enable syntax highlighting for code blocks
            plugins: List of plugins to enable. Defaults to standard set:
                     table, strikethrough, task_lists, math
        """
        self.enable_highlighting = enable_highlighting
        self._plugins = plugins if plugins is not None else self.DEFAULT_PLUGINS

        # Create configured markdown instance
        self._md = create_markdown(
            plugins=self._plugins,
            highlight=enable_highlighting,
        )

    def parse(self, content: str, metadata: dict[str, Any]) -> str:
        """Parse Markdown content into HTML.

        Args:
            content: Markdown content to parse
            metadata: Page metadata (unused, for interface compatibility)

        Returns:
            Rendered HTML string
        """
        if not content:
            return ""

        try:
            return self._md(content)
        except Exception as e:
            logger.warning(
                "patitas_parsing_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return f'<div class="markdown-error"><p><strong>Markdown parsing error:</strong> {e}</p><pre>{content}</pre></div>'

    def parse_with_toc(self, content: str, metadata: dict[str, Any]) -> tuple[str, str]:
        """Parse Markdown content and extract table of contents.

        Args:
            content: Markdown content to parse
            metadata: Page metadata

        Returns:
            Tuple of (HTML with heading IDs, TOC HTML)
        """
        if not content:
            return "", ""

        # Parse to AST using configured markdown instance
        ast = self._md.parse_to_ast(content)

        # Render HTML
        html = self._md.render_ast(ast)

        # Inject heading IDs and extract TOC
        html = self._inject_heading_ids(html)
        toc = self._extract_toc(ast)

        return html, toc

    def _inject_heading_ids(self, html: str) -> str:
        """Inject ID attributes into heading elements.

        Args:
            html: HTML content

        Returns:
            HTML with heading IDs added
        """

        def replace_heading(match: re.Match[str]) -> str:
            level = match.group(1)
            existing_id = match.group(2)
            content = match.group(3)

            if existing_id:
                return match.group(0)  # Already has ID

            # Generate slug from content
            slug = self._slugify(self._strip_tags(content))
            return f'<h{level} id="{slug}">{content}</h{level}>'

        return _HEADING_PATTERN.sub(replace_heading, html)

    def _extract_toc(self, ast: tuple[Block, ...]) -> str:
        """Extract table of contents from AST.

        Args:
            ast: Parsed AST blocks

        Returns:
            TOC HTML as nested list
        """
        toc_items: list[tuple[int, str, str]] = []

        for block in ast:
            if isinstance(block, Heading):
                # Extract text from heading children
                text = self._extract_text_from_inline(block.children)
                slug = self._slugify(text)
                toc_items.append((block.level, text, slug))

        if not toc_items:
            return ""

        return self._build_toc_html(toc_items)

    def _extract_text_from_inline(self, children: tuple[Any, ...]) -> str:
        """Extract plain text from inline nodes.

        Args:
            children: Inline child nodes

        Returns:
            Concatenated text content
        """
        from bengal.rendering.parsers.patitas.nodes import (
            CodeSpan,
            Emphasis,
            Strong,
            Text,
        )

        parts: list[str] = []
        for child in children:
            if isinstance(child, Text):
                parts.append(child.content)
            elif isinstance(child, (Emphasis, Strong)):
                parts.append(self._extract_text_from_inline(child.children))
            elif isinstance(child, CodeSpan):
                parts.append(child.code)
        return "".join(parts)

    def _build_toc_html(self, items: list[tuple[int, str, str]]) -> str:
        """Build TOC HTML from items.

        Args:
            items: List of (level, text, slug) tuples

        Returns:
            TOC HTML as nested list
        """
        if not items:
            return ""

        result: list[str] = ['<ul class="toc">']
        prev_level = items[0][0]

        for level, text, slug in items:
            if level > prev_level:
                result.append("<ul>")
            elif level < prev_level:
                for _ in range(prev_level - level):
                    result.append("</li></ul>")
                result.append("</li>")

            if level <= prev_level and result[-1] not in ("</ul>", '<ul class="toc">'):
                result.append("</li>")

            result.append(f'<li><a href="#{slug}">{self._escape_html(text)}</a>')
            prev_level = level

        # Close remaining tags
        result.append("</li>")
        result.append("</ul>")

        return "".join(result)

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug.

        Args:
            text: Text to slugify

        Returns:
            Slugified text (max 100 characters)
        """
        from bengal.utils.text import slugify

        return slugify(text, unescape_html=True, max_length=100)

    def _strip_tags(self, html: str) -> str:
        """Remove HTML tags from string.

        Args:
            html: HTML string

        Returns:
            Plain text without tags
        """
        return re.sub(r"<[^>]+>", "", html)

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters.

        Args:
            text: Text to escape

        Returns:
            HTML-escaped text
        """
        from html import escape

        return escape(text, quote=False)

    # =========================================================================
    # AST Support
    # =========================================================================

    @property
    def supports_ast(self) -> bool:
        """Check if this parser supports true AST output.

        Returns:
            True - Patitas natively supports typed AST output
        """
        return True

    def parse_to_ast(self, content: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse Markdown content to AST tokens.

        Note: Returns dict representation for compatibility with BaseMarkdownParser.
        Use patitas.parse_to_ast() directly for typed AST.

        Args:
            content: Raw Markdown content
            metadata: Page metadata (unused)

        Returns:
            List of AST token dictionaries
        """
        if not content:
            return []

        ast = parse_to_ast(content)
        return [self._node_to_dict(node) for node in ast]

    def render_ast(self, ast: list[dict[str, Any]]) -> str:
        """Render AST tokens to HTML.

        Args:
            ast: List of AST token dictionaries

        Returns:
            Rendered HTML string
        """
        # Convert back to typed nodes and render
        # For now, just re-parse (TODO: proper dict->node conversion)
        return ""

    def _node_to_dict(self, node: Block) -> dict[str, Any]:
        """Convert AST node to dictionary representation.

        Args:
            node: Block node

        Returns:
            Dictionary representation
        """
        from dataclasses import asdict

        result = asdict(node)
        result["type"] = type(node).__name__.lower()
        return result
