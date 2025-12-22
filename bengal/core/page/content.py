"""
Page Content Mixin - AST-based content representation.

This module provides the true AST architecture for content processing,
replacing the misleading `parsed_ast` field (which actually contains HTML).

Architecture:
    - _ast: True AST from parser (list of tokens) - Phase 3
    - html: HTML rendered from AST (or legacy parsed_ast)
    - plain_text: Plain text for search/LLM (AST walk or raw markdown)

Benefits:
    - Parse once, use many times
    - Faster post-processing (O(n) AST walks vs regex)
    - Cleaner transformations (shortcodes at AST level)
    - Better caching (cache AST separately from HTML)

Migration Plan:
    Phase 1: Add html, plain_text properties (non-breaking)
    Phase 2: Deprecate parsed_ast
    Phase 3: Implement true AST with hybrid fallback

See: plan/active/rfc-content-ast-architecture.md
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    pass


class PageContentMixin:
    """
    Mixin providing AST-based content properties for pages.

    This mixin handles content representation across multiple formats:
    - AST (Abstract Syntax Tree) - structural representation (Phase 3)
    - HTML - rendered for display
    - Plain text - for search indexing and LLM

    All properties use lazy evaluation with caching for performance.
    """

    # Fields from Page that this mixin accesses
    content: str
    # NOTE: Despite the name, parsed_ast currently stores rendered HTML (legacy).
    # The ASTNode types in bengal.rendering.ast_types are for future AST-based
    # processing. See plan/ready/plan-type-system-hardening.md for migration path.
    parsed_ast: Any
    links: list[str]

    # Private caches (set by Page dataclass __post_init__)
    _ast_cache: list[dict[str, Any]] | None
    _html_cache: str | None
    _plain_text_cache: str | None

    @property
    def ast(self) -> list[dict[str, Any]] | None:
        """
        True AST - list of tokens from markdown parser.

        Returns the structural representation of content as parsed by the
        markdown engine. This enables efficient multi-output generation:
        - HTML rendering
        - Plain text extraction
        - TOC generation
        - Link extraction

        Returns:
            List of AST tokens if available, None if parser doesn't support AST.

        Note:
            Returns None until Phase 3 AST support is implemented.
            See plan/active/rfc-content-ast-architecture.md for timeline.

        Example:
            >>> page.ast
            [{'type': 'heading', 'level': 1, 'children': [...]}, ...]
        """
        if hasattr(self, "_ast_cache"):
            return self._ast_cache
        return None

    @property
    def html(self) -> str:
        """
        HTML content rendered from AST or legacy parser.

        This is the preferred way to access rendered HTML content.
        Use this instead of the deprecated `parsed_ast` field.

        Returns:
            Rendered HTML string

        Example:
            >>> page.html
            '<h1>Hello World</h1><p>Content here...</p>'
        """
        # Check cache first (for when AST is available)
        if hasattr(self, "_html_cache") and self._html_cache is not None:
            return self._html_cache

        # If we have true AST, render from it (Phase 3)
        if hasattr(self, "_ast_cache") and self._ast_cache is not None:
            html = self._render_ast_to_html()
            if hasattr(self, "_html_cache"):
                self._html_cache = html
            return html

        # Phase 1/2 fallback: Delegate to parsed_ast (which is actually HTML)
        return self.parsed_ast if self.parsed_ast else ""

    @property
    def plain_text(self) -> str:
        """
        Plain text extracted from content (for search/LLM).

        Strips HTML tags from rendered content to get clean text.
        Uses the rendered HTML (which includes directive output) for accuracy.

        Returns:
            Plain text content with HTML tags removed

        Example:
            >>> page.plain_text
            'Hello World\n\nContent here without any formatting...'
        """
        # Check cache first
        if hasattr(self, "_plain_text_cache") and self._plain_text_cache is not None:
            return self._plain_text_cache

        # Use HTML-based extraction (works correctly with directives)
        # Get HTML from parsed_ast (the rendered HTML before template)
        html_content = getattr(self, "parsed_ast", None) or ""
        if html_content:
            text = self._strip_html_to_text(html_content)
        else:
            # Fallback to raw content if no HTML available
            text = self.content if self.content else ""

        if hasattr(self, "_plain_text_cache"):
            self._plain_text_cache = text
        return text

    def _render_ast_to_html(self) -> str:
        """
        Render AST tokens to HTML.

        Internal method used when true AST is available (Phase 3).

        Returns:
            Rendered HTML string
        """
        if not hasattr(self, "_ast_cache") or not self._ast_cache:
            return ""

        try:
            # Mistune 3.x requires HTMLRenderer instance and BlockState
            from mistune.core import BlockState
            from mistune.renderers.html import HTMLRenderer

            renderer = HTMLRenderer()
            state = BlockState()
            return renderer(self._ast_cache, state)
        except (ImportError, AttributeError, Exception) as e:
            # Fallback to empty string if rendering fails
            emit_diagnostic(
                self,
                "debug",
                "page_ast_to_html_failed",
                error=str(e),
                error_type=type(e).__name__,
                action="returning_empty_string",
            )
            return ""

    def _extract_text_from_ast(self) -> str:
        """
        Extract plain text from AST tokens.

        Walks the AST tree and extracts all text content,
        ignoring structural elements like code blocks.

        Returns:
            Plain text string
        """
        if not hasattr(self, "_ast_cache") or not self._ast_cache:
            return ""

        def walk_tokens(tokens: list[dict[str, Any]]) -> str:
            """Recursively extract text from tokens."""
            parts = []
            for token in tokens:
                token_type = token.get("type", "")

                # Extract raw text
                if "raw" in token:
                    parts.append(token["raw"])
                elif "text" in token:
                    parts.append(token["text"])

                # Recurse into children
                if "children" in token:
                    parts.append(walk_tokens(token["children"]))

                # Add spacing for block elements
                if token_type in ("paragraph", "heading", "list", "block_code"):
                    parts.append("\n")

            return "".join(parts)

        return walk_tokens(self._ast_cache).strip()

    def _extract_links_from_ast(self) -> list[str]:
        """
        Extract links from AST tokens.

        Walks the AST tree and extracts all link URLs (Phase 3).
        Handles Mistune 3.x AST format where URLs are in `attrs.url`.

        Returns:
            List of link URLs
        """
        if not hasattr(self, "_ast_cache") or not self._ast_cache:
            return []

        links: list[str] = []

        def walk_tokens(tokens: list[dict[str, Any]]) -> None:
            """Recursively extract links from tokens."""
            for token in tokens:
                token_type = token.get("type", "")

                # Extract link URLs (Mistune 3.x stores in attrs.url)
                if token_type == "link":
                    # Try attrs.url first (Mistune 3.x format)
                    attrs = token.get("attrs", {})
                    url = attrs.get("url", "") if isinstance(attrs, dict) else ""
                    # Fallback for other formats
                    if not url:
                        url = token.get("link", "") or token.get("href", "")
                    if url:
                        links.append(url)

                # Recurse into children
                if "children" in token:
                    children = token["children"]
                    if isinstance(children, list):
                        walk_tokens(children)

        walk_tokens(self._ast_cache)
        return links

    def _strip_html_to_text(self, html: str) -> str:
        """
        Strip HTML tags from content to get plain text.

        Fallback method when AST is not available.

        Args:
            html: HTML content

        Returns:
            Plain text with HTML tags removed
        """
        if not html:
            return ""

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", html)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text
