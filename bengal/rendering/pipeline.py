"""
Rendering Pipeline - Orchestrates the parsing, AST building, templating, and output rendering.
"""

import threading
from pathlib import Path
from typing import Any, Optional

from bengal.core.page import Page
from bengal.rendering.parser import create_markdown_parser, BaseMarkdownParser
from bengal.rendering.template_engine import TemplateEngine
from bengal.rendering.renderer import Renderer


# Thread-local storage for parser instances (reuse parsers per thread)
_thread_local = threading.local()

# Cache for created directories (reduces syscalls in parallel builds)
_created_dirs = set()
_created_dirs_lock = threading.Lock()


def _get_thread_parser(engine: Optional[str] = None) -> BaseMarkdownParser:
    """
    Get or create a MarkdownParser instance for the current thread.
    
    This avoids the overhead of creating a new parser for every page,
    while maintaining thread-safety by using thread-local storage.
    
    Args:
        engine: Parser engine to use ('python-markdown', 'mistune', or None for default)
    
    Returns:
        MarkdownParser instance for this thread
    """
    # Store parser per engine type
    cache_key = f'parser_{engine or "default"}'
    if not hasattr(_thread_local, cache_key):
        setattr(_thread_local, cache_key, create_markdown_parser(engine))
    return getattr(_thread_local, cache_key)


