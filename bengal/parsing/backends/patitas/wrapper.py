"""PatitasParser wrapper implementing BaseMarkdownParser.

Provides Bengal integration by implementing the BaseMarkdownParser interface.
This allows Patitas to be used as a drop-in replacement for legacy parsers.

Usage:
    parser = PatitasParser()
    html = parser.parse("# Hello", {})
html, toc = parser.parse_with_toc("## Section 1\n## Section 2", {})

Thread Safety:
PatitasParser is thread-safe. Each parse() call creates independent
parser/renderer instances with no shared state.

"""

from __future__ import annotations

from typing import Any, ClassVar

from patitas.nodes import Block, Document

from bengal.config.defaults import get_default
from bengal.parsing.backends.patitas import create_markdown, parse_to_ast, parse_to_document
from bengal.parsing.base import BaseMarkdownParser
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


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
    DEFAULT_PLUGINS: ClassVar[list[str]] = [
        "table",
        "strikethrough",
        "task_lists",
        "math",
        "footnotes",
    ]

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

    def parse_with_toc(self, content: str, metadata: dict[str, Any]) -> tuple[str, str, str, str]:
        """Parse Markdown content and extract table of contents, excerpt, and meta description.

        Uses single-pass heading decoration (RFC: rfc-path-to-200-pgs).
        Heading IDs and TOC are generated during the AST walk - no regex post-pass.
        Excerpt and meta description are extracted from AST for structurally correct plain text.

        Args:
            content: Markdown content to parse
            metadata: Page metadata (includes source path for cross-reference context)

        Returns:
            Tuple of (HTML with heading IDs, TOC HTML, excerpt, meta_description)
        """
        if not content:
            return "", "", "", ""

        # Parse to AST using configured markdown instance
        ast = self._md.parse_to_ast(content)

        # Extract excerpt and meta description from AST (parse once, use many)
        try:
            from patitas import extract_excerpt, extract_meta_description

            max_chars = metadata.get("_excerpt_length", get_default("content", "excerpt_length"))
            excerpt = extract_excerpt(ast, content, excerpt_as_html=True, max_chars=max_chars)
            meta_desc = (
                extract_meta_description(ast, content)
                if not metadata.get("description")
                else str(metadata.get("description", ""))
            )
        except Exception:
            excerpt = ""
            meta_desc = ""

        # Render HTML with single-pass TOC extraction (RFC: rfc-path-to-200-pgs)
        # Heading IDs are injected during render, TOC collected in same pass
        html, toc, _toc_items = self._md.render_ast_with_toc(ast, content)

        # Post-process cross-references if enabled
        html = self._apply_post_processing(html, metadata)

        return html, toc, excerpt, meta_desc

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

        # Extract page context for directives (child-cards, breadcrumbs, etc.)
        page_context = context.get("page")
        # Extract xref_index and site for link resolution and site-wide context
        xref_index = context.get("xref_index")
        site = context.get("site")

        try:
            # 1. Preprocess: handle {{/* escaped syntax */}}
            content = var_plugin.preprocess(content)

            # 2. Parse & Substitute in ONE pass (the "window thing")
            # The Lexer handles variable substitution as it scans lines.
            # This is O(n) with zero extra passes or AST walks.
            html = self._md(
                content,
                text_transformer=var_plugin.substitute_variables,
                page_context=page_context,
                xref_index=xref_index,
                site=site,
            )

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
    ) -> tuple[str, str, str, str]:
        """Parse Markdown with variable substitution and extract TOC, excerpt, and meta description.

        Uses single-pass heading decoration (RFC: rfc-path-to-200-pgs).
        Heading IDs and TOC are generated during the AST walk - no regex post-pass.
        Excerpt and meta description are extracted from AST for structurally correct plain text.

        Args:
            content: Markdown content to parse
            metadata: Page metadata
            context: Variable context (page, site, config)

        Returns:
            Tuple of (HTML with heading IDs, TOC HTML, excerpt, meta_description)
        """
        if not content:
            return "", "", "", ""

        from bengal.rendering.plugins import VariableSubstitutionPlugin

        # Create plugin instance for this page and store for pipeline access
        self._var_plugin = VariableSubstitutionPlugin(context)
        var_plugin = self._var_plugin

        # Extract page context for directives (child-cards, breadcrumbs, etc.)
        page_context = context.get("page")
        # Extract xref_index and site for link resolution and site-wide context
        xref_index = context.get("xref_index")
        site = context.get("site")

        try:
            # 1. Preprocess: handle {{/* escaped syntax */}}
            content = var_plugin.preprocess(content)

            # 2. Parse & Substitute in ONE pass (the "window thing")
            ast = self._md.parse_to_ast(content, text_transformer=var_plugin.substitute_variables)

            # 3. Extract excerpt and meta description from AST (parse once, use many)
            try:
                from patitas import extract_excerpt, extract_meta_description

                # Per-article override: pipeline sets metadata._excerpt_length
                content_cfg = context.get("config", {}).get("content", {}) or {}
                max_chars = metadata.get(
                    "_excerpt_length",
                    content_cfg.get("excerpt_length", get_default("content", "excerpt_length")),
                )
                excerpt = extract_excerpt(ast, content, excerpt_as_html=True, max_chars=max_chars)
                meta_desc = (
                    extract_meta_description(ast, content)
                    if not metadata.get("description")
                    else str(metadata.get("description", ""))
                )
            except Exception:
                excerpt = ""
                meta_desc = ""

            # 4. Render HTML with single-pass TOC extraction (RFC: rfc-path-to-200-pgs)
            # Heading IDs are injected during render, TOC collected in same pass
            html, toc, _toc_items = self._md.render_ast_with_toc(
                ast,
                content,
                text_transformer=var_plugin.substitute_variables,
                page_context=page_context,
                xref_index=xref_index,
                site=site,
            )

            # 5. Restore placeholders
            html = var_plugin.restore_placeholders(html)

            # 6. Apply other post-processing
            html = self._apply_post_processing(html, metadata)

            return html, toc, excerpt, meta_desc

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
                "",
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

    def parse_to_document(self, content: str, metadata: dict[str, Any]) -> Document:
        """Parse Markdown content to typed Document AST.

        Returns Document for serialization via patitas.to_dict(doc).
        Used when persist_tokens is enabled for canonical AST cache format.

        Args:
            content: Raw Markdown content
            metadata: Page metadata (unused)

        Returns:
            Document AST
        """
        text_transformer = None
        if self._var_plugin:
            text_transformer = self._var_plugin.substitute_variables
        return parse_to_document(content, plugins=self._plugins, text_transformer=text_transformer)

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

    def render_ast_from_dict(
        self,
        ast_dict: dict[str, Any],
        source: str,
        *,
        page: Any = None,
        site: Any = None,
    ) -> tuple[str, str] | None:
        """Render Patitas Document dict to HTML and TOC.

        Fallback when cached HTML is missing; requires patitas>=0.2.0.

        Args:
            ast_dict: Serialized Document from patitas.to_dict(doc)
            source: Original source buffer (required for ZCLH)
            page: Page for directive context (optional)
            site: Site for xref_index (optional)

        Returns:
            (html, toc) or None if not supported (patitas < 0.2.0 or invalid format)
        """
        if not isinstance(ast_dict, dict) or ast_dict.get("_type") != "Document":
            return None
        try:
            import patitas
        except ImportError:
            return None
        if not hasattr(patitas, "from_dict"):
            return None
        doc = patitas.from_dict(ast_dict)
        xref_index = getattr(site, "xref_index", None) if site else None
        html, toc, _ = self._md.render_ast_with_toc(
            doc.children,
            source,
            page_context=page,
            xref_index=xref_index,
            site=site,
        )
        metadata = getattr(page, "metadata", {}) if page else {}
        html = self._apply_post_processing(html, metadata)
        return html, toc

    def _node_to_dict(self, node: Block) -> dict[str, Any]:
        """Convert AST node to dictionary representation.

        Args:
            node: Block node

        Returns:
            Dictionary representation
        """
        from bengal.utils.serialization import to_jsonable

        result = to_jsonable(node)
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
        external_ref_resolver: Any | None = None,
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
            external_ref_resolver: Optional resolver for [[ext:project:target]] syntax.
                See: plan/rfc-external-references.md

        RFC: rfc-versioned-docs-pipeline-integration (Phase 2)
        RFC: rfc-external-references (External References)

        Raises:
            ImportError: If CrossReferencePlugin cannot be imported
        """
        if self._xref_enabled:
            # Already enabled, just update index, version_config, tracker, and resolver
            if self._xref_plugin:
                self._xref_plugin.xref_index = xref_index
                self._xref_plugin.version_config = version_config
                self._xref_plugin._cross_version_tracker = cross_version_tracker
                self._xref_plugin._external_ref_resolver = external_ref_resolver
            return

        from bengal.rendering.plugins import CrossReferencePlugin

        # Create plugin instance (for post-processing HTML)
        self._xref_plugin = CrossReferencePlugin(
            xref_index, version_config, cross_version_tracker, external_ref_resolver
        )
        self._xref_enabled = True
