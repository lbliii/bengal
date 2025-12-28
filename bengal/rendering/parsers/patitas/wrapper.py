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

    Supported features (via plugins):
    - Tables (GFM)
    - Strikethrough
    - Task lists
    - Math (inline and block)
    - Cross-references ([[link]] syntax)
    """

    # Default plugins to enable (matches mistune's plugins)
    DEFAULT_PLUGINS = ["table", "strikethrough", "task_lists", "math", "footnotes"]

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

        # Cross-reference support (enabled via enable_cross_references)
        self._xref_enabled = False
        self._xref_plugin: Any | None = None

        # Variable substitution plugin (stored for placeholder restoration)
        self._var_plugin: Any | None = None

    def parse(self, content: str, metadata: dict[str, Any]) -> str:
        """Parse Markdown content into HTML.

        Args:
            content: Markdown content to parse
            metadata: Page metadata (used for cross-reference context)

        Returns:
            Rendered HTML string
        """
        if not content:
            return ""

        try:
            html = self._md(content)

            # Post-process cross-references if enabled
            if self._xref_enabled and self._xref_plugin:
                # Set current page version for version-aware anchor resolution
                page_version = (
                    metadata.get("version") or metadata.get("_version") if metadata else None
                )
                self._xref_plugin.current_version = page_version

                # Set current page source path for cross-version dependency tracking
                source_path = metadata.get("_source_path") if metadata else None
                if source_path:
                    from pathlib import Path

                    self._xref_plugin.current_source_page = (
                        Path(source_path) if isinstance(source_path, str) else source_path
                    )
                else:
                    self._xref_plugin.current_source_page = None

                html = self._xref_plugin._substitute_xrefs(html)

            return html
        except Exception as e:
            source_path = metadata.get("_source_path", "unknown")
            logger.warning(
                "patitas_parsing_error",
                error=str(e),
                error_type=type(e).__name__,
                path=source_path,
                hint="Verify that the source buffer is being passed correctly for ZCLH zero-copy extraction."
                if "source" in str(e) and isinstance(e, TypeError)
                else None,
            )
            return f'<div class="markdown-error"><p><strong>Markdown parsing error in {source_path}:</strong> {e}</p><pre>{content[:500]}...</pre></div>'

    def parse_with_toc(self, content: str, metadata: dict[str, Any]) -> tuple[str, str]:
        """Parse Markdown content and extract table of contents.

        Args:
            content: Markdown content to parse
            metadata: Page metadata (includes source path for cross-reference context)

        Returns:
            Tuple of (HTML with heading IDs, TOC HTML)
        """
        if not content:
            return "", ""

        # Parse to AST using configured markdown instance
        ast = self._md.parse_to_ast(content)

        # Render HTML
        html = self._md.render_ast(ast, content)

        # Post-process cross-references if enabled
        html = self._apply_post_processing(html, metadata)

        # Inject heading IDs and extract TOC
        html = self._inject_heading_ids(html)
        toc = self._extract_toc(ast)

        return html, toc

    def parse_with_context(
        self, content: str, metadata: dict[str, Any], context: dict[str, Any]
    ) -> str:
        """Parse Markdown with variable substitution support.

        Enables {{ page.title }}, {{ site.baseurl }}, etc. in markdown content.
        Uses VariableSubstitutionPlugin for preprocessing and restoration.

        Args:
            content: Markdown content to parse
            metadata: Page metadata
            context: Variable context (page, site, config)

        Returns:
            Rendered HTML with variables substituted
        """
        if not content:
            return ""

        from bengal.rendering.plugins import VariableSubstitutionPlugin

        # Create plugin instance for this page and store for pipeline access
        self._var_plugin = VariableSubstitutionPlugin(context)
        var_plugin = self._var_plugin

        try:
            # 1. Preprocess: handle {{/* escaped syntax */}}
            content = var_plugin.preprocess(content)

            # 2. Parse & Substitute in ONE pass (the "window thing")
            # The Lexer handles variable substitution as it scans lines.
            # This is O(n) with zero extra passes or AST walks.
            html = self._md(content, text_transformer=var_plugin.substitute_variables)

            # 3. Restore placeholders: restore BENGALESCAPED placeholders
            html = var_plugin.restore_placeholders(html)

            # 4. Apply other post-processing (cross-references, etc.)
            html = self._apply_post_processing(html, metadata)

            return html

        except Exception as e:
            source_path = metadata.get("_source_path", "unknown")
            logger.warning(
                "patitas_parsing_error_with_context",
                error=str(e),
                error_type=type(e).__name__,
                path=source_path,
                hint="Variable substitution or zero-copy handoff may be missing required arguments."
                if isinstance(e, TypeError)
                else None,
            )
            return f'<div class="markdown-error"><p><strong>Markdown parsing error in {source_path}:</strong> {e}</p><pre>{content[:500]}...</pre></div>'

    def parse_with_toc_and_context(
        self, content: str, metadata: dict[str, Any], context: dict[str, Any]
    ) -> tuple[str, str]:
        """Parse Markdown with variable substitution and extract TOC.

        Args:
            content: Markdown content to parse
            metadata: Page metadata
            context: Variable context (page, site, config)

        Returns:
            Tuple of (HTML with heading IDs, TOC HTML)
        """
        if not content:
            return "", ""

        from bengal.rendering.plugins import VariableSubstitutionPlugin

        # Create plugin instance for this page and store for pipeline access
        self._var_plugin = VariableSubstitutionPlugin(context)
        var_plugin = self._var_plugin

        try:
            # 1. Preprocess: handle {{/* escaped syntax */}}
            content = var_plugin.preprocess(content)

            # 2. Parse & Substitute in ONE pass (the "window thing")
            ast = self._md.parse_to_ast(content, text_transformer=var_plugin.substitute_variables)

            # 3. Render to HTML
            html = self._md.render_ast(ast, content)

            # 4. Restore placeholders
            html = var_plugin.restore_placeholders(html)

            # 5. Apply other post-processing
            html = self._apply_post_processing(html, metadata)

            # 6. Inject heading IDs and extract TOC
            html = self._inject_heading_ids(html)
            toc = self._extract_toc(ast)

            return html, toc

        except Exception as e:
            source_path = metadata.get("_source_path", "unknown")
            logger.warning(
                "patitas_parsing_error_with_toc_and_context",
                error=str(e),
                error_type=type(e).__name__,
                path=source_path,
                hint="TOC extraction with ZCLH requires the source buffer to be passed to render_ast()."
                if "source" in str(e) and isinstance(e, TypeError)
                else None,
            )
            return (
                f'<div class="markdown-error"><p><strong>Markdown parsing error in {source_path}:</strong> {e}</p><pre>{content[:500]}...</pre></div>',
                "",
            )

    def _apply_post_processing(self, html: str, metadata: dict[str, Any]) -> str:
        """Apply common post-processing to HTML output."""
        # Post-process cross-references if enabled
        if self._xref_enabled and self._xref_plugin:
            # Set current page version for version-aware anchor resolution
            page_version = metadata.get("version") or metadata.get("_version") if metadata else None
            self._xref_plugin.current_version = page_version

            # Set current page source path for cross-version dependency tracking
            source_path = metadata.get("_source_path") if metadata else None
            if source_path:
                from pathlib import Path

                self._xref_plugin.current_source_page = (
                    Path(source_path) if isinstance(source_path, str) else source_path
                )
            else:
                self._xref_plugin.current_source_page = None

            html = self._xref_plugin._substitute_xrefs(html)

        return html

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

    # =========================================================================
    # Cross-Reference Support
    # =========================================================================

    def enable_cross_references(
        self,
        xref_index: dict[str, Any],
        version_config: Any | None = None,
        cross_version_tracker: Any | None = None,
    ) -> None:
        """Enable cross-reference support with [[link]] syntax.

        Should be called after content discovery when xref_index is built.
        Creates CrossReferencePlugin for post-processing HTML output.

        Performance: O(1) - just stores reference to index
        Thread-safe: Each parser instance needs this called once

        Args:
            xref_index: Pre-built cross-reference index from site discovery
            version_config: Optional versioning configuration for cross-version links
            cross_version_tracker: Optional callback for tracking cross-version link
                dependencies. Called with (source_page, target_version, target_path)
                when a [[v2:path]] link is resolved.

        RFC: rfc-versioned-docs-pipeline-integration (Phase 2)

        Raises:
            ImportError: If CrossReferencePlugin cannot be imported
        """
        if self._xref_enabled:
            # Already enabled, just update index, version_config, and tracker
            if self._xref_plugin:
                self._xref_plugin.xref_index = xref_index
                self._xref_plugin.version_config = version_config
                self._xref_plugin._cross_version_tracker = cross_version_tracker
            return

        from bengal.rendering.plugins import CrossReferencePlugin

        # Create plugin instance (for post-processing HTML)
        self._xref_plugin = CrossReferencePlugin(xref_index, version_config, cross_version_tracker)
        self._xref_enabled = True
