"""
Mistune parser implementation - fast with full documentation features.

This package provides the MistuneParser class using the mistune library.
Components are organized into focused modules:

Modules:
    - highlighting.py: Syntax highlighting plugin with Pygments
    - toc.py: TOC extraction and heading anchor injection
    - ast.py: AST parsing and rendering
    - patterns.py: Compiled regex patterns

Features:
    - Tables (GFM)
    - Fenced code blocks with syntax highlighting
    - Strikethrough
    - Task lists
    - Autolinks
    - TOC generation
    - Admonitions
    - Footnotes
    - Definition lists
    - Variable substitution
    - Cross-references
    - AST output
"""

from __future__ import annotations

from typing import Any, override

from mistune.renderers.html import HTMLRenderer

from bengal.errors import format_suggestion
from bengal.rendering.parsers.base import BaseMarkdownParser
from bengal.rendering.parsers.mistune.ast import (
    create_ast_parser,
    parse_to_ast,
    render_ast,
)
from bengal.rendering.parsers.mistune.highlighting import (
    create_syntax_highlighting_plugin,
)
from bengal.rendering.parsers.mistune.toc import extract_toc, inject_heading_anchors
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = ["MistuneParser"]


class MistuneParser(BaseMarkdownParser):
    """
    Parser using mistune library.
    Faster with full documentation features.

    Supported features:
    - Tables (GFM)
    - Fenced code blocks
    - Strikethrough
    - Task lists
    - Autolinks
    - TOC generation (custom implementation)
    - Admonitions (custom plugin)
    - Footnotes (custom plugin)
    - Definition lists (custom plugin)
    - Variable substitution (custom plugin)
    """

    def __init__(self, enable_highlighting: bool = True) -> None:
        """
        Initialize the mistune parser with plugins.

        Args:
            enable_highlighting: Enable Pygments syntax highlighting for code blocks
                                (defaults to True)

        Parser Instances:
            This parser is typically created via thread-local caching.
            With parallel builds (max_workers=N), you'll see N instances
            created - one per worker thread. This is OPTIMAL, not a bug!

        Internal Structure:
            - self.md: Main mistune instance for standard parsing
            - self._md_with_vars: Created lazily for pages with {{ var }} syntax

            Both instances share plugins (cross-references, etc.) but have
            different preprocessing (variable substitution).

        Performance:
            - Parser creation: ~10ms (one-time per thread)
            - Per-page parsing: ~1-5ms (reuses cached parser)
            - With max_workers=10: 10 × 10ms = 100ms total creation cost
            - This cost is amortized over all pages in the build

        Raises:
            ImportError: If mistune is not installed
        """
        try:
            import mistune
        except ImportError:
            raise ImportError(
                "mistune is not installed. Install it with: pip install mistune"
            ) from None

        self.enable_highlighting = enable_highlighting

        # Import our custom plugins
        from bengal.directives.validator import DirectiveSyntaxValidator
        from bengal.rendering.plugins import (
            BadgePlugin,
            InlineIconPlugin,
            TermPlugin,
            create_documentation_directives,
        )

        self._validator = DirectiveSyntaxValidator()

        # Build plugins list (reused for consistent parser configuration)
        plugins: list[Any] = [
            "table",  # Built-in: GFM tables
            "strikethrough",  # Built-in: ~~text~~
            "task_lists",  # Built-in: - [ ] tasks
            "url",  # Built-in: autolinks
            "footnotes",  # Built-in: [^1]
            "def_list",  # Built-in: Term\n:   Def
            "math",  # Built-in: $math$
            create_documentation_directives(),  # Custom: admonitions, tabs, dropdowns, cards
            TermPlugin(),  # Custom: {term}`Word`
        ]

        # Add syntax highlighting plugin if enabled
        if self.enable_highlighting:
            plugins.append(create_syntax_highlighting_plugin())

        # ARCHITECTURE: Shared Renderer Pattern
        # ======================================
        # We create a SINGLE HTMLRenderer instance that is shared across all
        # Markdown parser instances (self.md, self._md_with_vars, etc.).
        #
        # This ensures that renderer-level state (like _xref_index for the cards
        # :pull: directive) is automatically available to ALL parsing operations,
        # regardless of which internal Markdown instance is used.
        #
        # Shared renderer ensures consistent state across all Markdown instances.
        #
        # escape=False allows raw HTML (e.g., <br>) inside table cells and inline
        # content. This is required for GFM tables to support line breaks.
        self._shared_renderer = HTMLRenderer(escape=False)

        # Create markdown instance with built-in + custom plugins
        # Note: Variable substitution is added per-page in parse_with_context()
        # Note: Cross-references added via enable_cross_references() when xref_index available
        # Note: Badges are post-processed on HTML output (not registered as mistune plugin)
        self.md = mistune.create_markdown(
            plugins=plugins,
            renderer=self._shared_renderer,  # Use shared renderer (with escape=False)
        )
        self._base_plugins = list(plugins)

        # Cache for mistune library (import on first use)
        self._mistune = mistune

        # Cache parser with variable substitution (created lazily in parse_with_context)
        self._var_plugin: Any = None
        self._md_with_vars: Any = None

        # Cross-reference plugin (added when xref_index is available)
        self._xref_plugin: Any = None
        self._xref_enabled = False

        # Badge plugin (always enabled)
        self._badge_plugin = BadgePlugin()

        # Inline icon plugin (always enabled)
        self._inline_icon_plugin = InlineIconPlugin()

        # AST parser instance (created lazily for parse_to_ast)
        # Uses renderer=None to get raw AST tokens instead of HTML
        self._ast_parser: Any = None

    def parse(self, content: str, metadata: dict[str, Any]) -> str:
        """
        Parse Markdown content into HTML.

        Args:
            content: Markdown content to parse
            metadata: Page metadata (includes source path for validation warnings)

        Returns:
            Rendered HTML string
        """
        if not content:
            return ""

        try:
            html = self.md(content)
            # Post-process for badges and inline icons
            html = self._badge_plugin._substitute_badges(html)
            html = self._inline_icon_plugin._substitute_icons(html)
            # Post-process for cross-references if enabled
            if self._xref_enabled and self._xref_plugin:
                # Set current page version for version-aware anchor resolution
                # Try to get version from metadata (page object may not be available)
                page_version = (
                    metadata.get("version") or metadata.get("_version") if metadata else None
                )
                self._xref_plugin.current_version = page_version

                # RFC: rfc-versioned-docs-pipeline-integration (Phase 2)
                # Set current page source path for cross-version dependency tracking
                # (source_path may be passed via metadata._source_path)
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
            # Log error but don't fail the entire build
            suggestion = format_suggestion("parsing", "markdown_error")
            logger.warning(
                "mistune_parsing_error",
                error=str(e),
                error_type=type(e).__name__,
                suggestion=suggestion,
            )
            # Return content wrapped in error message
            return f'<div class="markdown-error"><p><strong>Markdown parsing error:</strong> {e}</p><pre>{content}</pre></div>'

    @override
    def parse_with_toc(self, content: str, metadata: dict[str, Any]) -> tuple[str, str]:
        """
        Parse Markdown content and extract table of contents.

        Two-stage process:
        1. Parse markdown to HTML
        2. Inject heading anchors (IDs and headerlinks)
        3. Extract TOC from anchored headings

        Args:
            content: Markdown content to parse
            metadata: Page metadata (includes source path for validation warnings)

        Returns:
            Tuple of (HTML with anchored headings, TOC HTML)
        """
        # Stage 1: Parse markdown
        html = self.md(content)

        # Stage 1.5: Post-process badges and inline icons
        html = self._badge_plugin._substitute_badges(html)
        html = self._inline_icon_plugin._substitute_icons(html)

        # Stage 1.6: Post-process cross-references if enabled
        if self._xref_enabled and self._xref_plugin:
            # Set current page version for version-aware anchor resolution
            # Try to get version from metadata (page object may not be available)
            page_version = metadata.get("version") or metadata.get("_version") if metadata else None
            self._xref_plugin.current_version = page_version

            # RFC: rfc-versioned-docs-pipeline-integration (Phase 2)
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

        # Stage 2: Inject heading anchors (IDs only; theme adds copy-link anchors)
        html = inject_heading_anchors(html, self._slugify)

        # Stage 3: Extract TOC from anchored HTML
        toc = extract_toc(html)

        return html, toc

    def parse_with_context(
        self, content: str, metadata: dict[str, Any], context: dict[str, Any]
    ) -> str:
        """
        Parse Markdown with variable substitution support.

        Variable Substitution:
            Enables {{ page.title }}, {{ site.baseurl }}, etc. in markdown content.
            Uses a separate mistune instance (_md_with_vars) with preprocessing.

        Lazy Initialization:
            _md_with_vars is created on first use and cached thereafter.
            This happens once per parser instance (i.e., once per thread).

        Args:
            content: Markdown content to parse
            metadata: Page metadata
            context: Variable context (page, site, config)

        Returns:
            Rendered HTML with variables substituted

        Performance:
            - First call (per thread): Creates _md_with_vars (~10ms)
            - Subsequent calls: Reuses cached parser (~0ms overhead)
            - Variable preprocessing: ~0.5ms per page
            - Markdown parsing: ~1-5ms per page
        """
        if not content:
            return ""

        from bengal.rendering.plugins import (
            TermPlugin,
            VariableSubstitutionPlugin,
            create_documentation_directives,
        )

        # Create parser once, reuse thereafter (saves ~150ms per build!)
        if self._md_with_vars is None:
            self._var_plugin = VariableSubstitutionPlugin(context)

            # Build plugins list
            var_plugins: list[Any] = [
                "table",
                "strikethrough",
                "task_lists",
                "url",
                "footnotes",
                "def_list",
                "math",
                self._var_plugin,  # Register variable substitution plugin
                create_documentation_directives(),
                TermPlugin(),
            ]

            # Add syntax highlighting if enabled
            if self.enable_highlighting:
                var_plugins.append(create_syntax_highlighting_plugin())

            # Use the SAME shared renderer as self.md
            # This ensures xref_index and other renderer state is automatically shared
            self._md_with_vars = self._mistune.create_markdown(
                plugins=var_plugins,
                renderer=self._shared_renderer,  # Inherits escape=False from shared renderer
            )
        else:
            # Just update the context on existing plugin (fast!)
            self._var_plugin.update_context(context)

        # Store current page on renderer for directive access
        current_page = context.get("page") if "page" in context else None
        self._shared_renderer._current_page = current_page  # type: ignore[attr-defined]

        # Store site on renderer for directive access
        site = context.get("site")
        self._shared_renderer._site = site  # type: ignore[attr-defined]

        # Also store content-relative path
        if current_page and hasattr(current_page, "source_path"):
            page_source = current_page.source_path
            source_str = str(page_source)
            if source_str.endswith("/_index.md"):
                self._shared_renderer._current_page_dir = source_str[:-10]  # type: ignore[attr-defined]
            elif source_str.endswith("/index.md"):
                self._shared_renderer._current_page_dir = source_str[:-9]  # type: ignore[attr-defined]
            elif "/" in source_str:
                self._shared_renderer._current_page_dir = source_str.rsplit("/", 1)[0]  # type: ignore[attr-defined]
            else:
                self._shared_renderer._current_page_dir = ""  # type: ignore[attr-defined]
        else:
            self._shared_renderer._current_page_dir = None  # type: ignore[attr-defined]

        try:
            # IMPORTANT: Only process escape syntax BEFORE Mistune parses markdown
            content = self._var_plugin.preprocess(content)

            html = self._md_with_vars(content)

            # Post-process: Restore __BENGAL_ESCAPED_*__ placeholders to literal {{ }}
            html = self._var_plugin.restore_placeholders(html)

            # Post-process: Escape any raw Jinja2 block syntax
            html = self._escape_jinja_blocks(html)

            # Post-process for badges and inline icons
            html = self._badge_plugin._substitute_badges(html)
            html = self._inline_icon_plugin._substitute_icons(html)

            # Post-process for cross-references if enabled
            if self._xref_enabled and self._xref_plugin:
                # Set current page version for version-aware anchor resolution
                if current_page and hasattr(current_page, "version"):
                    self._xref_plugin.current_version = current_page.version
                else:
                    # Fall back to metadata if page object not available
                    page_version = (
                        metadata.get("version") or metadata.get("_version") if metadata else None
                    )
                    self._xref_plugin.current_version = page_version

                # RFC: rfc-versioned-docs-pipeline-integration (Phase 2)
                # Set current page source path for cross-version dependency tracking
                if current_page and hasattr(current_page, "source_path"):
                    self._xref_plugin.current_source_page = current_page.source_path
                else:
                    self._xref_plugin.current_source_page = None

                html = self._xref_plugin._substitute_xrefs(html)
            return html
        except Exception as e:
            logger.warning(
                "mistune_parsing_error_with_toc", error=str(e), error_type=type(e).__name__
            )
            return f'<div class="markdown-error"><p><strong>Markdown parsing error:</strong> {e}</p><pre>{content}</pre></div>'

    def _escape_jinja_blocks(self, html: str) -> str:
        """
        Escape raw Jinja2 block delimiters in HTML content.

        This converts "{%"/"%}" into HTML entities so any documentation
        examples do not appear as unrendered template syntax in the final HTML.
        """
        try:
            return html.replace("{%", "&#123;%").replace("%}", "%&#125;")
        except Exception as e:
            logger.debug(
                "mistune_jinja_block_escape_failed",
                error=str(e),
                error_type=type(e).__name__,
                action="returning_original_html",
            )
            return html

    def parse_with_toc_and_context(
        self, content: str, metadata: dict[str, Any], context: dict[str, Any]
    ) -> tuple[str, str]:
        """
        Parse Markdown with variable substitution and extract TOC.

        Single-pass parsing with VariableSubstitutionPlugin for {{ vars }}.

        Args:
            content: Markdown content to parse
            metadata: Page metadata
            context: Variable context (page, site, config)

        Returns:
            Tuple of (HTML with anchored headings, TOC HTML)
        """
        # Parse markdown with variable substitution (includes badge post-processing)
        html = self.parse_with_context(content, metadata, context)

        # Inject heading anchors (IDs only; theme adds copy-link anchors)
        html = inject_heading_anchors(html, self._slugify)

        # Extract TOC from anchored HTML
        toc = extract_toc(html)

        return html, toc

    def enable_cross_references(
        self,
        xref_index: dict[str, Any],
        version_config: Any | None = None,
        cross_version_tracker: Any | None = None,
    ) -> None:
        """
        Enable cross-reference support with [[link]] syntax.

        Should be called after content discovery when xref_index is built.
        Creates CrossReferencePlugin for post-processing HTML output.

        Also stores xref_index on the renderer for directive access (e.g., cards :pull:).

        Performance: O(1) - just stores reference to index
        Thread-safe: Each thread-local parser instance needs this called once

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
            # Update shared renderer (automatically available to all Markdown instances)
            self._shared_renderer._xref_index = xref_index  # type: ignore[attr-defined]
            return

        from bengal.rendering.plugins import CrossReferencePlugin

        # Create plugin instance (for post-processing HTML)
        self._xref_plugin = CrossReferencePlugin(xref_index, version_config, cross_version_tracker)
        self._xref_enabled = True

        # Store xref_index on shared renderer for directive access
        self._shared_renderer._xref_index = xref_index  # type: ignore[attr-defined]

    # =========================================================================
    # AST Support
    # =========================================================================

    @property
    def supports_ast(self) -> bool:
        """
        Check if this parser supports true AST output.

        Mistune natively supports AST output via renderer=None.

        Returns:
            True - Mistune supports AST output
        """
        return True

    def parse_to_ast(self, content: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Parse Markdown content to AST tokens.

        Uses Mistune's built-in AST support by parsing with renderer=None.

        Args:
            content: Raw Markdown content
            metadata: Page metadata (unused, for interface compatibility)

        Returns:
            List of AST token dictionaries
        """
        if not content:
            return []

        # Create AST parser lazily
        if self._ast_parser is None:
            self._ast_parser = create_ast_parser(self._mistune, self._base_plugins)

        return parse_to_ast(content, self._ast_parser)

    def render_ast(self, ast: list[dict[str, Any]]) -> str:
        """
        Render AST tokens to HTML.

        Args:
            ast: List of AST token dictionaries from parse_to_ast()

        Returns:
            Rendered HTML string
        """
        return render_ast(ast)

    def parse_with_ast(
        self, content: str, metadata: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], str, str]:
        """
        Parse content and return AST, HTML, and TOC together.

        Single-pass parsing that returns all outputs efficiently.

        Args:
            content: Raw Markdown content
            metadata: Page metadata

        Returns:
            Tuple of (AST tokens, HTML content, TOC HTML)
        """
        if not content:
            return [], "", ""

        # Get AST first
        ast = self.parse_to_ast(content, metadata)

        # Render AST to HTML
        html = render_ast(ast) if ast else ""

        # Apply post-processing (badges, inline icons, xrefs)
        if html:
            html = self._badge_plugin._substitute_badges(html)
            html = self._inline_icon_plugin._substitute_icons(html)
            if self._xref_enabled and self._xref_plugin:
                # Set current page version for version-aware anchor resolution
                # Try to get version from metadata (page object may not be available)
                page_version = (
                    metadata.get("version") or metadata.get("_version") if metadata else None
                )
                self._xref_plugin.current_version = page_version

                # RFC: rfc-versioned-docs-pipeline-integration (Phase 2)
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

            # Inject heading anchors and extract TOC
            html = inject_heading_anchors(html, self._slugify)
            toc = extract_toc(html)
        else:
            toc = ""

        return ast, html, toc

    def _slugify(self, text: str) -> str:
        """
        Convert text to a URL-friendly slug.
        Matches python-markdown's default slugify behavior.

        Uses bengal.utils.text.slugify with HTML unescaping enabled.
        Limits slug length to prevent overly long IDs from headers with code.

        Args:
            text: Text to slugify

        Returns:
            Slugified text (max 100 characters)
        """
        from bengal.utils.text import slugify

        # Limit slug length to prevent overly long IDs
        return slugify(text, unescape_html=True, max_length=100)