class RenderingPipeline:
    """
    Coordinates the entire rendering process for content.
    
    Pipeline stages:
    1. Parse source content (Markdown, etc.)
    2. Build Abstract Syntax Tree (AST)
    3. Apply templates
    4. Render output (HTML)
    5. Write to output directory
    """
    
    def __init__(self, site: Any, dependency_tracker: Any = None, quiet: bool = False, build_stats: Any = None) -> None:
        """
        Initialize the rendering pipeline.
        
        Args:
            site: Site instance
            dependency_tracker: Optional dependency tracker for incremental builds
            quiet: If True, suppress per-page output
            build_stats: Optional BuildStats object to collect warnings
        """
        self.site = site
        # Get markdown engine from config (default: python-markdown)
        # Check both old location (markdown_engine) and new nested location (markdown.parser)
        markdown_engine = site.config.get('markdown_engine')
        if not markdown_engine:
            # Check nested markdown section
            markdown_config = site.config.get('markdown', {})
            markdown_engine = markdown_config.get('parser', 'python-markdown')
        # Use thread-local parser to avoid re-initialization overhead
        self.parser = _get_thread_parser(markdown_engine)
        
        # Enable cross-references if xref_index is available
        if hasattr(site, 'xref_index') and hasattr(self.parser, 'enable_cross_references'):
            self.parser.enable_cross_references(site.xref_index)
        
        self.dependency_tracker = dependency_tracker
        self.quiet = quiet
        self.build_stats = build_stats
        self.template_engine = TemplateEngine(site)
        if self.dependency_tracker:
            self.template_engine._dependency_tracker = self.dependency_tracker
        self.renderer = Renderer(self.template_engine, build_stats=build_stats)
    
    def process_page(self, page: Page) -> None:
        """
        Process a single page through the entire pipeline.
        
        Args:
            page: Page to process
        """
        # Track this page if we have a dependency tracker
        if self.dependency_tracker and not page.metadata.get('_generated'):
            self.dependency_tracker.start_page(page.source_path)
        
        # Stage 0: Determine output path early so page.url works correctly
        if not page.output_path:
            page.output_path = self._determine_output_path(page)
        
        # Stage 1 & 2: Parse content with variable substitution
        # 
        # ARCHITECTURE: Clean separation of concerns
        # - Mistune parser: Handles {{ vars }} via VariableSubstitutionPlugin
        # - Templates: Handle {% if %}, {% for %}, complex logic
        # - Code blocks: Naturally stay literal (AST-level operation)
        #
        # Pages can disable preprocessing by setting `preprocess: false` in frontmatter.
        # This is useful for documentation pages that show template syntax examples.
        #
        if hasattr(self.parser, 'parse_with_toc_and_context'):
            # Mistune with VariableSubstitutionPlugin (recommended)
            # Check if preprocessing is disabled
            if page.metadata.get('preprocess') is False:
                # Parse without variable substitution (for docs showing template syntax)
                parsed_content, toc = self.parser.parse_with_toc(
                    page.content,
                    page.metadata
                )
            else:
                # Single-pass parsing with variable substitution - fast and simple!
                context = {
                    'page': page,
                    'site': self.site,
                    'config': self.site.config
                }
                parsed_content, toc = self.parser.parse_with_toc_and_context(
                    page.content,
                    page.metadata,
                    context
                )
        else:
            # FALLBACK: python-markdown (legacy)
            # Uses Jinja2 preprocessing - deprecated, use Mistune instead
            content = self._preprocess_content(page)
            parsed_content, toc = self.parser.parse_with_toc(content, page.metadata)
        
        page.parsed_ast = parsed_content
        page.toc = toc
        # Note: toc_items is now a lazy property on Page (only extracted when accessed)
        
        # Stage 3: Extract links for validation
        page.extract_links()
        
        # Stage 4: Render content to HTML
        html_content = self.renderer.render_content(parsed_content)
        
        # Stage 5: Apply template (with dependency tracking already set in __init__)
        page.rendered_html = self.renderer.render_page(page, html_content)
        
        # Stage 6: Write output
        self._write_output(page)
        
        # End page tracking
        if self.dependency_tracker and not page.metadata.get('_generated'):
            self.dependency_tracker.end_page()
    
    def _write_output(self, page: Page) -> None:
        """
        Write rendered page to output directory.
        
        Args:
            page: Page with rendered content
        """
        # Ensure parent directory exists (with caching to reduce syscalls)
        parent_dir = page.output_path.parent
        
        # Only create directory if not already done (thread-safe check)
        if parent_dir not in _created_dirs:
            with _created_dirs_lock:
                # Double-check inside lock to avoid race condition
                if parent_dir not in _created_dirs:
                    parent_dir.mkdir(parents=True, exist_ok=True)
                    _created_dirs.add(parent_dir)
        
        # Write rendered HTML atomically (crash-safe)
        from bengal.utils.atomic_write import atomic_write_text
        atomic_write_text(page.output_path, page.rendered_html, encoding='utf-8')
        
        # Only print in verbose mode
        if not self.quiet:
            print(f"  ✓ {page.output_path.relative_to(self.site.output_dir)}")
    
    def _determine_output_path(self, page: Page) -> Path:
        """
        Determine the output path for a page.
        
        Args:
            page: Page to determine path for
            
        Returns:
            Output path
        """
        # Get relative path from content directory
        content_dir = self.site.root_path / "content"
        
        try:
            rel_path = page.source_path.relative_to(content_dir)
        except ValueError:
            # If not under content_dir, use just the filename
            rel_path = Path(page.source_path.name)
        
        # Change extension to .html
        output_rel_path = rel_path.with_suffix('.html')
        
        # Handle index pages specially (index.md and _index.md → index.html)
        # Others can optionally use pretty URLs (about.md → about/index.html)
        if self.site.config.get("pretty_urls", True) and output_rel_path.stem not in ("index", "_index"):
            output_rel_path = output_rel_path.parent / output_rel_path.stem / "index.html"
        elif output_rel_path.stem == "_index":
            # _index.md should become index.html in the same directory
            output_rel_path = output_rel_path.parent / "index.html"
        
        return self.site.output_dir / output_rel_path
    
    def _preprocess_content(self, page: Page) -> str:
        """
        Pre-process page content through Jinja2 to allow variable substitution.
        
        This allows technical writers to use {{ page.metadata.xxx }} directly
        in their markdown content, not just in templates.
        
        Pages can disable preprocessing by setting `preprocess: false` in frontmatter.
        This is useful for documentation pages that show Jinja2 syntax examples.
        
        Args:
            page: Page to pre-process
            
        Returns:
            Content with Jinja2 variables rendered
            
        Example:
            # In markdown:
            Today we're talking about {{ page.metadata.product_name }} 
            version {{ page.metadata.version }}.
        """
        # Skip preprocessing if disabled in frontmatter
        if page.metadata.get('preprocess') is False:
            return page.content
        
        from jinja2 import Template, TemplateSyntaxError
        
        try:
            # Create a Jinja2 template from the content
            template = Template(page.content)
            
            # Render with page and site context
            rendered_content = template.render(
                page=page,
                site=self.site,
                config=self.site.config
            )
            
            return rendered_content
            
        except TemplateSyntaxError as e:
            # If there's a syntax error, warn but continue with original content
            if self.build_stats:
                self.build_stats.add_warning(str(page.source_path), str(e), 'jinja2')
            elif not self.quiet:
                print(f"  ⚠️  Jinja2 syntax error in {page.source_path}: {e}")
            return page.content
        except Exception as e:
            # For any other error, warn but continue
            if self.build_stats:
                self.build_stats.add_warning(str(page.source_path), str(e), 'preprocessing')
            elif not self.quiet:
                print(f"  ⚠️  Error pre-processing {page.source_path}: {e}")
            return page.content


def extract_toc_structure(toc_html: str) -> list:
    """
    Parse TOC HTML into structured data for custom rendering.
    
    This is a standalone function so it can be called from Page.toc_items
    property for lazy evaluation.
    
    Args:
        toc_html: HTML table of contents
        
    Returns:
        List of TOC items with id, title, and level
    """
    if not toc_html:
        return []
    
    from html.parser import HTMLParser
    
    class TOCParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.items = []
            self.current_item = None
            self.depth = 0
        
        def handle_starttag(self, tag, attrs):
            if tag == 'ul':
                self.depth += 1
            elif tag == 'a':
                attrs_dict = dict(attrs)
                self.current_item = {
                    'id': attrs_dict.get('href', '').lstrip('#'),
                    'title': '',
                    'level': self.depth
                }
        
        def handle_data(self, data):
            if self.current_item is not None:
                self.current_item['title'] += data.strip()
        
        def handle_endtag(self, tag):
            if tag == 'ul':
                self.depth -= 1
            elif tag == 'a' and self.current_item:
                if self.current_item['title']:  # Only add if has content
                    self.items.append(self.current_item)
                self.current_item = None
    
    try:
        parser = TOCParser()
        parser.feed(toc_html)
        return parser.items
    except Exception:
        # If parsing fails, return empty list
        return []

