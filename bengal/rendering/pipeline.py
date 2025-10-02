"""
Rendering Pipeline - Orchestrates the parsing, AST building, templating, and output rendering.
"""

from pathlib import Path
from typing import Any

from bengal.core.page import Page
from bengal.rendering.parser import MarkdownParser
from bengal.rendering.template_engine import TemplateEngine
from bengal.rendering.renderer import Renderer


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
    
    def __init__(self, site: Any) -> None:
        """
        Initialize the rendering pipeline.
        
        Args:
            site: Site instance
        """
        self.site = site
        self.parser = MarkdownParser()
        self.template_engine = TemplateEngine(site)
        self.renderer = Renderer(self.template_engine)
    
    def process_page(self, page: Page) -> None:
        """
        Process a single page through the entire pipeline.
        
        Args:
            page: Page to process
        """
        # Stage 1: Parse content
        parsed_content = self.parser.parse(page.content, page.metadata)
        page.parsed_ast = parsed_content
        
        # Stage 2: Extract links for validation
        page.extract_links()
        
        # Stage 3: Render content to HTML
        html_content = self.renderer.render_content(parsed_content)
        
        # Stage 4: Apply template
        page.rendered_html = self.renderer.render_page(page, html_content)
        
        # Stage 5: Write output
        self._write_output(page)
    
    def _write_output(self, page: Page) -> None:
        """
        Write rendered page to output directory.
        
        Args:
            page: Page with rendered content
        """
        # Determine output path
        if not page.output_path:
            output_path = self._determine_output_path(page)
            page.output_path = output_path
        
        # Ensure parent directory exists
        page.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write rendered HTML
        with open(page.output_path, 'w', encoding='utf-8') as f:
            f.write(page.rendered_html)
        
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
        
        # Handle index pages specially (index.md → index.html)
        # Others can optionally use pretty URLs (about.md → about/index.html)
        if self.site.config.get("pretty_urls", True) and output_rel_path.stem != "index":
            output_rel_path = output_rel_path.parent / output_rel_path.stem / "index.html"
        
        return self.site.output_dir / output_rel_path

