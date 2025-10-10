"""
Content parser for Markdown and other formats.

Supports multiple parser engines:
- python-markdown: Full-featured, slower (default)
- mistune: Fast, subset of features
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import re

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class BaseMarkdownParser(ABC):
    """
    Abstract base class for Markdown parsers.
    All parser implementations must implement this interface.
    """
    
    @abstractmethod
    def parse(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        Parse Markdown content into HTML.
        
        Args:
            content: Raw Markdown content
            metadata: Page metadata
            
        Returns:
            Parsed HTML content
        """
        pass
    
    @abstractmethod
    def parse_with_toc(self, content: str, metadata: Dict[str, Any]) -> tuple[str, str]:
        """
        Parse Markdown content and extract table of contents.
        
        Args:
            content: Raw Markdown content
            metadata: Page metadata
            
        Returns:
            Tuple of (parsed HTML, table of contents HTML)
        """
        pass


class PythonMarkdownParser(BaseMarkdownParser):
    """
    Parser using python-markdown library.
    Full-featured with all extensions.
    """
    
    def __init__(self) -> None:
        """Initialize the python-markdown parser with extensions."""
        import markdown
        self.md = markdown.Markdown(
            extensions=[
                'extra',
                'codehilite',
                'fenced_code',
                'tables',
                'toc',
                'meta',
                'attr_list',
                'def_list',
                'footnotes',
                'admonition',
            ],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'linenums': False,
                },
                'toc': {
                    'permalink': False,  # Permalink handled by JavaScript copy-link
                    'toc_depth': '2-4',
                }
            }
        )
    
    def parse(self, content: str, metadata: Dict[str, Any]) -> str:
        """Parse Markdown content into HTML."""
        self.md.reset()
        return self.md.convert(content)
    
    def parse_with_toc(self, content: str, metadata: Dict[str, Any]) -> tuple[str, str]:
        """Parse Markdown content and extract table of contents."""
        self.md.reset()
        html = self.md.convert(content)
        toc = getattr(self.md, 'toc', '')
        return html, toc


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
    _HEADING_PATTERN = re.compile(
        r'<(h[234])([^>]*)>(.*?)</\1>',
        re.IGNORECASE | re.DOTALL
    )
    
    # Pattern for extracting TOC from anchored headings
    _TOC_HEADING_PATTERN = re.compile(
        r'<(h[234])\s+id="([^"]+)"[^>]*>(.*?)</\1>',
        re.IGNORECASE | re.DOTALL
    )
    
    # Pattern to strip HTML tags from text
    _HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    
    def __init__(self) -> None:
        """
        Initialize the mistune parser with plugins.
        
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
            )
        
        # Import our custom plugins
        from bengal.rendering.plugins import create_documentation_directives, BadgePlugin
        
        # Create markdown instance with built-in + custom plugins
        # Note: Variable substitution is added per-page in parse_with_context()
        # Note: Cross-references added via enable_cross_references() when xref_index available
        # Note: Badges are post-processed on HTML output (not registered as mistune plugin)
        self.md = mistune.create_markdown(
            plugins=[
                'table',              # Built-in: GFM tables
                'strikethrough',      # Built-in: ~~text~~
                'task_lists',         # Built-in: - [ ] tasks
                'url',                # Built-in: autolinks
                'footnotes',          # Built-in: [^1]
                'def_list',           # Built-in: Term\n:   Def
                create_documentation_directives(),  # Custom: admonitions, tabs, dropdowns, cards
            ],
            renderer='html',
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
    
    def parse(self, content: str, metadata: Dict[str, Any]) -> str:
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
            logger.warning("mistune_parsing_error", 
                          error=str(e), 
                          error_type=type(e).__name__)
            # Return content wrapped in error message
            return f'<div class="markdown-error"><p><strong>Markdown parsing error:</strong> {e}</p><pre>{content}</pre></div>'
    
    def parse_with_toc(self, content: str, metadata: Dict[str, Any]) -> tuple[str, str]:
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
        
        # Stage 2: Inject heading anchors (IDs and ¶ links)
        html = self._inject_heading_anchors(html)
        
        # Stage 3: Extract TOC from anchored HTML
        toc = self._extract_toc(html)
        
        return html, toc
    
    def parse_with_context(self, content: str, metadata: Dict[str, Any], context: Dict[str, Any]) -> str:
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
            VariableSubstitutionPlugin,
            create_documentation_directives
        )
        
        # Create parser once, reuse thereafter (saves ~150ms per build!)
        if self._md_with_vars is None:
            self._var_plugin = VariableSubstitutionPlugin(context)
            self._md_with_vars = self._mistune.create_markdown(
                plugins=[
                    'table',
                    'strikethrough',
                    'task_lists',
                    'url',
                    'footnotes',
                    'def_list',
                    create_documentation_directives(),
                    # NOTE: Don't register _var_plugin here - we do preprocessing before Mistune
                    # Registering it would cause double-processing and create placeholders that never get restored
                ],
                renderer='html',
            )
        else:
            # Just update the context on existing plugin (fast!)
            self._var_plugin.update_context(context)
        
        try:
            # IMPORTANT: Process escape syntax BEFORE Mistune parses markdown
            # because {{/* */}} contains * which Mistune treats as emphasis
            content = self._var_plugin._substitute_variables(content)
            
            html = self._md_with_vars(content)
            
            # Post-process: Restore __BENGAL_ESCAPED_*__ placeholders to literal {{ }}
            html = self._var_plugin.restore_placeholders(html)
            
            # Post-process for badges (Sphinx-Design compatibility)
            html = self._badge_plugin._substitute_badges(html)
            
            # Post-process for cross-references if enabled
            if self._xref_enabled and self._xref_plugin:
                html = self._xref_plugin._substitute_xrefs(html)
            return html
        except Exception as e:
            # Log error but don't fail the entire build
            logger.warning("mistune_parsing_error_with_toc",
                          error=str(e),
                          error_type=type(e).__name__)
            return f'<div class="markdown-error"><p><strong>Markdown parsing error:</strong> {e}</p><pre>{content}</pre></div>'
    
    def parse_with_toc_and_context(self, content: str, metadata: Dict[str, Any], context: Dict[str, Any]) -> tuple[str, str]:
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
        
        # Inject heading anchors (IDs and ¶ links)
        html = self._inject_heading_anchors(html)
        
        # Extract TOC from anchored HTML
        toc = self._extract_toc(html)
        
        return html, toc
    
    def enable_cross_references(self, xref_index: Dict[str, Any]) -> None:
        """
        Enable cross-reference support with [[link]] syntax.
        
        Should be called after content discovery when xref_index is built.
        Creates CrossReferencePlugin for post-processing HTML output.
        
        Performance: O(1) - just stores reference to index
        Thread-safe: Each thread-local parser instance needs this called once
        
        Args:
            xref_index: Pre-built cross-reference index from site discovery
        
        Example usage:
            parser = MistuneParser()
            # ... after content discovery ...
            parser.enable_cross_references(site.xref_index)
            # Now [[docs/installation]] works in markdown!
        """
        if self._xref_enabled:
            # Already enabled, just update index
            if self._xref_plugin:
                self._xref_plugin.xref_index = xref_index
            return
        
        from bengal.rendering.plugins import CrossReferencePlugin
        
        # Create plugin instance (for post-processing HTML)
        self._xref_plugin = CrossReferencePlugin(xref_index)
        self._xref_enabled = True
    
    def _inject_heading_anchors(self, html: str) -> str:
        """
        Inject IDs and headerlinks into heading tags using fast regex (5-10x faster than BS4).
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
            HTML with heading IDs and headerlinks added (except those in blockquotes)
        """
        # Quick rejection: skip if no headings
        if not html or not ('<h2' in html or '<h3' in html or '<h4' in html):
            return html
        
        # If no blockquotes, use fast path
        if '<blockquote' not in html:
            def replace_heading(match):
                """Replace heading with ID and headerlink anchor."""
                tag = match.group(1)  # 'h2', 'h3', or 'h4'
                attrs = match.group(2)  # Existing attributes
                content = match.group(3)  # Heading content
                
                # Skip if already has id= attribute
                if 'id=' in attrs or 'id =' in attrs:
                    return match.group(0)
                
                # Extract text for slug (strip any HTML tags from content)
                text = self._HTML_TAG_PATTERN.sub('', content).strip()
                if not text:
                    return match.group(0)
                
                slug = self._slugify(text)
                
                # Build heading with ID (anchor link added by JavaScript)
                return f'<{tag} id="{slug}"{attrs}>{content}</{tag}>'
            
            try:
                return self._HEADING_PATTERN.sub(replace_heading, html)
            except Exception as e:
                # On any error, return original HTML (safe fallback)
                logger.warning("heading_anchor_injection_error",
                              error=str(e),
                              error_type=type(e).__name__)
                return html
        
        # Slow path: need to skip headings inside blockquotes
        try:
            import re
            parts = []
            in_blockquote = 0  # Track nesting level
            current_pos = 0
            
            # Find all blockquote open/close tags
            blockquote_pattern = re.compile(r'<(/?)blockquote[^>]*>', re.IGNORECASE)
            
            for match in blockquote_pattern.finditer(html):
                # Process content before this tag
                before = html[current_pos:match.start()]
                
                if in_blockquote == 0:
                    # Outside blockquote: add anchors
                    def replace_heading(m):
                        tag = m.group(1)
                        attrs = m.group(2)
                        content = m.group(3)
                        
                        if 'id=' in attrs or 'id =' in attrs:
                            return m.group(0)
                        
                        text = self._HTML_TAG_PATTERN.sub('', content).strip()
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
                if match.group(1) == '/':
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
                    
                    if 'id=' in attrs or 'id =' in attrs:
                        return m.group(0)
                    
                    text = self._HTML_TAG_PATTERN.sub('', content).strip()
                    if not text:
                        return m.group(0)
                    
                    slug = self._slugify(text)
                    return f'<{tag} id="{slug}"{attrs}>{content}</{tag}>'
                
                parts.append(self._HEADING_PATTERN.sub(replace_heading, remaining))
            else:
                parts.append(remaining)
            
            return ''.join(parts)
            
        except Exception as e:
            # On any error, return original HTML (safe fallback)
            logger.warning("heading_anchor_injection_error_blockquote",
                          error=str(e),
                          error_type=type(e).__name__)
            return html
    
    def _extract_toc(self, html: str) -> str:
        """
        Extract table of contents from HTML with anchored headings using fast regex (5-8x faster than BS4).
        
        Builds a nested list of links to heading anchors.
        Expects headings to already have IDs and ¶ links (from _inject_heading_anchors).
        
        Args:
            html: HTML content with heading IDs and headerlinks
            
        Returns:
            TOC as HTML (div.toc > ul > li > a structure)
        """
        # Quick rejection: skip if no headings
        if not html or not ('<h2' in html or '<h3' in html or '<h4' in html):
            return ''
        
        try:
            toc_items = []
            
            # Match headings with IDs: <h2 id="slug" ...>Title<a ...>¶</a></h2>
            for match in self._TOC_HEADING_PATTERN.finditer(html):
                level = int(match.group(1)[1])  # 'h2' → 2, 'h3' → 3, etc.
                heading_id = match.group(2)  # The slug/ID
                title_html = match.group(3).strip()  # Title with possible HTML
                
                # Strip HTML tags to get clean title text
                title = self._HTML_TAG_PATTERN.sub('', title_html).strip()
                if not title:
                    continue
                
                # Build indented list item
                indent = '  ' * (level - 2)
                toc_items.append(
                    f'{indent}<li><a href="#{heading_id}">{title}</a></li>'
                )
            
            if toc_items:
                return (
                    '<div class="toc">\n'
                    '<ul>\n'
                    + '\n'.join(toc_items) + '\n'
                    '</ul>\n'
                    '</div>'
                )
            
            return ''
        
        except Exception as e:
            # On any error, return empty TOC (safe fallback)
            logger.warning("toc_extraction_error",
                          error=str(e),
                          error_type=type(e).__name__)
            return ''
    
    def _slugify(self, text: str) -> str:
        """
        Convert text to a URL-friendly slug.
        Matches python-markdown's default slugify behavior.
        
        Uses bengal.utils.text.slugify with HTML unescaping enabled.
        
        Args:
            text: Text to slugify
            
        Returns:
            Slugified text
        """
        from bengal.utils.text import slugify
        return slugify(text, unescape_html=True)


# Legacy alias for backwards compatibility
MarkdownParser = PythonMarkdownParser


def create_markdown_parser(engine: Optional[str] = None) -> BaseMarkdownParser:
    """
    Factory function to create a markdown parser instance.
    
    Args:
        engine: Parser engine to use ('python-markdown', 'mistune', or None for default)
        
    Returns:
        Markdown parser instance
        
    Raises:
        ValueError: If engine is not supported
    """
    engine = (engine or 'python-markdown').lower()
    
    if engine in ('python-markdown', 'python_markdown', 'markdown'):
        return PythonMarkdownParser()
    elif engine == 'mistune':
        return MistuneParser()
    else:
        raise ValueError(
            f"Unsupported markdown engine: {engine}. "
            f"Choose from: 'python-markdown', 'mistune'"
        )

