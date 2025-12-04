"""Mistune parser implementation - fast with full documentation features."""

from __future__ import annotations

import html as html_module
import re
from typing import Any, override

from mistune.renderers.html import HTMLRenderer

from bengal.rendering.parsers.base import BaseMarkdownParser
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


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
    - Variable substitution (custom plugin) - NEW!
    """

    # Pre-compiled regex patterns for heading anchor injection (5-10x faster than BeautifulSoup)
    _HEADING_PATTERN = re.compile(r"<(h[234])([^>]*)>(.*?)</\1>", re.IGNORECASE | re.DOTALL)

    # Pattern for extracting TOC from anchored headings
    _TOC_HEADING_PATTERN = re.compile(
        r'<(h[234])\s+id="([^"]+)"[^>]*>(.*?)</\1>', re.IGNORECASE | re.DOTALL
    )

    # Pattern to strip HTML tags from text
    _HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

    def __init__(self, enable_highlighting: bool = True) -> None:
        """
        Initialize the mistune parser with plugins.

        Args:
            enable_highlighting: Enable Pygments syntax highlighting for code blocks
                                (defaults to True for backward compatibility)

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
        from bengal.rendering.plugins import (
            BadgePlugin,
            TermPlugin,
            create_documentation_directives,
        )
        from bengal.rendering.plugins.directives.validator import DirectiveSyntaxValidator

        self._validator = DirectiveSyntaxValidator()

        # Build plugins list
        plugins = [
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
            plugins.append(self._create_syntax_highlighting_plugin())

        # ARCHITECTURE: Shared Renderer Pattern
        # ======================================
        # We create a SINGLE HTMLRenderer instance that is shared across all
        # Markdown parser instances (self.md, self._md_with_vars, etc.).
        #
        # This ensures that renderer-level state (like _xref_index for the cards
        # :pull: directive) is automatically available to ALL parsing operations,
        # regardless of which internal Markdown instance is used.
        #
        # Previously, each Markdown instance created its own renderer, requiring
        # manual state synchronization that was error-prone and easy to forget.
        self._shared_renderer = HTMLRenderer()

        # Create markdown instance with built-in + custom plugins
        # Note: Variable substitution is added per-page in parse_with_context()
        # Note: Cross-references added via enable_cross_references() when xref_index available
        # Note: Badges are post-processed on HTML output (not registered as mistune plugin)
        self.md = mistune.create_markdown(
            plugins=plugins,
            renderer=self._shared_renderer,  # Use shared renderer
        )

        # Cache for mistune library (import on first use)
        import mistune

        self._mistune = mistune

        # Cache parser with variable substitution (created lazily in parse_with_context)
        self._var_plugin = None
        self._md_with_vars = None

        # Cross-reference plugin (added when xref_index is available)
        self._xref_plugin = None
        self._xref_enabled = False

        # Badge plugin (always enabled for Sphinx-Design compatibility)
        self._badge_plugin = BadgePlugin()

        # AST parser instance (created lazily for parse_to_ast)
        # Uses renderer=None to get raw AST tokens instead of HTML
        self._ast_parser = None

    def _create_syntax_highlighting_plugin(self):
        """
        Create a Mistune plugin that adds Pygments syntax highlighting to code blocks.

        Returns:
            Plugin function that modifies the renderer to add syntax highlighting
        """
        from pygments import highlight
        from pygments.formatters.html import HtmlFormatter

        from bengal.rendering.pygments_cache import get_lexer_cached

        def plugin_syntax_highlighting(md):
            """Plugin function to add syntax highlighting to Mistune renderer."""
            # Get the original block_code renderer
            original_block_code = md.renderer.block_code

            def highlighted_block_code(code, info=None):
                """Render code block with syntax highlighting."""
                # If no language specified, use original renderer
                if not info:
                    return original_block_code(code, info)

                # Skip directive blocks (e.g., {info}, {rubric}, {note}, etc.)
                # These should be handled by the FencedDirective plugin
                info_stripped = info.strip()
                if info_stripped.startswith("{") and "}" in info_stripped:
                    return original_block_code(code, info)

                # Special handling: client-side rendered languages (e.g., Mermaid)
                lang_lower = info_stripped.lower()
                if lang_lower == "mermaid":
                    # Escape HTML so browsers don't interpret it; Mermaid will read textContent
                    escaped_code = (
                        code.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                        .replace('"', "&quot;")
                    )
                    return f'<div class="mermaid">{escaped_code}</div>\n'

                try:
                    # Get cached lexer for the language
                    lexer = get_lexer_cached(language=info_stripped)

                    # Format with Pygments using 'highlight' CSS class (matches python-markdown)
                    formatter = HtmlFormatter(
                        cssclass="highlight",
                        wrapcode=True,
                        noclasses=False,  # Use CSS classes instead of inline styles
                    )

                    # Highlight the code
                    highlighted = highlight(code, lexer, formatter)

                    return highlighted

                except Exception as e:
                    # If highlighting fails, return plain code block
                    logger.warning("pygments_highlight_failed", language=info, error=str(e))
                    # Escape HTML and return plain code block
                    escaped_code = (
                        code.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                        .replace('"', "&quot;")
                    )
                    return f'<pre><code class="language-{info}">{escaped_code}</code></pre>\n'

            # Replace the block_code method
            md.renderer.block_code = highlighted_block_code

        return plugin_syntax_highlighting

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
            # Post-process for badges (Sphinx-Design compatibility)
            html = self._badge_plugin._substitute_badges(html)
            # Post-process for cross-references if enabled
            if self._xref_enabled and self._xref_plugin:
                html = self._xref_plugin._substitute_xrefs(html)
            return html
        except Exception as e:
            # Log error but don't fail the entire build
            logger.warning("mistune_parsing_error", error=str(e), error_type=type(e).__name__)
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

        # Stage 1.5: Post-process badges
        html = self._badge_plugin._substitute_badges(html)

        # Stage 1.6: Post-process cross-references if enabled
        if self._xref_enabled and self._xref_plugin:
            html = self._xref_plugin._substitute_xrefs(html)

        # Stage 2: Inject heading anchors (IDs only; theme adds copy-link anchors)
        html = self._inject_heading_anchors(html)

        # Stage 3: Extract TOC from anchored HTML
        toc = self._extract_toc(html)

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

            Important: In parallel builds with max_workers=N:
            - N parser instances created (main: self.md)
            - N variable parser instances created (vars: self._md_with_vars)
            - Total: 2N mistune instances, but only 1 of each per thread
            - This is optimal - each thread uses its cached instances

        Parser Reuse:
            The parser with VariableSubstitutionPlugin is cached and reused.
            Only the context is updated per page (fast operation).
            This avoids expensive parser re-initialization (~10ms) for every page.

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

        # Import on demand
        if self._mistune is None:
            import mistune

            self._mistune = mistune

        from bengal.rendering.plugins import (
            TermPlugin,
            VariableSubstitutionPlugin,
            create_documentation_directives,
        )

        # Create parser once, reuse thereafter (saves ~150ms per build!)
        if self._md_with_vars is None:
            self._var_plugin = VariableSubstitutionPlugin(context)

            # Build plugins list
            var_plugins = [
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
                var_plugins.append(self._create_syntax_highlighting_plugin())

            # Use the SAME shared renderer as self.md
            # This ensures xref_index and other renderer state is automatically shared
            self._md_with_vars = self._mistune.create_markdown(
                plugins=var_plugins,
                renderer=self._shared_renderer,
            )
        else:
            # Just update the context on existing plugin (fast!)
            self._var_plugin.update_context(context)

        # Store current page on renderer for directive access
        # This enables directives (cards, etc.) to access page._section.subsections directly
        # Much cleaner than xref_index lookups!
        current_page = context.get("page") if "page" in context else None
        self._shared_renderer._current_page = current_page

        # Store site on renderer for directive access
        # This enables directives (glossary, data_table, etc.) to access site.data and site.root_path
        site = context.get("site")
        self._shared_renderer._site = site

        # Also store content-relative path for backward compatibility
        if current_page and hasattr(current_page, "source_path"):
            page_source = current_page.source_path
            source_str = str(page_source)
            if source_str.endswith("/_index.md"):
                self._shared_renderer._current_page_dir = source_str[:-10]
            elif source_str.endswith("/index.md"):
                self._shared_renderer._current_page_dir = source_str[:-9]
            elif "/" in source_str:
                self._shared_renderer._current_page_dir = source_str.rsplit("/", 1)[0]
            else:
                self._shared_renderer._current_page_dir = ""
        else:
            self._shared_renderer._current_page_dir = None

        try:
            # IMPORTANT: Only process escape syntax BEFORE Mistune parses markdown
            content = self._var_plugin.preprocess(content)

            html = self._md_with_vars(content)

            # Post-process: Restore __BENGAL_ESCAPED_*__ placeholders to literal {{ }}
            html = self._var_plugin.restore_placeholders(html)

            # Post-process: Escape any raw Jinja2 block syntax so it never leaks
            # through to the final output (outside templates). Browsers render these
            # HTML entities as the expected characters for documentation.
            html = self._escape_jinja_blocks(html)

            # Post-process for badges (Sphinx-Design compatibility)
            html = self._badge_plugin._substitute_badges(html)

            # Post-process for cross-references if enabled
            if self._xref_enabled and self._xref_plugin:
                html = self._xref_plugin._substitute_xrefs(html)
            return html
        except Exception as e:
            # Log error but don't fail the entire build
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
        except Exception:
            return html

    def parse_with_toc_and_context(
        self, content: str, metadata: dict[str, Any], context: dict[str, Any]
    ) -> tuple[str, str]:
        """
        Parse Markdown with variable substitution and extract TOC.

        Single-pass parsing with VariableSubstitutionPlugin for {{ vars }}.

        ARCHITECTURE DECISION: Separation of Concerns
        ================================================

        SUPPORTED in markdown content:
        - {{ page.metadata.xxx }} - Variable substitution
        - {{ site.config.xxx }} - Site configuration access
        - Code blocks naturally stay literal (AST-level protection)

        NOT SUPPORTED in markdown content:
        - {% if %} - Conditional blocks
        - {% for %} - Loop constructs
        - Complex Jinja2 logic

        WHY: These belong in TEMPLATES, not markdown content.

        Use conditionals and loops in your page templates:

            <!-- templates/page.html -->
            <article>
              {% if page.metadata.enterprise %}
              <div class="enterprise-badge">Enterprise</div>
              {% endif %}

              {{ content }}  <!-- Markdown renders here -->
            </article>

        This design:
        - Keeps parsing simple and fast (single pass)
        - Follows Hugo's architecture (content vs logic separation)
        - Maintains performance (no preprocessing overhead)
        - Makes code blocks work naturally

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
        html = self._inject_heading_anchors(html)

        # Extract TOC from anchored HTML
        toc = self._extract_toc(html)

        return html, toc

    def enable_cross_references(self, xref_index: dict[str, Any]) -> None:
        """
        Enable cross-reference support with [[link]] syntax.

        Should be called after content discovery when xref_index is built.
        Creates CrossReferencePlugin for post-processing HTML output.

        Also stores xref_index on the renderer for directive access (e.g., cards :pull:).

        Performance: O(1) - just stores reference to index
        Thread-safe: Each thread-local parser instance needs this called once

        Args:
            xref_index: Pre-built cross-reference index from site discovery

        Raises:
            ImportError: If CrossReferencePlugin cannot be imported

        Example:
            >>> parser = MistuneParser()
            >>> # ... after content discovery ...
            >>> parser.enable_cross_references(site.xref_index)
            >>> # Now [[docs/installation]] works in markdown!
            >>> html = parser.parse("See [[docs/getting-started]]", {})
            >>> print(html)  # Contains <a href="/docs/getting-started">...</a>
        """
        if self._xref_enabled:
            # Already enabled, just update index
            if self._xref_plugin:
                self._xref_plugin.xref_index = xref_index
            # Update shared renderer (automatically available to all Markdown instances)
            self._shared_renderer._xref_index = xref_index
            return

        from bengal.rendering.plugins import CrossReferencePlugin

        # Create plugin instance (for post-processing HTML)
        self._xref_plugin = CrossReferencePlugin(xref_index)
        self._xref_enabled = True

        # Store xref_index on shared renderer for directive access (e.g., cards :pull: option)
        # Because we use a shared renderer, this is automatically available to ALL
        # Markdown instances (self.md, self._md_with_vars, etc.)
        self._shared_renderer._xref_index = xref_index

    # =========================================================================
    # AST Support (Phase 3 of RFC)
    # See: plan/active/rfc-content-ast-architecture.md
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
        The AST is a list of token dictionaries representing the document structure.

        Performance:
            - Parsing cost is similar to parse() (same tokenization)
            - AST is more memory-efficient than HTML for caching
            - Multiple outputs can be generated from single AST

        Args:
            content: Raw Markdown content
            metadata: Page metadata (unused, for interface compatibility)

        Returns:
            List of AST token dictionaries

        Example:
            >>> parser.parse_to_ast("# Hello\\n\\nWorld")
            [
                {'type': 'heading', 'attrs': {'level': 1}, 'children': [...]},
                {'type': 'paragraph', 'children': [{'type': 'text', 'raw': 'World'}]}
            ]
        """
        if not content:
            return []

        # Create AST parser lazily (shares plugins with main parser)
        if self._ast_parser is None:
            self._ast_parser = self._mistune.create_markdown(renderer=None)

        try:
            # Parse returns AST when renderer=None
            ast = self._ast_parser(content)
            return ast if ast else []
        except Exception as e:
            logger.warning(
                "mistune_ast_parsing_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return []

    def render_ast(self, ast: list[dict[str, Any]]) -> str:
        """
        Render AST tokens to HTML.

        Uses Mistune's renderer to convert AST tokens back to HTML.
        This enables parse-once, render-many patterns.

        Args:
            ast: List of AST token dictionaries from parse_to_ast()

        Returns:
            Rendered HTML string

        Example:
            >>> ast = parser.parse_to_ast("# Hello")
            >>> html = parser.render_ast(ast)
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

    def parse_with_ast(
        self, content: str, metadata: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], str, str]:
        """
        Parse content and return AST, HTML, and TOC together.

        Single-pass parsing that returns all outputs efficiently.
        Use this when you need both AST (for caching) and HTML (for display).

        Args:
            content: Raw Markdown content
            metadata: Page metadata

        Returns:
            Tuple of (AST tokens, HTML content, TOC HTML)

        Performance:
            - Single parse pass for AST
            - Single render pass for HTML
            - TOC extracted from HTML (fast regex)
            - ~30% overhead vs parse() alone, but saves re-parsing

        Example:
            >>> ast, html, toc = parser.parse_with_ast("# Hello\\n\\nWorld", {})
            >>> # Cache AST for later use
            >>> # Use HTML for immediate display
        """
        if not content:
            return [], "", ""

        # Get AST first
        ast = self.parse_to_ast(content, metadata)

        # Render AST to HTML
        html = self.render_ast(ast) if ast else ""

        # Apply post-processing (badges, xrefs)
        if html:
            html = self._badge_plugin._substitute_badges(html)
            if self._xref_enabled and self._xref_plugin:
                html = self._xref_plugin._substitute_xrefs(html)

            # Inject heading anchors and extract TOC
            html = self._inject_heading_anchors(html)
            toc = self._extract_toc(html)
        else:
            toc = ""

        return ast, html, toc

    def _inject_heading_anchors(self, html: str) -> str:
        """
        Inject IDs into heading tags using fast regex (5-10x faster than BS4).

        Excludes headings inside blockquotes from getting IDs (so they don't appear in TOC).

        Single-pass regex replacement handles:
        - h2, h3, h4 headings (matching python-markdown's toc_depth)
        - Existing IDs (preserves them)
        - Heading content with nested HTML
        - Generates clean slugs from heading text
        - Skips headings inside <blockquote> tags

        Args:
            html: HTML content from markdown parser

        Returns:
            HTML with heading IDs added (except those in blockquotes)
        """
        # Quick rejection: skip if no headings
        if not html or not ("<h2" in html or "<h3" in html or "<h4" in html):
            return html

        # If no blockquotes, use fast path
        if "<blockquote" not in html:

            def replace_heading(match):
                """Replace heading with ID only (no inline headerlink)."""
                tag = match.group(1)  # 'h2', 'h3', or 'h4'
                attrs = match.group(2)  # Existing attributes
                content = match.group(3)  # Heading content

                # Skip if already has id= attribute
                if "id=" in attrs or "id =" in attrs:
                    return match.group(0)

                # Extract text for slug (strip any HTML tags from content)
                text = self._HTML_TAG_PATTERN.sub("", content).strip()
                if not text:
                    return match.group(0)

                slug = self._slugify(text)

                # Build heading with ID only; theme JS adds copy-link anchor
                return f'<{tag} id="{slug}"{attrs}>{content}</{tag}>'

            try:
                return self._HEADING_PATTERN.sub(replace_heading, html)
            except Exception as e:
                # On any error, return original HTML (safe fallback)
                logger.warning(
                    "heading_anchor_injection_error", error=str(e), error_type=type(e).__name__
                )
                return html

        # Slow path: need to skip headings inside blockquotes
        try:
            import re

            parts = []
            in_blockquote = 0  # Track nesting level
            current_pos = 0

            # Find all blockquote open/close tags
            blockquote_pattern = re.compile(r"<(/?)blockquote[^>]*>", re.IGNORECASE)

            for match in blockquote_pattern.finditer(html):
                # Process content before this tag
                before = html[current_pos : match.start()]

                if in_blockquote == 0:
                    # Outside blockquote: add anchors
                    def replace_heading(m):
                        tag = m.group(1)
                        attrs = m.group(2)
                        content = m.group(3)

                        if "id=" in attrs or "id =" in attrs:
                            return m.group(0)

                        text = self._HTML_TAG_PATTERN.sub("", content).strip()
                        if not text:
                            return m.group(0)

                        slug = self._slugify(text)
                        return f'<{tag} id="{slug}"{attrs}>{content}</{tag}>'

                    parts.append(self._HEADING_PATTERN.sub(replace_heading, before))
                else:
                    # Inside blockquote: keep as-is
                    parts.append(before)

                # Add the blockquote tag
                parts.append(match.group(0))

                # Update nesting level
                if match.group(1) == "/":
                    in_blockquote = max(0, in_blockquote - 1)
                else:
                    in_blockquote += 1

                current_pos = match.end()

            # Process remaining content
            remaining = html[current_pos:]
            if in_blockquote == 0:

                def replace_heading(m):
                    tag = m.group(1)
                    attrs = m.group(2)
                    content = m.group(3)

                    if "id=" in attrs or "id =" in attrs:
                        return m.group(0)

                    text = self._HTML_TAG_PATTERN.sub("", content).strip()
                    if not text:
                        return m.group(0)

                    slug = self._slugify(text)
                    return f'<{tag} id="{slug}"{attrs}>{content}</{tag}>'

                parts.append(self._HEADING_PATTERN.sub(replace_heading, remaining))
            else:
                parts.append(remaining)

            return "".join(parts)

        except Exception as e:
            # On any error, return original HTML (safe fallback)
            logger.warning(
                "heading_anchor_injection_error_blockquote",
                error=str(e),
                error_type=type(e).__name__,
            )
            return html

    def _extract_toc(self, html: str) -> str:
        """
        Extract table of contents from HTML with anchored headings using fast regex (5-8x faster than BS4).

        Builds a nested list of links to heading anchors.
        Expects headings to have IDs (anchors handled by theme).

        Args:
            html: HTML content with heading IDs and headerlinks

        Returns:
            TOC as HTML (div.toc > ul > li > a structure)
        """
        # Quick rejection: skip if no headings
        if not html or not ("<h2" in html or "<h3" in html or "<h4" in html):
            return ""

        try:
            toc_items = []

            # Match headings with IDs: <h2 id="slug" ...>Title</h2>
            for match in self._TOC_HEADING_PATTERN.finditer(html):
                level = int(match.group(1)[1])  # 'h2' → 2, 'h3' → 3, etc.
                heading_id = match.group(2)  # The slug/ID
                title_html = match.group(3).strip()  # Title with possible HTML

                # Strip HTML tags to get clean title text
                title = self._HTML_TAG_PATTERN.sub("", title_html).strip()
                # Decode HTML entities (e.g., &quot; -> ", &amp; -> &)
                title = html_module.unescape(title)
                # Remove pilcrow (¶) character that remains after stripping headerlink
                title = title.replace("¶", "").strip()
                if not title:
                    continue

                # Truncate long titles (especially those with code) for TOC display
                # 50 chars is reasonable for 280px sidebar TOC to prevent overflow
                # This ensures titles fit even with code snippets and file paths
                if len(title) > 50:
                    title = title[:47] + "..."

                # Build indented list item
                indent = "  " * (level - 2)
                toc_items.append(f'{indent}<li><a href="#{heading_id}">{title}</a></li>')

            if toc_items:
                return '<div class="toc">\n<ul>\n' + "\n".join(toc_items) + "\n</ul>\n</div>"

            return ""

        except Exception as e:
            # On any error, return empty TOC (safe fallback)
            logger.warning("toc_extraction_error", error=str(e), error_type=type(e).__name__)
            return ""

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

        # Limit slug length to prevent overly long IDs from headers with long code snippets
        # 100 chars is reasonable for HTML IDs while still being descriptive
        return slugify(text, unescape_html=True, max_length=100)
