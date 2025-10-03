"""
Rendering Pipeline - Orchestrates the parsing, AST building, templating, and output rendering.
"""

import threading
from pathlib import Path
from typing import Any

from bengal.core.page import Page
from bengal.rendering.parser import MarkdownParser
from bengal.rendering.template_engine import TemplateEngine
from bengal.rendering.renderer import Renderer


# Thread-local storage for parser instances (reuse parsers per thread)
_thread_local = threading.local()


def _get_thread_parser() -> MarkdownParser:
    """
    Get or create a MarkdownParser instance for the current thread.
    
    This avoids the overhead of creating a new parser for every page,
    while maintaining thread-safety by using thread-local storage.
    
    Returns:
        MarkdownParser instance for this thread
    """
    if not hasattr(_thread_local, 'parser'):
        _thread_local.parser = MarkdownParser()
    return _thread_local.parser


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
        # Use thread-local parser to avoid re-initialization overhead
        self.parser = _get_thread_parser()
        self.dependency_tracker = dependency_tracker
        self.quiet = quiet
        self.build_stats = build_stats
        self.template_engine = TemplateEngine(site)
        if self.dependency_tracker:
            self.template_engine._dependency_tracker = self.dependency_tracker
        self.renderer = Renderer(self.template_engine)
    
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
        
        # Stage 1: Pre-process content through Jinja2 if enabled
        # This allows using {{ page.metadata.xxx }} directly in markdown content
        content = self._preprocess_content(page)
        
        # Stage 2: Parse content with TOC extraction
        parsed_content, toc = self.parser.parse_with_toc(content, page.metadata)
        page.parsed_ast = parsed_content
        page.toc = toc
        page.toc_items = self._extract_toc_structure(toc)
        
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
        # Ensure parent directory exists
        page.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write rendered HTML
        with open(page.output_path, 'w', encoding='utf-8') as f:
            f.write(page.rendered_html)
        
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
    
    def _extract_toc_structure(self, toc_html: str) -> list:
        """
        Parse TOC HTML into structured data for custom rendering.
        
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
    
    def _preprocess_content(self, page: Page) -> str:
        """
        Pre-process page content through Jinja2 to allow variable substitution.
        
        This allows technical writers to use {{ page.metadata.xxx }} directly
        in their markdown content, not just in templates.
        
        Args:
            page: Page to pre-process
            
        Returns:
            Content with Jinja2 variables rendered
            
        Example:
            # In markdown:
            Today we're talking about {{ page.metadata.product_name }} 
            version {{ page.metadata.version }}.
        """
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

