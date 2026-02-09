"""
Page Content Mixin - AST-based content representation.

This module provides the AST-first content architecture where
the Patitas Document AST is the structural source of truth.

Architecture:
- _ast_cache: Patitas Document AST (frozen dataclass tree)
- html_content: HTML rendered from AST (derived view)
- plain_text: Plain text for search/LLM (AST walk or HTML stripping)

Benefits:
- Parse once, use many times (HTML, TOC, plain text, links)
- Incremental diffing via Patitas diff_documents()
- Fragment updates via AST comparison
- Semantic provenance hashing (AST structure, not raw bytes)
- Better caching (AST serializable via to_json/from_json)

"""

from __future__ import annotations

from typing import Any

from bengal.core.utils.text import strip_html_and_normalize


class PageContentMixin:
    """
    Mixin providing AST-based content properties for pages.

    The Patitas Document AST is the canonical content representation.
    HTML, plain text, and TOC are derived views of the AST.

    Key Properties:
        content: Rendered HTML content (template-ready, display output)
        html: Alias for content (rendered HTML)
        ast: Patitas Document AST (frozen dataclass tree)
        plain_text: Plain text for search indexing and LLM
        _source: Raw markdown source (internal use, via PageComputedMixin)

    """

    # Fields from Page that this mixin accesses
    _raw_content: str
    # HTML content rendered from Markdown by Patitas parser.
    html_content: str | None
    links: list[str]

    # Private caches (set by Page dataclass __post_init__)
    # _ast_cache: Patitas Document (frozen dataclass) or None
    _ast_cache: Any
    _html_cache: str | None
    _plain_text_cache: str | None

    @property
    def content(self) -> str:
        """
        Rendered HTML content for template display.

        This property returns the rendered HTML content, ready for use in templates.
        It follows the convention that properties without underscore prefix are
        template-ready.

        For raw markdown source, use page._source (internal/advanced use only).

        Returns:
            Rendered HTML string

        Example:
            {{ page.content | safe }}  {# In templates #}

        See Also:
            - page._source: Raw markdown (internal use)
            - page.word_count: Pre-computed word count
            - page.reading_time: Pre-computed reading time
        """
        return self.html

    @property
    def ast(self) -> Any:
        """
        Patitas Document AST — the structural source of truth.

        Returns the frozen Patitas Document dataclass tree parsed from
        the page's markdown content. This enables:
        - Incremental diffing (diff_documents)
        - Fragment updates (AST comparison)
        - Multi-output generation (HTML, TOC, plain text, links)
        - Semantic provenance hashing

        Returns:
            Patitas Document (frozen dataclass) if available, None otherwise.

        Example:
            >>> page.ast
            Document(children=(Heading(...), Paragraph(...), ...))
        """
        if hasattr(self, "_ast_cache"):
            return self._ast_cache
        return None

    @property
    def html(self) -> str:
        """
        HTML content rendered from the pipeline or AST fallback.

        Prefers html_content (set by the full rendering pipeline with
        variable substitution, heading IDs, and post-processing).
        Falls back to rendering from the Patitas AST when html_content
        is missing (e.g., page loaded from disk cache).

        Returns:
            Rendered HTML string

        Example:
            >>> page.html
            '<h1>Hello World</h1><p>Content here...</p>'
        """
        # Primary: html_content from the rendering pipeline
        if self.html_content:
            return self.html_content

        # Secondary: cached HTML (from previous AST render)
        if hasattr(self, "_html_cache") and self._html_cache is not None:
            return self._html_cache

        # Fallback: render from Patitas AST if available
        if hasattr(self, "_ast_cache") and self._ast_cache is not None:
            html = self._render_ast_to_html()
            if html and hasattr(self, "_html_cache"):
                self._html_cache = html
            return html

        return ""

    @property
    def plain_text(self) -> str:
        """
        Plain text extracted from content (for search/LLM).

        Uses Patitas Document AST extraction when available (faster, more
        accurate), falling back to HTML tag stripping for legacy content.

        Returns:
            Plain text content

        Example:
            >>> page.plain_text
            'Hello World\n\nContent here without any formatting...'
        """
        # Check cache first
        if hasattr(self, "_plain_text_cache") and self._plain_text_cache is not None:
            return self._plain_text_cache

        # Prefer Patitas Document AST extraction (fast, accurate)
        if hasattr(self, "_ast_cache") and self._ast_cache is not None:
            from bengal.parsing.ast.patitas_extract import (
                extract_plain_text_from_document,
            )

            text = extract_plain_text_from_document(self._ast_cache)
            if text:
                if hasattr(self, "_plain_text_cache"):
                    self._plain_text_cache = text
                return text

        # Fallback: Use HTML-based extraction (works correctly with directives)
        html_content = getattr(self, "html_content", None) or ""
        if html_content:
            text = strip_html_and_normalize(html_content)
        else:
            # Fallback to raw content if no HTML available
            text = self._raw_content if self._raw_content else ""

        if hasattr(self, "_plain_text_cache"):
            self._plain_text_cache = text
        return text

    def _render_ast_to_html(self) -> str:
        """
        Render Patitas Document AST to HTML.

        Uses Patitas' own HtmlRenderer for correct output. In the normal
        pipeline, html_content is set during parsing and this method is not
        called. It serves as a fallback when html_content is missing but
        the AST is available (e.g., loaded from disk cache).

        Returns:
            Rendered HTML string
        """
        if not hasattr(self, "_ast_cache") or not self._ast_cache:
            return ""

        from bengal.parsing.ast.patitas_extract import render_document_to_html

        return render_document_to_html(self._ast_cache)

    def _extract_text_from_ast(self) -> str:
        """
        Extract plain text from Patitas Document AST.

        Returns:
            Plain text string
        """
        if not hasattr(self, "_ast_cache") or not self._ast_cache:
            return ""

        from bengal.parsing.ast.patitas_extract import (
            extract_plain_text_from_document,
        )

        return extract_plain_text_from_document(self._ast_cache)

    def _extract_links_from_ast(self) -> list[str]:
        """
        Extract links from Patitas Document AST.

        Returns:
            List of link URLs
        """
        if not hasattr(self, "_ast_cache") or not self._ast_cache:
            return []

        from bengal.parsing.ast.patitas_extract import (
            extract_links_from_document,
        )

        return extract_links_from_document(self._ast_cache)

    def _strip_html_to_text(self, html: str) -> str:
        """
        Strip HTML tags from content to get plain text.

        Fallback method when AST is not available.

        Args:
            html: HTML content

        Returns:
            Plain text with HTML tags removed

        Note:
            This method is kept for backward compatibility but now
            delegates to the unified strip_html_and_normalize utility.
        """
        return strip_html_and_normalize(html)
