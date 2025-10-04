"""
Content parser for Markdown and other formats.

Supports multiple parser engines:
- python-markdown: Full-featured, slower (default)
- mistune: Fast, subset of features
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import re


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
                    'permalink': True,
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
    
    def __init__(self) -> None:
        """Initialize the mistune parser with plugins."""
        try:
            import mistune
        except ImportError:
            raise ImportError(
                "mistune is not installed. Install it with: pip install mistune"
            )
        
        # Import our custom plugins
        from bengal.rendering.plugins import create_documentation_directives
        
        # Create markdown instance with built-in + custom plugins
        # Note: Variable substitution is added per-page in parse_with_context()
        # Note: Cross-references added via enable_cross_references() when xref_index available
        self.md = mistune.create_markdown(
            plugins=[
                'table',              # Built-in: GFM tables
                'strikethrough',      # Built-in: ~~text~~
                'task_lists',         # Built-in: - [ ] tasks
                'url',                # Built-in: autolinks
                'footnotes',          # Built-in: [^1]
                'def_list',           # Built-in: Term\n:   Def
                create_documentation_directives(),  # Custom: admonitions, tabs, dropdowns
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
    
    def parse(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        Parse Markdown content into HTML.
        
        Args:
            content: Markdown content to parse
            metadata: Page metadata (unused by Mistune but required by interface)
            
        Returns:
            Rendered HTML string
        """
        if not content:
            return ""
        
        try:
            html = self.md(content)
            # Post-process for cross-references if enabled
            if self._xref_enabled and self._xref_plugin:
                html = self._xref_plugin._substitute_xrefs(html)
            return html
        except Exception as e:
            # Log error but don't fail the entire build
            import sys
            print(f"Warning: Mistune parsing error: {e}", file=sys.stderr)
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
            metadata: Page metadata (unused)
            
        Returns:
            Tuple of (HTML with anchored headings, TOC HTML)
        """
        # Stage 1: Parse markdown
        html = self.md(content)
        
        # Stage 2: Inject heading anchors (IDs and ¶ links)
        html = self._inject_heading_anchors(html)
        
        # Stage 3: Extract TOC from anchored HTML
        toc = self._extract_toc(html)
        
        return html, toc
    
    def parse_with_context(self, content: str, metadata: Dict[str, Any], context: Dict[str, Any]) -> str:
        """
        Parse Markdown with variable substitution support.
        
        Caches the parser with VariableSubstitutionPlugin and reuses it,
        updating only the context per page. This avoids expensive parser
        re-initialization for every page.
        
        Args:
            content: Markdown content to parse
            metadata: Page metadata
            context: Variable context (page, site, config)
            
        Returns:
            Rendered HTML with variables substituted
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
                    self._var_plugin,  # Reusable plugin instance
                ],
                renderer='html',
            )
        else:
            # Just update the context on existing plugin (fast!)
            self._var_plugin.update_context(context)
        
        try:
            html = self._md_with_vars(content)
            # Post-process for cross-references if enabled
            if self._xref_enabled and self._xref_plugin:
                html = self._xref_plugin._substitute_xrefs(html)
            return html
        except Exception as e:
            # Log error but don't fail the entire build
            import sys
            print(f"Warning: Mistune parsing error: {e}", file=sys.stderr)
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
        # Parse markdown with variable substitution
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
        Inject IDs and headerlinks into heading tags.
        
        Uses BeautifulSoup for robust HTML manipulation that handles:
        - Any whitespace/formatting variations
        - Existing IDs (preserves them)
        - Special characters in headings
        - Nested elements in headings
        
        Args:
            html: HTML content from markdown parser
            
        Returns:
            HTML with heading IDs and headerlinks added
        """
        if not html or not ('<h2' in html or '<h3' in html or '<h4' in html):
            return html
        
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Process h2, h3, h4 headings (matching python-markdown's toc_depth)
            for level in [2, 3, 4]:
                for heading in soup.find_all(f'h{level}'):
                    # Skip if heading already has an ID
                    if heading.get('id'):
                        continue
                    
                    # Get heading text and create slug
                    title = heading.get_text().strip()
                    if not title:
                        continue
                    
                    slug = self._slugify(title)
                    
                    # Add ID attribute
                    heading['id'] = slug
                    
                    # Create headerlink anchor (¶ symbol)
                    anchor = soup.new_tag(
                        'a',
                        href=f'#{slug}',
                        title='Permanent link',
                        **{'class': 'headerlink'}
                    )
                    anchor.string = '¶'
                    
                    # Append anchor to heading
                    heading.append(anchor)
            
            return str(soup)
        
        except ImportError:
            # Fallback if BeautifulSoup not available
            # (unlikely as it's a project dependency, but safe)
            return html
        
        except Exception as e:
            # On any parsing error, return original HTML
            import sys
            print(f"Warning: Error injecting heading anchors: {e}", file=sys.stderr)
            return html
    
    def _extract_toc(self, html: str) -> str:
        """
        Extract table of contents from HTML with anchored headings.
        
        Builds a nested list of links to heading anchors.
        Expects headings to already have IDs (from _inject_heading_anchors).
        
        Args:
            html: HTML content with heading IDs
            
        Returns:
            TOC as HTML (div.toc > ul > li > a structure)
        """
        if not html or not ('<h2' in html or '<h3' in html or '<h4' in html):
            return ''
        
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html, 'html.parser')
            toc_items = []
            
            # Extract h2-h4 headings with IDs
            for level in [2, 3, 4]:
                for heading in soup.find_all(f'h{level}'):
                    heading_id = heading.get('id')
                    if not heading_id:
                        continue
                    
                    # Get heading text (strip the ¶ symbol)
                    title = heading.get_text().replace('¶', '').strip()
                    if not title:
                        continue
                    
                    # Build indented list item
                    indent = '  ' * (level - 2)
                    toc_items.append(
                        f'{indent}<li><a href="#{heading_id}">{title}</a></li>'
                    )
            
            if toc_items:
                toc_html = (
                    '<div class="toc">\n'
                    '<ul>\n'
                    + '\n'.join(toc_items) + '\n'
                    '</ul>\n'
                    '</div>'
                )
                return toc_html
            
            return ''
        
        except ImportError:
            # Fallback: return empty TOC if BeautifulSoup not available
            return ''
        
        except Exception as e:
            # On any parsing error, return empty TOC
            import sys
            print(f"Warning: Error extracting TOC: {e}", file=sys.stderr)
            return ''
    
    def _slugify(self, text: str) -> str:
        """
        Convert text to a URL-friendly slug.
        Matches python-markdown's default slugify behavior.
        
        Args:
            text: Text to slugify
            
        Returns:
            Slugified text
        """
        # Convert to lowercase
        text = text.lower()
        # Replace spaces and special chars with hyphens
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text.strip('-')


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

